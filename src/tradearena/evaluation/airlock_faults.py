"""E1 fault-injection harness for the Airlock live-readiness control plane.

Airlock fault evaluation (results under ``docs/results/live_readiness_e1/``). The evaluated object is the *deterministic control
plane*, not a model: this module performs **zero LLM calls and zero network
I/O**. It takes one fully valid, reconciled weekly session bundle as a template
and emits single-defect faulted variants (mutation-testing discipline, so the
first-intercepting layer is unambiguous), then pushes each variant through the
five validation layers in deployment order and records where it is caught, or
records an *escape* if the sealed final gate passes it.

Six fault families (aligned with the fault-family table and
the E1 experiment plan):

- ``F1`` identifier pollution   whitespace / homoglyph / case / duplicate ids.
- ``F2`` capability overreach   order type, symbol, TIF, or mode absent from the
                                capability manifest; live flags on a paper adapter.
- ``F3`` approval bypass/replay expired approval, hash naming a different handoff,
                                post-approval handoff edit, replay of a stale approval.
- ``F4`` response mismatch      unknown ``client_order_id``, changed fill quantity,
                                dropped order, self-inconsistent reconciliation counts.
- ``F5`` clock/timestamp faults timezone-naive stamps, expiry before issuance,
                                ``--now`` disagreeing with the recorded review time.
- ``F6`` runbook violations     shell-chained or competing final-gate commands,
                                drill scope missing traded symbols.

An auxiliary family ``F7`` covers append-only journal hash-chain attacks
(rewrite / delete-row / reorder); the journal is not one of the six headline
columns of the interception matrix but the guard (``verify_journal_chain``) is real and
worth exercising, so it is reported separately.

The five interception layers (deployment order; a variant is attributed to the
first that rejects it):

1. ``schema_validation``          closed-world JSON Schema (Draft 2020-12).
2. ``single_artifact_validator``  the five in-code per-artifact validators.
3. ``approval_hash_binding``      canonical handoff hash + approval request
                                  binding (expiry, scope, hash) + response hash.
4. ``cross_artifact_preflight``   the deployed sealed final gate over the bundle.
5. ``orchestrator_revalidation``  the live execute-time state machine (replay,
                                  out-of-order execution) and the journal chain.

Each variant of the two catalog sources is tracked:

- **In-catalog (directed):** one variant per known guard, measuring *coverage*.
- **Out-of-catalog (fuzz):** generic mutation operators drawn independently of
  the guard list (deletion, type replacement, cross-artifact field splice,
  boundary numerics, unknown fields, free-text tamper). This is where escapes
  are found and is the primary mitigation against evaluating the system on
  questions it wrote itself.
"""

from __future__ import annotations

import copy
import json
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from tradearena.evaluation.statistics import wilson_interval
from tradearena.tools.broker_capability import validate_broker_adapter_capability
from tradearena.tools.broker_export import (
    BrokerAdapterContractError,
    broker_handoff_artifact_hash,
    validate_broker_approval_artifact,
    validate_broker_approval_request_binding,
    validate_broker_handoff_artifact,
    validate_broker_response_artifact,
)
from tradearena.tools.live_readiness import validate_live_readiness_preflight_bundle_file
from tradearena.tools.live_session import (
    APPROVAL_FILENAME,
    BUNDLE_FILENAME,
    CAPABILITY_FILENAME,
    JOURNAL_FILENAME,
    RESPONSE_FILENAME,
    RUNBOOK_FILENAME,
    STATE_FILENAME,
    LiveSessionConfig,
    LiveSessionError,
    approve_session,
    execute_session,
    propose_session,
    reconcile_session,
    verify_journal_chain,
)
from tradearena.tools.operator_runbook import validate_operator_runbook_artifact

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "schemas"

# Fixed deterministic session timestamps (mirror scripts/run_live_readiness_e2.py
# so the template is reproducible and the sealed gate is unexpired at CHECK_NOW).
PROPOSE_NOW = "2026-07-02T09:00:00Z"
APPROVE_NOW = "2026-07-02T09:05:00Z"
EXECUTE_NOW = "2026-07-02T09:06:00Z"
RECONCILE_NOW = "2026-07-02T09:07:00Z"
CHECK_NOW = RECONCILE_NOW

# Three pre-registered forward-window symbols, all closing up week-over-week so
# the rule-based decision source emits one limit order per symbol (3 orders).
FIXTURE_PRICES: dict[str, dict[str, float]] = {
    "BTC-USD": {"close": 109250.5, "prev_close": 108000.0},
    "BTC=F": {"close": 111000.0, "prev_close": 110500.0},
    "GSPC": {"close": 6150.25, "prev_close": 6100.0},
}
FIXTURE_SYMBOLS = ("BTC-USD", "BTC=F", "GSPC")

# Template variants for the E6 cross-template arm. Variant "a" is the original
# template above (bytes unchanged; the E1 results depend on it). Variant "b" is
# a different market week -- same symbols, same all-rising direction (the tier
# constructors' invariants: every order a buy, three orders, dry-run adapter),
# but different price levels, session id, and timestamps, so every quantity,
# notional, hash, and timestamp the monitor reads differs from variant "a".
TEMPLATE_VARIANTS: dict[str, dict[str, object]] = {
    "a": {
        "session_id": "e1tpl",
        "prices": FIXTURE_PRICES,
        "times": (PROPOSE_NOW, APPROVE_NOW, EXECUTE_NOW, RECONCILE_NOW),
    },
    "b": {
        "session_id": "e6tplb",
        "prices": {
            "BTC-USD": {"close": 93410.75, "prev_close": 91200.0},
            "BTC=F": {"close": 95125.0, "prev_close": 94900.0},
            "GSPC": {"close": 5804.5, "prev_close": 5761.25},
        },
        "times": (
            "2026-07-09T14:30:00Z",
            "2026-07-09T14:41:00Z",
            "2026-07-09T14:43:00Z",
            "2026-07-09T14:45:00Z",
        ),
    },
}

# Interception layers, in deployment order.
LAYER_SCHEMA = "schema_validation"
LAYER_SINGLE = "single_artifact_validator"
LAYER_BINDING = "approval_hash_binding"
LAYER_PREFLIGHT = "cross_artifact_preflight"
LAYER_ORCHESTRATOR = "orchestrator_revalidation"
ESCAPE = "escape"

LAYERS: tuple[str, ...] = (
    LAYER_SCHEMA,
    LAYER_SINGLE,
    LAYER_BINDING,
    LAYER_PREFLIGHT,
    LAYER_ORCHESTRATOR,
)
LAYER_LABELS: dict[str, str] = {
    LAYER_SCHEMA: "Schema validation",
    LAYER_SINGLE: "Single-artifact validator",
    LAYER_BINDING: "Approval/hash binding",
    LAYER_PREFLIGHT: "Cross-artifact preflight",
    LAYER_ORCHESTRATOR: "Orchestrator re-validation",
}

# The six headline families of the interception matrix, plus the auxiliary journal family.
HEADLINE_FAMILIES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6")
AUX_FAMILIES: tuple[str, ...] = ("F7",)
FAMILY_LABELS: dict[str, str] = {
    "F1": "identifier pollution",
    "F2": "capability overreach",
    "F3": "approval bypass & replay",
    "F4": "response mismatch",
    "F5": "clock & timestamp",
    "F6": "runbook violations",
    "F7": "journal chain (aux)",
}

# Artifact logical name -> (on-disk filename, JSON-schema filename).
ARTIFACT_SCHEMAS: tuple[tuple[str, str], ...] = (
    ("capability", "broker_adapter_capability.schema.json"),
    ("handoff", "broker_handoff_artifact.schema.json"),
    ("approval", "broker_approval_artifact.schema.json"),
    ("response", "broker_response_artifact.schema.json"),
    ("runbook", "operator_runbook_artifact.schema.json"),
    ("bundle", "live_readiness_preflight.schema.json"),
)

# Homoglyphs and invisible characters that pass a ``^\S+$`` pattern but are not
# the ASCII character they impersonate. Spelled as escapes so the source itself
# stays ASCII (and lint-clean) while injecting genuine look-alikes at runtime.
_CYRILLIC_A = "\u0430"  # Cyrillic small a, look-alike of ASCII a
_GREEK_O = "\u03bf"  # Greek small omicron, look-alike of ASCII o
_ZERO_WIDTH_SPACE = "\u200b"  # zero-width space, still non-space to \S
_FULLWIDTH_B = "\uff22"  # fullwidth Latin B, look-alike of ASCII B

