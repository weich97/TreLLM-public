from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.reproducibility import attach_reproducibility_hash, sha256_file, sha256_text
from tradearena.evaluation.evidence import evidence_payload_for_row, format_evidence_tags
from tradearena.evaluation.statistics import (
    benjamini_hochberg,
    paired_bootstrap_difference,
    sample_std,
    summarize_metric,
)
from tradearena.factory import build_default_system

DEFAULT_LLM_MODELS = (
    "poe:gpt-5.5",
    "poe:gemini-3.1-pro",
    "poe:kimi-k2.5",
    "poe:glm-5",
    "poe:claude-opus-4.7",
    "deepseek:deepseek-v4-flash",
    "deepseek:deepseek-v4-pro",
)
DEFAULT_BASELINES = (
    "baseline:random",
    "baseline:always-hold",
)
DEFAULT_MODELS = DEFAULT_LLM_MODELS + DEFAULT_BASELINES
DEFAULT_SEEDS = (7, 11, 17, 23, 31)
QUALITY_FIELDS = (
    "alpha_pre_risk_total_return",
    "alpha_pre_risk_sharpe",
    "alpha_pre_risk_hit_rate",
    "alpha_pre_risk_steps",
    "alpha_quality_score",
    "risk_discipline_score",
    "execution_robustness_score",
)

