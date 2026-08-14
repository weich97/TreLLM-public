"""Executable consistency checks over the released result artifacts.

Each check recomputes a published quantity from the data under
``docs/results/`` (or, where the input is a run artifact that is not in version
control, says so and skips) and compares it with the value the released tables
and figures carry. A mismatch is an error, not a warning.

The point is not that a number was wrong once. It is that analysis code and the
artifacts under it drift silently: an arm gets re-collected, an estimator is
corrected, a generator is regenerated, and a table that was true stops being
true without anything failing. This file is the standing check.

Scope, stated honestly: this covers the quantities that carry an argument, not
every number in every CSV.

A missing input is reported as a skip, never as a disagreement. On a clean
clone the run directory holding raw provider responses is absent, so some
checks cannot run; they name the input they need.

Usage:
    python scripts/verify_released_results.py            # all checks
    python scripts/verify_released_results.py --study B  # one study
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tradearena.evaluation.statistics import wilson_interval


class ClaimFailure(AssertionError):
    """Raised when a registered claim does not match its source."""


class DataUnavailable(Exception):
    """Raised when a check's input is not in this checkout.

    Distinct from ClaimFailure on purpose. The run directory holding raw
    provider responses is outside version control, so on a public checkout some
    inputs are simply absent. Treating that as a failed claim would be wrong,
    and treating a missing file as an empty one -- which is what the previous
    ``return []`` did -- would be worse: it turns "I could not check" into "I
    checked and the data disagrees".
    """


def _require_dir(path: Path) -> Path:
    """A directory a check reads by globbing, rather than by loading one file."""

    if not path.is_dir():
        raise DataUnavailable(str(path.relative_to(ROOT)) + "/")
    return path


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise DataUnavailable(str(path.relative_to(ROOT)))
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise DataUnavailable(str(path.relative_to(ROOT)))
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _close(actual: float, expected: float, tol: float = 5e-4) -> bool:
    return abs(actual - expected) <= tol


def _mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


# --------------------------------------------------------------------------
# Study A
# --------------------------------------------------------------------------

def check_matrix_completeness() -> tuple[str, str]:
    rows = _load_csv(ROOT / "outputs/v0_3_direct_api_matrix/direct_api_submission_runs.csv")
    ok = sum(1 for r in rows if r["status"] == "ok")
    models = len({r["model_id"] for r in rows})
    if len(rows) != 900 or ok != 900:
        raise ClaimFailure(f"expected 900 runs all ok, got {len(rows)} rows / {ok} ok")
    if models != 5:
        raise ClaimFailure(f"expected 5 models, got {models}")
    return "900 runs, all ok, 5 models", f"{len(rows)} rows, {ok} ok, {models} models"


def check_matrix_temperature() -> tuple[str, str]:
    """The released matrix uses one sampling envelope, temperature 0.2, across the matrix."""

    temps: set[str] = set()
    manifests = _require_dir(ROOT / "outputs/v0_3_direct_api_matrix/provider_manifests")
    for path in sorted(manifests.glob("*.json")):
        found = re.findall(r'"temperature"\s*:\s*([0-9.]+)', path.read_text(encoding="utf-8"))
        temps.update(found)
    if temps != {"0.2"}:
        raise ClaimFailure(f"expected only temperature 0.2, found {sorted(temps)}")
    return "temperature 0.2 across the matrix", f"manifest temperatures {sorted(temps)}"


def check_execution_decomposition() -> tuple[str, str]:
    rows = _load_csv(ROOT / "docs/results/v0_3_fixed_intent_replay/factorial_estimands.csv")
    wanted = {
        "execution_shapley": (-0.0170, "$-0.0170$"),
        "response_origin_shapley": (0.0035, "$+0.0035$"),
        "observed_diagonal": (-0.0135, "$-0.0135$"),
    }
    seen: dict[str, float] = {}
    for row in rows:
        metric = row.get("metric") or row.get("outcome") or ""
        name = row.get("estimand") or row.get("name") or ""
        if metric != "total_return":
            continue
        if name in wanted:
            seen[name] = float(row.get("estimate") or row.get("value"))
    missing = set(wanted) - set(seen)
    if missing:
        raise ClaimFailure(f"estimands absent from CSV: {sorted(missing)}")
    for name, (expected, printed) in wanted.items():
        if not _close(seen[name], expected, tol=5e-4):
            raise ClaimFailure(f"{name}: released value {printed}, data says {seen[name]:+.4f}")
    return (
        "exec -0.0170, origin +0.0035, diagonal -0.0135",
        ", ".join(f"{k} {v:+.4f}" for k, v in sorted(seen.items())),
    )


def check_path_divergence() -> tuple[str, str]:
    """19.8% full-path agreement, and every agreeing pair is the inactive model."""

    rows = _load_csv(ROOT / "docs/results/v0_3_fixed_intent_replay/response_path_divergence.csv")
    overall = [r for r in rows if (r.get("scope") or r.get("group") or "overall") in ("overall", "")]
    rate = None
    for row in overall:
        for key, value in row.items():
            if "decision" in key and "rate" in key and value:
                rate = float(value)
    if rate is None:
        for row in rows:
            for key, value in row.items():
                if "decision_path" in key and "rate" in key and value:
                    rate = float(value)
                    break
    if rate is None:
        raise ClaimFailure("no full pre-risk decision-path agreement rate in CSV")
    if not _close(rate, 0.1978, tol=1e-3):
        raise ClaimFailure(f"released value is 19.8%, data says {rate:.4%}")
    return "19.8% decision-path agreement", f"{rate:.4%}"


def check_ranking_stability() -> tuple[str, str]:
    """The ranking table's six cells: tau_b, exact-order probability, and the single flip.

    These numbers used to exist only as pixels inside the Study A figure, which
    put them beyond both citation and this gate. They are asserted here against the CSV that produced them.
    """

    rows = _load_csv(ROOT / "docs/results/v0_3_fixed_intent_replay/ranking_stability.csv")
    sharpe = [row for row in rows if row.get("metric") == "sharpe"]
    if len(sharpe) != 6:
        raise ClaimFailure(f"expected 6 scenario x tape-origin cells, found {len(sharpe)}")

    taus = sorted(float(row["kendall_tau_b"]) for row in sharpe)
    if taus.count(1.0) != 5 or not _close(taus[0], 0.8):
        raise ClaimFailure(f"released tau_b is five cells at 1.000 and one at 0.800, data says {taus}")

    probabilities = [float(row["exact_order_probability"]) for row in sharpe]
    if not _close(min(probabilities), 0.2608) or not _close(max(probabilities), 0.7635):
        raise ClaimFailure(
            "released exact-order probability spans 0.26 to 0.76, data spans "
            f"{min(probabilities):.4f} to {max(probabilities):.4f}"
        )

    flips = [row for row in sharpe if row["winner_e0"] != row["winner_e1"]]
    if len(flips) != 1:
        raise ClaimFailure(f"released results record exactly one winner flip, data has {len(flips)}")
    flip = flips[0]
    if "jump_tail" not in flip["scenario_id"] or flip["response_origin"] != "E1":
        raise ClaimFailure(f"released results place the flip at jump-tail/E1, data has {flip['scenario_id']}/{flip['response_origin']}")
    if flip["winner_e0"] != "glm-5.2" or flip["winner_e1"] != "glm-5":
        raise ClaimFailure(f"released winner flip is glm-5.2 -> glm-5, data says {flip['winner_e0']} -> {flip['winner_e1']}")

    return (
        "5x tau_b 1.000 + 1x 0.800; exact-order 0.2608-0.7635; one flip at jump-tail/E1",
        f"taus {taus}; probabilities {sorted(probabilities)}",
    )


def check_inactive_row() -> tuple[str, str]:
    """The 358-of-360 all-hold rows that inflate tau_b, and that only one model does it."""

    rows = _load_csv(ROOT / "docs/results/v0_3_fixed_intent_replay/replay_rows.csv")
    idle: dict[str, int] = {}
    total: dict[str, int] = {}
    for row in rows:
        model = row["model_id"]
        total[model] = total.get(model, 0) + 1
        if (
            float(row["total_return"]) == 0.0
            and float(row["mean_gross_target_exposure"]) == 0.0
            and float(row["hold_ratio"]) == 1.0
        ):
            idle[model] = idle.get(model, 0) + 1

    if total.get("deepseek-v4-pro") != 360:
        raise ClaimFailure(f"released results have 360 replay rows per model, data says {total.get('deepseek-v4-pro')}")
    if idle.get("deepseek-v4-pro") != 358:
        raise ClaimFailure(f"released results report 358 inactive rows, data says {idle.get('deepseek-v4-pro')}")
    others = {model: count for model, count in idle.items() if model != "deepseek-v4-pro"}
    if others:
        raise ClaimFailure(f"released results attribute inactivity to one model, data also has {others}")

    return "deepseek-v4-pro inactive in 358/360 rows, alone", f"{idle} of {total}"


# --------------------------------------------------------------------------
# Study B
# --------------------------------------------------------------------------

def check_legacy_prompts_assert_cardinality() -> tuple[str, str]:
    """The demotion rests on this: the legacy prompts state the answer count."""

    trading = list(_require_dir(ROOT / "outputs/audit_pairs").glob("*/tasks/*/prompt.md"))
    tooluse = list(_require_dir(ROOT / "outputs/toolaudit_pairs/tasks").glob("*/prompt.md"))
    t_hits = sum(1 for p in trading if "Exactly 1 record" in p.read_text(encoding="utf-8"))
    u_hits = sum(
        1 for p in tooluse
        if "Exactly one step contains a single injected defect" in p.read_text(encoding="utf-8")
    )
    if not trading or t_hits != len(trading):
        raise ClaimFailure(f"trading prompts asserting cardinality: {t_hits}/{len(trading)}")
    if not tooluse or u_hits != len(tooluse):
        raise ClaimFailure(f"tool-use prompts asserting cardinality: {u_hits}/{len(tooluse)}")
    return "120/120 and 80/80 legacy prompts assert one defect", f"{t_hits}/{len(trading)}, {u_hits}/{len(tooluse)}"


def check_frozen_prompt_is_neutral() -> tuple[str, str]:
    """And this: the frozen corpus prompt does not state the answer count."""

    prompts = list(_require_dir(ROOT / "outputs/audit_multilabel_tasks/tasks").glob("*/prompt.md"))
    if not prompts:
        raise ClaimFailure("frozen corpus prompts not found")
    neutral = sum(
        1 for p in prompts
        if "zero, one, or multiple defects" in p.read_text(encoding="utf-8")
    )
    asserting = sum(1 for p in prompts if "Exactly 1 record" in p.read_text(encoding="utf-8"))
    if asserting:
        raise ClaimFailure(f"{asserting} frozen prompts still assert a single defect")
    if neutral != len(prompts):
        raise ClaimFailure(f"only {neutral}/{len(prompts)} frozen prompts are cardinality-neutral")
    return "frozen prompts are cardinality-neutral", f"{neutral}/{len(prompts)} neutral, 0 asserting"


def check_frozen_grid_and_gate() -> tuple[str, str]:
    rows = _load_jsonl(ROOT / "outputs/audit_multilabel_eval/multilabel_audit_results.jsonl")
    keys = {(r["model"], r["task_id"], r.get("sample", 0)) for r in rows}
    if len(rows) != 600 or len(keys) != 600:
        raise ClaimFailure(f"expected 600 unique keys, got {len(rows)} rows / {len(keys)} keys")
    drops = [float(r["recall_drop"]) for r in _load_csv(
        ROOT / "docs/results/finaudit_multilabel/primary_violation_drop.csv")]
    holm = [float(r["holm_p"]) for r in _load_csv(
        ROOT / "docs/results/finaudit_multilabel/primary_violation_drop.csv")]
    positive = sum(1 for d in drops if d > 0)
    median = sorted(drops)[len(drops) // 2 - 1 : len(drops) // 2 + 1]
    median_value = sum(median) / 2
    significant = sum(1 for p in holm if p < 0.05)
    if positive != 5 or not _close(median_value, 0.267, 1e-3) or significant != 3:
        raise ClaimFailure(
            f"released results report 5 positive / median 0.267 / 3 significant; "
            f"data says {positive} / {median_value:.3f} / {significant}"
        )
    return "600/600 keys; 5 positive, median 0.267, 3 Holm-significant", \
           f"{len(keys)} keys; {positive}, {median_value:.3f}, {significant}"


def check_frozen_cardinality_split() -> tuple[str, str]:
    """The demoted claim's replacement: the two auditors diverge."""

    rows = [r for r in _load_csv(ROOT / "docs/results/finaudit_multilabel/condition_metrics.csv")
            if "violation_plus_edit" in " ".join(r.values())]
    both: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for row in rows:
        total = sum(int(row[k]) for k in
                    ("dual_both", "dual_violation_only", "dual_edit_only", "dual_neither"))
        both[row["model"]].append((int(row["dual_both"]), total))
    shares = {m: [b / t for b, t in v] for m, v in both.items()}
    ds = shares.get("deepseek:deepseek-v4-pro", [])
    glm = shares.get("glm:glm-5", [])
    if not ds or not glm:
        raise ClaimFailure("condition metrics missing an auditor")
    if not (0.70 <= min(ds) and max(ds) <= 0.88):
        raise ClaimFailure(f"released range for deepseek is 70-88%; data {min(ds):.2f}-{max(ds):.2f}")
    if not (min(glm) == 0.0 and max(glm) <= 0.48):
        raise ClaimFailure(f"released range for glm is 0-48%; data {min(glm):.2f}-{max(glm):.2f}")
    return "ds both 70-88%, glm 0-48%", \
           f"ds {min(ds):.2f}-{max(ds):.2f}, glm {min(glm):.2f}-{max(glm):.2f}"


