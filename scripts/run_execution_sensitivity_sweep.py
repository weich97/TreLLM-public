"""Execution-assumption sensitivity sweep for deterministic agents.

Research question (research plan 01): how much does an agent leaderboard
reorder when the execution assumptions move along the ladder from idealized
fills to stressed frictions? This script runs the deterministic strategy set
across execution levels and reports ranking stability (Kendall tau-b and
top-k Jaccard) between every pair of levels.

Deterministic agents run at zero provider cost. Provider-backed LLM agents
(`--llm-models poe:gpt-5.5,...`) join the same (scenario, level, seed) cells so
their rankings are directly comparable with the classical baselines; when LLM
rows are included, keep `--periods` small because every period is one provider
call per model. Runs checkpoint to the runs CSV as they finish and a rerun
resumes from whatever is already there (cached LLM responses replay for free).

Usage:

  # deterministic-only matrix
  python scripts/run_execution_sensitivity_sweep.py \
    --output-dir docs/results/execution_sensitivity

  # LLM + baselines, comparable cells
  POE_API_KEY=... python scripts/run_execution_sensitivity_sweep.py \
    --llm-models poe:gpt-5.5,poe:claude-opus-4.7 --samples-per-seed 3 \
    --periods 12 --output-dir docs/results/execution_sensitivity_llm
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.statistics import (
    kendall_tau,
    mean,
    summarize_metric,
    top_k_jaccard,
)
from tradearena.factory import build_default_system

DEFAULT_AGENTS = (
    "buy-and-hold",
    "signal-weighted",
    "naive-momentum",
    "mean-reversion",
    "risk-parity",
    "minimum-variance",
    "random",
)
DEFAULT_SEEDS = tuple(range(1, 11))

# Execution-assumption ladder. E0 is the idealized fill model most trading
# papers implicitly assume; E1 is the repository's default stress simulator;
# the E2 levels stress one friction axis each, plus a harsh corner.
EXECUTION_LEVELS: dict[str, dict[str, Any]] = {
    "E0_ideal": {"execution_mode": "ideal"},
    "E1_default_stress": {"execution_mode": "realistic"},
    "E2_spread_20bps": {"execution_mode": "realistic", "spread_bps": 20.0},
    "E2_latency_3": {"execution_mode": "realistic", "latency_steps": 3},
    "E2_participation_1pct": {"execution_mode": "realistic", "participation_rate": 0.01},
    "E2_harsh_corner": {
        "execution_mode": "realistic",
        "spread_bps": 20.0,
        "latency_steps": 3,
        "participation_rate": 0.01,
        "market_impact": 0.3,
    },
}

SCENARIOS: dict[str, dict[str, Any]] = {
    "calm": {
        "label": "Calm trend",
        "seed_offset": 0,
        "synthetic": {
            "synthetic_volatility_scale": 1.0,
            "synthetic_trend_scale": 1.0,
        },
    },
    "high_vol": {
        "label": "High volatility",
        "seed_offset": 100,
        "synthetic": {
            "synthetic_volatility_scale": 2.25,
            "synthetic_trend_scale": 0.65,
            "synthetic_macro_scale": 1.4,
        },
    },
    "jump_tail": {
        "label": "Jump and tail risk",
        "seed_offset": 200,
        "synthetic": {
            "synthetic_volatility_scale": 1.65,
            "synthetic_tail_df": 3,
            "synthetic_jump_probability": 0.15,
            "synthetic_jump_scale": 0.08,
        },
    },
}

RANK_METRIC = "sharpe"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sweep deterministic agents across execution-assumption levels.")
    parser.add_argument("--agents", default=",".join(DEFAULT_AGENTS))
    parser.add_argument(
        "--llm-models",
        default="",
        help="Comma-separated provider:model entries (poe/deepseek/glm) to run alongside the "
        "deterministic agents; append +mem (e.g. deepseek:deepseek-v4-pro+mem) to wrap the "
        "LLM signal in the memory-aware exposure scaffold.",
    )
    parser.add_argument(
        "--samples-per-seed",
        type=int,
        default=1,
        help="Repeated provider samples per seed for LLM agents; deterministic agents always run once.",
    )
    parser.add_argument("--cache-dir", default="outputs/llm_cache/execution_sensitivity")
    parser.add_argument("--levels", default=",".join(EXECUTION_LEVELS), help=f"Available: {', '.join(EXECUTION_LEVELS)}.")
    parser.add_argument("--scenarios", default=",".join(SCENARIOS), help=f"Available: {', '.join(SCENARIOS)}.")
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--periods", type=int, default=120)
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--symbols", default="SYN,ALT")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output-dir", default="docs/results/execution_sensitivity")
    args = parser.parse_args(argv)

    agents = [item.strip() for item in args.agents.split(",") if item.strip()]
    llm_agents = [item.strip() for item in args.llm_models.split(",") if item.strip()]
    for spec in llm_agents:
        provider = spec.removesuffix("+mem").split(":", 1)[0].lower()
        if provider not in {"poe", "deepseek", "glm"}:
            raise SystemExit(f"Unsupported LLM provider in {spec!r}; expected poe:, deepseek:, or glm: prefix")
    levels = {name: EXECUTION_LEVELS[name] for name in args.levels.split(",") if name.strip()}
    scenarios = {name: SCENARIOS[name] for name in args.scenarios.split(",") if name.strip()}
    seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]
    symbols = tuple(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip())
    samples_per_seed = max(1, int(args.samples_per_seed))
    cache_dir = ROOT / args.cache_dir if not Path(args.cache_dir).is_absolute() else Path(args.cache_dir)

    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if llm_agents:
        cache_dir.mkdir(parents=True, exist_ok=True)

    run_fields = [
        "scenario",
        "level",
        "agent",
        "seed",
        "sample",
        "total_return",
        "sharpe",
        "max_drawdown",
        "execution_fill_rate",
        "total_slippage_cost",
        "turnover_events",
    ]
    runs_path = output_dir / "execution_sensitivity_runs.csv"
    run_rows = _load_existing_runs(runs_path)
    completed = {
        (row["scenario"], row["level"], row["agent"], int(row["seed"]), int(row.get("sample", 0) or 0))
        for row in run_rows
    }
    if completed:
        print(f"Resuming: {len(completed)} runs already checkpointed in {runs_path}", flush=True)

    with runs_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=run_fields, extrasaction="ignore")
        if not run_rows:
            writer.writeheader()
        for scenario_key, scenario in scenarios.items():
            for level_key, level in levels.items():
                for agent in agents + llm_agents:
                    sample_count = samples_per_seed if ":" in agent else 1
                    fresh = 0
                    for seed in seeds:
                        actual_seed = seed + int(scenario["seed_offset"])
                        for sample in range(sample_count):
                            if (scenario_key, level_key, agent, actual_seed, sample) in completed:
                                continue
                            metrics = _run_case(
                                agent=agent,
                                level=level,
                                scenario=scenario,
                                seed=actual_seed,
                                sample=sample,
                                periods=args.periods,
                                symbols=symbols,
                                cache_dir=cache_dir,
                                initial_cash=args.initial_cash,
                            )
                            row = {
                                "scenario": scenario_key,
                                "level": level_key,
                                "agent": agent,
                                "seed": actual_seed,
                                "sample": sample,
                                "total_return": metrics.get("total_return", 0.0),
                                "sharpe": metrics.get("sharpe", 0.0),
                                "max_drawdown": metrics.get("max_drawdown", 0.0),
                                "execution_fill_rate": metrics.get("execution_fill_rate", ""),
                                "total_slippage_cost": metrics.get("total_slippage_cost", ""),
                                "turnover_events": metrics.get("turnover_events", ""),
                            }
                            run_rows.append(row)
                            writer.writerow(row)
                            handle.flush()
                            fresh += 1
                    print(
                        f"OK {scenario_key} {level_key} {agent} ({fresh} new / {len(seeds) * sample_count} runs)",
                        flush=True,
                    )

    aggregate_rows = _aggregate_rows(run_rows)
    _write_csv(
        output_dir / "execution_sensitivity_aggregate.csv",
        aggregate_rows,
        [
            "scenario",
            "level",
            "agent",
            "run_count",
            f"{RANK_METRIC}_mean",
            f"{RANK_METRIC}_std",
            f"{RANK_METRIC}_ci_low",
            f"{RANK_METRIC}_ci_high",
            "return_mean",
            "rank",
        ],
    )

    stability_rows = _ranking_stability_rows(aggregate_rows, top_k=args.top_k)
    _write_csv(
        output_dir / "execution_sensitivity_rank_stability.csv",
        stability_rows,
        ["scenario", "level_a", "level_b", "agent_count", "rank_metric", "kendall_tau", f"top_{args.top_k}_jaccard"],
    )

    _write_markdown(output_dir / "execution_sensitivity.md", aggregate_rows, stability_rows, top_k=args.top_k)
    print(f"Wrote {len(run_rows)} runs, {len(aggregate_rows)} aggregates, {len(stability_rows)} stability pairs to {output_dir}")
    return 0


def _run_case(
    *,
    agent: str,
    level: dict[str, Any],
    scenario: dict[str, Any],
    seed: int,
    sample: int = 0,
    periods: int,
    symbols: tuple[str, ...],
    cache_dir: Path | None = None,
    initial_cash: float = 100_000.0,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = dict(scenario.get("synthetic", {}))
    kwargs.update(level)
    if ":" in agent:
        # A "+mem" suffix wraps the LLM signal in the memory-aware exposure
        # overlay (audit-memory scaffold) instead of the plain strategy.
        scaffolded = agent.endswith("+mem")
        provider, model = agent.removesuffix("+mem").split(":", 1)
        analyst = {"poe": "poe-llm", "glm": "glm-llm"}.get(provider, "deepseek-llm")
        model_slug = re.sub(r"[^a-z0-9]+", "_", f"{provider}-{model}".lower()).strip("_")
        kwargs.update(
            {
                "strategy_name": "memory-aware" if scaffolded else "signal-weighted",
                "analyst_names": (analyst,),
                "llm_model": model,
                "llm_cache_path": str((cache_dir or ROOT / "outputs/llm_cache/execution_sensitivity") / f"{model_slug}.jsonl"),
                "llm_mask_timestamps": True,
                "llm_use_risk_feedback": True,
                "llm_risk_feedback_mode": "true",
                "llm_sample_index": sample,
            }
        )
    else:
        kwargs.update({"strategy_name": agent, "analyst_names": ("momentum", "macro-news")})
    _, metrics = build_default_system(
        name=f"execution_sweep_{re.sub(r'[^A-Za-z0-9]+', '_', agent)}_{seed}",
        symbols=symbols,
        periods=periods,
        seed=seed,
        initial_cash=initial_cash,
        risk_name="max-position",
        **kwargs,
    ).run()
    return metrics


def _load_existing_runs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _aggregate_rows(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in run_rows:
        grouped.setdefault((str(row["scenario"]), str(row["level"]), str(row["agent"])), []).append(row)
    output = []
    for (scenario, level, agent), rows in sorted(grouped.items()):
        stats = summarize_metric((float(row[RANK_METRIC]) for row in rows), prefix=RANK_METRIC)
        output.append(
            {
                "scenario": scenario,
                "level": level,
                "agent": agent,
                "run_count": len(rows),
                **stats,
                "return_mean": mean(float(row["total_return"]) for row in rows),
                "rank": None,
            }
        )
    # Rank within each (scenario, level) by the rank metric mean, best first.
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in output:
        by_cell.setdefault((str(row["scenario"]), str(row["level"])), []).append(row)
    for rows in by_cell.values():
        rows.sort(key=lambda row: -float(row[f"{RANK_METRIC}_mean"]))
        for position, row in enumerate(rows, start=1):
            row["rank"] = position
    return output


def _ranking_stability_rows(aggregate_rows: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    scores: dict[tuple[str, str], dict[str, float]] = {}
    for row in aggregate_rows:
        cell = (str(row["scenario"]), str(row["level"]))
        scores.setdefault(cell, {})[str(row["agent"])] = float(row[f"{RANK_METRIC}_mean"])
    scenarios = sorted({scenario for scenario, _ in scores})
    output = []
    for scenario in scenarios:
        levels = sorted(level for cell_scenario, level in scores if cell_scenario == scenario)
        for i in range(len(levels)):
            for j in range(i + 1, len(levels)):
                scores_a = scores[(scenario, levels[i])]
                scores_b = scores[(scenario, levels[j])]
                output.append(
                    {
                        "scenario": scenario,
                        "level_a": levels[i],
                        "level_b": levels[j],
                        "agent_count": len(set(scores_a) & set(scores_b)),
                        "rank_metric": f"{RANK_METRIC}_mean",
                        "kendall_tau": kendall_tau(scores_a, scores_b),
                        f"top_{top_k}_jaccard": top_k_jaccard(scores_a, scores_b, k=top_k),
                    }
                )
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(
    path: Path,
    aggregate_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    *,
    top_k: int,
) -> None:
    lines = [
        "# Execution-Assumption Sensitivity (Deterministic Agents)",
        "",
        "How much the agent ranking reorders between execution-assumption levels.",
        "Rankings use mean Sharpe over seeds within each (scenario, level) cell.",
        "Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;",
        "lower values mean execution assumptions change conclusions.",
        "",
        "## Ranking Stability",
        "",
        f"| Scenario | Level A | Level B | Kendall tau | Top-{top_k} Jaccard |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in stability_rows:
        tau = row["kendall_tau"]
        jaccard = row[f"top_{top_k}_jaccard"]
        tau_text = f"{float(tau):.3f}" if tau is not None else ""
        jaccard_text = f"{float(jaccard):.3f}" if jaccard is not None else ""
        lines.append(f"| {row['scenario']} | {row['level_a']} | {row['level_b']} | {tau_text} | {jaccard_text} |")
    lines += [
        "",
        "## Per-Level Leaderboards",
        "",
        "| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |",
        "| --- | --- | ---: | --- | ---: | --- | ---: |",
    ]
    ordered = sorted(aggregate_rows, key=lambda row: (str(row["scenario"]), str(row["level"]), int(row["rank"])))
    for row in ordered:
        ci_low = row.get(f"{RANK_METRIC}_ci_low")
        ci_high = row.get(f"{RANK_METRIC}_ci_high")
        ci_text = f"[{float(ci_low):.3f}, {float(ci_high):.3f}]" if ci_low is not None and ci_high is not None else ""
        lines.append(
            f"| {row['scenario']} | {row['level']} | {row['rank']} | {row['agent']} "
            f"| {float(row[f'{RANK_METRIC}_mean']):.3f} | {ci_text} | {float(row['return_mean']):.4f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