class E1HarnessError(RuntimeError):
    """Raised when a harness precondition fails (the clean template is invalid)."""


# ---------------------------------------------------------------------------
# Fault specification
# ---------------------------------------------------------------------------


@dataclass
class FaultSpec:
    """One single-defect fault variant.

    ``apply`` mutates a fresh deep copy of the clean artifact payload set in
    place (``kind`` in {"static", "journal"}). ``run`` drives a live orchestrator
    probe on its own session directories and returns ``(layer, detail)`` directly
    (``kind == "orchestrator"``).
    """

    family: str
    bucket: str  # "directed" | "fuzz"
    fault_id: str
    description: str
    expected_layer: str | None = None
    kind: str = "static"
    target_field: str | None = None
    apply: Callable[..., None] | None = None
    run: Callable[[Path], tuple[str, str]] | None = None


@dataclass
class InterceptResult:
    fault_id: str
    family: str
    bucket: str
    kind: str
    expected_layer: str | None
    target_field: str | None
    description: str
    first_layer: str  # a LAYERS entry or ESCAPE
    detail: str
    resolved_field: str | None = None

    @property
    def field_name(self) -> str:
        return self.resolved_field or self.target_field or ""


@dataclass
class CleanTemplate:
    payloads: dict[str, Any]
    journal_lines: list[str]
    session_dir: Path
    sessions_root: Path
    handoff_filename: str
    filenames: dict[str, str]

    def fresh_payloads(self) -> dict[str, Any]:
        return copy.deepcopy(self.payloads)


# ---------------------------------------------------------------------------
# Clean template construction (one reconciled dry-run session)
# ---------------------------------------------------------------------------