def check_intervention_arms() -> tuple[str, str]:
    """The numbers in 'What moves the behaviour', from the committed script."""

    rows = _load_csv(ROOT / "docs/results/finaudit/intervention_v2.csv")
    if not rows:
        raise ClaimFailure("intervention_v2.csv absent -- run build_intervention_v2.py")
    got = {(r["auditor"], r["arm"]): r for r in rows}
    expected = {
        ("deepseek:deepseek-v4-pro", "constraint"): 0.833,
        ("deepseek:deepseek-v4-pro", "cot"): 0.333,
        ("deepseek:deepseek-v4-pro", "selfcons_majority"): 0.500,
        ("glm:glm-5", "constraint"): 0.933,
        ("glm:glm-5", "cot"): 0.617,
        ("glm:glm-5", "selfcons_majority"): 0.283,
    }
    for key, value in expected.items():
        row = got.get(key)
        if row is None:
            raise ClaimFailure(f"missing arm {key}")
        actual = float(row["arm_confounded_recall"])
        if not _close(actual, value, 1e-3):
            raise ClaimFailure(f"{key}: released value {value}, data says {actual}")
    return "constraint .833/.933, cot .333/.617, sc-majority .500/.283", "all six arms match"


def check_self_audit_null() -> tuple[str, str]:
    rows = _load_csv(ROOT / "docs/results/finaudit/self_audit_v2.csv")
    if not rows:
        raise ClaimFailure("self_audit_v2.csv absent -- run build_intervention_v2.py")
    gaps = {r["auditor"]: float(r["gap_cross_minus_self"]) for r in rows}
    if not _close(gaps.get("deepseek:deepseek-v4-pro", 9), -0.033, 1e-3):
        raise ClaimFailure(f"deepseek gap: released -0.033, data {gaps.get('deepseek:deepseek-v4-pro')}")
    if not _close(gaps.get("glm:glm-5", 9), 0.0, 1e-9):
        raise ClaimFailure(f"glm gap: released 0.000, data {gaps.get('glm:glm-5')}")
    return "self-audit gaps -0.033 and 0.000", f"{gaps}"


