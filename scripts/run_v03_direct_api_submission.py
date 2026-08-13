"""W0 dry-run bridge: pre-registered call packets -> runs -> manifests -> submissions -> gate.

This script turns TreLLM v0.3 direct API call packets
(docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.jsonl) into
executed benchmark rows for the pre-registered matrix:

1. run the real TreLLM pipeline (build_default_system + LLM analyst) for each
   pre-registered (scenario, tier, execution level, seed, sample) packet;
2. write a per-run private call log (raw prompts/responses stay under the
   output root's ``private/llm_cache`` directory and are never published);
3. emit a hash-only direct provider manifest that passes
   scripts/validate_direct_provider_manifest.py;
4. emit a benchmark submission that passes
   tradearena.evaluation.submissions.validate_submission_file and binds the
   provider manifest by file hash, so
   scripts/build_v03_direct_api_matrix_gate.py can promote the rows.

Modes:

- default (no ``--execute``): offline fixture transport. No network call is
  made, no credential is read, and every artifact is labeled as a
  ``protocol-fixture`` dry-run row so the matrix gate keeps it non-headline.
- ``--execute``: live direct provider calls (DeepSeek / GLM chat-completions)
  with the packet-pinned sampling envelope (temperature, top_p, max_tokens).
  Requires the packet's credential environment variable to be present.

Usage (offline self-check, no keys):

  python scripts/run_v03_direct_api_submission.py \
    --packets outputs/v03_dryrun_selftest/packets/direct_api_call_packets.jsonl \
    --model deepseek-v4-pro --limit-seeds 2 --samples 0,1 --periods 6 \
    --output-root outputs/v03_dryrun_selftest/bundle

Usage (real W0 single-model dry run; operator supplies credentials):

  python scripts/run_v03_direct_api_submission.py --model deepseek-v4-pro --execute

See docs/results/v0_3_direct_api_submission/README.md for the full
packets -> submission -> gate command chain and the scenario-parameter basis.
"""

from __future__ import annotations

import argparse
import csv
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from validate_direct_provider_manifest import validate_direct_provider_manifest_file

from tradearena.agents.llm import DeepSeekLLMAnalyst, _get_secret
from tradearena.core.reproducibility import canonical_json, compute_reproducibility_hash, sha256_file, sha256_text
from tradearena.evaluation.evidence import evidence_payload
from tradearena.evaluation.submissions import validate_submission_file
from tradearena.factory import build_default_system

PROTOCOL_ID = "trellm-v0.3-protocol"
PACKET_SCHEMA = "trellm_v0_3_direct_api_call_packet_v0.1"
RUN_RECORD_SCHEMA = "trellm_v0_3_direct_api_submission_run_v0.1"
SUMMARY_SCHEMA = "trellm_v0_3_direct_api_submission_v0.1"
DEFAULT_PACKETS = "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.jsonl"
DEFAULT_OUTPUT_ROOT = "outputs/v0_3_direct_api_matrix"

# Direct-provider analyst wiring (factory analyst names). Routed providers
# (poe/openrouter/...) are intentionally unsupported: the v0.3 protocol forbids
# routed rows on the headline direct API evidence path.
PROVIDER_ANALYSTS = {"deepseek": "deepseek-llm", "glm": "glm-llm"}

# Operational definition of the pre-registered scenario ids. The calm-trend C0
# scenario follows scripts/run_v03_execution_ladder.py (the v0.3 artifact that
# introduced `synthetic_calm_trend_c0_v0_3`): SYN+ALT synthetic universe,
# volatility/trend scale 1.0, 24 periods, $100k initial cash, max-position risk.
SCENARIOS: dict[str, dict[str, Any]] = {
    "synthetic_calm_trend_c0_v0_3": {
        "contamination_tier": "C0",
        "symbols": ("SYN", "ALT"),
        "periods": 24,
        "initial_cash": 100_000.0,
        "synthetic": {"synthetic_volatility_scale": 1.0, "synthetic_trend_scale": 1.0},
        "data_source_name": "trellm-synthetic-c0",
        "frequency": "daily",
    },
    # 2026-07-05 amendment: the two additional C0 regimes whose generator
    # parameters are already validated in the execution-sensitivity study
    # (scripts/run_execution_sensitivity_sweep.py: high_vol, jump_tail). Same
    # universe / periods / cash / execution ladder; only the synthetic knobs
    # differ, so the expansion is grounded, not invented.
    "synthetic_high_volatility_c0_v0_3": {
        "contamination_tier": "C0",
        "symbols": ("SYN", "ALT"),
        "periods": 24,
        "initial_cash": 100_000.0,
        "synthetic": {
            "synthetic_volatility_scale": 2.25,
            "synthetic_trend_scale": 0.65,
            "synthetic_macro_scale": 1.4,
        },
        "data_source_name": "trellm-synthetic-c0",
        "frequency": "daily",
    },
    "synthetic_jump_tail_c0_v0_3": {
        "contamination_tier": "C0",
        "symbols": ("SYN", "ALT"),
        "periods": 24,
        "initial_cash": 100_000.0,
        "synthetic": {
            "synthetic_volatility_scale": 1.65,
            "synthetic_tail_df": 3,
            "synthetic_jump_probability": 0.15,
            "synthetic_jump_scale": 0.08,
        },
        "data_source_name": "trellm-synthetic-c0",
        "frequency": "daily",
    },
}