def build_clean_template(tmp_dir: Path, variant: str = "a") -> CleanTemplate:
    """Run one full deterministic session and load its six artifacts + journal.

    ``variant`` selects a :data:`TEMPLATE_VARIANTS` entry; the default "a" is
    byte-identical to the original template the E1 results were produced on.
    """

    spec = TEMPLATE_VARIANTS[variant]
    session_id = str(spec["session_id"])
    prices = spec["prices"]
    times = cast("tuple[str, str, str, str]", spec["times"])
    propose_now, approve_now, execute_now, reconcile_now = times

    session_root = tmp_dir / f"template_{variant}" if variant != "a" else tmp_dir / "template"
    if session_root.exists():
        _rmtree(session_root)
    prices_path = session_root / "weekly_prices.json"
    prices_path.parent.mkdir(parents=True, exist_ok=True)
    prices_path.write_text(json.dumps(prices, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    sessions_root = session_root / "sessions"
    config = LiveSessionConfig(
        session_id=session_id,
        root=sessions_root,
        symbols=FIXTURE_SYMBOLS,
        prices_file=prices_path,
    )
    proposed = propose_session(config, now=propose_now)
    if proposed.get("status") != "proposed":
        raise E1HarnessError(f"template session did not propose orders: {proposed}")
    approve_session(
        session_id,
        root=sessions_root,
        approved_by="e1-operator",
        reason="deterministic E1 fault-injection template",
        now=approve_now,
    )
    execute_session(session_id, root=sessions_root, now=execute_now)
    reconciled = reconcile_session(session_id, root=sessions_root, now=reconcile_now)
    if reconciled.get("preflight_ready") is not True:
        raise E1HarnessError(f"template session failed preflight: {reconciled}")

    session_dir = sessions_root / session_id
    state = json.loads((session_dir / STATE_FILENAME).read_text(encoding="utf-8"))
    handoff_filename = str(state["handoff_filename"])
    filenames = {
        "capability": CAPABILITY_FILENAME,
        "handoff": handoff_filename,
        "approval": APPROVAL_FILENAME,
        "response": RESPONSE_FILENAME,
        "runbook": RUNBOOK_FILENAME,
        "bundle": BUNDLE_FILENAME,
    }
    payloads = {name: json.loads((session_dir / fn).read_text(encoding="utf-8")) for name, fn in filenames.items()}
    journal_path = sessions_root / JOURNAL_FILENAME
    journal_lines = [line for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return CleanTemplate(
        payloads=payloads,
        journal_lines=journal_lines,
        session_dir=session_dir,
        sessions_root=sessions_root,
        handoff_filename=handoff_filename,
        filenames=filenames,
    )


# ---------------------------------------------------------------------------
# Layered interceptor
# ---------------------------------------------------------------------------


class LayeredInterceptor:
    """Push a variant through the five layers and report the first that rejects."""

    def __init__(self, template: CleanTemplate) -> None:
        self.template = template
        self._validators = {name: Draft202012Validator(_load_schema(schema)) for name, schema in ARTIFACT_SCHEMAS}
        self._journal_path = template.sessions_root / JOURNAL_FILENAME
        self._bundle_path = template.session_dir / template.filenames["bundle"]

    def run(self, spec: FaultSpec) -> InterceptResult:
        if spec.kind == "orchestrator":
            assert spec.run is not None
            layer, detail = spec.run(self.template.sessions_root.parent.parent / "orch")
            return self._result(spec, layer, detail)

        payloads = self.template.fresh_payloads()
        journal_lines = list(self.template.journal_lines)
        container: dict[str, Any] = dict(payloads)
        container["journal"] = journal_lines
        assert spec.apply is not None
        spec.apply(container)
        fuzz_meta = container.pop("__fuzz_meta__", None)
        journal_lines = container.pop("journal")
        payloads = container

        self._materialize(payloads, journal_lines)
        layer, detail = self._detect(payloads)
        result = self._result(spec, layer, detail)
        if isinstance(fuzz_meta, dict):
            result.resolved_field = str(fuzz_meta.get("field"))
        return result

    def _result(self, spec: FaultSpec, layer: str, detail: str) -> InterceptResult:
        return InterceptResult(
            fault_id=spec.fault_id,
            family=spec.family,
            bucket=spec.bucket,
            kind=spec.kind,
            expected_layer=spec.expected_layer,
            target_field=spec.target_field,
            description=spec.description,
            first_layer=layer,
            detail=detail[:240],
        )

    def restore_clean(self) -> None:
        self._materialize(self.template.payloads, self.template.journal_lines)

    # -- layer stages -------------------------------------------------------

    def _detect(self, payloads: dict[str, Any]) -> tuple[str, str]:
        for name, _schema in ARTIFACT_SCHEMAS:
            errors = [error.message for error in self._validators[name].iter_errors(payloads[name])]
            if errors:
                return LAYER_SCHEMA, f"{name}: {errors[0]}"

        single = (
            ("capability", validate_broker_adapter_capability(payloads["capability"])),
            ("handoff", validate_broker_handoff_artifact(payloads["handoff"])),
            ("approval", validate_broker_approval_artifact(payloads["approval"])),
            ("response", validate_broker_response_artifact(payloads["response"])),
            ("runbook", validate_operator_runbook_artifact(payloads["runbook"])),
        )
        for name, errors in single:
            if errors:
                return LAYER_SINGLE, f"{name}: {errors[0]}"

        binding_detail = self._binding_errors(payloads)
        if binding_detail is not None:
            return LAYER_BINDING, binding_detail

        _summary, preflight_errors = validate_live_readiness_preflight_bundle_file(self._bundle_path, now=CHECK_NOW)
        if preflight_errors:
            return LAYER_PREFLIGHT, preflight_errors[0]

        journal_errors = verify_journal_chain(self._journal_path)
        if journal_errors:
            return LAYER_ORCHESTRATOR, f"journal: {journal_errors[0]}"

        return ESCAPE, "passed all five layers and the sealed final gate"

    def _binding_errors(self, payloads: dict[str, Any]) -> str | None:
        try:
            handoff_hash = broker_handoff_artifact_hash(payloads["handoff"])
        except BrokerAdapterContractError as exc:  # pragma: no cover - handoff caught earlier
            return f"handoff hash refused: {exc}"
        errors = validate_broker_approval_request_binding(payloads["approval"], payloads["handoff"], now=CHECK_NOW)
        if errors:
            return f"approval binding: {errors[0]}"
        response_hash = payloads["response"].get("request_artifact_hash")
        if response_hash != handoff_hash:
            return f"response.request_artifact_hash {response_hash} does not match handoff hash {handoff_hash}"
        return None

    def _materialize(self, payloads: dict[str, Any], journal_lines: list[str]) -> None:
        for name, filename in self.template.filenames.items():
            path = self.template.session_dir / filename
            path.write_text(json.dumps(payloads[name], indent=2, sort_keys=True) + "\n", encoding="utf-8")
        text = ("\n".join(journal_lines) + "\n") if journal_lines else ""
        self._journal_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


def _first_order(handoff: dict[str, Any]) -> dict[str, Any]:
    return handoff["orders"][0]


def _first_response(response: dict[str, Any]) -> dict[str, Any]:
    return response["responses"][0]


def _pollute(value: str, op: str) -> str:
    return {
        "lead_space": " " + value,
        "trail_space": value + " ",
        "inner_space": value.replace("-", " ", 1) if "-" in value else value + " x",
        "tab": "\t" + value,
        "newline": value + "\n",
        "homoglyph_a": value.replace("a", _CYRILLIC_A, 1),
        "homoglyph_o": value.replace("o", _GREEK_O, 1),
        "zero_width": value + _ZERO_WIDTH_SPACE,
        "fullwidth": _FULLWIDTH_B + value,
        "upcase": value.upper() if value.lower() == value else value.lower(),
    }[op]


_POLLUTE_OPS = (
    "lead_space",
    "trail_space",
    "inner_space",
    "tab",
    "newline",
    "homoglyph_a",
    "homoglyph_o",
    "zero_width",
    "fullwidth",
    "upcase",
)


# ---------------------------------------------------------------------------
# Family generators (directed / in-catalog)
# ---------------------------------------------------------------------------


def _f1_identifier() -> list[FaultSpec]:
    specs: list[FaultSpec] = []
    # (artifact, path-description, setter) for string identifier fields.
    fields: list[tuple[str, str, Callable[[dict[str, Any], str], None]]] = [
        ("handoff", "orders[0].client_order_id", lambda c, v: _first_order(c["handoff"]).__setitem__("client_order_id", v)),
        ("handoff", "orders[0].symbol", lambda c, v: _first_order(c["handoff"]).__setitem__("symbol", v)),
        ("handoff", "adapter", lambda c, v: c["handoff"].__setitem__("adapter", v)),
        ("approval", "approved_by", lambda c, v: c["approval"].__setitem__("approved_by", v)),
        ("approval", "approval_id", lambda c, v: c["approval"].__setitem__("approval_id", v)),
        ("approval", "allowed_symbols[0]", lambda c, v: c["approval"]["allowed_symbols"].__setitem__(0, v)),
        ("response", "responses[0].client_order_id", lambda c, v: _first_response(c["response"]).__setitem__("client_order_id", v)),
        ("response", "responses[0].broker_order_id", lambda c, v: _first_response(c["response"]).__setitem__("broker_order_id", v)),
        ("capability", "adapter_id", lambda c, v: c["capability"].__setitem__("adapter_id", v)),
        ("runbook", "drill.rollback_owner", lambda c, v: c["runbook"]["incident_response_drill"].__setitem__("rollback_owner", v)),
    ]
    for artifact, path, setter in fields:
        base_value = _base_string(artifact, path)
        for op in _POLLUTE_OPS:
            polluted = _pollute(base_value, op)
            if polluted == base_value:
                continue
            specs.append(
                FaultSpec(
                    family="F1",
                    bucket="directed",
                    fault_id=f"F1-{artifact}-{path}-{op}",
                    description=f"{op} pollution of {artifact}.{path}",
                    expected_layer=LAYER_SCHEMA,
                    target_field=f"{artifact}.{path}",
                    apply=lambda c, setter=setter, polluted=polluted: setter(c, polluted),
                )
            )
    # Duplicate ids (a structural identifier collision, not a character trick).
    def _dup_client_order_id(container: dict[str, Any]) -> None:
        orders = container["handoff"]["orders"]
        orders[1]["client_order_id"] = orders[0]["client_order_id"]

    def _dup_broker_order_id(container: dict[str, Any]) -> None:
        rows = container["response"]["responses"]
        rows[1]["broker_order_id"] = rows[0]["broker_order_id"]

    specs.append(
        FaultSpec(
            family="F1",
            bucket="directed",
            fault_id="F1-handoff-duplicate-client-order-id",
            description="two handoff orders share one client_order_id",
            expected_layer=LAYER_SINGLE,
            target_field="handoff.orders[1].client_order_id",
            apply=_dup_client_order_id,
        )
    )
    specs.append(
        FaultSpec(
            family="F1",
            bucket="directed",
            fault_id="F1-response-duplicate-broker-order-id",
            description="two responses share one broker_order_id",
            expected_layer=LAYER_SINGLE,
            target_field="response.responses[1].broker_order_id",
            apply=_dup_broker_order_id,
        )
    )
    return specs


def _f2_capability() -> list[FaultSpec]:
    specs: list[FaultSpec] = []

    def narrow(field_name: str, value: Any, detail: str, expected: str = LAYER_PREFLIGHT) -> FaultSpec:
        return FaultSpec(
            family="F2",
            bucket="directed",
            fault_id=f"F2-capability-{field_name}-{_slug(detail)}",
            description=detail,
            expected_layer=expected,
            target_field=f"capability.{field_name}",
            apply=lambda c, field_name=field_name, value=value: c["capability"].__setitem__(field_name, value),
        )

    # Narrow the (non-hashed) capability manifest so the handoff overreaches it.
    specs.append(narrow("supported_order_types", ["market"], "limit order absent from supported_order_types"))
    specs.append(narrow("supported_time_in_force", ["fok"], "handoff time_in_force absent from capability"))
    specs.append(narrow("supported_time_in_force", ["ioc", "gtc"], "day TIF absent from capability list"))
    specs.append(narrow("account_modes", ["none"], "paper account_mode absent from capability"))
    specs.append(narrow("account_modes", ["none", "live"], "paper account_mode absent (none/live only)"))
    specs.append(narrow("supported_modes", ["offline_export", "paper_sandbox"], "dry_run mode absent from capability"))
    specs.append(narrow("supported_modes", ["offline_export"], "only offline_export declared"))
    specs.append(narrow("adapter_id", "some-other-adapter", "adapter_id disagrees with handoff.adapter"))
    specs.append(narrow("default_mode", "paper_sandbox", "default_mode disagrees with runbook default_mode"))
    # Live flags on a paper adapter (schema/semantic layer).
    specs.append(
        FaultSpec(
            family="F2",
            bucket="directed",
            fault_id="F2-handoff-live-submission-true",
            description="dry_run handoff sets live_submission true",
            expected_layer=LAYER_SCHEMA,
            target_field="handoff.live_submission",
            apply=lambda c: c["handoff"].__setitem__("live_submission", True),
        )
    )
    specs.append(
        FaultSpec(
            family="F2",
            bucket="directed",
            fault_id="F2-handoff-paper-only-false",
            description="dry_run handoff sets paper_only false",
            expected_layer=LAYER_SCHEMA,
            target_field="handoff.paper_only",
            apply=lambda c: c["handoff"].__setitem__("paper_only", False),
        )
    )
    specs.append(
        FaultSpec(
            family="F2",
            bucket="directed",
            fault_id="F2-capability-supports-live-submission",
            description="paper capability claims supports_live_submission without live-capable controls",
            expected_layer=LAYER_SINGLE,
            target_field="capability.supports_live_submission",
            apply=lambda c: c["capability"].__setitem__("supports_live_submission", True),
        )
    )
    specs.append(
        FaultSpec(
            family="F2",
            bucket="directed",
            fault_id="F2-capability-live-submission-default",
            description="capability sets live_submission_default true",
            expected_layer=LAYER_SCHEMA,
            target_field="capability.live_submission_default",
            apply=lambda c: c["capability"].__setitem__("live_submission_default", True),
        )
    )
    # Handoff overreaches (change hashed handoff fields -> caught at binding).
    for tif in ("gtc", "ioc", "fok", "opg", "cls"):
        specs.append(
            FaultSpec(
                family="F2",
                bucket="directed",
                fault_id=f"F2-handoff-tif-{tif}",
                description=f"handoff order time_in_force escalated to {tif}",
                expected_layer=LAYER_BINDING,
                target_field="handoff.orders[0].time_in_force",
                apply=lambda c, tif=tif: _first_order(c["handoff"]).__setitem__("time_in_force", tif),
            )
        )
    for symbol in ("XAU-USD", "ETH-USD", "AAPL", "TSLA", "NVDA"):
        specs.append(
            FaultSpec(
                family="F2",
                bucket="directed",
                fault_id=f"F2-handoff-symbol-{_slug(symbol)}",
                description=f"handoff injects out-of-scope symbol {symbol}",
                expected_layer=LAYER_BINDING,
                target_field="handoff.orders[0].symbol",
                apply=lambda c, symbol=symbol: _first_order(c["handoff"]).__setitem__("symbol", symbol),
            )
        )
    return specs


def _f3_approval() -> list[FaultSpec]:
    specs: list[FaultSpec] = []
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-approval-expired",
            description="approval expires_at precedes the review time",
            expected_layer=LAYER_BINDING,
            target_field="approval.expires_at",
            apply=lambda c: c["approval"].__setitem__("expires_at", "2026-07-02T09:06:30Z"),
        )
    )
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-approval-expires-before-approved",
            description="approval expires_at precedes approved_at",
            expected_layer=LAYER_SINGLE,
            target_field="approval.expires_at",
            apply=lambda c: c["approval"].__setitem__("expires_at", "2026-07-02T09:04:00Z"),
        )
    )
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-approval-hash-zeroed",
            description="approval request_artifact_hash names a different (all-zero) handoff",
            expected_layer=LAYER_BINDING,
            target_field="approval.request_artifact_hash",
            apply=lambda c: c["approval"].__setitem__("request_artifact_hash", "sha256:" + "0" * 64),
        )
    )
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-response-hash-zeroed",
            description="response request_artifact_hash names a different handoff",
            expected_layer=LAYER_BINDING,
            target_field="response.request_artifact_hash",
            apply=lambda c: c["response"].__setitem__("request_artifact_hash", "sha256:" + "1" * 64),
        )
    )
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-approval-status-revoked",
            description="approval_status is not 'approved'",
            expected_layer=LAYER_SCHEMA,
            target_field="approval.approval_status",
            apply=lambda c: c["approval"].__setitem__("approval_status", "revoked"),
        )
    )
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-approval-scope-drops-symbol",
            description="approval allowed_symbols omits a reviewed handoff symbol",
            expected_layer=LAYER_BINDING,
            target_field="approval.allowed_symbols",
            apply=lambda c: c["approval"].__setitem__("allowed_symbols", c["approval"]["allowed_symbols"][:1]),
        )
    )
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-approval-max-quantity-below-order",
            description="approval max_quantity below a reviewed order quantity",
            expected_layer=LAYER_BINDING,
            target_field="approval.max_quantity",
            apply=lambda c: c["approval"].__setitem__("max_quantity", 1e-06),
        )
    )
    specs.append(
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-approval-max-notional-below-order",
            description="approval max_notional below a reviewed order notional",
            expected_layer=LAYER_BINDING,
            target_field="approval.max_notional",
            apply=lambda c: c["approval"].__setitem__("max_notional", 1.0),
        )
    )
    # Post-approval edits to the hashed handoff (any change breaks the binding).
    handoff_edits: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("quantity-x10", lambda c: _first_order(c["handoff"]).__setitem__("quantity", _first_order(c["handoff"])["quantity"] * 10)),
        ("quantity-plus-epsilon", lambda c: _first_order(c["handoff"]).__setitem__("quantity", _first_order(c["handoff"])["quantity"] + 1e-06)),
        ("limit-price-bump", lambda c: _first_order(c["handoff"]).__setitem__("limit_price", _first_order(c["handoff"])["limit_price"] * 1.25)),
        ("side-flip", lambda c: _first_order(c["handoff"]).__setitem__("side", "sell")),
        ("reason-tamper", lambda c: _first_order(c["handoff"]).__setitem__("reason", "post-approval rewrite of the order rationale")),
        ("add-order", lambda c: c["handoff"]["orders"].append(copy.deepcopy(_first_order(c["handoff"])))),
    ]
    for name, edit in handoff_edits:
        specs.append(
            FaultSpec(
                family="F3",
                bucket="directed",
                fault_id=f"F3-handoff-postapproval-{name}",
                description=f"post-approval handoff edit ({name}) breaks the approval binding",
                expected_layer=LAYER_BINDING,
                target_field="handoff.orders[0]",
                apply=edit,
            )
        )
    return specs