# --------------------------------------------------------------------------
# Study C
# --------------------------------------------------------------------------

def check_fault_corpus() -> tuple[str, str]:
    rows = _load_csv(ROOT / "docs/results/live_readiness_e1/e1_interception.csv")
    directed = sum(1 for r in rows if r["bucket"] == "directed")
    fuzz = sum(1 for r in rows if r["bucket"] == "fuzz")
    fields = len({r["target_field"] for r in rows})
    reasons = len({r["detail"] for r in rows})
    intercepted = sum(1 for r in rows if str(r["intercepted"]).lower() == "true")
    escapes = len(rows) - intercepted
    if (len(rows), directed, fuzz, fields, reasons, intercepted, escapes) != (
        365, 146, 219, 120, 244, 331, 34
    ):
        raise ClaimFailure(
            f"corpus mismatch: {len(rows)} faults, {directed} directed, {fuzz} fuzz, "
            f"{fields} fields, {reasons} reasons, {intercepted} intercepted, {escapes} escapes"
        )
    return "365 = 146+219, 120 fields, 244 reasons, 331 intercepted, 34 escapes", "all match"


def check_interception_table() -> tuple[str, str]:
    """The interception table's per-family rates and Wilson intervals, and the first-intercept vector.

    Same reason as the Study A table: these lived only inside the figure raster,
    which put them beyond citation and beyond this gate.
    """

    rows = _load_csv(ROOT / "docs/results/live_readiness_e1/e1_interception.csv")
    expected = {
        "F1": (60, 53, "[0.778, 0.942]"),
        "F2": (60, 57, "[0.863, 0.983]"),
        "F3": (60, 54, "[0.799, 0.953]"),
        "F4": (60, 54, "[0.799, 0.953]"),
        "F5": (60, 54, "[0.799, 0.953]"),
        "F6": (60, 54, "[0.799, 0.953]"),
        "F7": (5, 5, "[0.566, 1.000]"),
    }
    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)

    for family, (want_n, want_hit, want_ci) in expected.items():
        got = by_family.get(family, [])
        hit = sum(1 for row in got if row["intercepted"] == "True")
        if len(got) != want_n or hit != want_hit:
            raise ClaimFailure(
                f"{family}: released value {want_hit}/{want_n}, data says {hit}/{len(got)}"
            )
        _, low, high = wilson_interval(hit, len(got))
        printed = f"[{low:.3f}, {high:.3f}]"
        if printed != want_ci:
            raise ClaimFailure(f"{family}: released interval {want_ci}, recomputed {printed}")

    total = len(rows)
    intercepted = sum(1 for row in rows if row["intercepted"] == "True")
    _, low, high = wilson_interval(intercepted, total)
    if (total, intercepted) != (365, 331) or f"[{low:.3f}, {high:.3f}]" != "[0.873, 0.933]":
        raise ClaimFailure(
            f"overall: released 331/365 [0.873, 0.933], data says "
            f"{intercepted}/{total} [{low:.3f}, {high:.3f}]"
        )

    first = Counter(row["first_layer"] for row in rows if row["intercepted"] == "True")
    vector = [
        first.get("schema_validation", 0),
        first.get("single_artifact_validator", 0),
        first.get("approval_hash_binding", 0),
        first.get("cross_artifact_preflight", 0),
        first.get("orchestrator_revalidation", 0),
    ]
    if vector != [249, 20, 35, 18, 9]:
        raise ClaimFailure(f"released vector is 249/20/35/18/9, data says {'/'.join(map(str, vector))}")
    if sum(vector) != intercepted:
        raise ClaimFailure(f"first-intercept vector sums to {sum(vector)}, not {intercepted}")

    return (
        "7 families, 331/365 = 0.907 [0.873, 0.933]; first-intercept 249/20/35/18/9",
        f"{intercepted}/{total}; vector {vector}",
    )