REAL_SCENARIOS: dict[str, dict[str, Any]] = {
    "recent_cross_asset": {
        "scenario_id": "leaderboard_real_yahoo_recent_gspc_btc_btcf_weekly_v0_1",
        "label": "Yahoo recent GSPC/BTC/BTC futures",
        "start": "2025-05-01",
        "end": "2026-05-14",
    },
    "rates_drawdown": {
        "scenario_id": "leaderboard_real_yahoo_2022_gspc_btc_btcf_weekly_v0_1",
        "label": "Yahoo 2022 rates drawdown",
        "start": "2022-01-01",
        "end": "2022-12-31",
    },
    "c2_window": {
        # The hash-committed C2 forward window (commitment frozen 2026-06-11,
        # window 2026-07-01..2026-09-15). Evaluated only after window close;
        # driven by scripts/build_v03_c2_window.py, which verifies the frozen
        # declaration hash before invoking this preset.
        "scenario_id": "leaderboard_c2_forward_window_2026q3_weekly_v0_3",
        "label": "C2 forward-frozen window 2026Q3",
        "start": "2026-07-01",
        "end": "2026-09-15",
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run provider-backed LLM leaderboard rows on real Yahoo Finance market data."
    )
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated provider:model entries.")
    parser.add_argument(
        "--scenarios",
        default="recent_cross_asset,rates_drawdown",
        help=f"Comma-separated real-data scenario presets. Available: {', '.join(REAL_SCENARIOS)}.",
    )
    parser.add_argument("--data-dir", default="data/real/yahoo_daily_leaderboard_2021_2026")
    parser.add_argument("--symbols", default="GSPC,BTC-USD,BTC=F")
    parser.add_argument("--frequency", default="weekly", choices=["daily", "weekly"])
    parser.add_argument("--max-periods", type=int, default=12)
    parser.add_argument(
        "--seeds",
        default=",".join(str(seed) for seed in DEFAULT_SEEDS),
        help="Comma-separated benchmark seeds. Real-market seeds are mapped to rolling window offsets.",
    )
    parser.add_argument("--output-dir", default="docs/results/real_market_matrix")
    parser.add_argument("--submission-dir", default="examples/benchmark_submissions/real_market_matrix")
    parser.add_argument("--cache-dir", default="outputs/llm_cache/real_market_matrix")
    parser.add_argument(
        "--provider-mode",
        default="cached",
        choices=["cached", "live"],
        help="Evidence label for provider-backed rows; defaults to cached because public rows are redacted manifests.",
    )
    parser.add_argument("--update-registry", action="store_true")
    args = parser.parse_args(argv)

    output_dir = ROOT / args.output_dir
    submission_dir = ROOT / args.submission_dir
    cache_dir = ROOT / args.cache_dir
    _clean_generated_dir(output_dir)
    _clean_generated_dir(submission_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    data_dir = ROOT / args.data_dir
    symbols = tuple(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip())
    model_specs = [_parse_model_spec(item) for item in args.models.split(",") if item.strip()]
    scenarios = [_scenario(name) for name in args.scenarios.split(",") if name.strip()]
    seeds = _parse_seeds(args.seeds)
    data_hash = _data_hash(data_dir, symbols)

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for scenario in scenarios:
        for provider, model in model_specs:
            for seed_index, seed in enumerate(seeds):
                try:
                    row = _run_one(
                        provider=provider,
                        model=model,
                        scenario=scenario,
                        symbols=symbols,
                        frequency=args.frequency,
                        max_periods=args.max_periods,
                        seed=int(seed),
                        window_offset=seed_index,
                        data_dir=data_dir,
                        data_hash=data_hash,
                        output_dir=output_dir,
                        submission_dir=submission_dir,
                        cache_dir=cache_dir,
                        provider_mode=args.provider_mode,
                    )
                    rows.append(row)
                    print(
                        f"OK {row['scenario_key']} seed={row['seed']} {provider}:{model} -> {row['submission']}",
                        flush=True,
                    )
                except Exception as exc:  # pragma: no cover - live provider/data failures
                    failures.append(
                        {
                            "scenario": str(scenario["key"]),
                            "seed": str(seed),
                            "provider": provider,
                            "model": model,
                            "error": type(exc).__name__,
                        }
                    )
                    print(
                        f"FAILED {scenario['key']} seed={seed} {provider}:{model}: {type(exc).__name__}: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )

    _write_matrix_table(output_dir / "real_market_model_matrix.csv", rows)
    aggregate_rows = _aggregate_rows(rows)
    _write_aggregate_table(output_dir / "real_market_model_matrix_aggregate.csv", aggregate_rows)
    scenario_rows = _scenario_aggregate_rows(rows)
    _write_scenario_aggregate_table(output_dir / "real_market_model_matrix_scenario_aggregate.csv", scenario_rows)
    significance_rows = _significance_rows(rows)
    _write_significance_table(output_dir / "real_market_model_matrix_significance.csv", significance_rows)
    walk_forward_rows = _walk_forward_rows(rows)
    _write_walk_forward_table(output_dir / "real_market_walk_forward.csv", walk_forward_rows)
    _write_matrix_markdown(
        output_dir / "real_market_model_matrix.md",
        rows,
        aggregate_rows,
        scenario_rows,
        significance_rows,
        walk_forward_rows,
        failures,
    )
    if failures:
        (output_dir / "real_market_model_matrix_failures.json").write_text(
            json.dumps(failures, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if args.update_registry:
        from tradearena.evaluation.submissions import build_registry_rows, write_registry_html, write_registry_markdown

        registry_rows, errors = build_registry_rows(ROOT / "examples" / "benchmark_submissions")
        if errors:
            raise RuntimeError("Registry build failed:\n" + "\n".join(errors))
        for row in registry_rows:
            source_file = Path(str(row.get("source_file", "")))
            if source_file.is_absolute():
                try:
                    row["source_file"] = source_file.resolve().relative_to(ROOT).as_posix()
                except ValueError:
                    row["source_file"] = source_file.as_posix()
        write_registry_markdown(registry_rows, ROOT / "docs/results/community_registry.md")
        write_registry_html(registry_rows, ROOT / "docs/results/community_registry.html")
        _write_registry_csv(registry_rows, ROOT / "docs/results/community_registry.csv")

    print(f"Successful real-market rows: {len(rows)}")
    if failures:
        print(f"Failed real-market rows: {len(failures)}")
    return 0 if rows else 1


def _run_one(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
    symbols: tuple[str, ...],
    frequency: str,
    max_periods: int,
    seed: int,
    window_offset: int,
    data_dir: Path,
    data_hash: str,
    output_dir: Path,
    submission_dir: Path,
    cache_dir: Path,
    provider_mode: str,
) -> dict[str, Any]:
    model_slug = _slug(f"{provider}-{model}")
    scenario_key = str(scenario["key"])
    slug = f"{scenario_key}__{model_slug}__seed_{seed}"
    analyst_name = _analyst_name(provider)
    strategy_name = _strategy_name(provider, model)
    trajectory, metrics = build_default_system(
        name=f"real_leaderboard_{slug}",
        symbols=symbols,
        periods=max_periods,
        seed=seed,
        analyst_names=(analyst_name,) if analyst_name else (),
        strategy_name=strategy_name,
        risk_name="max-position",
        execution_mode="realistic",
        data_source="csv",
        real_data_dir=str(data_dir),
        real_data_frequency=frequency,
        real_data_start=str(scenario["start"]),
        real_data_end=str(scenario["end"]),
        real_data_max_periods=max_periods,
        real_data_window_offset=window_offset,
        llm_model=model,
        llm_cache_path=str(cache_dir / f"{scenario_key}__{model_slug}.jsonl"),
        llm_mask_timestamps=True,
        llm_use_risk_feedback=True,
        llm_risk_feedback_mode="true",
    ).run()

    parse_coverage = 1.0 if provider == "baseline" else _parse_coverage(trajectory.to_dict(), symbols)
    evidence = evidence_payload_for_row(
        provider=provider,
        execution_mode="realistic-stress",
        provider_mode=provider_mode,
        raw_provider_text_removed=True,
        trajectory_format="redacted_manifest",
    )
    evidence_tags = format_evidence_tags(evidence["tags"])
    metrics_payload = {
        "total_return": float(metrics.get("total_return", 0.0)),
        "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
        "sharpe": float(metrics.get("sharpe", 0.0)),
        "execution_fill_rate": float(metrics.get("execution_fill_rate", 0.0)),
        "rejected_order_count": int(metrics.get("rejected_order_count", 0)),
        "risk_clipped_decisions": int(metrics.get("risk_clipped_decisions", 0)),
        "risk_violation_count": int(metrics.get("risk_violation_count", 0)),
        "trajectory_reproducibility_coverage": float(metrics.get("trajectory_reproducibility_coverage", 0.0)),
        **_quality_metrics(metrics),
    }
    summary = {
        "schema_version": "0.1",
        "scenario_id": scenario["scenario_id"],
        "scenario_label": scenario["label"],
        "provider": provider,
        "model": model,
        "symbols": list(symbols),
        "frequency": frequency,
        "start": scenario["start"],
        "end": scenario["end"],
        "max_periods": max_periods,
        "seed": seed,
        "window_offset": window_offset,
        "walk_forward_unit": "rolling_window_offset",
        "parse_coverage": parse_coverage,
        "metrics": metrics_payload,
        "evidence": evidence,
        "evaluation_protocol": {
            "repeat_unit": "seed_mapped_to_window_offset",
            "cache_policy": _cache_policy(provider),
            "provider_call_policy": _provider_call_policy(provider),
            "provider_drift_guard": _provider_drift_guard(provider),
            "statistical_tests": ["bootstrap_ci", "paired_bootstrap", "paired_sign_flip_permutation", "benjamini_hochberg_fdr", "paired_cohens_d", "cliffs_delta"],
        },
        "redaction": {
            "raw_prompts_included": False,
            "raw_responses_included": False,
            "timestamps_masked": True,
        },
    }
    summary_path = output_dir / f"{slug}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_hash = sha256_file(summary_path)

    submission = attach_reproducibility_hash(
        {
            "schema_version": "0.1",
            "scenario_id": scenario["scenario_id"],
            "agent": {
                "provider": provider,
                "agent_type": "control_policy" if provider == "baseline" else "llm_policy",
                "model_family": model,
                "model_display_name": model,
                "model_identifier_redacted": False,
                "prompt_mode": "rationale",
                "risk_feedback_mode": "true",
                "parse_coverage": parse_coverage,
                "response_format": "json_object",
                "prompt_version": "risk-feedback-v1",
                "agent_commit": "redacted-or-local",
            },
            "data_source": {
                "name": "yahoo-finance-csv",
                "frequency": frequency,
                "symbols": list(symbols),
                "timestamp_policy": "relative_masked",
                "data_hash": data_hash,
            },
            "evaluation_protocol": {
                "repeat_unit": "seed_mapped_to_window_offset",
                "window_offset": window_offset,
                "cache_policy": _cache_policy(provider),
                "provider_call_policy": _provider_call_policy(provider),
                "provider_drift_guard": _provider_drift_guard(provider),
                "statistical_tests": ["bootstrap_ci", "paired_bootstrap", "paired_sign_flip_permutation", "benjamini_hochberg_fdr", "paired_cohens_d", "cliffs_delta"],
            },
            "execution_config": {
                "commission_bps": 1.0,
                "base_slippage_bps": 2.0,
                "spread_bps": 0.0,
                "latency_steps": 1,
                "participation_rate": 0.05,
                "market_impact": 0.15,
            },
            "risk_config": {
                "risk_manager": "max-position",
                "risk_budget": {
                    "max_position_weight": 0.35,
                    "max_gross_exposure": 1.0,
                    "max_single_step_turnover": 0.75,
                    "max_drawdown": 0.20,
                    "drawdown_lookback": 5,
                    "drawdown_de_risk_weight": 0.0,
                    "risk_feedback_mode": "true",
                },
            },
            "metrics": metrics_payload,
            "evidence": evidence,
            "trajectory_manifest": {
                "format": "redacted_manifest",
                "path_or_uri": _rel(summary_path),
                "raw_prompts_included": False,
                "raw_responses_included": False,
                "manifest_hash": summary_hash,
                "artifact_hashes": {"redacted_summary": summary_hash},
            },
            "redaction": {
                "provider_secrets_removed": True,
                "timestamps_masked": True,
                "raw_provider_text_removed": True,
                "notes": (
                    "Real-market leaderboard manifest generated from Yahoo Finance CSV data. "
                    "Raw prompts and responses remain in ignored local cache files."
                ),
            },
        }
    )
    submission_path = submission_dir / f"{slug}.json"
    submission_path.write_text(json.dumps(submission, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "scenario_key": scenario_key,
        "scenario_id": scenario["scenario_id"],
        "scenario_label": scenario["label"],
        "provider": provider,
        "model": model,
        "seed": seed,
        "window_offset": window_offset,
        "frequency": frequency,
        "start": scenario["start"],
        "end": scenario["end"],
        "max_periods": max_periods,
        "walk_forward_unit": "rolling_window_offset",
        "cache_policy": _cache_policy(provider),
        "provider_call_policy": _provider_call_policy(provider),
        "provider_drift_guard": _provider_drift_guard(provider),
        "timestamp_policy": "relative_masked",
        "data_hash": data_hash,
        "parse_coverage": parse_coverage,
        "evidence_tags": evidence_tags,
        "claim_scope": evidence["claim_scope"],
        **metrics_payload,
        "reproducibility_hash": submission["reproducibility_hash"],
        "submission": _rel(submission_path),
        "summary": _rel(summary_path),
    }


def _parse_model_spec(value: str) -> tuple[str, str]:
    if ":" in value:
        provider, model = value.split(":", 1)
    else:
        provider, model = "poe", value
    provider = provider.strip().lower()
    model = model.strip()
    if provider not in {"poe", "deepseek", "glm", "baseline"}:
        raise ValueError(f"Unsupported provider in model spec: {value}")
    if not model:
        raise ValueError(f"Missing model name in model spec: {value}")
    if provider == "baseline" and model not in {"random", "always-hold"}:
        raise ValueError(f"Unsupported baseline model: {model}")
    return provider, model


def _parse_seeds(value: str) -> tuple[int, ...]:
    return tuple(int(seed.strip()) for seed in value.split(",") if seed.strip())


def _analyst_name(provider: str) -> str:
    if provider == "poe":
        return "poe-llm"
    if provider == "deepseek":
        return "deepseek-llm"
    if provider == "glm":
        return "glm-llm"
    return ""


def _strategy_name(provider: str, model: str) -> str:
    if provider != "baseline":
        return "signal-weighted"
    return "random-allocation" if model == "random" else "always-hold"


def _scenario(name: str) -> dict[str, Any]:
    key = name.strip()
    if key not in REAL_SCENARIOS:
        raise ValueError(f"Unknown real scenario preset: {key}. Available: {', '.join(REAL_SCENARIOS)}")
    scenario = dict(REAL_SCENARIOS[key])
    scenario["key"] = key
    return scenario


def _parse_coverage(trajectory: dict[str, Any], symbols: tuple[str, ...]) -> float:
    steps = trajectory.get("steps", [])
    expected = max(1, len(steps) * max(1, len(symbols)))
    observed = 0
    for step in steps:
        signals = step.get("signals", []) if isinstance(step, dict) else []
        if isinstance(signals, list):
            observed += sum(1 for signal in signals if isinstance(signal, dict) and signal.get("symbol") in symbols)
    return round(min(1.0, observed / expected), 4)


def _quality_metrics(metrics: dict[str, float | int | str]) -> dict[str, float | int]:
    return {
        "alpha_pre_risk_total_return": float(metrics.get("alpha_pre_risk_total_return", 0.0)),
        "alpha_pre_risk_sharpe": float(metrics.get("alpha_pre_risk_sharpe", 0.0)),
        "alpha_pre_risk_hit_rate": float(metrics.get("alpha_pre_risk_hit_rate", 0.0)),
        "alpha_pre_risk_steps": int(metrics.get("alpha_pre_risk_steps", 0)),
        "alpha_quality_score": float(metrics.get("alpha_quality_score", 0.0)),
        "risk_discipline_score": float(metrics.get("risk_discipline_score", 0.0)),
        "execution_robustness_score": float(metrics.get("execution_robustness_score", 0.0)),
    }


def _data_hash(data_dir: Path, symbols: tuple[str, ...]) -> str:
    file_hashes = []
    for symbol in symbols:
        path = data_dir / f"{_safe_symbol(symbol)}_Daily_2021_2026.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing Yahoo CSV for {symbol}: {path}")
        file_hashes.append({"symbol": symbol, "sha256": sha256_file(path)})
    manifest = data_dir / "manifest.json"
    if manifest.exists():
        file_hashes.append({"symbol": "__manifest__", "sha256": sha256_file(manifest)})
    return sha256_text(json.dumps(file_hashes, sort_keys=True, separators=(",", ":")))


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["provider"]), str(row["model"])), []).append(row)
    aggregate_rows = []
    for (provider, model), model_rows in sorted(grouped.items()):
        return_stats = summarize_metric((row["total_return"] for row in model_rows), prefix="return")
        sharpe_stats = summarize_metric((row["sharpe"] for row in model_rows), prefix="sharpe")
        hold_test = _baseline_test(rows, model_rows, baseline_model="always-hold")
        random_test = _baseline_test(rows, model_rows, baseline_model="random")
        aggregate_rows.append(
            {
                "provider": provider,
                "model": model,
                "scenario_count": len({row["scenario_key"] for row in model_rows}),
                "run_count": len(model_rows),
                "avg_return": return_stats["return_mean"],
                "std_return": return_stats["return_std"],
                "return_ci_low": return_stats["return_ci_low"],
                "return_ci_high": return_stats["return_ci_high"],
                "worst_drawdown": min(float(row["max_drawdown"]) for row in model_rows),
                "avg_sharpe": sharpe_stats["sharpe_mean"],
                "std_sharpe": sharpe_stats["sharpe_std"],
                "sharpe_ci_low": sharpe_stats["sharpe_ci_low"],
                "sharpe_ci_high": sharpe_stats["sharpe_ci_high"],
                "avg_fill_rate": _avg(row["execution_fill_rate"] for row in model_rows),
                "total_rejected_orders": sum(int(row["rejected_order_count"]) for row in model_rows),
                "total_risk_edits": sum(int(row["risk_clipped_decisions"]) for row in model_rows),
                "avg_parse_coverage": _avg(row["parse_coverage"] for row in model_rows),
                "avg_alpha_quality": _avg(row["alpha_quality_score"] for row in model_rows),
                "avg_risk_discipline": _avg(row["risk_discipline_score"] for row in model_rows),
                "avg_execution_robustness": _avg(row["execution_robustness_score"] for row in model_rows),
                "evidence_tags": _collapse_values(row.get("evidence_tags", "") for row in model_rows),
                "claim_scope": _collapse_values(row.get("claim_scope", "") for row in model_rows),
                "delta_return_vs_hold": hold_test["mean_delta"],
                "delta_return_vs_hold_ci_low": hold_test["delta_ci_low"],
                "delta_return_vs_hold_ci_high": hold_test["delta_ci_high"],
                "p_value_vs_hold": hold_test["p_value"],
                "bootstrap_p_value_vs_hold": hold_test["bootstrap_p_value"],
                "permutation_p_value_vs_hold": hold_test["permutation_p_value"],
                "paired_n_vs_hold": hold_test["paired_n"],
                "cohens_d_vs_hold": hold_test["cohens_d"],
                "cliffs_delta_vs_hold": hold_test["cliffs_delta"],
                "delta_return_vs_random": random_test["mean_delta"],
                "p_value_vs_random": random_test["p_value"],
                "bootstrap_p_value_vs_random": random_test["bootstrap_p_value"],
                "permutation_p_value_vs_random": random_test["permutation_p_value"],
                "paired_n_vs_random": random_test["paired_n"],
                "cohens_d_vs_random": random_test["cohens_d"],
                "cliffs_delta_vs_random": random_test["cliffs_delta"],
            }
        )
    _attach_fdr_q_values(aggregate_rows)
    return sorted(
        aggregate_rows,
        key=lambda row: (
            -float(row["avg_return"]),
            float(row["worst_drawdown"]),
            -float(row["avg_fill_rate"]),
        ),
    )


def _scenario_aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["scenario_key"]), str(row["provider"]), str(row["model"])), []).append(row)
    output = []
    for (scenario_key, provider, model), model_rows in sorted(grouped.items()):
        return_stats = summarize_metric((row["total_return"] for row in model_rows), prefix="return")
        output.append(
            {
                "scenario_key": scenario_key,
                "scenario_label": model_rows[0]["scenario_label"],
                "provider": provider,
                "model": model,
                "run_count": len(model_rows),
                "avg_return": return_stats["return_mean"],
                "std_return": return_stats["return_std"],
                "return_ci_low": return_stats["return_ci_low"],
                "return_ci_high": return_stats["return_ci_high"],
                "worst_drawdown": min(float(row["max_drawdown"]) for row in model_rows),
                "avg_sharpe": _avg(row["sharpe"] for row in model_rows),
                "std_sharpe": sample_std(row["sharpe"] for row in model_rows),
                "avg_fill_rate": _avg(row["execution_fill_rate"] for row in model_rows),
                "avg_alpha_quality": _avg(row["alpha_quality_score"] for row in model_rows),
                "avg_risk_discipline": _avg(row["risk_discipline_score"] for row in model_rows),
                "avg_execution_robustness": _avg(row["execution_robustness_score"] for row in model_rows),
                "evidence_tags": _collapse_values(row.get("evidence_tags", "") for row in model_rows),
                "claim_scope": _collapse_values(row.get("claim_scope", "") for row in model_rows),
            }
        )
    return sorted(output, key=lambda row: (str(row["scenario_key"]), -float(row["avg_return"])))