# Execution-ladder parameters, aligned with scripts/run_v03_execution_ladder.py
# and the fixture pilot's recorded execution_config. E2/E3 are intentionally
# rejected here because the pre-registered matrix plan only covers E1.
EXECUTION_LEVELS: dict[str, dict[str, Any]] = {
    "E0": {
        "execution_mode": "ideal",
        "commission_bps": 1.0,
        "slippage_bps": 2.0,
        "spread_bps": 0.0,
        "latency_steps": 1,
        "participation_rate": 0.05,
        "market_impact": 0.15,
    },
    "E1": {
        "execution_mode": "realistic",
        "commission_bps": 1.0,
        "slippage_bps": 2.0,
        "spread_bps": 0.0,
        "latency_steps": 1,
        "participation_rate": 0.05,
        "market_impact": 0.15,
    },
}

RUN_CSV_FIELDS = [
    "plan_id",
    "provider",
    "model_id",
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "seed",
    "sample_index",
    "mode",
    "transport",
    "status",
    "total_return",
    "sharpe",
    "max_drawdown",
    "execution_fill_rate",
    "rejected_order_count",
    "risk_clipped_decisions",
    "risk_violation_count",
    "trajectory_reproducibility_coverage",
    "parse_coverage",
    "llm_call_count",
    "cache_status",
    "provider_manifest_sha256",
    "reproducibility_hash",
    "error_class",
]

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

TransportFn = Callable[[dict[str, Any], str], str]