def _f4_response() -> list[FaultSpec]:
    specs: list[FaultSpec] = []
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-unknown-client-order-id",
            description="response row references an unknown client_order_id",
            expected_layer=LAYER_PREFLIGHT,
            target_field="response.responses[0].client_order_id",
            apply=lambda c: _first_response(c["response"]).__setitem__("client_order_id", "ghost-order-9999"),
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-submitted-quantity-mismatch",
            description="response submitted_quantity disagrees with the reviewed handoff quantity",
            expected_layer=LAYER_PREFLIGHT,
            target_field="response.responses[0].submitted_quantity",
            apply=_f4_submitted_qty_mismatch,
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-fill-exceeds-submitted",
            description="fill_quantity exceeds submitted_quantity",
            expected_layer=LAYER_SINGLE,
            target_field="response.responses[0].fill_quantity",
            apply=lambda c: _first_response(c["response"]).__setitem__("fill_quantity", _first_response(c["response"])["submitted_quantity"] * 2),
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-dropped-order",
            description="a reviewed order has no response row and counts are stale",
            expected_layer=LAYER_SINGLE,
            target_field="response.responses",
            apply=lambda c: c["response"]["responses"].pop(),
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-dropped-order-recounted",
            description="dropped order with reconciliation.response_count decremented (linkage catch)",
            expected_layer=LAYER_PREFLIGHT,
            target_field="response.responses",
            apply=_f4_drop_order_recounted,
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-filled-count-inflated",
            description="reconciliation.filled_count disagrees with the response rows",
            expected_layer=LAYER_SINGLE,
            target_field="response.reconciliation.filled_count",
            apply=lambda c: c["response"]["reconciliation"].__setitem__("filled_count", c["response"]["reconciliation"]["filled_count"] + 3),
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-fill-ratio-faked",
            description="reconciliation.fill_ratio_mean does not recompute from rows",
            expected_layer=LAYER_SINGLE,
            target_field="response.reconciliation.fill_ratio_mean",
            apply=lambda c: c["response"]["reconciliation"].__setitem__("fill_ratio_mean", 0.5),
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-missing-count-faked",
            description="reconciliation.missing_response_count understates a dropped order",
            expected_layer=LAYER_SINGLE,
            target_field="response.reconciliation.missing_response_count",
            apply=lambda c: c["response"]["reconciliation"].__setitem__("missing_response_count", 5),
        )
    )
    specs.append(
        FaultSpec(
            family="F4",
            bucket="directed",
            fault_id="F4-response-account-mode-mismatch",
            description="a response row account_mode disagrees with the artifact",
            expected_layer=LAYER_SINGLE,
            target_field="response.responses[0].account_mode",
            apply=lambda c: _first_response(c["response"]).__setitem__("account_mode", "live"),
        )
    )
    # Status-invariant violations across the status machine.
    status_edits: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
        ("rejected-with-fill", LAYER_SINGLE, _f4_rejected_with_fill),
        ("filled-without-price", LAYER_SINGLE, lambda c: _first_response(c["response"]).__setitem__("fill_price", None)),
        ("filled-qty-not-equal", LAYER_SINGLE, lambda c: _first_response(c["response"]).__setitem__("fill_quantity", _first_response(c["response"])["submitted_quantity"] / 2)),
        ("accepted-with-fill", LAYER_SINGLE, _f4_accepted_with_fill),
        ("unknown-without-reason", LAYER_SINGLE, _f4_unknown_without_reason),
        ("negative-fees", LAYER_SCHEMA, lambda c: _first_response(c["response"]).__setitem__("fees", -1.0)),
        ("broker-before-submit", LAYER_SINGLE, _f4_broker_before_submit),
    ]
    for name, expected, edit in status_edits:
        specs.append(
            FaultSpec(
                family="F4",
                bucket="directed",
                fault_id=f"F4-response-{name}",
                description=f"response status invariant violated ({name})",
                expected_layer=expected,
                target_field="response.responses[0]",
                apply=edit,
            )
        )
    return specs


def _f4_submitted_qty_mismatch(container: dict[str, Any]) -> None:
    row = _first_response(container["response"])
    row["submitted_quantity"] = row["submitted_quantity"] + 5.0
    # keep the row self-consistent so the linkage layer, not the row validator, fires
    row["accepted_quantity"] = row["submitted_quantity"]
    row["fill_quantity"] = row["submitted_quantity"]