def _walk_forward_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["scenario_key"]), str(row["provider"]), str(row["model"])), []).append(row)
    output = []
    for (scenario_key, provider, model), model_rows in sorted(grouped.items()):
        return_stats = summarize_metric((row["total_return"] for row in model_rows), prefix="return")
        offsets = sorted({int(row.get("window_offset", 0)) for row in model_rows})
        seeds = sorted({int(row.get("seed", 0)) for row in model_rows})
        scenario = REAL_SCENARIOS.get(scenario_key, {})
        output.append(
            {
                "scenario_key": scenario_key,
                "scenario_label": model_rows[0].get("scenario_label", scenario.get("label", "")),
                "provider": provider,
                "model": model,
                "run_count": len(model_rows),
                "seed_count": len(seeds),
                "seeds": ",".join(str(seed) for seed in seeds),
                "window_offsets": ",".join(str(offset) for offset in offsets),
                "frequency": _collapse_values(row.get("frequency", "weekly") for row in model_rows),
                "start": _collapse_values(row.get("start", scenario.get("start", "")) for row in model_rows),
                "end": _collapse_values(row.get("end", scenario.get("end", "")) for row in model_rows),
                "max_periods": _collapse_values(row.get("max_periods", "") for row in model_rows),
                "return_mean": return_stats["return_mean"],
                "return_std": return_stats["return_std"],
                "return_ci_low": return_stats["return_ci_low"],
                "return_ci_high": return_stats["return_ci_high"],
                "evidence_tags": _collapse_values(row.get("evidence_tags", "") for row in model_rows),
                "claim_scope": _collapse_values(row.get("claim_scope", "") for row in model_rows),
                "provider_call_policy": _collapse_values(
                    row.get("provider_call_policy", _provider_call_policy(provider)) for row in model_rows
                ),
                "cache_policy": _collapse_values(row.get("cache_policy", _cache_policy(provider)) for row in model_rows),
                "timestamp_policy": _collapse_values(row.get("timestamp_policy", "relative_masked") for row in model_rows),
                "provider_drift_guard": _provider_drift_guard(provider),
            }
        )
    return output