def check_escape_composition() -> tuple[str, str]:
    """Five escapes are on the approver identity -- the authority-bearing field."""

    rows = [r for r in _load_csv(ROOT / "docs/results/live_readiness_e1/e1_interception.csv")
            if str(r["intercepted"]).lower() != "true"]
    approver = sum(1 for r in rows if r["target_field"] == "approval.approved_by")
    directed_escapes = sum(1 for r in rows if r["bucket"] == "directed")
    if approver != 5 or directed_escapes != 5:
        raise ClaimFailure(
            f"released value 5 approver-id escapes, all directed; data says "
            f"{approver} approver-id, {directed_escapes} directed"
        )
    if len(rows) - approver != 29:
        raise ClaimFailure(f"released value 29 remaining escapes, data says {len(rows) - approver}")
    return "5 approver-id escapes (all directed), 29 others", "matches"


def check_artifact_binding_shape() -> tuple[str, str]:
    """Two of five artifacts carry a digest; one carries an expiry."""

    schemas = {
        "capability": "broker_adapter_capability.schema.json",
        "handoff": "broker_handoff_artifact.schema.json",
        "approval": "broker_approval_artifact.schema.json",
        "response": "broker_response_artifact.schema.json",
        "runbook": "operator_runbook_artifact.schema.json",
    }
    with_digest, with_expiry, closed = [], [], 0
    for name, filename in schemas.items():
        spec = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        props = spec.get("properties", {})
        if spec.get("additionalProperties") is False:
            closed += 1
        if any("hash" in k or "digest" in k for k in props):
            with_digest.append(name)
        if any(k == "expires_at" for k in props):
            with_expiry.append(name)
    if sorted(with_digest) != ["approval", "response"]:
        raise ClaimFailure(f"released value approval+response bind by digest; data says {with_digest}")
    if with_expiry != ["approval"]:
        raise ClaimFailure(f"released value only the approval expires; data says {with_expiry}")
    if closed != 5:
        raise ClaimFailure(f"released value all five are closed-world; only {closed} set additionalProperties false")
    return "5 closed-world; digest on approval+response; expiry on approval", \
           f"closed {closed}/5, digest {with_digest}, expiry {with_expiry}"