def _f4_drop_order_recounted(container: dict[str, Any]) -> None:
    response = container["response"]
    response["responses"].pop()
    recon = response["reconciliation"]
    recon["response_count"] = len(response["responses"])
    recon["filled_count"] = len(response["responses"])


def _f4_rejected_with_fill(container: dict[str, Any]) -> None:
    row = _first_response(container["response"])
    row["status"] = "rejected"
    row["rejection_reason"] = "insufficient buying power"


def _f4_accepted_with_fill(container: dict[str, Any]) -> None:
    row = _first_response(container["response"])
    row["status"] = "accepted"  # accepted rows must not report a fill


def _f4_unknown_without_reason(container: dict[str, Any]) -> None:
    row = _first_response(container["response"])
    row["status"] = "unknown"
    row["fill_quantity"] = None
    row["fill_price"] = None
    row["rejection_reason"] = None


def _f4_broker_before_submit(container: dict[str, Any]) -> None:
    row = _first_response(container["response"])
    row["broker_timestamp"] = "2026-07-02T08:59:00Z"  # before submitted_at


def _f5_clock() -> list[FaultSpec]:
    specs: list[FaultSpec] = []
    naive = "2026-07-02T09:05:00"
    bad_offset = "2026-07-02T09:05:00+0500"  # missing the colon the pattern requires
    nonsense = "yesterday"
    empty = ""

    timestamp_targets: list[tuple[str, str, str, Callable[[dict[str, Any], str], None]]] = [
        ("approval", "approved_at", LAYER_SCHEMA, lambda c, v: c["approval"].__setitem__("approved_at", v)),
        ("approval", "expires_at", LAYER_SCHEMA, lambda c, v: c["approval"].__setitem__("expires_at", v)),
        ("response", "responses[0].submitted_at", LAYER_SINGLE, lambda c, v: _first_response(c["response"]).__setitem__("submitted_at", v)),
        ("response", "responses[0].broker_timestamp", LAYER_SINGLE, lambda c, v: _first_response(c["response"]).__setitem__("broker_timestamp", v)),
    ]
    malformations = (("naive", naive), ("badoffset", bad_offset), ("nonsense", nonsense), ("empty", empty))
    for artifact, path, expected, setter in timestamp_targets:
        for tag, value in malformations:
            specs.append(
                FaultSpec(
                    family="F5",
                    bucket="directed",
                    fault_id=f"F5-{artifact}-{_slug(path)}-{tag}",
                    description=f"{artifact}.{path} timestamp is {tag}",
                    expected_layer=expected,
                    target_field=f"{artifact}.{path}",
                    apply=lambda c, setter=setter, value=value: setter(c, value),
                )
            )
    # Bundle review-time disagreement and runbook command-time binding.
    specs.append(
        FaultSpec(
            family="F5",
            bucket="directed",
            fault_id="F5-bundle-checked-at-drift",
            description="bundle approval_checked_at disagrees with validation --now",
            expected_layer=LAYER_PREFLIGHT,
            target_field="bundle.approval_checked_at",
            apply=lambda c: c["bundle"].__setitem__("approval_checked_at", "2026-07-02T09:08:00Z"),
        )
    )
    specs.append(
        FaultSpec(
            family="F5",
            bucket="directed",
            fault_id="F5-runbook-command-now-drift",
            description="runbook final-gate command --now disagrees with the review time",
            expected_layer=LAYER_PREFLIGHT,
            target_field="runbook.verification_commands",
            apply=_f5_runbook_now_drift,
        )
    )
    specs.append(
        FaultSpec(
            family="F5",
            bucket="directed",
            fault_id="F5-runbook-command-now-invalid",
            description="runbook final-gate command --now is not an ISO timestamp",
            expected_layer=LAYER_SINGLE,
            target_field="runbook.verification_commands",
            apply=_f5_runbook_now_invalid,
        )
    )
    specs.append(
        FaultSpec(
            family="F5",
            bucket="directed",
            fault_id="F5-approval-expiry-far-future-naive",
            description="approval expires_at is far-future but timezone-naive",
            expected_layer=LAYER_SCHEMA,
            target_field="approval.expires_at",
            apply=lambda c: c["approval"].__setitem__("expires_at", "2027-01-01T00:00:00"),
        )
    )
    return specs


def _f5_runbook_now_drift(container: dict[str, Any]) -> None:
    commands = container["runbook"]["verification_commands"]
    commands[0] = commands[0].replace(RECONCILE_NOW, "2026-07-02T10:00:00Z")


def _f5_runbook_now_invalid(container: dict[str, Any]) -> None:
    commands = container["runbook"]["verification_commands"]
    commands[0] = commands[0].replace(RECONCILE_NOW, "not-a-timestamp")


def _f6_runbook() -> list[FaultSpec]:
    specs: list[FaultSpec] = []

    def command_variant(fault_id: str, description: str, expected: str, mutate: Callable[..., None]) -> FaultSpec:
        return FaultSpec(
            family="F6",
            bucket="directed",
            fault_id=fault_id,
            description=description,
            expected_layer=expected,
            target_field="runbook.verification_commands",
            apply=mutate,
        )

    for tag, suffix in (("semicolon", "; rm -rf outputs"), ("ampersand", " & curl evil"), ("pipe", " | tee /tmp/x")):
        specs.append(
            command_variant(
                f"F6-command-shell-chaining-{tag}",
                f"final-gate command carries shell chaining ({tag})",
                LAYER_SINGLE,
                lambda c, suffix=suffix: c["runbook"]["verification_commands"].__setitem__(0, c["runbook"]["verification_commands"][0] + suffix),
            )
        )
    specs.append(
        command_variant(
            "F6-command-competing-gate",
            "two supported validate-live-readiness commands compete",
            LAYER_SINGLE,
            _f6_competing_command,
        )
    )
    specs.append(
        command_variant(
            "F6-command-unportable-bundle",
            "final-gate command names an absolute bundle path",
            LAYER_SINGLE,
            _f6_unportable_command,
        )
    )
    specs.append(
        command_variant(
            "F6-command-unsupported-prefix",
            "final-gate command uses an unsupported executable prefix",
            LAYER_SINGLE,
            _f6_unsupported_command,
        )
    )
    # Drill scope faults.
    specs.append(
        FaultSpec(
            family="F6",
            bucket="directed",
            fault_id="F6-drill-symbol-scope-missing",
            description="incident drill affected_symbols omits a traded symbol",
            expected_layer=LAYER_PREFLIGHT,
            target_field="runbook.incident_response_drill.affected_symbols",
            apply=lambda c: c["runbook"]["incident_response_drill"].__setitem__("affected_symbols", ["BTC-USD"]),
        )
    )
    specs.append(
        FaultSpec(
            family="F6",
            bucket="directed",
            fault_id="F6-drill-account-mode-mismatch",
            description="incident drill affected_account_mode does not cover the handoff",
            expected_layer=LAYER_PREFLIGHT,
            target_field="runbook.incident_response_drill.affected_account_mode",
            apply=lambda c: c["runbook"]["incident_response_drill"].__setitem__("affected_account_mode", "live"),
        )
    )
    specs.append(
        FaultSpec(
            family="F6",
            bucket="directed",
            fault_id="F6-default-mode-mismatch",
            description="runbook default_mode disagrees with the capability manifest",
            expected_layer=LAYER_PREFLIGHT,
            target_field="runbook.default_mode",
            apply=lambda c: c["runbook"].__setitem__("default_mode", "offline_export"),
        )
    )
    specs.append(
        FaultSpec(
            family="F6",
            bucket="directed",
            fault_id="F6-retention-path-escape",
            description="incident drill artifact_retention_path escapes the sanctioned root",
            expected_layer=LAYER_SINGLE,
            target_field="runbook.incident_response_drill.artifact_retention_path",
            apply=lambda c: c["runbook"]["incident_response_drill"].__setitem__("artifact_retention_path", "outputs/elsewhere/leak/"),
        )
    )
    specs.append(
        FaultSpec(
            family="F6",
            bucket="directed",
            fault_id="F6-rollback-owner-whitespace",
            description="incident drill rollback_owner contains whitespace",
            expected_layer=LAYER_SINGLE,
            target_field="runbook.incident_response_drill.rollback_owner",
            apply=lambda c: c["runbook"]["incident_response_drill"].__setitem__("rollback_owner", "on call"),
        )
    )
    specs.append(
        FaultSpec(
            family="F6",
            bucket="directed",
            fault_id="F6-live-submission-true",
            description="runbook advertises live_submission true",
            expected_layer=LAYER_SCHEMA,
            target_field="runbook.live_submission",
            apply=lambda c: c["runbook"].__setitem__("live_submission", True),
        )
    )
    for control in ("manual_approval_required", "kill_switch_required", "approval_expiry_required", "artifact_retention_required", "incident_owner_required"):
        specs.append(
            FaultSpec(
                family="F6",
                bucket="directed",
                fault_id=f"F6-control-off-{control}",
                description=f"runbook control {control} disabled",
                expected_layer=LAYER_SCHEMA,
                target_field=f"runbook.{control}",
                apply=lambda c, control=control: c["runbook"].__setitem__(control, False),
            )
        )
    for cid in ("mode-boundary", "approval-expiry", "kill-switch", "reconciliation", "rollback", "artifact-retention", "incident-owner"):
        specs.append(
            FaultSpec(
                family="F6",
                bucket="directed",
                fault_id=f"F6-checklist-drop-{cid}",
                description=f"runbook checklist drops the required '{cid}' control",
                expected_layer=LAYER_SINGLE,
                target_field="runbook.checklist",
                apply=lambda c, cid=cid: _drop_checklist(c, cid),
            )
        )
    return specs