def _significance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["provider"]), str(row["model"])), []).append(row)
    output = []
    for (provider, model), model_rows in sorted(grouped.items()):
        for baseline_model in ("always-hold", "random"):
            result = _baseline_test(rows, model_rows, baseline_model=baseline_model)
            output.append(
                {
                    "provider": provider,
                    "model": model,
                    "baseline_provider": "baseline",
                    "baseline_model": baseline_model,
                    "paired_n": result["paired_n"],
                    "mean_return_delta": result["mean_delta"],
                    "delta_ci_low": result["delta_ci_low"],
                    "delta_ci_high": result["delta_ci_high"],
                    "bootstrap_p_value": result["bootstrap_p_value"],
                    "permutation_p_value": result["permutation_p_value"],
                    "cohens_d": result["cohens_d"],
                    "cliffs_delta": result["cliffs_delta"],
                }
            )
    bootstrap_q = benjamini_hochberg(
        {index: row["bootstrap_p_value"] for index, row in enumerate(output)}
    )
    permutation_q = benjamini_hochberg(
        {index: row["permutation_p_value"] for index, row in enumerate(output)}
    )
    for index, row in enumerate(output):
        row["bootstrap_q_value"] = bootstrap_q[index]
        row["permutation_q_value"] = permutation_q[index]
    return output