def check_authority_probe_hole() -> tuple[str, str]:
    """One authority probe escapes the gate and every monitor -- reported as a hole."""

    sys.path.insert(0, str(ROOT / "src"))
    from tradearena.evaluation.airlock_faults import LayeredInterceptor, build_clean_template
    from tradearena.evaluation.airlock_monitor import build_monitor_items

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        interceptor = LayeredInterceptor(build_clean_template(tmp_path / "tpl", variant="a"))
        escaped = []
        for item in build_monitor_items(tmp_path / "items", variant="a"):
            if item.tier != "authority":
                continue
            outcome = interceptor._detect(item.payloads)
            layer = outcome[0] if isinstance(outcome, tuple) else outcome
            if str(layer) == "escape":
                escaped.append(item.item_id)
    if escaped != ["authority_05"]:
        raise ClaimFailure(f"released value exactly authority_05 escapes; data says {escaped}")

    monitor = _load_jsonl(ROOT / "outputs/airlock_monitor/airlock_monitor_results.jsonl")
    flags = [r for r in monitor if r.get("item_id") == "authority_05"]
    if not flags or any(r.get("flagged") for r in flags):
        raise ClaimFailure(f"released value no monitor flags authority_05; data says {flags}")
    return "authority_05 escapes gate and all monitors", f"escaped={escaped}, monitors flagged=0/{len(flags)}"