def _f6_competing_command(container: dict[str, Any]) -> None:
    commands = container["runbook"]["verification_commands"]
    commands.append(commands[0].replace(RECONCILE_NOW, "2026-07-02T11:11:00Z"))


def _f6_unportable_command(container: dict[str, Any]) -> None:
    commands = container["runbook"]["verification_commands"]
    commands[0] = "python -m tradearena.cli validate-live-readiness /abs/preflight_bundle.json --now " + RECONCILE_NOW


def _f6_unsupported_command(container: dict[str, Any]) -> None:
    commands = container["runbook"]["verification_commands"]
    commands[0] = commands[0].replace("python -m tradearena.cli", "bash tools/run.sh")


def _drop_checklist(container: dict[str, Any], cid: str) -> None:
    checklist = container["runbook"]["checklist"]
    container["runbook"]["checklist"] = [item for item in checklist if item.get("id") != cid]


# ---------------------------------------------------------------------------
# Journal chain family (F7, auxiliary)
# ---------------------------------------------------------------------------


def _f7_journal() -> list[FaultSpec]:
    specs: list[FaultSpec] = []
    specs.append(
        FaultSpec(
            family="F7",
            bucket="directed",
            fault_id="F7-journal-rewrite-detail",
            description="rewrite a journal entry payload without recomputing its hash",
            expected_layer=LAYER_ORCHESTRATOR,
            target_field="journal",
            apply=_f7_rewrite_detail,
        )
    )
    specs.append(
        FaultSpec(
            family="F7",
            bucket="directed",
            fault_id="F7-journal-delete-row",
            description="delete a middle journal row and break the prev-hash chain",
            expected_layer=LAYER_ORCHESTRATOR,
            target_field="journal",
            apply=_f7_delete_row,
        )
    )
    specs.append(
        FaultSpec(
            family="F7",
            bucket="directed",
            fault_id="F7-journal-reorder",
            description="reorder two journal rows and break the prev-hash chain",
            expected_layer=LAYER_ORCHESTRATOR,
            target_field="journal",
            apply=_f7_reorder,
        )
    )
    specs.append(
        FaultSpec(
            family="F7",
            bucket="directed",
            fault_id="F7-journal-truncate-head",
            description="drop the genesis journal row so the chain no longer roots at null",
            expected_layer=LAYER_ORCHESTRATOR,
            target_field="journal",
            apply=lambda c: c["journal"].pop(0),
        )
    )
    specs.append(
        FaultSpec(
            family="F7",
            bucket="directed",
            fault_id="F7-journal-corrupt-json",
            description="corrupt a journal row into invalid JSON",
            expected_layer=LAYER_ORCHESTRATOR,
            target_field="journal",
            apply=lambda c: c["journal"].__setitem__(0, c["journal"][0][:-3] + "@@@"),
        )
    )
    return specs


def _f7_rewrite_detail(container: dict[str, Any]) -> None:
    lines = container["journal"]
    entry = json.loads(lines[0])
    if isinstance(entry.get("details"), dict):
        entry["details"]["order_count"] = 99
    lines[0] = json.dumps(entry, sort_keys=True, separators=(",", ":"))


def _f7_delete_row(container: dict[str, Any]) -> None:
    lines = container["journal"]
    if len(lines) > 2:
        lines.pop(1)


def _f7_reorder(container: dict[str, Any]) -> None:
    lines = container["journal"]
    if len(lines) > 2:
        lines[1], lines[2] = lines[2], lines[1]


# ---------------------------------------------------------------------------
# Orchestrator lifecycle family (live execute-time re-validation, attributed to F3)
# ---------------------------------------------------------------------------


def _orchestrator_faults() -> list[FaultSpec]:
    return [
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-orchestrator-replay-foreign-approval",
            description="a valid unexpired approval from another session is replayed into this one",
            expected_layer=LAYER_ORCHESTRATOR,
            kind="orchestrator",
            target_field="approval",
            run=_probe_replay_foreign_approval,
        ),
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-orchestrator-replay-expired-approval",
            description="a stale expired approval from another session is replayed into this one",
            expected_layer=LAYER_ORCHESTRATOR,
            kind="orchestrator",
            target_field="approval",
            run=_probe_replay_expired_approval,
        ),
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-orchestrator-execute-before-approve",
            description="execution is attempted on a proposed-but-unapproved session",
            expected_layer=LAYER_ORCHESTRATOR,
            kind="orchestrator",
            target_field="state",
            run=_probe_execute_before_approve,
        ),
        FaultSpec(
            family="F3",
            bucket="directed",
            fault_id="F3-orchestrator-execute-after-reject",
            description="execution is attempted on a rejected session",
            expected_layer=LAYER_ORCHESTRATOR,
            kind="orchestrator",
            target_field="state",
            run=_probe_execute_after_reject,
        ),
    ]