def main(argv: list[str] | None = None, *, transport: TransportFn | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run pre-registered TreLLM v0.3 direct API call packets through the real pipeline and emit "
            "provider manifests plus benchmark submissions for the matrix gate."
        )
    )
    parser.add_argument("--packets", default=DEFAULT_PACKETS, help="Call packet JSONL built from the matrix plan.")
    parser.add_argument("--model", default="", help="Only run packets whose model_id matches (e.g. deepseek-v4-pro).")
    parser.add_argument("--provider", default="", help="Only run packets for this provider (deepseek or glm).")
    parser.add_argument("--seeds", default="", help="Comma-separated seed subset; default keeps every packet seed.")
    parser.add_argument("--samples", default="", help="Comma-separated sample subset; default keeps every sample.")
    parser.add_argument("--limit-seeds", type=int, default=0, help="Keep only the first N distinct seeds per model.")
    parser.add_argument("--max-runs", type=int, default=0, help="Stop after N fresh runs (skips do not count).")
    parser.add_argument("--periods", type=int, default=0, help="Override scenario periods (default: scenario value).")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Make live direct provider calls. Without this flag the offline fixture transport is used.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Re-run packets even when artifacts already exist.")
    args = parser.parse_args(argv)

    mode = "execute" if args.execute else "dry-run"
    transport_label = "injected" if transport is not None else ("direct-api" if args.execute else "fixture")
    output_root = _resolve(args.output_root)
    packets_path = _resolve(args.packets)
    packets = _select_packets(
        _load_packets(packets_path),
        model=args.model,
        provider=args.provider,
        seeds=_parse_int_set(args.seeds, "--seeds"),
        samples=_parse_int_set(args.samples, "--samples"),
        limit_seeds=args.limit_seeds,
    )
    if not packets:
        raise SystemExit(
            "No call packets match the requested filters. If the packet file still lists a stale provider set, "
            "rebuild it from the amended plan: python scripts/build_v03_direct_api_call_packets.py"
        )
    _validate_selected_packets(packets)
    if args.execute and transport is None:
        _preflight_credentials(packets)

    manifest_dir = output_root / "provider_manifests"
    submission_dir = output_root / "submissions"
    runs_dir = output_root / "runs"
    call_log_dir = output_root / "private" / "llm_cache"
    for directory in (manifest_dir, submission_dir, runs_dir, call_log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    executed = 0
    skipped = 0
    failed = 0
    for packet in packets:
        plan_id = str(packet["plan_id"])
        manifest_path = manifest_dir / Path(str(packet["output_contract"]["expected_provider_manifest_path"])).name
        submission_path = submission_dir / Path(str(packet["output_contract"]["expected_submission_path"])).name
        run_record_path = runs_dir / f"{plan_id}.json"
        call_log_path = call_log_dir / f"{plan_id}.jsonl"

        if not args.overwrite:
            complete, reason = _existing_complete(run_record_path, manifest_path, submission_path, mode=mode)
            if reason == "mode_mismatch":
                raise SystemExit(
                    f"{plan_id}: existing artifacts were produced in a different mode. "
                    "Use a separate --output-root for dry-run rehearsals or pass --overwrite."
                )
            if complete:
                skipped += 1
                print(f"SKIP {plan_id} (already complete)", flush=True)
                continue

        if args.max_runs and executed >= args.max_runs:
            print(f"STOP after --max-runs={args.max_runs}; remaining packets untouched.", flush=True)
            break

        record = _run_packet(
            packet,
            mode=mode,
            transport_label=transport_label,
            transport=transport,
            periods_override=args.periods,
            manifest_path=manifest_path,
            submission_path=submission_path,
            call_log_path=call_log_path,
        )
        _write_json(run_record_path, record)
        executed += 1
        if record["status"] == "ok":
            print(
                f"OK {plan_id} (calls={record['llm_call_count']}, return={record['metrics']['total_return']})",
                flush=True,
            )
        else:
            failed += 1
            print(f"FAIL {plan_id} ({record['error_class']})", flush=True)

    run_rows = _collect_run_rows(runs_dir)
    _write_run_tables(output_root, run_rows)
    summary = _summary(run_rows, mode=mode, packets_path=packets_path, output_root=output_root)
    _write_json(output_root / "direct_api_submission_summary.json", summary)
    (output_root / "direct_api_submission_summary.md").write_text(_summary_markdown(summary, run_rows), encoding="utf-8")

    print(f"Wrote {_display(output_root / 'direct_api_submission_runs.csv')}")
    print(f"Wrote {_display(output_root / 'direct_api_submission_runs.jsonl')}")
    print(f"Wrote {_display(output_root / 'direct_api_submission_summary.json')}")
    print(f"Wrote {_display(output_root / 'direct_api_submission_summary.md')}")
    print(f"Selected packets: {len(packets)} (executed={executed}, skipped={skipped}, failed={failed})")
    print(
        "Next: python scripts/build_v03_direct_api_matrix_gate.py "
        f"--submission-dirs {_display(submission_dir)} --provider-manifest-dirs {_display(manifest_dir)}"
    )
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# Packet selection


def _load_packets(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Call packet file not found: {_display(path)}")
    packets: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            packet = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{_display(path)}:{line_number}: invalid packet JSON: {exc}") from exc
        packets.append(packet)
    return packets


def _select_packets(
    packets: list[dict[str, Any]],
    *,
    model: str,
    provider: str,
    seeds: set[int] | None,
    samples: set[int] | None,
    limit_seeds: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_plan_ids: set[str] = set()
    seeds_kept_by_model: dict[str, list[int]] = {}
    for packet in packets:
        prompt_packet = packet.get("request_envelope", {}).get("prompt_packet", {})
        seed = int(prompt_packet.get("seed", -1))
        sample_index = int(prompt_packet.get("sample_index", -1))
        if model and str(packet.get("model_id", "")) != model:
            continue
        if provider and str(packet.get("provider", "")) != provider:
            continue
        if seeds is not None and seed not in seeds:
            continue
        if samples is not None and sample_index not in samples:
            continue
        if limit_seeds:
            kept = seeds_kept_by_model.setdefault(str(packet.get("model_id", "")), [])
            if seed not in kept:
                if len(kept) >= limit_seeds:
                    continue
                kept.append(seed)
        plan_id = str(packet.get("plan_id", ""))
        if plan_id in seen_plan_ids:
            continue
        seen_plan_ids.add(plan_id)
        selected.append(packet)
    return selected


def _validate_selected_packets(packets: list[dict[str, Any]]) -> None:
    for packet in packets:
        plan_id = str(packet.get("plan_id", "<missing plan_id>"))
        if packet.get("schema") != PACKET_SCHEMA:
            raise SystemExit(f"{plan_id}: unsupported packet schema {packet.get('schema')!r}")
        if packet.get("protocol_id") != PROTOCOL_ID:
            raise SystemExit(f"{plan_id}: packet protocol_id {packet.get('protocol_id')!r} != {PROTOCOL_ID!r}")
        provider = str(packet.get("provider", ""))
        if provider not in PROVIDER_ANALYSTS:
            raise SystemExit(
                f"{plan_id}: provider {provider!r} has no direct-API adapter here (supported: "
                f"{', '.join(sorted(PROVIDER_ANALYSTS))}). Rebuild packets from the amended plan if this file is stale."
            )
        prompt_packet = packet.get("request_envelope", {}).get("prompt_packet", {})
        scenario_id = str(prompt_packet.get("scenario_id", ""))
        if scenario_id not in SCENARIOS:
            raise SystemExit(f"{plan_id}: scenario {scenario_id!r} is not defined in this bridge's scenario registry")
        execution_level = str(prompt_packet.get("execution_level", ""))
        if execution_level not in EXECUTION_LEVELS:
            raise SystemExit(f"{plan_id}: execution level {execution_level!r} is not supported (pre-registered: E1)")
        tier = str(prompt_packet.get("contamination_tier", ""))
        if tier != SCENARIOS[scenario_id]["contamination_tier"]:
            raise SystemExit(f"{plan_id}: contamination tier {tier!r} does not match scenario registry")


def _preflight_credentials(packets: list[dict[str, Any]]) -> None:
    missing = sorted(
        {
            str(packet["credential_env_var"])
            for packet in packets
            if not _get_secret(str(packet.get("credential_env_var", "")))
        }
    )
    if missing:
        raise SystemExit(
            "Missing credential environment variables for --execute: "
            + ", ".join(missing)
            + ". Set them in the environment; this script never reads key files."
        )


# ---------------------------------------------------------------------------
# Single-packet execution


def _run_packet(
    packet: dict[str, Any],
    *,
    mode: str,
    transport_label: str,
    transport: TransportFn | None,
    periods_override: int,
    manifest_path: Path,
    submission_path: Path,
    call_log_path: Path,
) -> dict[str, Any]:
    prompt_packet = packet["request_envelope"]["prompt_packet"]
    scenario_id = str(prompt_packet["scenario_id"])
    scenario = SCENARIOS[scenario_id]
    execution_level = str(prompt_packet["execution_level"])
    level = EXECUTION_LEVELS[execution_level]
    seed = int(prompt_packet["seed"])
    sample_index = int(prompt_packet["sample_index"])
    periods = periods_override or int(scenario["periods"])
    started_at = _utc_now()

    record: dict[str, Any] = {
        "schema": RUN_RECORD_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "plan_id": str(packet["plan_id"]),
        "mode": mode,
        "transport": transport_label,
        "status": "failed",
        "provider": str(packet["provider"]),
        "model_id": str(packet["model_id"]),
        "model_version_or_release": str(packet["model_version_or_release"]),
        "api_endpoint_family": str(packet["api_endpoint_family"]),
        "scenario_id": scenario_id,
        "contamination_tier": str(prompt_packet["contamination_tier"]),
        "execution_level": execution_level,
        "seed": seed,
        "sample_index": sample_index,
        "periods": periods,
        "symbols": list(scenario["symbols"]),
        "started_at": started_at,
        "completed_at": started_at,
        "error_class": "",
        "error_message": "",
    }
    try:
        result = _run_pipeline(
            packet,
            mode=mode,
            transport=transport,
            scenario=scenario,
            level=level,
            periods=periods,
            call_log_path=call_log_path,
        )
        manifest = _provider_manifest(packet, mode=mode, result=result)
        _write_json(manifest_path, manifest)
        _, manifest_errors = validate_direct_provider_manifest_file(manifest_path)
        if manifest_errors:
            raise RuntimeError("provider manifest validation failed: " + "; ".join(manifest_errors))
        manifest_hash = sha256_file(manifest_path)

        submission = _benchmark_submission(
            packet,
            mode=mode,
            result=result,
            scenario=scenario,
            level=level,
            periods=periods,
            provider_manifest_hash=manifest_hash,
            call_log_path=call_log_path,
        )
        submission["reproducibility_hash"] = compute_reproducibility_hash(submission)
        _write_json(submission_path, submission)
        _, submission_errors = validate_submission_file(submission_path)
        if submission_errors:
            raise RuntimeError("benchmark submission validation failed: " + "; ".join(submission_errors))
    except Exception as exc:  # Broad by design: every failure becomes a pre-registered failure row.
        record["completed_at"] = _utc_now()
        record["error_class"] = type(exc).__name__
        record["error_message"] = str(exc)[:300]
        return record

    record.update(
        {
            "status": "ok",
            "completed_at": _utc_now(),
            "metrics": submission["metrics"],
            "llm_call_count": result["llm_call_count"],
            "live_call_appended_count": result["live_call_appended_count"],
            "parse_coverage": result["parse_coverage"],
            "parse_status": result["parse_status"],
            "cache_status": result["cache_status"],
            "prompt_calls_sha256": result["prompt_calls_sha256"],
            "response_calls_sha256": result["response_calls_sha256"],
            "call_log_path": _display(call_log_path),
            "call_log_sha256": result["call_log_sha256"],
            "provider_manifest_path": _display(manifest_path),
            "provider_manifest_sha256": manifest_hash,
            "submission_path": _display(submission_path),
            "reproducibility_hash": submission["reproducibility_hash"],
        }
    )
    return record


def _run_pipeline(
    packet: dict[str, Any],
    *,
    mode: str,
    transport: TransportFn | None,
    scenario: dict[str, Any],
    level: dict[str, Any],
    periods: int,
    call_log_path: Path,
) -> dict[str, Any]:
    prompt_packet = packet["request_envelope"]["prompt_packet"]
    sampling = packet["request_envelope"]["sampling"]
    provider = str(packet["provider"])
    model_id = str(packet["model_id"])
    seed = int(prompt_packet["seed"])
    sample_index = int(prompt_packet["sample_index"])

    arena = build_default_system(
        name=f"v03_direct_api_{packet['plan_id']}",
        symbols=tuple(scenario["symbols"]),
        periods=periods,
        seed=seed,
        initial_cash=float(scenario["initial_cash"]),
        strategy_name="signal-weighted",
        risk_name="max-position",
        analyst_names=(PROVIDER_ANALYSTS[provider],),
        llm_model=model_id,
        llm_cache_path=str(call_log_path),
        llm_use_risk_feedback=True,
        llm_risk_feedback_mode="true",
        llm_output_mode="weights_only",
        llm_mask_timestamps=True,
        llm_anonymize_symbols=False,
        llm_sample_index=sample_index,
        execution_mode=str(level["execution_mode"]),
        commission_bps=float(level["commission_bps"]),
        slippage_bps=float(level["slippage_bps"]),
        spread_bps=float(level["spread_bps"]),
        latency_steps=int(level["latency_steps"]),
        participation_rate=float(level["participation_rate"]),
        market_impact=float(level["market_impact"]),
        **scenario["synthetic"],
    )
    analyst = arena.analysts[0]
    if not isinstance(analyst, DeepSeekLLMAnalyst):  # pragma: no cover - defensive wiring check.
        raise RuntimeError(f"expected an LLM analyst for provider {provider!r}")
    analyst.temperature = float(sampling["temperature"])

    context = {
        "plan_id": str(packet["plan_id"]),
        "provider": provider,
        "model_id": model_id,
        "seed": seed,
        "sample_index": sample_index,
    }
    if transport is not None:
        call_fn = transport
    elif mode == "execute":
        call_fn = _pinned_live_transport(analyst, sampling)
    else:
        call_fn = _fixture_transport()
    # Instance-attribute shadowing keeps the analyst's prompt/cache/parse path
    # intact while routing only the innermost provider call through the bridge.
    analyst._call_deepseek = _bind_transport(call_fn, context)  # type: ignore[method-assign]

    entries_before = len(_read_call_log(call_log_path))
    _, metrics = arena.run()
    entries = _read_call_log(call_log_path)
    if not entries:
        raise RuntimeError("run produced no LLM call evidence in the private call log")

    parser_analyst = DeepSeekLLMAnalyst(output_mode="weights_only")
    prompt_hashes = [_call_prompt_sha(entry) for entry in entries]
    response_texts = [str(entry.get("response_text", "")) for entry in entries]
    response_hashes = [sha256_text(text) for text in response_texts]
    parsed_flags = [bool(parser_analyst._signal_items(parser_analyst._parse_response(text))) for text in response_texts]
    parse_coverage = round(sum(parsed_flags) / len(parsed_flags), 6)
    if all(parsed_flags):
        parse_status = "parsed"
    elif any(parsed_flags):
        parse_status = "partial"
    else:
        parse_status = "failed"
    created_ats = [int(entry.get("created_at", 0)) for entry in entries if entry.get("created_at")]
    live_appended = len(entries) - entries_before
    if mode == "execute":
        cache_status = "live_call" if live_appended > 0 else "cache_replay"
    else:
        cache_status = "cache_replay"

    return {
        "metrics": metrics,
        "llm_call_count": len(entries),
        "live_call_appended_count": max(0, live_appended),
        "parse_coverage": parse_coverage,
        "parse_status": parse_status,
        "cache_status": cache_status,
        "prompt_calls_sha256": sha256_text(canonical_json(prompt_hashes)),
        "response_calls_sha256": sha256_text(canonical_json(response_hashes)),
        "call_started_at": _iso_utc(min(created_ats)) if created_ats else _utc_now(),
        "call_completed_at": _iso_utc(max(created_ats)) if created_ats else _utc_now(),
        "call_log_sha256": sha256_file(call_log_path),
        "system_prompt_sha256": sha256_text(_system_prompt_text()),
    }


def _bind_transport(call_fn: TransportFn, context: dict[str, Any]) -> Callable[[str], str]:
    def call(prompt: str) -> str:
        return call_fn(context, prompt)

    return call


def _system_prompt_text() -> str:
    """The exact weights-only system prompt sent by the repository LLM adapter."""

    response_shape = '{"weights":[{"symbol":"SYMBOL","target_weight":0.0,"confidence":0.0,"horizon":"1w"}]}.'
    return (
        "You are a cautious trading research analyst. "
        "Use only the provided OHLCV and portfolio state. "
        "Return calibrated signals or target weights, not executable orders. Do not mention API keys. "
        "Return only valid JSON with this shape: "
        f"{response_shape}"
    )


def _pinned_live_transport(analyst: DeepSeekLLMAnalyst, sampling: dict[str, Any]) -> TransportFn:
    """Live chat-completions call that enforces the pre-registered sampling envelope.

    Mirrors DeepSeekLLMAnalyst._call_deepseek (endpoint, headers, retry policy,
    secret redaction, system prompt) and additionally pins ``top_p`` and
    ``max_tokens`` from the call packet, which the base adapter does not send.
    """

    if analyst.output_mode != "weights_only":  # pragma: no cover - bridge always configures weights_only.
        raise RuntimeError("pinned transport only supports the weights_only prompt contract")

    def call(context: dict[str, Any], prompt: str) -> str:
        api_key = _get_secret(analyst.api_key_env) or _get_secret(analyst.fallback_api_key_env)
        if not api_key:
            raise RuntimeError(f"{analyst.api_key_env} is not set; refusing to attempt a live {analyst.provider} call.")
        request_body: dict[str, Any] = {
            "model": analyst.api_model or analyst.model,
            "temperature": float(sampling["temperature"]),
            "top_p": float(sampling["top_p"]),
            "max_tokens": int(sampling["max_tokens"]),
            "messages": [
                {"role": "system", "content": _system_prompt_text()},
                {"role": "user", "content": prompt},
            ],
        }
        if analyst.use_response_format:
            request_body["response_format"] = {"type": "json_object"}
        if analyst.thinking:
            request_body["thinking"] = {"type": analyst.thinking}
        request = urllib.request.Request(
            f"{analyst.api_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        payload: dict[str, Any] = {}
        for attempt in range(1, analyst.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=analyst.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                if exc.code in {408, 409, 425, 429, 500, 502, 503, 504} and attempt < analyst.max_retries:
                    time.sleep(2.0 * attempt)
                    continue
                raise RuntimeError(
                    f"{analyst.provider} API error {exc.code}; response body omitted to avoid leaking secrets."
                ) from exc
            except (http.client.IncompleteRead, http.client.RemoteDisconnected, urllib.error.URLError, TimeoutError) as exc:
                if attempt == analyst.max_retries:
                    raise RuntimeError(
                        f"{analyst.provider} API transport error after {attempt} attempts: {type(exc).__name__}"
                    ) from exc
                time.sleep(1.5 * attempt)
        return str(payload["choices"][0]["message"]["content"])

    return call


def _fixture_transport() -> TransportFn:
    """Deterministic offline responder for dry runs. Never touches the network."""

    def call(context: dict[str, Any], prompt: str) -> str:
        try:
            payload = json.loads(prompt)
            symbols = sorted(str(bar.get("symbol", "")) for bar in payload.get("bars", []) if isinstance(bar, dict))
        except (json.JSONDecodeError, AttributeError, TypeError):
            symbols = []
        symbols = [symbol for symbol in symbols if symbol] or ["SYN"]
        digest = sha256_text(f"{context['model_id']}|{context['seed']}|{context['sample_index']}|{prompt}").split(":", 1)[1]
        weights = []
        for index, symbol in enumerate(symbols):
            nibble = int(digest[(index * 2) % 60 : (index * 2) % 60 + 2], 16)
            weights.append(
                {
                    "symbol": symbol,
                    "target_weight": round(0.05 + (nibble / 255.0) * 0.30, 4),
                    "confidence": 0.7,
                    "horizon": "1w",
                }
            )
        return json.dumps({"weights": weights}, sort_keys=True)

    return call


# ---------------------------------------------------------------------------
# Artifact builders (shape-aligned with scripts/run_v03_direct_api_pilot.py)


def _provider_manifest(packet: dict[str, Any], *, mode: str, result: dict[str, Any]) -> dict[str, Any]:
    prompt_packet = packet["request_envelope"]["prompt_packet"]
    sampling = packet["request_envelope"]["sampling"]
    if mode == "execute":
        claim_scope = (
            "Direct-provider matrix row for the TreLLM v0.3 direct API evidence path; "
            "stress-only execution benchmark row, not a trading-profit claim."
        )
        redaction_notes = (
            "Live direct-provider row. Raw prompts and responses stay in the private run call log; "
            "this manifest publishes hashes and metadata only."
        )
    else:
        claim_scope = (
            "Dry-run protocol fixture for the TreLLM v0.3 direct API evidence path; "
            "no live provider call was made and this row is not model-performance evidence."
        )
        redaction_notes = (
            "Deterministic dry-run fixture; no live API call was made and no raw provider text is published."
        )
    return {
        "schema": "trellm_direct_provider_manifest_v0.1",
        "protocol_id": PROTOCOL_ID,
        "provider_route": "direct-api",
        "provider": str(packet["provider"]),
        "model_id": str(packet["model_id"]),
        "model_version_or_release": str(packet["model_version_or_release"]),
        "api_endpoint_family": str(packet["api_endpoint_family"]),
        "call_window": {
            "call_started_at": result["call_started_at"],
            "call_completed_at": result["call_completed_at"],
            "request_id_redacted": True,
            "retry_count": 0,
        },
        "sampling": {
            "temperature": float(sampling["temperature"]),
            "top_p": float(sampling["top_p"]),
            "max_tokens": int(sampling["max_tokens"]),
        },
        "prompt": {
            "prompt_template_id": str(prompt_packet["prompt_template_id"]),
            "prompt_version": str(prompt_packet["prompt_version"]),
            "prompt_sha256": result["prompt_calls_sha256"],
            "system_prompt_sha256": result["system_prompt_sha256"],
            "raw_prompt_public": False,
        },
        "response": {
            "response_sha256": result["response_calls_sha256"],
            "response_format": "json_object",
            "parse_status": result["parse_status"],
            "raw_response_public": False,
        },
        "redaction": {
            "provider_secrets_removed": True,
            "raw_prompt_public": False,
            "raw_response_public": False,
            "private_account_data_removed": True,
            "redaction_policy": "hash-only-public-manifest",
            "notes": redaction_notes,
        },
        "cache": {
            "cache_status": result["cache_status"],
            "cache_key_sha256": sha256_text(
                ":".join(
                    [
                        str(packet["provider"]),
                        str(packet["model_id"]),
                        str(result["prompt_calls_sha256"]),
                        str(result["response_calls_sha256"]),
                        str(prompt_packet["sample_index"]),
                    ]
                )
            ),
        },
        "run_binding": {
            "scenario_id": str(prompt_packet["scenario_id"]),
            "contamination_tier": str(prompt_packet["contamination_tier"]),
            "execution_level": str(prompt_packet["execution_level"]),
            "seed": int(prompt_packet["seed"]),
            "sample_index": int(prompt_packet["sample_index"]),
            "trajectory_manifest_sha256": result["call_log_sha256"],
        },
        "evidence": {
            "evidence_label": "direct-api",
            "claim_scope": claim_scope,
            "appendix_only": False,
        },
    }


def _benchmark_submission(
    packet: dict[str, Any],
    *,
    mode: str,
    result: dict[str, Any],
    scenario: dict[str, Any],
    level: dict[str, Any],
    periods: int,
    provider_manifest_hash: str,
    call_log_path: Path,
) -> dict[str, Any]:
    prompt_packet = packet["request_envelope"]["prompt_packet"]
    metrics = result["metrics"]
    if mode == "execute":
        provider_mode_tag = "live-provider" if result["cache_status"] == "live_call" else "cached-provider"
        tags = ["stress-only", "direct-api", provider_mode_tag, "redacted-prompt"]
        redaction_notes = (
            "Submission publishes hashes, metrics, and redacted metadata for a live direct-provider run; "
            "raw prompt and response text stays in the private call log."
        )
    else:
        tags = ["stress-only", "direct-api", "protocol-fixture", "redacted-prompt"]
        redaction_notes = (
            "Dry-run protocol fixture submission; no live provider call was made and no raw provider text is included."
        )
    data_hash = sha256_text(
        canonical_json(
            {
                "generator": "synthetic-market",
                "scenario_id": str(prompt_packet["scenario_id"]),
                "seed": int(prompt_packet["seed"]),
                "periods": periods,
                "symbols": list(scenario["symbols"]),
                **scenario["synthetic"],
            }
        )
    )
    return {
        "schema_version": "0.1",
        "scenario_id": str(prompt_packet["scenario_id"]),
        "agent": {
            "provider": str(packet["provider"]),
            "agent_type": "llm_policy",
            "model_family": str(packet["model_id"]),
            "model_display_name": f"{packet['model_id']} ({packet['model_version_or_release']})",
            "model_identifier_redacted": False,
            "prompt_mode": "weights_only",
            "risk_feedback_mode": "true",
            "parse_coverage": float(result["parse_coverage"]),
            "response_format": "json_object",
            "prompt_version": str(prompt_packet["prompt_template_id"]),
            "agent_commit": "v0.3-direct-api-matrix",
        },
        "data_source": {
            "name": str(scenario["data_source_name"]),
            "frequency": str(scenario["frequency"]),
            "symbols": list(scenario["symbols"]),
            "timestamp_policy": "relative_masked",
            "data_hash": data_hash,
        },
        "execution_config": {
            "commission_bps": float(level["commission_bps"]),
            "base_slippage_bps": float(level["slippage_bps"]),
            "spread_bps": float(level["spread_bps"]),
            "latency_steps": int(level["latency_steps"]),
            "participation_rate": float(level["participation_rate"]),
            "market_impact": float(level["market_impact"]),
            "execution_level": str(prompt_packet["execution_level"]),
        },
        "risk_config": {
            "risk_manager": "max-position",
            "risk_budget": {
                "max_position_weight": 0.35,
                "max_gross_exposure": 1.0,
                "max_single_step_turnover": 0.75,
                "risk_feedback_mode": "true",
            },
        },
        "metrics": {
            "total_return": _round6(metrics.get("total_return", 0.0)),
            "max_drawdown": _round6(metrics.get("max_drawdown", 0.0)),
            "sharpe": _round6(metrics.get("sharpe", 0.0)),
            "execution_fill_rate": _round6(metrics.get("execution_fill_rate", 0.0)),
            "total_slippage_cost": _round6(metrics.get("total_slippage_cost", 0.0)),
            "rejected_order_count": int(metrics.get("rejected_order_count", 0)),
            "risk_clipped_decisions": int(metrics.get("risk_clipped_decisions", 0)),
            "risk_violation_count": int(metrics.get("risk_violation_count", 0)),
            "trajectory_reproducibility_coverage": _round6(metrics.get("trajectory_reproducibility_coverage", 0.0)),
        },
        "evidence": evidence_payload(tags),
        "trajectory_manifest": {
            "format": "redacted_manifest",
            "path_or_uri": _display(call_log_path),
            "raw_prompts_included": False,
            "raw_responses_included": False,
            "manifest_hash": result["call_log_sha256"],
            "artifact_hashes": {"direct_provider_manifest": provider_manifest_hash},
        },
        "reproducibility_hash": "",
        "redaction": {
            "provider_secrets_removed": True,
            "timestamps_masked": True,
            "raw_provider_text_removed": True,
            "notes": redaction_notes,
        },
    }


# ---------------------------------------------------------------------------
# Resume, run tables, summary


def _existing_complete(run_record_path: Path, manifest_path: Path, submission_path: Path, *, mode: str) -> tuple[bool, str]:
    if not (run_record_path.exists() and manifest_path.exists() and submission_path.exists()):
        return False, ""
    try:
        record = json.loads(run_record_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, ""
    if record.get("status") != "ok":
        return False, ""
    if record.get("mode") != mode:
        return False, "mode_mismatch"
    _, manifest_errors = validate_direct_provider_manifest_file(manifest_path)
    submission, submission_errors = validate_submission_file(submission_path)
    if manifest_errors or submission_errors:
        return False, ""
    linked_hash = submission.get("trajectory_manifest", {}).get("artifact_hashes", {}).get("direct_provider_manifest", "")
    if linked_hash != sha256_file(manifest_path):
        return False, ""
    return True, ""


def _collect_run_rows(runs_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(runs_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if record.get("schema") == RUN_RECORD_SCHEMA:
            rows.append(record)
    rows.sort(key=lambda row: (str(row.get("provider")), str(row.get("model_id")), int(row.get("seed", 0)), int(row.get("sample_index", 0))))
    return rows


def _write_run_tables(output_root: Path, run_rows: list[dict[str, Any]]) -> None:
    jsonl_path = output_root / "direct_api_submission_runs.jsonl"
    jsonl_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in run_rows),
        encoding="utf-8",
    )
    metric_fields = {
        "total_return",
        "sharpe",
        "max_drawdown",
        "execution_fill_rate",
        "rejected_order_count",
        "risk_clipped_decisions",
        "risk_violation_count",
        "trajectory_reproducibility_coverage",
    }
    csv_rows = []
    for row in run_rows:
        metrics = row.get("metrics", {})
        csv_row = {field: row.get(field, "") for field in RUN_CSV_FIELDS if field not in metric_fields}
        csv_row.update({field: metrics.get(field, "") for field in metric_fields})
        csv_rows.append(csv_row)
    csv_path = output_root / "direct_api_submission_runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_rows)


def _summary(run_rows: list[dict[str, Any]], *, mode: str, packets_path: Path, output_root: Path) -> dict[str, Any]:
    ok_rows = [row for row in run_rows if row.get("status") == "ok"]
    failed_rows = [row for row in run_rows if row.get("status") != "ok"]
    coverage = _coverage(ok_rows)
    return {
        "schema": SUMMARY_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "direct_api_submission_bundle",
        "mode": mode,
        "source_packets": _display(packets_path),
        "run_count": len(run_rows),
        "ok_run_count": len(ok_rows),
        "failed_run_count": len(failed_rows),
        "models": sorted({str(row.get("model_id")) for row in run_rows}),
        "coverage": coverage,
        "claim_boundary": (
            "This bundle turns pre-registered direct API call packets into provider manifests and benchmark "
            "submissions. Dry-run rows are protocol fixtures and stay non-headline; live rows become headline "
            "candidates only after the direct API matrix gate verifies provenance and the 10x3 seed/sample threshold."
        ),
        "gate_command": (
            "python scripts/build_v03_direct_api_matrix_gate.py "
            f"--submission-dirs {_display(output_root / 'submissions')} "
            f"--provider-manifest-dirs {_display(output_root / 'provider_manifests')}"
        ),
        "artifacts": [
            "direct_api_submission_runs.csv",
            "direct_api_submission_runs.jsonl",
            "direct_api_submission_summary.json",
            "direct_api_submission_summary.md",
            "provider_manifests/*.json",
            "submissions/*.json",
            "runs/*.json",
            "private/llm_cache/*.jsonl (private; never publish)",
        ],
    }


def _coverage(ok_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], dict[int, set[int]]] = {}
    modes: dict[tuple[str, str, str, str, str], set[str]] = {}
    for row in ok_rows:
        key = (
            str(row.get("provider")),
            str(row.get("model_id")),
            str(row.get("scenario_id")),
            str(row.get("contamination_tier")),
            str(row.get("execution_level")),
        )
        grouped.setdefault(key, {}).setdefault(int(row.get("seed", 0)), set()).add(int(row.get("sample_index", 0)))
        modes.setdefault(key, set()).add(str(row.get("mode")))
    coverage = []
    for key, samples_by_seed in sorted(grouped.items()):
        provider, model_id, scenario_id, tier, level = key
        coverage.append(
            {
                "provider": provider,
                "model_id": model_id,
                "scenario_id": scenario_id,
                "contamination_tier": tier,
                "execution_level": level,
                "modes": sorted(modes[key]),
                "seed_count": len(samples_by_seed),
                "minimum_samples_per_seed": min((len(samples) for samples in samples_by_seed.values()), default=0),
            }
        )
    return coverage


def _summary_markdown(summary: dict[str, Any], run_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 Direct API Submission Bundle",
        "",
        "Generated by scripts/run_v03_direct_api_submission.py from the pre-registered call packets.",
        "It is not a trading-profit claim; the matrix gate decides whether rows become headline candidates.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Mode: `{summary['mode']}`",
        f"- Source packets: `{summary['source_packets']}`",
        f"- Runs: `{summary['run_count']}` (ok `{summary['ok_run_count']}`, failed `{summary['failed_run_count']}`)",
        f"- Claim boundary: {summary['claim_boundary']}",
        f"- Gate command: `{summary['gate_command']}`",
        "",
        "## Coverage",
        "",
        "| Provider | Model | Scenario | Tier | Execution | Modes | Seeds | Min samples/seed |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for row in summary["coverage"]:
        lines.append(
            f"| {row['provider']} | {row['model_id']} | {row['scenario_id']} | {row['contamination_tier']} | "
            f"{row['execution_level']} | {';'.join(row['modes'])} | {row['seed_count']} | {row['minimum_samples_per_seed']} |"
        )
    failed = [row for row in run_rows if row.get("status") != "ok"]
    if failed:
        lines += ["", "## Failure Rows", "", "| Plan | Error class |", "| --- | --- |"]
        lines.extend(f"| {row.get('plan_id')} | {row.get('error_class')} |" for row in failed)
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Small helpers


def _read_call_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _call_prompt_sha(entry: dict[str, Any]) -> str:
    prompt_hash = str(entry.get("prompt_hash", ""))
    if _HEX64.fullmatch(prompt_hash):
        return f"sha256:{prompt_hash}"
    return sha256_text(str(entry.get("prompt", "")))


def _parse_int_set(value: str, label: str) -> set[int] | None:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        return None
    try:
        return {int(item) for item in items}
    except ValueError as exc:
        raise SystemExit(f"{label} must be a comma-separated list of integers") from exc


def _round6(value: Any) -> float:
    return round(float(value or 0.0), 6)


def _iso_utc(timestamp: int | float) -> str:
    return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