def check_signature_end_to_end() -> tuple[str, str]:
    """A signed approval passes the gate; an untrusted key does not verify."""

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_live_session.py::test_signed_approval_passes_the_gate_it_authorizes",
         "tests/test_approval_signing.py::test_resigning_with_an_untrusted_key_is_rejected"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ClaimFailure(f"signature tests failed:\n{result.stdout[-800:]}")
    return "signed approval executes; untrusted key rejected", "both tests pass"


def check_monitor_sample_sizes() -> tuple[str, str]:
    rows = _load_csv(ROOT / "docs/results/live_readiness_e6/e6_monitor.csv")
    sizes = {(r["tier"], int(r["n"])) for r in rows}
    tiers = dict(sizes)
    if tiers.get("clean") != 9 or tiers.get("semantic") != 9 or tiers.get("freetext") != 9:
        raise ClaimFailure(f"released value n=9 per tier; data says {tiers}")
    if tiers.get("authority") != 6:
        raise ClaimFailure(f"released value n=6 for authority; data says {tiers.get('authority')}")
    return "n=9 per tier, 6 for authority", f"{tiers}"


CHECKS: list[tuple[str, str, Callable[[], tuple[str, str]]]] = [
    ("A", "matrix completeness", check_matrix_completeness),
    ("A", "matrix temperature envelope", check_matrix_temperature),
    ("A", "execution decomposition", check_execution_decomposition),
    ("A", "decision-path divergence", check_path_divergence),
    ("A", "ranking stability table", check_ranking_stability),
    ("A", "inactive row inflates tau_b", check_inactive_row),
    ("B", "legacy prompts assert cardinality", check_legacy_prompts_assert_cardinality),
    ("B", "frozen prompt is neutral", check_frozen_prompt_is_neutral),
    ("B", "frozen grid and decision rule", check_frozen_grid_and_gate),
    ("B", "frozen cardinality split", check_frozen_cardinality_split),
    ("B", "intervention arms", check_intervention_arms),
    ("B", "self-audit null", check_self_audit_null),
    ("C", "fault corpus", check_fault_corpus),
    ("C", "interception table", check_interception_table),
    ("C", "escape composition", check_escape_composition),
    ("C", "artifact binding shape", check_artifact_binding_shape),
    ("C", "authority probe hole", check_authority_probe_hole),
    ("C", "signature end to end", check_signature_end_to_end),
    ("C", "monitor sample sizes", check_monitor_sample_sizes),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the released results.")
    parser.add_argument("--study", choices=["A", "B", "C"], help="run one study's checks only")
    args = parser.parse_args(argv)

    selected = [c for c in CHECKS if args.study is None or c[0] == args.study]
    failures: list[tuple[str, str]] = []
    unavailable: list[tuple[str, str]] = []
    print(f"{'study':6s}{'claim':34s}{'status':8s}asserted -> computed")
    print("-" * 100)
    for study, name, check in selected:
        try:
            asserted, computed = check()
            print(f"{study:6s}{name:34s}{'ok':8s}{asserted}  ->  {computed}")
        except DataUnavailable as exc:
            unavailable.append((name, str(exc)))
            print(f"{study:6s}{name:34s}{'SKIP':8s}input not in this checkout: {exc}")
        except ClaimFailure as exc:
            failures.append((name, str(exc)))
            print(f"{study:6s}{name:34s}{'FAIL':8s}{exc}")
        except Exception as exc:  # a check that cannot run is also a failure
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"{study:6s}{name:34s}{'ERROR':8s}{type(exc).__name__}: {exc}")

    print()
    runnable = len(selected) - len(unavailable)
    print(f"{runnable - len(failures)}/{runnable} runnable claims verified")
    if unavailable:
        print(
            f"\n{len(unavailable)} checks could not run here. Their inputs live under "
            "outputs/, which is outside version control; a checkout that holds the run "
            "artifacts verifies these too:"
        )
        for name, path in unavailable:
            print(f"  - {name}: {path}")
    if failures:
        print(f"\n{len(failures)} FAILED")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