def _session_config(root: Path, session_id: str, prices: dict[str, dict[str, float]], **overrides: Any) -> LiveSessionConfig:
    prices_path = root.parent / f"{session_id}_prices.json"
    prices_path.parent.mkdir(parents=True, exist_ok=True)
    prices_path.write_text(json.dumps(prices, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return LiveSessionConfig(session_id=session_id, root=root, symbols=FIXTURE_SYMBOLS, prices_file=prices_path, **overrides)


def _probe_replay_foreign_approval(orch_root: Path) -> tuple[str, str]:
    base = orch_root / "replay_foreign"
    _rmtree(base)
    root = base / "sessions"
    propose_session(_session_config(root, "srcA", FIXTURE_PRICES), now=PROPOSE_NOW)
    approve_session("srcA", root=root, approved_by="op-a", reason="source approval", now=APPROVE_NOW)
    approval_a = (root / "srcA" / APPROVAL_FILENAME).read_text(encoding="utf-8")

    propose_session(_session_config(root, "dstB", FIXTURE_PRICES, per_symbol_notional=1500.0), now=PROPOSE_NOW)
    approve_session("dstB", root=root, approved_by="op-b", reason="dest approval", now=APPROVE_NOW)
    (root / "dstB" / APPROVAL_FILENAME).write_text(approval_a, encoding="utf-8")
    return _expect_execute_refusal(root, "dstB", EXECUTE_NOW, "replayed foreign approval")


def _probe_replay_expired_approval(orch_root: Path) -> tuple[str, str]:
    base = orch_root / "replay_expired"
    _rmtree(base)
    root = base / "sessions"
    propose_session(_session_config(root, "srcA", FIXTURE_PRICES), now=PROPOSE_NOW)
    approve_session("srcA", root=root, approved_by="op-a", reason="source approval", now=APPROVE_NOW, valid_minutes=1)
    approval_a = (root / "srcA" / APPROVAL_FILENAME).read_text(encoding="utf-8")

    propose_session(_session_config(root, "dstB", FIXTURE_PRICES, per_symbol_notional=1500.0), now=PROPOSE_NOW)
    approve_session("dstB", root=root, approved_by="op-b", reason="dest approval", now=APPROVE_NOW)
    (root / "dstB" / APPROVAL_FILENAME).write_text(approval_a, encoding="utf-8")
    return _expect_execute_refusal(root, "dstB", "2026-07-02T12:00:00Z", "replayed expired approval")


def _probe_execute_before_approve(orch_root: Path) -> tuple[str, str]:
    base = orch_root / "before_approve"
    _rmtree(base)
    root = base / "sessions"
    propose_session(_session_config(root, "solo", FIXTURE_PRICES), now=PROPOSE_NOW)
    return _expect_execute_refusal(root, "solo", EXECUTE_NOW, "execute before approve")


def _probe_execute_after_reject(orch_root: Path) -> tuple[str, str]:
    base = orch_root / "after_reject"
    _rmtree(base)
    root = base / "sessions"
    from tradearena.tools.live_session import reject_session

    propose_session(_session_config(root, "solo", FIXTURE_PRICES), now=PROPOSE_NOW)
    reject_session("solo", root=root, rejected_by="op-a", reason="volatility too high", now=APPROVE_NOW)
    return _expect_execute_refusal(root, "solo", EXECUTE_NOW, "execute after reject")


def _expect_execute_refusal(root: Path, session_id: str, now: str, label: str) -> tuple[str, str]:
    try:
        execute_session(session_id, root=root, now=now)
    except LiveSessionError as exc:
        return LAYER_ORCHESTRATOR, f"{label}: {exc}"
    return ESCAPE, f"{label}: orchestrator executed the tampered session"


# ---------------------------------------------------------------------------
# Out-of-catalog fuzzing (generic mutation operators, independent of the guards)
# ---------------------------------------------------------------------------

_FUZZ_ARTIFACT_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "F1": ("handoff", "approval", "response"),
    "F2": ("capability", "handoff"),
    "F3": ("approval", "handoff"),
    "F4": ("response",),
    "F5": ("approval", "response", "bundle"),
    "F6": ("runbook",),
    "F7": ("runbook", "capability"),
}

_BOUNDARY_NUMERICS: tuple[Any, ...] = (0, -0.0, -1, 1e308, "NaN", "Infinity")


def _fuzz_specs(family: str, count: int, rng: random.Random) -> list[FaultSpec]:
    artifacts = _FUZZ_ARTIFACT_BY_FAMILY.get(family, ("handoff",))
    ops = (
        "delete_field",
        "retype_field",
        "boundary_numeric",
        "unknown_field",
        "cross_splice",
        "nesting_abuse",
        "free_text_tamper",
    )
    specs: list[FaultSpec] = []
    for index in range(count):
        artifact = artifacts[rng.randrange(len(artifacts))]
        op = ops[rng.randrange(len(ops))]
        seed = rng.randrange(2**31)
        specs.append(
            FaultSpec(
                family=family,
                bucket="fuzz",
                fault_id=f"{family}-fuzz-{op}-{index:03d}",
                description=f"out-of-catalog {op} on {artifact}",
                expected_layer=None,
                target_field=f"{artifact}.<fuzz>",
                apply=lambda c, artifact=artifact, op=op, seed=seed: _apply_fuzz(c, artifact, op, seed),
            )
        )
    return specs


# Free-text / label fields present in the clean template that are neither hashed
# nor cross-checked; tampering them is a genuine (single-defect) mutation.
_FREE_TEXT_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("approval", "approval_reason", "approval.approval_reason"),
    ("capability", "adapter_name", "capability.adapter_name"),
    ("capability", "safety_note", "capability.safety_note"),
    ("runbook", "safety_note", "runbook.safety_note"),
    ("bundle", "safety_note", "bundle.safety_note"),
)


def _apply_fuzz(container: dict[str, Any], artifact: str, op: str, seed: int) -> None:
    rng = random.Random(seed)
    payload = container[artifact]
    keys = [key for key in payload if key != "schema"]
    if not keys:
        container["__fuzz_meta__"] = {"field": f"{artifact}.<empty>", "op": op}
        return
    key = keys[rng.randrange(len(keys))]
    resolved = f"{artifact}.{key}"
    if op == "delete_field":
        payload.pop(key, None)
    elif op == "retype_field":
        payload[key] = _retype(payload[key], rng)
    elif op == "boundary_numeric":
        target = _numeric_key(payload, rng)
        if target is not None:
            payload[target] = _BOUNDARY_NUMERICS[rng.randrange(len(_BOUNDARY_NUMERICS))]
            resolved = f"{artifact}.{target}"
        else:
            payload[key] = _BOUNDARY_NUMERICS[rng.randrange(len(_BOUNDARY_NUMERICS))]
    elif op == "unknown_field":
        injected = f"injected_{seed % 1000}"
        payload[injected] = "closed-world probe"
        resolved = f"{artifact}.{injected}"
    elif op == "cross_splice":
        other = container["approval"] if artifact != "approval" else container["handoff"]
        other_keys = [k for k in other if k != "schema"]
        if other_keys:
            source = other_keys[rng.randrange(len(other_keys))]
            new_value = copy.deepcopy(other[source])
            if new_value == payload.get(key):  # avoid a no-op splice
                payload[f"injected_{seed % 1000}"] = "closed-world probe"
                resolved = f"{artifact}.injected_{seed % 1000}"
            else:
                payload[key] = new_value
    elif op == "nesting_abuse":
        payload[key] = [[{"depth": [payload.get(key)]}]]
    elif op == "free_text_tamper":
        resolved = _tamper_free_text(container, rng)
    container["__fuzz_meta__"] = {"field": resolved, "op": op}


def _tamper_free_text(container: dict[str, Any], rng: random.Random) -> str:
    present = [(art, field_name, label) for art, field_name, label in _FREE_TEXT_TARGETS if field_name in container.get(art, {})]
    if not present:  # pragma: no cover - approval_reason is always present
        container["approval"][f"injected_{rng.randrange(1000)}"] = "closed-world probe"
        return "approval.<injected>"
    art, field_name, label = present[rng.randrange(len(present))]
    container[art][field_name] = "UNILATERALLY OVERRIDDEN by the decision process without human review"
    return label


def _retype(value: Any, rng: random.Random) -> Any:
    options = ["string-instead", 12345, True, None, ["as", "list"], {"as": "object"}]
    choice = options[rng.randrange(len(options))]
    if type(choice) is type(value):
        return options[(rng.randrange(len(options) - 1) + 1) % len(options)]
    return choice