def _attach_fdr_q_values(aggregate_rows: list[dict[str, Any]]) -> None:
    """BH-FDR over the full model x baseline test family of this matrix run."""

    family: dict[tuple[int, str], float | None] = {}
    for index, row in enumerate(aggregate_rows):
        family[(index, "hold")] = row.get("bootstrap_p_value_vs_hold")
        family[(index, "random")] = row.get("bootstrap_p_value_vs_random")
    q_values = benjamini_hochberg(family)
    for index, row in enumerate(aggregate_rows):
        row["q_value_vs_hold"] = q_values[(index, "hold")]
        row["q_value_vs_random"] = q_values[(index, "random")]


def _baseline_test(
    all_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    baseline_model: str,
) -> dict[str, float | int | None]:
    candidate = {
        (str(row["scenario_key"]), str(row["seed"])): float(row["total_return"])
        for row in candidate_rows
    }
    baseline = {
        (str(row["scenario_key"]), str(row["seed"])): float(row["total_return"])
        for row in all_rows
        if row.get("provider") == "baseline" and row.get("model") == baseline_model
    }
    return paired_bootstrap_difference(candidate, baseline)


def _write_matrix_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scenario_key",
        "scenario_id",
        "scenario_label",
        "provider",
        "model",
        "seed",
        "window_offset",
        "frequency",
        "start",
        "end",
        "max_periods",
        "walk_forward_unit",
        "cache_policy",
        "provider_call_policy",
        "provider_drift_guard",
        "timestamp_policy",
        "data_hash",
        "parse_coverage",
        "evidence_tags",
        "claim_scope",
        "total_return",
        "max_drawdown",
        "sharpe",
        "execution_fill_rate",
        "rejected_order_count",
        "risk_clipped_decisions",
        "risk_violation_count",
        "trajectory_reproducibility_coverage",
        *QUALITY_FIELDS,
        "reproducibility_hash",
        "submission",
        "summary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_aggregate_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "provider",
        "model",
        "scenario_count",
        "run_count",
        "avg_return",
        "std_return",
        "return_ci_low",
        "return_ci_high",
        "worst_drawdown",
        "avg_sharpe",
        "std_sharpe",
        "sharpe_ci_low",
        "sharpe_ci_high",
        "avg_fill_rate",
        "total_rejected_orders",
        "total_risk_edits",
        "avg_parse_coverage",
        "avg_alpha_quality",
        "avg_risk_discipline",
        "avg_execution_robustness",
        "evidence_tags",
        "claim_scope",
        "delta_return_vs_hold",
        "delta_return_vs_hold_ci_low",
        "delta_return_vs_hold_ci_high",
        "p_value_vs_hold",
        "bootstrap_p_value_vs_hold",
        "permutation_p_value_vs_hold",
        "paired_n_vs_hold",
        "q_value_vs_hold",
        "cohens_d_vs_hold",
        "cliffs_delta_vs_hold",
        "delta_return_vs_random",
        "p_value_vs_random",
        "bootstrap_p_value_vs_random",
        "permutation_p_value_vs_random",
        "paired_n_vs_random",
        "q_value_vs_random",
        "cohens_d_vs_random",
        "cliffs_delta_vs_random",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_scenario_aggregate_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scenario_key",
        "scenario_label",
        "provider",
        "model",
        "run_count",
        "avg_return",
        "std_return",
        "return_ci_low",
        "return_ci_high",
        "worst_drawdown",
        "avg_sharpe",
        "std_sharpe",
        "avg_fill_rate",
        "avg_alpha_quality",
        "avg_risk_discipline",
        "avg_execution_robustness",
        "evidence_tags",
        "claim_scope",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_significance_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "provider",
        "model",
        "baseline_provider",
        "baseline_model",
        "paired_n",
        "mean_return_delta",
        "delta_ci_low",
        "delta_ci_high",
        "bootstrap_p_value",
        "permutation_p_value",
        "bootstrap_q_value",
        "permutation_q_value",
        "cohens_d",
        "cliffs_delta",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_walk_forward_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scenario_key",
        "scenario_label",
        "provider",
        "model",
        "run_count",
        "seed_count",
        "seeds",
        "window_offsets",
        "frequency",
        "start",
        "end",
        "max_periods",
        "return_mean",
        "return_std",
        "return_ci_low",
        "return_ci_high",
        "evidence_tags",
        "claim_scope",
        "provider_call_policy",
        "cache_policy",
        "timestamp_policy",
        "provider_drift_guard",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_matrix_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    aggregate_rows: list[dict[str, Any]],
    scenario_rows: list[dict[str, Any]],
    significance_rows: list[dict[str, Any]],
    walk_forward_rows: list[dict[str, Any]],
    failures: list[dict[str, str]],
) -> None:
    lines = [
        "# Real-Market Leaderboard Matrix",
        "",
        "This table is generated by `python scripts/run_real_market_leaderboard.py --update-registry`.",
        "It uses Yahoo Finance daily CSVs for `GSPC`, `BTC-USD`, and `BTC=F` and records redacted manifests only.",
        "Raw provider prompts and responses remain in ignored local caches.",
        "The default protocol evaluates five rolling-window seeds per `(model, scenario)` and reports mean, sample standard deviation, 95% bootstrap confidence intervals, paired bootstrap tests, and paired sign-flip permutation tests against `always-hold` and `random` anchors.",
        "",
        "## Result Interpretation",
        "",
        *_interpretation_lines(aggregate_rows, scenario_rows),
        "",
        "## Cross-Scenario Aggregate",
        "",
        "| Rank | Provider | Model | Evidence | Scenarios | Runs | Return mean +- std | 95% CI | Worst DD | Sharpe mean +- std | Avg fill | Alpha | Risk | Execution | boot p vs hold | perm p vs hold | boot p vs random | perm p vs random | Parse |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(aggregate_rows, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    str(row["provider"]),
                    str(row["model"]),
                    _format_evidence(row.get("evidence_tags", "")),
                    str(row["scenario_count"]),
                    str(row["run_count"]),
                    _fmt_pm(row["avg_return"], row["std_return"]),
                    _fmt_ci(row["return_ci_low"], row["return_ci_high"]),
                    _fmt(row["worst_drawdown"]),
                    _fmt_pm(row["avg_sharpe"], row["std_sharpe"]),
                    _fmt(row["avg_fill_rate"]),
                    _fmt(row["avg_alpha_quality"]),
                    _fmt(row["avg_risk_discipline"]),
                    _fmt(row["avg_execution_robustness"]),
                    _fmt(row["bootstrap_p_value_vs_hold"]),
                    _fmt(row["permutation_p_value_vs_hold"]),
                    _fmt(row["bootstrap_p_value_vs_random"]),
                    _fmt(row["permutation_p_value_vs_random"]),
                    _fmt(row["avg_parse_coverage"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Scenario Aggregates",
            "",
            "| Scenario | Provider | Model | Evidence | Runs | Return mean +- std | 95% CI | Worst DD | Sharpe mean +- std | Alpha | Risk | Execution | Fill |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in scenario_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["scenario_label"]),
                    str(row["provider"]),
                    str(row["model"]),
                    _format_evidence(row.get("evidence_tags", "")),
                    str(row["run_count"]),
                    _fmt_pm(row["avg_return"], row["std_return"]),
                    _fmt_ci(row["return_ci_low"], row["return_ci_high"]),
                    _fmt(row["worst_drawdown"]),
                    _fmt_pm(row["avg_sharpe"], row["std_sharpe"]),
                    _fmt(row["avg_alpha_quality"]),
                    _fmt(row["avg_risk_discipline"]),
                    _fmt(row["avg_execution_robustness"]),
                    _fmt(row["avg_fill_rate"]),
                ]
            )
            + " |"
        )
    if significance_rows:
        lines.extend(
            [
                "",
                "## Paired Bootstrap Tests",
                "",
                "Positive deltas mean the model beat the named anchor on matched `(scenario, seed)` rolling-window runs. The permutation column is a paired sign-flip test, which is less sensitive to bootstrap distribution shape when only a few windows are available.",
                "",
                "| Provider | Model | Baseline | Paired n | Mean return delta | 95% CI | Bootstrap p | Permutation p |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in significance_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["provider"]),
                        str(row["model"]),
                        str(row["baseline_model"]),
                        str(row["paired_n"]),
                        _fmt(row["mean_return_delta"]),
                        _fmt_ci(row["delta_ci_low"], row["delta_ci_high"]),
                        _fmt(row["bootstrap_p_value"]),
                        _fmt(row["permutation_p_value"]),
                    ]
                )
                + " |"
            )
    if walk_forward_rows:
        lines.extend(
            [
                "",
                "## Walk-Forward / Provenance Checks",
                "",
                "Each real-market seed maps to a rolling window offset. Provider-backed rows keep raw text in ignored caches and publish redacted manifests with provider/model labels, masked timestamps, and data hashes; this reduces cache-bias ambiguity and makes provider drift auditable without exposing prompts.",
                "",
                "| Scenario | Provider | Model | Evidence | Runs | Seeds | Window offsets | Period | Return mean +- std | 95% CI | Provider policy | Cache policy |",
                "| --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for row in walk_forward_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["scenario_label"]),
                        str(row["provider"]),
                        str(row["model"]),
                        _format_evidence(row.get("evidence_tags", "")),
                        str(row["run_count"]),
                        str(row["seed_count"]),
                        str(row["window_offsets"]),
                        f"{row['start']} to {row['end']} ({row['frequency']}, max {row['max_periods']})",
                        _fmt_pm(row["return_mean"], row["return_std"]),
                        _fmt_ci(row["return_ci_low"], row["return_ci_high"]),
                        str(row["provider_call_policy"]),
                        str(row["cache_policy"]),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Raw Seed Rows",
            "",
            "Per-seed rows, manifest links, and reproducibility hashes are stored in `real_market_model_matrix.csv`.",
        ]
    )
    if failures:
        lines.extend(["", "## Provider Failures", ""])
        for failure in failures:
            lines.append(
                f"- `{failure['scenario']}:{failure['provider']}:{failure['model']}` failed with `{failure['error']}`."
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _interpretation_lines(
    aggregate_rows: list[dict[str, Any]],
    scenario_rows: list[dict[str, Any]],
) -> list[str]:
    baseline_rows = [row for row in aggregate_rows if row.get("provider") == "baseline"]
    llm_rows = [row for row in aggregate_rows if row.get("provider") != "baseline"]
    total_runs = sum(int(row["run_count"]) for row in aggregate_rows)
    lines = [
        f"- The tracked snapshot contains {total_runs} real-market runs across {len(aggregate_rows)} policies. "
        "Each policy is evaluated on matched rolling-window seeds, so the paired tests compare like-for-like market windows rather than isolated point estimates.",
    ]
    if baseline_rows:
        best_baseline = max(baseline_rows, key=lambda row: float(row["avg_return"]))
        lines.append(
            f"- The strongest anchor is `{best_baseline['provider']}:{best_baseline['model']}` with mean return "
            f"{_fmt(best_baseline['avg_return'])} and 95% CI {_fmt_ci(best_baseline['return_ci_low'], best_baseline['return_ci_high'])}. "
            "This anchor is intentionally reported beside LLM policies so the leaderboard asks whether model reasoning adds signal after risk and execution costs."
        )
    if llm_rows:
        best_llm = max(llm_rows, key=lambda row: float(row["avg_return"]))
        positive_vs_hold = [
            row for row in llm_rows if float(row.get("delta_return_vs_hold") or 0.0) > 0.0
        ]
        significant_vs_random = [
            row
            for row in llm_rows
            if float(row.get("delta_return_vs_random") or 0.0) > 0.0
            and float(row.get("p_value_vs_random") or 1.0) < 0.05
        ]
        lines.append(
            f"- The best provider-backed LLM is `{best_llm['provider']}:{best_llm['model']}` with mean return "
            f"{_fmt(best_llm['avg_return'])} +- {_fmt(best_llm['std_return'])}, worst drawdown "
            f"{_fmt(best_llm['worst_drawdown'])}, and average fill rate {_fmt(best_llm['avg_fill_rate'])}. "
            f"{len(positive_vs_hold)} LLM policies have a positive paired mean return delta versus `always-hold`, "
            f"and {len(significant_vs_random)} beat the `random` anchor at p < 0.05 in this snapshot."
        )
        lines.append(
            "- The current result is therefore a reliability finding, not a profitability claim: the LLM policies still produce active risk edits and execution exposure, but their realized returns do not consistently dominate simple anchors on these two Yahoo windows."
        )
    scenario_groups: dict[str, list[dict[str, Any]]] = {}
    for row in scenario_rows:
        if row.get("provider") == "baseline":
            continue
        scenario_groups.setdefault(str(row["scenario_label"]), []).append(row)
    if scenario_groups:
        scenario_means = [
            (label, _avg(row["avg_return"] for row in rows))
            for label, rows in scenario_groups.items()
        ]
        hardest_label, hardest_return = min(scenario_means, key=lambda item: item[1])
        easiest_label, easiest_return = max(scenario_means, key=lambda item: item[1])
        lines.append(
            f"- Scenario-level diagnostics show `{hardest_label}` as the hardest LLM window "
            f"(mean provider-backed return {_fmt(hardest_return)}), while `{easiest_label}` is less severe "
            f"(mean provider-backed return {_fmt(easiest_return)}). This separation is why the report keeps scenario aggregates in addition to the cross-scenario rank."
        )
    return lines


def _write_registry_csv(rows: list[dict[str, object]], path: Path) -> None:
    fieldnames = list(rows[0]) if rows else ["scenario_id"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _clean_generated_dir(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file() and child.suffix.lower() in {".json", ".csv", ".md"}:
            child.unlink()


def _safe_symbol(symbol: str) -> str:
    return symbol.replace("^", "").replace("/", "-")


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"{float(value):.4f}"


def _fmt_pm(mean_value: Any, std_value: Any) -> str:
    return f"{_fmt(mean_value)} +- {_fmt(std_value)}"


def _fmt_ci(low: Any, high: Any) -> str:
    if low is None or high is None:
        return ""
    return f"[{_fmt(low)}, {_fmt(high)}]"


def _format_evidence(value: Any) -> str:
    tags = [tag for tag in str(value or "").split(";") if tag]
    return "<br>".join(f"`{tag}`" for tag in tags)


def _avg(values: Any) -> float:
    numbers = [float(value) for value in values]
    return sum(numbers) / len(numbers) if numbers else 0.0


def _cache_policy(provider: str) -> str:
    if provider == "baseline":
        return "deterministic_no_provider_cache"
    return "live_or_cache_backed_raw_cache_ignored"


def _provider_call_policy(provider: str) -> str:
    if provider == "baseline":
        return "deterministic_baseline"
    return "provider_api_or_frozen_cache"


def _provider_drift_guard(provider: str) -> str:
    if provider == "baseline":
        return "not_applicable"
    return "record_provider_model_data_hash_and_redacted_manifest"


def _collapse_values(values: Any) -> str:
    unique = sorted({str(value) for value in values if value is not None and str(value) != ""})
    return ",".join(unique)


if __name__ == "__main__":
    raise SystemExit(main())
