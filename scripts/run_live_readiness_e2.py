"""E2: validation-latency microbenchmark for the live-readiness control plane.

Airlock live-readiness experiment E2 (latency); results under docs/results/live_readiness_e2/.
Measures per-layer wall-clock latency of the deterministic control plane with
``time.perf_counter_ns`` over repeated iterations, on one fixed synthetic
session fixture, and a full-chain scaling arm over the order count.

Layers (every one is deterministic local computation; zero LLM, zero network):

- ``schema_validation_*``          JSON Schema (Draft 2020-12) validation of one
                                   artifact, reloading the schema from disk per
                                   call exactly as the deployed validators do.
- ``single_artifact_validators``   the six per-artifact validators in code.
- ``risk_gate``                    the session risk gate over the proposal.
- ``hash_binding_checks``          canonical SHA-256 handoff hash + approval
                                   request-binding re-validation against disk.
- ``journal_chain_verify``         append-only journal hash-chain verification.
- ``cross_artifact_preflight``     the full preflight bundle final gate.
- ``step_propose/approve/execute/reconcile``  orchestrator steps, each on a
                                   fresh session directory per iteration.
- ``orchestrator_step``            the four steps pooled ("per step").
- ``full_chain_session``           propose+approve+execute+reconcile+final gate
                                   per session (the E3 compute-cost input).
- ``scaling_full_chain_n{K}``      full chain at K orders (scaling arm).

Anchor for interpretation: one provider-backed LLM decision call measured in
``docs/results/llm_live_baseline.md`` (mean 8682.86 ms, min 5204.72 ms,
max 11945.79 ms).

Usage:

  python scripts/run_live_readiness_e2.py \
    --iterations 200 --scaling-iterations 100 \
    --output-dir docs/results/live_readiness_e2 \
    --tmp-dir outputs/live_readiness_e2e3_tmp/e2
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import shutil
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from jsonschema import Draft202012Validator

from tradearena.tools.broker_capability import validate_broker_adapter_capability
from tradearena.tools.broker_export import (
    broker_handoff_artifact_hash,
    validate_broker_approval_artifact,
    validate_broker_approval_request_binding,
    validate_broker_handoff_artifact,
    validate_broker_response_artifact,
)
from tradearena.tools.live_readiness import validate_live_readiness_preflight_bundle_file
from tradearena.tools.live_session import (
    JOURNAL_FILENAME,
    LiveSessionConfig,
    RuleBasedDecisionSource,
    _apply_risk_gate,
    _build_market_snapshot,
    _resolved_config,
    approve_session,
    execute_session,
    propose_session,
    reconcile_session,
    verify_journal_chain,
)
from tradearena.tools.operator_runbook import validate_operator_runbook_artifact

DEFAULT_OUTPUT_DIR = ROOT / "docs" / "results" / "live_readiness_e2"
DEFAULT_TMP_DIR = ROOT / "outputs" / "live_readiness_e2e3_tmp" / "e2"

# Fixed deterministic session timestamps (mirrors examples/live_session_demo.py).
PROPOSE_NOW = "2026-07-02T09:00:00Z"
APPROVE_NOW = "2026-07-02T09:05:00Z"
EXECUTE_NOW = "2026-07-02T09:06:00Z"
RECONCILE_NOW = "2026-07-02T09:07:00Z"

# All three pre-registered forward-window symbols close up week-over-week so
# the rule-based decision source emits one limit order per symbol (3 orders).
FIXTURE_PRICES = {
    "BTC-USD": {"close": 109250.5, "prev_close": 108000.0},
    "BTC=F": {"close": 111000.0, "prev_close": 110500.0},
    "GSPC": {"close": 6150.25, "prev_close": 6100.0},
}
FIXTURE_SYMBOLS = ("BTC-USD", "BTC=F", "GSPC")

# Anchor constants copied from docs/results/llm_live_baseline.md (measured on
# 2026-05-18 through the Poe chat-completions endpoint, model label gpt-5.5).
LLM_ANCHOR_MEAN_MS = 8682.86
LLM_ANCHOR_MIN_MS = 5204.72
LLM_ANCHOR_MAX_MS = 11945.79

SCHEMA_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("capability_manifest", "capability_manifest.json", "broker_adapter_capability.schema.json"),
    ("handoff", "dry_run_orders.json", "broker_handoff_artifact.schema.json"),
    ("approval", "broker_approval_artifact.json", "broker_approval_artifact.schema.json"),
    ("response", "broker_response_artifact.json", "broker_response_artifact.schema.json"),
    ("operator_runbook", "operator_runbook_artifact.json", "operator_runbook_artifact.schema.json"),
    ("preflight_bundle", "preflight_bundle.json", "live_readiness_preflight.schema.json"),
)

CSV_FIELDS = (
    "layer",
    "samples",
    "order_count",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "mean_ms",
    "min_ms",
    "max_ms",
)


class E2BenchmarkError(RuntimeError):
    """Raised when a benchmark precondition fails (a validator reported errors)."""


def _percentile(sorted_samples: Sequence[float], q: float) -> float:
    """Nearest-rank percentile over pre-sorted samples (q in (0, 100])."""

    rank = max(1, math.ceil(q / 100.0 * len(sorted_samples)))
    return sorted_samples[rank - 1]


def _summarize(layer: str, samples: Sequence[float], *, order_count: int) -> dict[str, object]:
    ordered = sorted(samples)
    return {
        "layer": layer,
        "samples": len(ordered),
        "order_count": order_count,
        "p50_ms": round(_percentile(ordered, 50.0), 4),
        "p95_ms": round(_percentile(ordered, 95.0), 4),
        "p99_ms": round(_percentile(ordered, 99.0), 4),
        "mean_ms": round(statistics.fmean(ordered), 4),
        "min_ms": round(ordered[0], 4),
        "max_ms": round(ordered[-1], 4),
    }


def _time_callable(fn: Callable[[], None], *, iterations: int, warmup: int) -> list[float]:
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - start) / 1e6)
    return samples


def _require_clean(label: str, errors: Sequence[str]) -> None:
    if errors:
        raise E2BenchmarkError(f"{label} reported validation errors: " + "; ".join(list(errors)[:5]))


def _cpu_name() -> str:
    if os.name == "nt":
        try:
            import winreg

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            return " ".join(str(value).split())
        except OSError:
            pass
    return platform.processor() or "unknown"


def _machine_spec() -> dict[str, object]:
    return {
        "cpu_model": _cpu_name(),
        "logical_cores": os.cpu_count(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "perf_counter_resolution_ns": time.get_clock_info("perf_counter").resolution * 1e9,
    }


def _write_prices_file(path: Path, prices: dict[str, dict[str, float]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prices, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _session_config(root: Path, session_id: str, prices_path: Path, symbols: tuple[str, ...]) -> LiveSessionConfig:
    return LiveSessionConfig(session_id=session_id, root=root, symbols=symbols, prices_file=prices_path)


def _run_full_session(config: LiveSessionConfig) -> Path:
    result = propose_session(config, now=PROPOSE_NOW)
    if result.get("status") != "proposed":
        raise E2BenchmarkError(f"fixture session did not propose orders: {result}")
    approve_session(
        config.session_id,
        root=config.root,
        approved_by="e2-bench-operator",
        reason="deterministic E2 latency benchmark fixture",
        now=APPROVE_NOW,
    )
    execute_session(config.session_id, root=config.root, now=EXECUTE_NOW)
    reconciled = reconcile_session(config.session_id, root=config.root, now=RECONCILE_NOW)
    if reconciled.get("preflight_ready") is not True:
        raise E2BenchmarkError(f"fixture session failed preflight: {reconciled}")
    return Path(config.root) / config.session_id


def _build_fixture(tmp_dir: Path) -> dict[str, object]:
    fixture_root = tmp_dir / "fixture"
    if fixture_root.exists():
        shutil.rmtree(fixture_root)
    prices_path = _write_prices_file(fixture_root / "weekly_prices.json", FIXTURE_PRICES)
    config = _session_config(fixture_root / "sessions", "e2-fixture", prices_path, FIXTURE_SYMBOLS)
    session_dir = _run_full_session(config)

    payloads: dict[str, dict[str, object]] = {}
    schema_texts: dict[str, Path] = {}
    for label, artifact_name, schema_name in SCHEMA_PAIRS:
        artifact_path = session_dir / artifact_name
        payloads[label] = json.loads(artifact_path.read_text(encoding="utf-8"))
        schema_texts[label] = ROOT / "schemas" / schema_name
        validator = Draft202012Validator(json.loads(schema_texts[label].read_text(encoding="utf-8")))
        _require_clean(f"fixture schema {label}", [error.message for error in validator.iter_errors(payloads[label])])

    return {
        "config": config,
        "session_dir": session_dir,
        "prices_path": prices_path,
        "journal_path": Path(config.root) / JOURNAL_FILENAME,
        "handoff_path": session_dir / "dry_run_orders.json",
        "bundle_path": session_dir / "preflight_bundle.json",
        "payloads": payloads,
        "schema_paths": schema_texts,
    }


def _benchmark_schema_layers(fixture: dict[str, object], *, iterations: int, warmup: int) -> list[dict[str, object]]:
    payloads = fixture["payloads"]
    schema_paths = fixture["schema_paths"]
    assert isinstance(payloads, dict) and isinstance(schema_paths, dict)
    rows: list[dict[str, object]] = []
    pooled: list[float] = []
    for label, _artifact_name, _schema_name in SCHEMA_PAIRS:
        payload = payloads[label]
        schema_path = schema_paths[label]

        def _iteration(payload: dict[str, object] = payload, schema_path: Path = schema_path) -> None:
            # Deployed validators reload and recompile the schema on every
            # call (see broker_capability.py / operator_runbook.py), so the
            # honest per-call number includes schema load + compile.
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            errors = [error.message for error in Draft202012Validator(schema).iter_errors(payload)]
            _require_clean("schema validation", errors)

        samples = _time_callable(_iteration, iterations=iterations, warmup=warmup)
        pooled.extend(samples)
        rows.append(_summarize(f"schema_validation_{label}", samples, order_count=3))
    rows.insert(0, _summarize("schema_validation_per_artifact", pooled, order_count=3))
    return rows


def _benchmark_single_artifact_validators(
    fixture: dict[str, object], *, iterations: int, warmup: int
) -> dict[str, object]:
    payloads = fixture["payloads"]
    schema_paths = fixture["schema_paths"]
    assert isinstance(payloads, dict) and isinstance(schema_paths, dict)
    bundle_schema_path = schema_paths["preflight_bundle"]

    def _iteration() -> None:
        _require_clean("capability validator", validate_broker_adapter_capability(payloads["capability_manifest"]))
        _require_clean("handoff validator", validate_broker_handoff_artifact(payloads["handoff"]))
        _require_clean(
            "approval validator", validate_broker_approval_artifact(payloads["approval"], now=EXECUTE_NOW)
        )
        _require_clean("response validator", validate_broker_response_artifact(payloads["response"]))
        _require_clean("runbook validator", validate_operator_runbook_artifact(payloads["operator_runbook"]))
        bundle_schema = json.loads(bundle_schema_path.read_text(encoding="utf-8"))
        bundle_errors = [
            error.message
            for error in Draft202012Validator(bundle_schema).iter_errors(payloads["preflight_bundle"])
        ]
        _require_clean("bundle schema", bundle_errors)

    samples = _time_callable(_iteration, iterations=iterations, warmup=warmup)
    return _summarize("single_artifact_validators_all_six", samples, order_count=3)


def _benchmark_risk_gate(fixture: dict[str, object], *, iterations: int, warmup: int) -> dict[str, object]:
    config = fixture["config"]
    assert isinstance(config, LiveSessionConfig)
    resolved = _resolved_config(config)
    snapshot = _build_market_snapshot(resolved, PROPOSE_NOW)
    orders = RuleBasedDecisionSource().propose_orders(snapshot, resolved)
    if len(orders) != len(FIXTURE_SYMBOLS):
        raise E2BenchmarkError(f"fixture risk-gate proposal produced {len(orders)} orders, expected 3")

    def _iteration() -> None:
        approved, report = _apply_risk_gate(orders, resolved, now=PROPOSE_NOW)
        if len(approved) != len(orders) or report["blocked_count"] != 0:
            raise E2BenchmarkError("risk gate unexpectedly blocked a fixture order")

    samples = _time_callable(_iteration, iterations=iterations, warmup=warmup)
    return _summarize("risk_gate", samples, order_count=len(orders))


def _benchmark_hash_binding(fixture: dict[str, object], *, iterations: int, warmup: int) -> dict[str, object]:
    payloads = fixture["payloads"]
    handoff_path = fixture["handoff_path"]
    assert isinstance(payloads, dict) and isinstance(handoff_path, Path)
    approval = payloads["approval"]
    handoff = payloads["handoff"]

    def _iteration() -> None:
        recomputed = broker_handoff_artifact_hash(handoff)
        if recomputed != approval["request_artifact_hash"]:
            raise E2BenchmarkError("handoff hash does not match the approval binding")
        # Execute-time re-validation: approval + on-disk handoff + binding.
        _require_clean(
            "approval binding", validate_broker_approval_request_binding(approval, handoff_path, now=EXECUTE_NOW)
        )

    samples = _time_callable(_iteration, iterations=iterations, warmup=warmup)
    return _summarize("hash_binding_checks", samples, order_count=3)


def _benchmark_journal_verify(fixture: dict[str, object], *, iterations: int, warmup: int) -> dict[str, object]:
    journal_path = fixture["journal_path"]
    assert isinstance(journal_path, Path)

    def _iteration() -> None:
        _require_clean("journal chain", verify_journal_chain(journal_path))

    samples = _time_callable(_iteration, iterations=iterations, warmup=warmup)
    return _summarize("journal_chain_verify", samples, order_count=3)


def _benchmark_preflight(fixture: dict[str, object], *, iterations: int, warmup: int) -> dict[str, object]:
    bundle_path = fixture["bundle_path"]
    assert isinstance(bundle_path, Path)

    def _iteration() -> None:
        summary, errors = validate_live_readiness_preflight_bundle_file(bundle_path, now=RECONCILE_NOW)
        _require_clean("preflight bundle", errors)
        if summary.get("ready") is not True:
            raise E2BenchmarkError("preflight bundle summary is not ready")

    samples = _time_callable(_iteration, iterations=iterations, warmup=warmup)
    return _summarize("cross_artifact_preflight_full_bundle", samples, order_count=3)


def _timed_session(
    root: Path, session_id: str, prices_path: Path, symbols: tuple[str, ...]
) -> dict[str, float]:
    """Run one full gated session on a fresh root, timing each step in ms."""

    config = _session_config(root, session_id, prices_path, symbols)
    timings: dict[str, float] = {}

    start = time.perf_counter_ns()
    proposed = propose_session(config, now=PROPOSE_NOW)
    timings["step_propose"] = (time.perf_counter_ns() - start) / 1e6
    if proposed.get("status") != "proposed":
        raise E2BenchmarkError(f"benchmark session did not propose orders: {proposed}")

    start = time.perf_counter_ns()
    approve_session(
        session_id,
        root=root,
        approved_by="e2-bench-operator",
        reason="deterministic E2 latency benchmark session",
        now=APPROVE_NOW,
    )
    timings["step_approve"] = (time.perf_counter_ns() - start) / 1e6

    start = time.perf_counter_ns()
    execute_session(session_id, root=root, now=EXECUTE_NOW)
    timings["step_execute"] = (time.perf_counter_ns() - start) / 1e6

    start = time.perf_counter_ns()
    reconciled = reconcile_session(session_id, root=root, now=RECONCILE_NOW)
    timings["step_reconcile"] = (time.perf_counter_ns() - start) / 1e6
    if reconciled.get("preflight_ready") is not True:
        raise E2BenchmarkError("benchmark session failed preflight")

    bundle_path = root / session_id / "preflight_bundle.json"
    start = time.perf_counter_ns()
    _summary, errors = validate_live_readiness_preflight_bundle_file(bundle_path, now=RECONCILE_NOW)
    timings["final_gate"] = (time.perf_counter_ns() - start) / 1e6
    _require_clean("final gate", errors)

    timings["full_chain_session"] = sum(timings.values())
    return timings


def _benchmark_orchestrator(
    tmp_dir: Path,
    *,
    iterations: int,
    warmup: int,
    prices: dict[str, dict[str, float]],
    symbols: tuple[str, ...],
    label_suffix: str = "",
) -> tuple[list[dict[str, object]], list[float]]:
    steps_tmp = tmp_dir / f"steps{label_suffix}"
    if steps_tmp.exists():
        shutil.rmtree(steps_tmp)
    prices_path = _write_prices_file(steps_tmp / "weekly_prices.json", prices)

    per_step: dict[str, list[float]] = {}
    for index in range(warmup + iterations):
        session_root = steps_tmp / f"iter{index:05d}"
        timings = _timed_session(session_root, "e2-bench", prices_path, symbols)
        if index >= warmup:
            for key, value in timings.items():
                per_step.setdefault(key, []).append(value)
        shutil.rmtree(session_root, ignore_errors=True)

    order_count = len(symbols)
    rows = [
        _summarize(f"step_propose{label_suffix}", per_step["step_propose"], order_count=order_count),
        _summarize(f"step_approve{label_suffix}", per_step["step_approve"], order_count=order_count),
        _summarize(f"step_execute{label_suffix}", per_step["step_execute"], order_count=order_count),
        _summarize(f"step_reconcile{label_suffix}", per_step["step_reconcile"], order_count=order_count),
        _summarize(f"final_gate{label_suffix}", per_step["final_gate"], order_count=order_count),
    ]
    pooled = (
        per_step["step_propose"]
        + per_step["step_approve"]
        + per_step["step_execute"]
        + per_step["step_reconcile"]
    )
    rows.append(_summarize(f"orchestrator_step{label_suffix}", pooled, order_count=order_count))
    rows.append(
        _summarize(f"full_chain_session{label_suffix}", per_step["full_chain_session"], order_count=order_count)
    )
    shutil.rmtree(steps_tmp, ignore_errors=True)
    return rows, per_step["full_chain_session"]


def _benchmark_scaling(
    tmp_dir: Path, *, order_counts: Sequence[int], iterations: int, warmup: int
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for count in order_counts:
        symbols = tuple(f"SYM{index:02d}" for index in range(count))
        prices = {symbol: {"close": 110.0, "prev_close": 100.0} for symbol in symbols}
        step_rows, chain_samples = _benchmark_orchestrator(
            tmp_dir,
            iterations=iterations,
            warmup=warmup,
            prices=prices,
            symbols=symbols,
            label_suffix=f"_scaling_n{count}",
        )
        del step_rows  # scaling arm reports only the full-chain row per order count
        rows.append(_summarize(f"scaling_full_chain_n{count}", chain_samples, order_count=count))
    return rows


def _headline_rows(rows: list[dict[str, object]]) -> list[tuple[str, dict[str, object]]]:
    by_layer = {str(row["layer"]): row for row in rows}
    mapping = (
        ("Schema validation (per artifact)", "schema_validation_per_artifact"),
        ("Single-artifact validators (all six)", "single_artifact_validators_all_six"),
        ("Hash computation + binding checks", "hash_binding_checks"),
        ("Cross-artifact preflight (full bundle)", "cross_artifact_preflight_full_bundle"),
        ("Orchestrator step overhead (per step)", "orchestrator_step"),
    )
    return [(label, by_layer[key]) for label, key in mapping]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _markdown_table(rows: list[dict[str, object]]) -> list[str]:
    lines = [
        "| Layer | Samples | Orders | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | Max (ms) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['layer']}` | {row['samples']} | {row['order_count']} | {row['p50_ms']} "
            f"| {row['p95_ms']} | {row['p99_ms']} | {row['mean_ms']} | {row['max_ms']} |"
        )
    return lines


def _write_markdown(
    path: Path,
    *,
    rows: list[dict[str, object]],
    scaling_rows: list[dict[str, object]],
    machine: dict[str, object],
    iterations: int,
    scaling_iterations: int,
    warmup: int,
) -> None:
    by_layer = {str(row["layer"]): row for row in rows}
    preflight = by_layer["cross_artifact_preflight_full_bundle"]
    full_chain = by_layer["full_chain_session"]
    anchor_over_preflight = LLM_ANCHOR_MEAN_MS / float(preflight["p95_ms"])
    anchor_over_chain = LLM_ANCHOR_MEAN_MS / float(full_chain["p95_ms"])

    lines: list[str] = []
    lines.append("# E2: Validation-Latency Microbenchmark (Live-Readiness Control Plane)")
    lines.append("")
    lines.append(
        "Per-layer wall-clock latency of the deterministic live-readiness control plane "
        "(live-readiness E2). Pure local computation: zero LLM calls, zero network, "
        "deterministic synthetic market snapshot, fixed session timestamps."
    )
    lines.append("")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append("- Command: `python scripts/run_live_readiness_e2.py`")
    lines.append(
        f"- Iterations: {iterations} per layer (schema layer pools 6 artifacts x {iterations}; "
        f"orchestrator-step row pools 4 steps x {iterations}), warmup {warmup} excluded"
    )
    lines.append(f"- Scaling arm: {scaling_iterations} sessions per order count")
    lines.append(
        "- Timer: `time.perf_counter_ns`; percentiles are nearest-rank over the sorted samples"
    )
    lines.append(
        "- Fixture: one reconciled weekly session, 3 symbols / 3 limit orders, dry-run engine, "
        f"timestamps {PROPOSE_NOW} -> {RECONCILE_NOW}"
    )
    lines.append("")
    lines.append("## Machine")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("| --- | --- |")
    for key, value in machine.items():
        lines.append(f"| {key} | `{value}` |")
    lines.append("")
    lines.append("## Headline layers")
    lines.append("")
    headline = _headline_rows(rows)
    lines.append("| Layer | Samples | P50 (ms) | P95 (ms) | P99 (ms) |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for label, row in headline:
        lines.append(f"| {label} | {row['samples']} | {row['p50_ms']} | {row['p95_ms']} | {row['p99_ms']} |")
    lines.append(
        f"| LLM decision call (measured anchor) | 3 | mean {LLM_ANCHOR_MEAN_MS} | "
        f"range {LLM_ANCHOR_MIN_MS}-{LLM_ANCHOR_MAX_MS} | |"
    )
    lines.append("")
    lines.append("## Anchor comparison")
    lines.append("")
    lines.append(
        f"- One measured LLM decision call (docs/results/llm_live_baseline.md): mean {LLM_ANCHOR_MEAN_MS} ms, "
        f"min {LLM_ANCHOR_MIN_MS} ms, max {LLM_ANCHOR_MAX_MS} ms."
    )
    lines.append(
        f"- Full-bundle cross-artifact preflight P95 = {preflight['p95_ms']} ms "
        f"=> anchor mean / preflight P95 = {anchor_over_preflight:,.0f}x "
        f"({math.log10(anchor_over_preflight):.1f} orders of magnitude)."
    )
    lines.append(
        f"- Entire gated session chain (propose+approve+execute+reconcile+final gate) P95 = "
        f"{full_chain['p95_ms']} ms => anchor mean / chain P95 = {anchor_over_chain:,.0f}x "
        f"({math.log10(anchor_over_chain):.1f} orders of magnitude)."
    )
    lines.append("")
    lines.append("## All layers")
    lines.append("")
    lines.extend(_markdown_table(rows))
    lines.append("")
    lines.append("## Scaling with order count (full chain per session)")
    lines.append("")
    lines.extend(_markdown_table(scaling_rows))
    lines.append("")
    lines.append(
        "The full chain includes every filesystem write, JSON Schema reload/recompile, hash "
        "recomputation, and journal append the deployed weekly path performs; the E3 sweep "
        "(docs/results/live_readiness_e3/) consumes the `scaling_full_chain_n*` P95 values as its "
        "per-session compute-cost input."
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E2 validation-latency microbenchmark (zero LLM, zero network).")
    parser.add_argument("--iterations", type=int, default=200, help="Timed iterations per layer (default 200).")
    parser.add_argument("--warmup", type=int, default=10, help="Warmup iterations excluded from stats (default 10).")
    parser.add_argument(
        "--scaling-iterations", type=int, default=100, help="Timed sessions per scaling order count (default 100)."
    )
    parser.add_argument(
        "--scaling-order-counts",
        default="1,2,5,10,25,50",
        help="Comma-separated order counts for the scaling arm (default 1,2,5,10,25,50).",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for e2_latency.csv/.md.")
    parser.add_argument("--tmp-dir", default=str(DEFAULT_TMP_DIR), help="Scratch directory for session fixtures.")
    args = parser.parse_args(argv)

    if args.iterations < 1 or args.scaling_iterations < 1 or args.warmup < 0:
        print("iterations and scaling-iterations must be >= 1 and warmup >= 0")
        return 1
    order_counts = sorted({int(part) for part in str(args.scaling_order_counts).split(",") if part.strip()})
    if not order_counts or any(count < 1 for count in order_counts):
        print("scaling-order-counts must be positive integers")
        return 1

    tmp_dir = Path(args.tmp_dir)
    output_dir = Path(args.output_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    machine = _machine_spec()
    print(f"E2 microbenchmark on {machine['cpu_model']} ({machine['logical_cores']} logical cores)")
    print(f"  iterations={args.iterations} warmup={args.warmup} scaling={args.scaling_iterations}x{order_counts}")

    fixture = _build_fixture(tmp_dir)
    print("  fixture session reconciled and schema-clean")

    rows: list[dict[str, object]] = []
    rows.extend(_benchmark_schema_layers(fixture, iterations=args.iterations, warmup=args.warmup))
    print("  schema layers done")
    rows.append(_benchmark_single_artifact_validators(fixture, iterations=args.iterations, warmup=args.warmup))
    rows.append(_benchmark_risk_gate(fixture, iterations=args.iterations, warmup=args.warmup))
    rows.append(_benchmark_hash_binding(fixture, iterations=args.iterations, warmup=args.warmup))
    rows.append(_benchmark_journal_verify(fixture, iterations=args.iterations, warmup=args.warmup))
    rows.append(_benchmark_preflight(fixture, iterations=args.iterations, warmup=args.warmup))
    print("  validator/binding/preflight layers done")

    step_rows, _chain = _benchmark_orchestrator(
        tmp_dir,
        iterations=args.iterations,
        warmup=min(args.warmup, 5),
        prices=FIXTURE_PRICES,
        symbols=FIXTURE_SYMBOLS,
    )
    rows.extend(step_rows)
    print("  orchestrator steps done")

    scaling_rows = _benchmark_scaling(
        tmp_dir, order_counts=order_counts, iterations=args.scaling_iterations, warmup=min(args.warmup, 3)
    )
    print("  scaling arm done")

    all_rows = rows + scaling_rows
    csv_path = output_dir / "e2_latency.csv"
    md_path = output_dir / "e2_latency.md"
    _write_csv(csv_path, all_rows)
    _write_markdown(
        md_path,
        rows=rows,
        scaling_rows=scaling_rows,
        machine=machine,
        iterations=args.iterations,
        scaling_iterations=args.scaling_iterations,
        warmup=args.warmup,
    )

    shutil.rmtree(tmp_dir, ignore_errors=True)
    elapsed = time.perf_counter() - started
    print(f"  wrote {csv_path}")
    print(f"  wrote {md_path}")
    print(f"E2 done in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