def _numeric_key(payload: dict[str, Any], rng: random.Random) -> str | None:
    numeric = [key for key, value in payload.items() if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not numeric:
        return None
    return numeric[rng.randrange(len(numeric))]


# ---------------------------------------------------------------------------
# Selection, aggregation, and autopsy
# ---------------------------------------------------------------------------

_DIRECTED_GENERATORS: dict[str, Callable[[], list[FaultSpec]]] = {
    "F1": _f1_identifier,
    "F2": _f2_capability,
    "F3": lambda: _f3_approval() + _orchestrator_faults(),
    "F4": _f4_response,
    "F5": _f5_clock,
    "F6": _f6_runbook,
    "F7": _f7_journal,
}


def build_fault_catalog(*, variants_per_family: int, reserve_fuzz: int, seed: int) -> dict[str, list[FaultSpec]]:
    """Return an ordered fault catalog per family (directed first, then fuzz)."""

    rng = random.Random(seed)
    catalog: dict[str, list[FaultSpec]] = {}
    for family in HEADLINE_FAMILIES:
        directed = _DIRECTED_GENERATORS[family]()
        target_fuzz = max(reserve_fuzz, variants_per_family - len(directed))
        target_fuzz = min(target_fuzz, variants_per_family)
        keep_directed = variants_per_family - target_fuzz
        selected_directed = directed[:keep_directed]
        fuzz = _fuzz_specs(family, variants_per_family - len(selected_directed), random.Random(rng.randrange(2**31)))
        catalog[family] = selected_directed + fuzz
    # Auxiliary families (journal chain) are outside the six-column headline and
    # its >=50-per-family requirement; report only their focused directed faults.
    for family in AUX_FAMILIES:
        catalog[family] = _DIRECTED_GENERATORS[family]()
    return catalog


def run_intercept_matrix(
    template: CleanTemplate, catalog: dict[str, list[FaultSpec]]
) -> list[InterceptResult]:
    interceptor = LayeredInterceptor(template)
    # Sanity gate: the untouched template must pass every layer (i.e., "escape").
    baseline = interceptor.run(
        FaultSpec(family="F0", bucket="baseline", fault_id="baseline-clean", description="clean template", apply=lambda c: None)
    )
    if baseline.first_layer != ESCAPE:
        raise E1HarnessError(f"clean template was rejected at {baseline.first_layer}: {baseline.detail}")
    results: list[InterceptResult] = []
    for family in (*HEADLINE_FAMILIES, *AUX_FAMILIES):
        for spec in catalog[family]:
            results.append(interceptor.run(spec))
            interceptor.restore_clean()
    return results


def aggregate_matrix(results: list[InterceptResult]) -> dict[str, Any]:
    families = (*HEADLINE_FAMILIES, *AUX_FAMILIES)
    by_family: dict[str, list[InterceptResult]] = {family: [] for family in families}
    for result in results:
        if result.family in by_family:
            by_family[result.family].append(result)

    matrix: dict[str, Any] = {"families": {}, "layers": list(LAYERS)}
    for family in families:
        rows = by_family[family]
        total = len(rows)
        layer_counts = {layer: sum(1 for row in rows if row.first_layer == layer) for layer in LAYERS}
        escapes = [row for row in rows if row.first_layer == ESCAPE]
        intercepted = total - len(escapes)
        cells = {}
        for layer in LAYERS:
            point, low, high = wilson_interval(layer_counts[layer], total) if total else (0.0, 0.0, 0.0)
            cells[layer] = {
                "count": layer_counts[layer],
                "pct": round(100 * point, 2),
                "ci_low_pct": round(100 * low, 2),
                "ci_high_pct": round(100 * high, 2),
            }
        point, low, high = wilson_interval(intercepted, total) if total else (0.0, 0.0, 0.0)
        matrix["families"][family] = {
            "label": FAMILY_LABELS[family],
            "total": total,
            "directed": sum(1 for row in rows if row.bucket == "directed"),
            "fuzz": sum(1 for row in rows if row.bucket == "fuzz"),
            "cells": cells,
            "intercepted_count": intercepted,
            "intercepted_pct": round(100 * point, 2),
            "intercepted_ci_low_pct": round(100 * low, 2),
            "intercepted_ci_high_pct": round(100 * high, 2),
            "escape_count": len(escapes),
        }
    total_all = len(results)
    intercepted_all = sum(1 for row in results if row.first_layer != ESCAPE)
    point, low, high = wilson_interval(intercepted_all, total_all) if total_all else (0.0, 0.0, 0.0)
    matrix["overall"] = {
        "total": total_all,
        "intercepted_count": intercepted_all,
        "intercepted_pct": round(100 * point, 2),
        "intercepted_ci_low_pct": round(100 * low, 2),
        "intercepted_ci_high_pct": round(100 * high, 2),
        "escape_count": total_all - intercepted_all,
    }
    return matrix


_IDENTIFIER_SUFFIXES = ("approved_by", "approval_id", "adapter_id")
_IDENTITY_POLLUTION_OPS = ("homoglyph", "zero_width", "fullwidth", "upcase")


def classify_escape(result: InterceptResult) -> dict[str, str]:
    """Bin an escape into the three autopsy classes with a proposed diff."""

    field_name = result.field_name
    is_identity_pollution = any(op in result.fault_id for op in _IDENTITY_POLLUTION_OPS)
    if is_identity_pollution or field_name.endswith(_IDENTIFIER_SUFFIXES):
        return {
            "class": "a",
            "class_label": "schema-expressible but unchecked",
            "mechanism": f"{field_name} accepted a homoglyph/invisible/case-folded identifier that is self-asserted and not cross-checked",
            "proposed_hardening": "restrict the operator/identifier pattern to an ASCII allow-list and apply Unicode NFKC + confusable normalization",
        }
    if "reason" in field_name or "safety_note" in field_name or "adapter_name" in field_name:
        return {
            "class": "c",
            "class_label": "requires a human",
            "mechanism": f"{field_name} is free-text rationale/labeling; the artifact chain stays internally consistent",
            "proposed_hardening": "none at the artifact layer; this is the argument for the human gate (record in autopsy prose)",
        }
    if "env_vars" in field_name or "verification_commands" in field_name:
        return {
            "class": "a",
            "class_label": "schema-expressible but unchecked",
            "mechanism": f"{field_name} accepted a value no constraint currently rejects",
            "proposed_hardening": "add a closed-world pattern/enum or cross-artifact equality check for this field",
        }
    if "max_notional" in field_name or "max_quantity" in field_name or "boundary_numeric" in result.fault_id:
        return {
            "class": "a",
            "class_label": "schema-expressible but unchecked",
            "mechanism": f"{field_name} accepted a boundary numeric more permissive than intended",
            "proposed_hardening": "bound the field against the reviewed handoff (semantic cross-check) or a schema maximum",
        }
    return {
        "class": "b",
        "class_label": "requires semantic cross-artifact checking",
        "mechanism": f"{field_name} passed every single-artifact constraint; only a cross-artifact rule can catch it",
        "proposed_hardening": "extend the cross-artifact preflight with the missing linkage assertion",
    }


def build_autopsy(results: list[InterceptResult]) -> list[dict[str, Any]]:
    autopsy: list[dict[str, Any]] = []
    for result in results:
        if result.first_layer != ESCAPE:
            continue
        classification = classify_escape(result)
        autopsy.append(
            {
                "escape_id": result.fault_id,
                "family": result.family,
                "family_label": FAMILY_LABELS[result.family],
                "bucket": result.bucket,
                "target_field": result.field_name,
                "class": classification["class"],
                "class_label": classification["class_label"],
                "mechanism": classification["mechanism"],
                "proposed_hardening": classification["proposed_hardening"],
                "detail": result.detail,
            }
        )
    return autopsy


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


@dataclass
class E1Report:
    matrix: dict[str, Any]
    autopsy: list[dict[str, Any]]
    results: list[InterceptResult]
    config: dict[str, Any]


def run_e1(
    tmp_dir: Path,
    *,
    variants_per_family: int = 60,
    reserve_fuzz: int = 20,
    seed: int = 2027,
) -> E1Report:
    """Build the clean template, run the full fault matrix, and aggregate results."""

    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    template = build_clean_template(tmp_dir)
    catalog = build_fault_catalog(variants_per_family=variants_per_family, reserve_fuzz=reserve_fuzz, seed=seed)
    results = run_intercept_matrix(template, catalog)
    matrix = aggregate_matrix(results)
    autopsy = build_autopsy(results)
    config = {
        "variants_per_family": variants_per_family,
        "reserve_fuzz": reserve_fuzz,
        "seed": seed,
        "headline_families": list(HEADLINE_FAMILIES),
        "aux_families": list(AUX_FAMILIES),
        "layers": list(LAYERS),
        "check_now": CHECK_NOW,
        "total_variants": len(results),
    }
    return E1Report(matrix=matrix, autopsy=autopsy, results=results, config=config)


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def _load_schema(schema_filename: str) -> dict[str, Any]:
    if schema_filename not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[schema_filename] = json.loads((SCHEMA_DIR / schema_filename).read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[schema_filename]


_BASE_STRING_CACHE: dict[tuple[str, str], str] = {}


def _base_string(artifact: str, path: str) -> str:
    """Return a representative clean string for a pollution target field."""

    defaults = {
        ("handoff", "orders[0].client_order_id"): "ls-e1tpl-0001-btc-usd",
        ("handoff", "orders[0].symbol"): "BTC-USD",
        ("handoff", "adapter"): "dry-run-broker-adapter",
        ("approval", "approved_by"): "e1-operator",
        ("approval", "approval_id"): "e1tpl-approval-001",
        ("approval", "allowed_symbols[0]"): "BTC-USD",
        ("response", "responses[0].client_order_id"): "ls-e1tpl-0001-btc-usd",
        ("response", "responses[0].broker_order_id"): "simfill-0000000000000000",
        ("capability", "adapter_id"): "dry-run-broker-adapter",
        ("runbook", "drill.rollback_owner"): "operator",
    }
    return defaults[(artifact, path)]


def _slug(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in text).strip("-")[:40]


def _rmtree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


__all__ = [
    "CleanTemplate",
    "E1HarnessError",
    "E1Report",
    "FaultSpec",
    "HEADLINE_FAMILIES",
    "AUX_FAMILIES",
    "FAMILY_LABELS",
    "LAYERS",
    "LAYER_LABELS",
    "InterceptResult",
    "LayeredInterceptor",
    "aggregate_matrix",
    "build_autopsy",
    "build_clean_template",
    "build_fault_catalog",
    "classify_escape",
    "run_e1",
    "run_intercept_matrix",
]
