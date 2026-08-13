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

from tradearena.core.reproducibility import attach_reproducibility_hash, sha256_file
from tradearena.evaluation.evidence import evidence_payload_for_row, format_evidence_tags
from tradearena.evaluation.statistics import (
    benjamini_hochberg,
    mean,
    paired_bootstrap_difference,
    sample_std,
    summarize_metric,
    variance_components,
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

DEFAULT_SCENARIOS = (
    "calm_trend",
    "high_vol",
    "jump_tail",
    "liquidity_collapse",
    "spread_explosion",
    "latency_spike",
)
QUALITY_FIELDS = (
    "alpha_pre_risk_total_return",
    "alpha_pre_risk_sharpe",
    "alpha_pre_risk_hit_rate",
    "alpha_pre_risk_steps",
    "alpha_quality_score",
    "risk_discipline_score",
    "execution_robustness_score",
)

SCENARIOS: dict[str, dict[str, Any]] = {
    "calm_trend": {
        "scenario_id": "leaderboard_llm_calm_trend_synthetic_v0_1",
        "label": "Calm trend",
        "stress_family": "market",
        "seed_offset": 0,
        "synthetic": {
            "synthetic_volatility_scale": 1.0,
            "synthetic_trend_scale": 1.0,
            "synthetic_seasonal_scale": 1.0,
            "synthetic_macro_scale": 1.0,
        },
    },
    "high_vol": {
        "scenario_id": "leaderboard_llm_high_vol_synthetic_v0_1",
        "label": "High volatility",
        "stress_family": "market",
        "seed_offset": 10,
        "synthetic": {
            "synthetic_volatility_scale": 2.25,
            "synthetic_trend_scale": 0.65,
            "synthetic_seasonal_scale": 1.2,
            "synthetic_macro_scale": 1.4,
        },
    },
    "jump_tail": {
        "scenario_id": "leaderboard_llm_jump_tail_synthetic_v0_1",
        "label": "Jump and tail risk",
        "stress_family": "market",
        "seed_offset": 22,
        "synthetic": {
            "synthetic_volatility_scale": 1.65,
            "synthetic_trend_scale": 0.85,
            "synthetic_seasonal_scale": 1.0,
            "synthetic_macro_scale": 1.5,
            "synthetic_tail_df": 3,
            "synthetic_jump_probability": 0.15,
            "synthetic_jump_scale": 0.08,
        },
    },
    "liquidity_collapse": {
        "scenario_id": "leaderboard_llm_liquidity_collapse_synthetic_v0_1",
        "label": "Liquidity collapse",
        "stress_family": "execution",
        "seed_offset": 34,
        "synthetic": {
            "synthetic_volatility_scale": 1.85,
            "synthetic_trend_scale": 0.45,
            "synthetic_seasonal_scale": 1.35,
            "synthetic_macro_scale": 1.6,
            "synthetic_tail_df": 4,
            "synthetic_jump_probability": 0.08,
            "synthetic_jump_scale": 0.05,
        },
        "execution": {
            "commission_bps": 1.0,
            "slippage_bps": 4.0,
            "spread_bps": 15.0,
            "participation_rate": 0.005,
            "latency_steps": 1,
            "market_impact": 0.35,
        },
        "description": "Volume participation collapses to 0.5%, exposing overconfident target weights through partial fills and rejections.",
    },
    "spread_explosion": {
        "scenario_id": "leaderboard_llm_spread_explosion_synthetic_v0_1",
        "label": "Spread explosion",
        "stress_family": "execution",
        "seed_offset": 46,
        "synthetic": {
            "synthetic_volatility_scale": 1.6,
            "synthetic_trend_scale": 0.55,
            "synthetic_seasonal_scale": 1.4,
            "synthetic_macro_scale": 1.5,
            "synthetic_tail_df": 4,
            "synthetic_jump_probability": 0.08,
            "synthetic_jump_scale": 0.045,
        },
        "execution": {
            "commission_bps": 1.0,
            "slippage_bps": 6.0,
            "spread_bps": 150.0,
            "participation_rate": 0.05,
            "latency_steps": 1,
            "market_impact": 0.25,
        },
        "description": "Quoted spread widens to 150 bps, testing whether the model keeps trading despite high crossing costs.",
    },
    "latency_spike": {
        "scenario_id": "leaderboard_llm_latency_spike_synthetic_v0_1",
        "label": "Latency spike",
        "stress_family": "execution",
        "seed_offset": 58,
        "synthetic": {
            "synthetic_volatility_scale": 2.05,
            "synthetic_trend_scale": 0.5,
            "synthetic_seasonal_scale": 1.25,
            "synthetic_macro_scale": 1.7,
            "synthetic_tail_df": 4,
            "synthetic_jump_probability": 0.1,
            "synthetic_jump_scale": 0.055,
        },
        "execution": {
            "commission_bps": 1.0,
            "slippage_bps": 4.0,
            "spread_bps": 25.0,
            "participation_rate": 0.03,
            "latency_steps": 4,
            "market_impact": 0.3,
        },
        "description": "Orders wait four bars before eligibility, surfacing stale-intent and pending-order risk.",
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a small provider-backed model matrix and write redacted benchmark manifests."
    )
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated provider:model entries.")
    parser.add_argument(
        "--scenarios",
        default=",".join(DEFAULT_SCENARIOS),
        help=f"Comma-separated scenario presets. Available: {', '.join(SCENARIOS)}.",
    )
    parser.add_argument("--periods", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--seeds",
        default=",".join(str(seed) for seed in DEFAULT_SEEDS),
        help="Comma-separated benchmark seeds. Defaults to five seeds for statistical summaries.",
    )
    parser.add_argument(
        "--samples-per-seed",
        type=int,
        default=1,
        help="Repeated provider samples per market seed for LLM rows; lets aggregates separate market-path variance from model stochasticity. Baseline rows always run once per seed.",
    )
    parser.add_argument("--symbols", default="SYN,ALT")
    parser.add_argument("--output-dir", default="docs/results/model_matrix")
    parser.add_argument("--submission-dir", default="examples/benchmark_submissions/model_matrix")
    parser.add_argument("--cache-dir", default="outputs/llm_cache/leaderboard_model_matrix")
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

    symbols = tuple(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip())
    model_specs = [_parse_model_spec(item) for item in args.models.split(",") if item.strip()]
    scenarios = [_scenario(name) for name in args.scenarios.split(",") if name.strip()]
    seeds = _parse_seeds(args.seeds) or (int(args.seed),)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    samples_per_seed = max(1, int(args.samples_per_seed))
    for scenario in scenarios:
        for provider, model in model_specs:
            sample_count = 1 if provider == "baseline" else samples_per_seed
            for seed_index, seed in enumerate(seeds):
                actual_seed = int(seed) + int(scenario["seed_offset"])
                for sample_index in range(sample_count):
                    try:
                        row = _run_one(
                            provider=provider,
                            model=model,
                            scenario=scenario,
                            symbols=symbols,
                            periods=args.periods,
                            seed=actual_seed,
                            seed_index=seed_index,
                            sample_index=sample_index,
                            output_dir=output_dir,
                            submission_dir=submission_dir,
                            cache_dir=cache_dir,
                            provider_mode=args.provider_mode,
                        )
                        rows.append(row)
                        print(
                            f"OK {row['scenario_key']} seed={row['seed']} sample={sample_index} {provider}:{model} -> {row['submission']}"
                        )
                    except Exception as exc:  # pragma: no cover - exercised only by live provider failures
                        failures.append(
                            {
                                "scenario": str(scenario["key"]),
                                "seed": str(actual_seed),
                                "sample_index": str(sample_index),
                                "provider": provider,
                                "model": model,
                                "error": type(exc).__name__,
                            }
                        )
                        print(
                            f"FAILED {scenario['key']} seed={actual_seed} sample={sample_index} {provider}:{model}: {type(exc).__name__}: {exc}",
                            file=sys.stderr,
                        )

    _write_matrix_table(output_dir / "leaderboard_model_matrix.csv", rows)
    aggregate_rows = _aggregate_rows(rows)
    _write_aggregate_table(output_dir / "leaderboard_model_matrix_aggregate.csv", aggregate_rows)
    scenario_rows = _scenario_aggregate_rows(rows)
    _write_scenario_aggregate_table(output_dir / "leaderboard_model_matrix_scenario_aggregate.csv", scenario_rows)
    significance_rows = _significance_rows(rows)
    _write_significance_table(output_dir / "leaderboard_model_matrix_significance.csv", significance_rows)
    if samples_per_seed > 1:
        _write_variance_decomposition_table(
            output_dir / "leaderboard_model_matrix_variance_decomposition.csv",
            _variance_decomposition_rows(rows),
        )
    shock_rows = _execution_shock_aggregate_rows(rows)
    _write_shock_aggregate_table(output_dir / "leaderboard_execution_shock_aggregate.csv", shock_rows)
    _write_matrix_markdown(
        output_dir / "leaderboard_model_matrix.md",
        rows,
        aggregate_rows,
        scenario_rows,
        shock_rows,
        significance_rows,
        failures,
    )
    if failures:
        (output_dir / "leaderboard_model_matrix_failures.json").write_text(
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

    print(f"Successful model rows: {len(rows)}")
    if failures:
        print(f"Failed model rows: {len(failures)}")
    return 0 if rows else 1


def _run_one(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
    symbols: tuple[str, ...],
    periods: int,
    seed: int,
    seed_index: int,
    sample_index: int = 0,
    output_dir: Path,
    submission_dir: Path,
    cache_dir: Path,
    provider_mode: str,
) -> dict[str, Any]:
    model_slug = _slug(f"{provider}-{model}")
    scenario_key = str(scenario["key"])
    slug = f"{scenario_key}__{model_slug}__seed_{seed}"
    if sample_index:
        slug = f"{slug}__sample_{sample_index}"
    analyst_name = _analyst_name(provider)
    strategy_name = _strategy_name(provider, model)
    execution_config = _scenario_execution_config(scenario)
    trajectory, metrics = build_default_system(
        name=f"leaderboard_{slug}",
        symbols=symbols,
        periods=periods,
        seed=seed,
        analyst_names=(analyst_name,) if analyst_name else (),
        strategy_name=strategy_name,
        risk_name="max-position",
        execution_mode="realistic",
        commission_bps=float(execution_config["commission_bps"]),
        slippage_bps=float(execution_config["base_slippage_bps"]),
        spread_bps=float(execution_config["spread_bps"]),
        participation_rate=float(execution_config["participation_rate"]),
        latency_steps=int(execution_config["latency_steps"]),
        market_impact=float(execution_config["market_impact"]),
        llm_model=model,
        llm_cache_path=str(cache_dir / f"{model_slug}.jsonl"),
        llm_mask_timestamps=True,
        llm_use_risk_feedback=True,
        llm_risk_feedback_mode="true",
        llm_sample_index=sample_index,
        **scenario["synthetic"],
    ).run()

    parse_coverage = 1.0 if provider == "baseline" else _parse_coverage(trajectory.to_dict(), symbols)
    quality_metrics = _quality_metrics(metrics)
    evidence = evidence_payload_for_row(
        provider=provider,
        execution_mode="realistic-stress",
        provider_mode=provider_mode,
        raw_provider_text_removed=True,
        trajectory_format="redacted_manifest",
    )
    evidence_tags = format_evidence_tags(evidence["tags"])
    summary = {
        "schema_version": "0.1",
        "scenario_id": scenario["scenario_id"],
        "scenario_label": scenario["label"],
        "provider": provider,
        "model": model,
        "symbols": list(symbols),
        "periods": periods,
        "seed": seed,
        "seed_index": seed_index,
        "sample_index": sample_index,
        "stress_family": scenario.get("stress_family", "market"),
        "scenario_description": scenario.get("description", ""),
        "execution_config": execution_config,
        "parse_coverage": parse_coverage,
        "metrics": metrics,
        "evidence": evidence,
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
                "name": "synthetic-market",
                "frequency": "daily",
                "symbols": list(symbols),
                "timestamp_policy": "relative_masked",
                "data_hash": (
                    f"sha256:{scenario_key}-synthetic-seed-{seed}-symbols-"
                    f"{'-'.join(symbols)}-periods-{periods}"
                ),
            },
            "execution_config": execution_config,
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
            "metrics": {
                "total_return": float(metrics.get("total_return", 0.0)),
                "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
                "sharpe": float(metrics.get("sharpe", 0.0)),
                "execution_fill_rate": float(metrics.get("execution_fill_rate", 0.0)),
                "rejected_order_count": int(metrics.get("rejected_order_count", 0)),
                "risk_clipped_decisions": int(metrics.get("risk_clipped_decisions", 0)),
                "risk_violation_count": int(metrics.get("risk_violation_count", 0)),
                "trajectory_reproducibility_coverage": float(
                    metrics.get("trajectory_reproducibility_coverage", 0.0)
                ),
                **quality_metrics,
            },
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
                    "Leaderboard smoke manifest generated from a live or cache-backed provider run; "
                    "raw prompts and responses remain in ignored local cache files."
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
        "seed_index": seed_index,
        "sample_index": sample_index,
        "stress_family": scenario.get("stress_family", "market"),
        "participation_rate": execution_config["participation_rate"],
        "spread_bps": execution_config["spread_bps"],
        "latency_steps": execution_config["latency_steps"],
        "parse_coverage": parse_coverage,
        "evidence_tags": evidence_tags,
        "claim_scope": evidence["claim_scope"],
        "total_return": submission["metrics"]["total_return"],
        "max_drawdown": submission["metrics"]["max_drawdown"],
        "sharpe": submission["metrics"]["sharpe"],
        "execution_fill_rate": submission["metrics"]["execution_fill_rate"],
        "rejected_order_count": submission["metrics"]["rejected_order_count"],
        "risk_clipped_decisions": submission["metrics"]["risk_clipped_decisions"],
        "risk_violation_count": submission["metrics"]["risk_violation_count"],
        **quality_metrics,
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
    if provider not in {"poe", "deepseek", "baseline"}:
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
    return ""


def _strategy_name(provider: str, model: str) -> str:
    if provider != "baseline":
        return "signal-weighted"
    return "random-allocation" if model == "random" else "always-hold"


def _scenario(name: str) -> dict[str, Any]:
    key = name.strip()
    if key not in SCENARIOS:
        raise ValueError(f"Unknown scenario preset: {key}. Available: {', '.join(SCENARIOS)}")
    scenario = dict(SCENARIOS[key])
    scenario["key"] = key
    scenario["synthetic"] = dict(scenario["synthetic"])
    scenario["execution"] = dict(scenario.get("execution", {}))
    return scenario


def _default_execution_config() -> dict[str, float | int]:
    return {
        "commission_bps": 1.0,
        "base_slippage_bps": 2.0,
        "spread_bps": 0.0,
        "latency_steps": 1,
        "participation_rate": 0.05,
        "market_impact": 0.15,
    }


def _scenario_execution_config(scenario: dict[str, Any]) -> dict[str, float | int]:
    execution_config = _default_execution_config()
    overrides = dict(scenario.get("execution", {}))
    if "slippage_bps" in overrides:
        overrides["base_slippage_bps"] = overrides.pop("slippage_bps")
    execution_config.update(overrides)
    execution_config["latency_steps"] = int(execution_config["latency_steps"])
    return execution_config


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


def _write_matrix_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scenario_key",
        "scenario_id",
        "scenario_label",
        "provider",
        "model",
        "seed",
        "seed_index",
        "sample_index",
        "stress_family",
        "participation_rate",
        "spread_bps",
        "latency_steps",
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
        *QUALITY_FIELDS,
        "reproducibility_hash",
        "submission",
        "summary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def _execution_shock_aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    execution_rows = [row for row in rows if row.get("stress_family") == "execution"]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in execution_rows:
        grouped.setdefault((str(row["provider"]), str(row["model"])), []).append(row)
    shock_rows = []
    for (provider, model), model_rows in sorted(grouped.items()):
        return_stats = summarize_metric((row["total_return"] for row in model_rows), prefix="return")
        shock_rows.append(
            {
                "provider": provider,
                "model": model,
                "shock_scenarios": len({row["scenario_key"] for row in model_rows}),
                "run_count": len(model_rows),
                "avg_return": return_stats["return_mean"],
                "std_return": return_stats["return_std"],
                "return_ci_low": return_stats["return_ci_low"],
                "return_ci_high": return_stats["return_ci_high"],
                "worst_drawdown": min(float(row["max_drawdown"]) for row in model_rows),
                "avg_fill_rate": _avg(row["execution_fill_rate"] for row in model_rows),
                "total_rejected_orders": sum(int(row["rejected_order_count"]) for row in model_rows),
                "total_risk_edits": sum(int(row["risk_clipped_decisions"]) for row in model_rows),
                "avg_parse_coverage": _avg(row["parse_coverage"] for row in model_rows),
                "evidence_tags": _collapse_values(row.get("evidence_tags", "") for row in model_rows),
                "claim_scope": _collapse_values(row.get("claim_scope", "") for row in model_rows),
            }
        )
    return sorted(
        shock_rows,
        key=lambda row: (
            -float(row["avg_fill_rate"]),
            int(row["total_rejected_orders"]),
            -float(row["avg_return"]),
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
                "stress_family": model_rows[0].get("stress_family", "market"),
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


def _mean_by_scenario_seed(rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    """Average total_return over repeated provider samples within each (scenario, seed)."""

    grouped: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        key = (str(row["scenario_key"]), str(row["seed"]))
        grouped.setdefault(key, []).append(float(row["total_return"]))
    return {key: mean(values) for key, values in grouped.items()}


def _baseline_test(
    all_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    baseline_model: str,
) -> dict[str, float | int | None]:
    candidate = _mean_by_scenario_seed(candidate_rows)
    baseline = _mean_by_scenario_seed(
        [
            row
            for row in all_rows
            if row.get("provider") == "baseline" and row.get("model") == baseline_model
        ]
    )
    return paired_bootstrap_difference(candidate, baseline)


def _variance_decomposition_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Between-seed (market path) vs within-seed (provider sampling) variance per model."""

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["provider"]), str(row["model"])), []).append(row)
    output = []
    for (provider, model), model_rows in sorted(grouped.items()):
        by_seed: dict[tuple[str, str], list[float]] = {}
        for row in model_rows:
            key = (str(row["scenario_key"]), str(row["seed"]))
            by_seed.setdefault(key, []).append(float(row["total_return"]))
        components = variance_components(by_seed)
        output.append(
            {
                "provider": provider,
                "model": model,
                "metric": "total_return",
                "seed_group_count": components["group_count"],
                "total_runs": components["total_n"],
                "between_seed_variance": components["between_group_variance"],
                "within_seed_variance": components["within_group_variance"],
                "within_seed_share": components["within_group_share"],
            }
        )
    return output


def _write_variance_decomposition_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "provider",
        "model",
        "metric",
        "seed_group_count",
        "total_runs",
        "between_seed_variance",
        "within_seed_variance",
        "within_seed_share",
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
        "stress_family",
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


def _write_shock_aggregate_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "provider",
        "model",
        "shock_scenarios",
        "run_count",
        "avg_return",
        "std_return",
        "return_ci_low",
        "return_ci_high",
        "worst_drawdown",
        "avg_fill_rate",
        "total_rejected_orders",
        "total_risk_edits",
        "avg_parse_coverage",
        "evidence_tags",
        "claim_scope",
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
    shock_rows: list[dict[str, Any]],
    significance_rows: list[dict[str, Any]],
    failures: list[dict[str, str]],
) -> None:
    protocol_note = _model_matrix_protocol_note(aggregate_rows)
    lines = [
        "# Leaderboard Model Matrix",
        "",
        "This table is generated by `python scripts/run_leaderboard_model_matrix.py --update-registry`.",
        "It records redacted model manifests only; raw provider prompts and responses remain in ignored local caches.",
        "Default scenarios include three market regimes and three execution shocks: liquidity collapse, spread explosion, and latency spike.",
        "The default protocol runs five seeds per `(model, scenario)` and reports mean, sample standard deviation, 95% bootstrap confidence intervals, paired bootstrap tests, and paired sign-flip permutation tests against `always-hold` and `random` anchors.",
        *([protocol_note] if protocol_note else []),
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
    if shock_rows:
        lines.extend(
            [
                "",
                "## Execution-Shock Aggregate",
                "",
                "This slice uses only `liquidity_collapse`, `spread_explosion`, and `latency_spike` rows.",
                "Lower fill and more rejections are direct symptoms of intent that failed to survive paper-execution stress.",
                "",
                "| Rank | Provider | Model | Evidence | Shock scenarios | Runs | Return mean +- std | 95% CI | Worst DD | Avg fill | Rejected | Risk edits | Parse |",
                "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for rank, row in enumerate(shock_rows, start=1):
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(rank),
                        str(row["provider"]),
                        str(row["model"]),
                        _format_evidence(row.get("evidence_tags", "")),
                        str(row["shock_scenarios"]),
                        str(row["run_count"]),
                        _fmt_pm(row["avg_return"], row["std_return"]),
                        _fmt_ci(row["return_ci_low"], row["return_ci_high"]),
                        _fmt(row["worst_drawdown"]),
                        _fmt(row["avg_fill_rate"]),
                        str(row["total_rejected_orders"]),
                        str(row["total_risk_edits"]),
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
            "| Scenario | Stress | Provider | Model | Evidence | Runs | Return mean +- std | 95% CI | Worst DD | Sharpe mean +- std | Alpha | Risk | Execution | Fill |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in scenario_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["scenario_label"]),
                    str(row["stress_family"]),
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
                "Positive deltas mean the model beat the named anchor on matched `(scenario, seed)` runs. The permutation column is a paired sign-flip test for small-sample robustness.",
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
    lines.extend(
        [
            "",
            "## Raw Seed Rows",
            "",
            "Per-seed rows, manifest links, and reproducibility hashes are stored in `leaderboard_model_matrix.csv`.",
        ]
    )
    if failures:
        lines.extend(["", "## Provider Failures", ""])
        for failure in failures:
            lines.append(f"- `{failure['provider']}:{failure['model']}` failed with `{failure['error']}`.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _collapse_values(values: Any) -> str:
    unique = sorted({str(value) for value in values if value is not None and str(value) != ""})
    return ",".join(unique)


def _model_matrix_protocol_note(aggregate_rows: list[dict[str, Any]]) -> str:
    baseline_repeats = [
        float(row["run_count"]) / max(1.0, float(row["scenario_count"]))
        for row in aggregate_rows
        if row.get("provider") == "baseline"
    ]
    llm_repeats = [
        float(row["run_count"]) / max(1.0, float(row["scenario_count"]))
        for row in aggregate_rows
        if row.get("provider") != "baseline"
    ]
    if not baseline_repeats or not llm_repeats:
        return ""
    anchor_repeats = max(baseline_repeats)
    provider_repeats = min(llm_repeats)
    if anchor_repeats <= provider_repeats:
        return ""
    return (
        f"The tracked snapshot currently has {provider_repeats:g} cached provider-backed repeat(s) "
        f"per scenario and {anchor_repeats:g} deterministic anchor repeats; this keeps paired anchor "
        "tests available while reserving a full provider refresh for explicit live benchmark runs."
    )


if __name__ == "__main__":
    raise SystemExit(main())
