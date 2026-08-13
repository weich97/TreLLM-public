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

from tradearena.evaluation.statistics import kendall_tau, mean, summarize_metric, top_k_jaccard
from tradearena.factory import build_default_system

SCENARIO_ID = "synthetic_calm_trend_c0_v0_3"
CONTAMINATION_TIER = "C0"
RANK_METRIC = "sharpe"
DEFAULT_AGENTS = ("signal-weighted", "naive-momentum", "risk-parity", "random")
DEFAULT_SEEDS = (7, 11)
DEFAULT_LEVELS = ("E0", "E1", "E2", "E3")

# Synthetic-scenario definitions, byte-copied from the pre-registered direct-API
# submission runner (`scripts/run_v03_direct_api_submission.py`) so the
# deterministic classical ladder sits on exactly the same market configs as the
# LLM headline matrix. `calm` reproduces the frozen calm-trend anchor (vol/trend
# scale 1.0, all other synthetic knobs at their factory defaults), so the default
# invocation is byte-identical to the replication-pack expected values.
SCENARIOS: dict[str, dict[str, Any]] = {
    "calm": {
        "scenario_id": "synthetic_calm_trend_c0_v0_3",
        "synthetic": {"synthetic_volatility_scale": 1.0, "synthetic_trend_scale": 1.0},
    },
    "high_vol": {
        "scenario_id": "synthetic_high_volatility_c0_v0_3",
        "synthetic": {
            "synthetic_volatility_scale": 2.25,
            "synthetic_trend_scale": 0.65,
            "synthetic_macro_scale": 1.4,
        },
    },
    "jump_tail": {
        "scenario_id": "synthetic_jump_tail_c0_v0_3",
        "synthetic": {
            "synthetic_volatility_scale": 1.65,
            "synthetic_tail_df": 3,
            "synthetic_jump_probability": 0.15,
            "synthetic_jump_scale": 0.08,
        },
    },
}
EXECUTION_LEVELS: dict[str, dict[str, Any]] = {
    "E0": {
        "label": "ideal execution",
        "execution_mode": "ideal",
        "claim_scope": "Idealized fill baseline for sensitivity analysis.",
    },
    "E1": {
        "label": "paper stress execution",
        "execution_mode": "realistic",
        "claim_scope": "Default paper-execution stress assumptions used for comparable leaderboard rows.",
    },
    "E2": {
        "label": "harsh friction sweep corner",
        "execution_mode": "realistic",
        "spread_bps": 20.0,
        "latency_steps": 3,
        "participation_rate": 0.01,
        "market_impact": 0.3,
        "claim_scope": "Stress corner for execution-friction sensitivity; not calibrated cost prediction.",
    },
    "E3": {
        "label": "calibrated replay fixture",
        "execution_mode": "calibrated",
        "spread_bps": 8.0,
        "latency_steps": 2,
        "participation_rate": 0.03,
        "market_impact": 0.22,
        "execution_calibration_profile_id": "public-binance-fixture-calibration",
        "claim_scope": "Calibrated replay fixture path. Venue-wide E3 claims require external quote/fill provenance.",
    },
}

ROW_FIELDS = [
    "protocol_id",
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "execution_label",
    "execution_mode",
    "agent",
    "seed",
    "total_return",
    "sharpe",
    "max_drawdown",
    "execution_fill_rate",
    "rejected_order_count",
    "total_slippage_cost",
    "intent_risk_gap_l1",
    "risk_execution_gap_l1",
    "intent_execution_gap_l1",
    "max_intent_execution_gap_l1",
    "trajectory_reproducibility_coverage",
    "evidence_tier",
    "claim_scope",
]
AGGREGATE_FIELDS = [
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "execution_label",
    "agent",
    "run_count",
    "rank",
    "sharpe_mean",
    "sharpe_std",
    "sharpe_ci_low",
    "sharpe_ci_high",
    "total_return_mean",
    "max_drawdown_mean",
    "execution_fill_rate_mean",
    "rejected_order_count_mean",
    "total_slippage_cost_mean",
    "intent_execution_gap_l1_mean",
    "intent_risk_gap_l1_mean",
    "risk_execution_gap_l1_mean",
]
STABILITY_FIELDS = [
    "scenario_id",
    "contamination_tier",
    "baseline_level",
    "comparison_level",
    "agent_count",
    "rank_metric",
    "kendall_tau",
    "top_k",
    "top_k_jaccard",
    "mean_return_delta_vs_e0",
    "mean_fill_rate_delta_vs_e0",
    "mean_intent_execution_gap_delta_vs_e0",
    "mean_slippage_delta_vs_e0",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the TreLLM v0.3 execution-assumption ladder artifact."
    )
    parser.add_argument("--output-dir", default="docs/results/v0_3_execution_ladder")
    parser.add_argument("--agents", default=",".join(DEFAULT_AGENTS))
    parser.add_argument("--levels", default=",".join(DEFAULT_LEVELS))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--periods", type=int, default=24)
    parser.add_argument("--symbols", default="SYN,ALT")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="calm")
    args = parser.parse_args(argv)

    global SCENARIO_ID
    scenario = SCENARIOS[args.scenario]
    SCENARIO_ID = scenario["scenario_id"]
    synthetic = scenario["synthetic"]

    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    agents = _parse_list(args.agents, "agents")
    levels = _parse_levels(args.levels)
    seeds = _parse_ints(args.seeds, "seeds")
    symbols = tuple(_parse_list(args.symbols, "symbols"))

    rows = [
        _run_case(agent=agent, level_id=level_id, level=EXECUTION_LEVELS[level_id], seed=seed, periods=args.periods, symbols=symbols, synthetic=synthetic)
        for level_id in levels
        for agent in agents
        for seed in seeds
    ]
    aggregate_rows = _aggregate_rows(rows)
    stability_rows = _stability_rows(aggregate_rows, top_k=args.top_k)
    summary = _summary(rows, aggregate_rows, stability_rows, levels=levels, agents=agents, seeds=seeds, periods=args.periods, top_k=args.top_k)

    _write_csv(output_dir / "execution_ladder_rows.csv", rows, ROW_FIELDS)
    _write_csv(output_dir / "execution_ladder_aggregate.csv", aggregate_rows, AGGREGATE_FIELDS)
    _write_csv(output_dir / "execution_ladder_ranking_stability.csv", stability_rows, STABILITY_FIELDS)
    _write_json(output_dir / "execution_ladder_summary.json", summary)
    (output_dir / "execution_ladder_summary.md").write_text(
        _summary_markdown(summary, aggregate_rows, stability_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display_path(output_dir / 'execution_ladder_rows.csv')}")
    print(f"Wrote {_display_path(output_dir / 'execution_ladder_aggregate.csv')}")
    print(f"Wrote {_display_path(output_dir / 'execution_ladder_ranking_stability.csv')}")
    print(f"Wrote {_display_path(output_dir / 'execution_ladder_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'execution_ladder_summary.md')}")
    print(f"Rows: {len(rows)}")
    return 0


def _run_case(
    *,
    agent: str,
    level_id: str,
    level: dict[str, Any],
    seed: int,
    periods: int,
    symbols: tuple[str, ...],
    synthetic: dict[str, Any],
) -> dict[str, Any]:
    kwargs = {
        "strategy_name": agent,
        "analyst_names": ("momentum", "macro-news"),
        "symbols": symbols,
        "periods": periods,
        "seed": seed,
        "risk_name": "max-position",
        **synthetic,
        "execution_mode": level["execution_mode"],
        "spread_bps": float(level.get("spread_bps", 0.0)),
        "latency_steps": int(level.get("latency_steps", 1)),
        "participation_rate": float(level.get("participation_rate", 0.05)),
        "market_impact": float(level.get("market_impact", 0.15)),
    }
    if level.get("execution_calibration_profile_id"):
        kwargs["execution_calibration_profile_id"] = level["execution_calibration_profile_id"]
    _, metrics = build_default_system(
        name=f"v03_execution_ladder_{_safe(agent)}_{level_id}_{seed}",
        **kwargs,
    ).run()
    return {
        "protocol_id": "trellm-v0.3-protocol",
        "scenario_id": SCENARIO_ID,
        "contamination_tier": CONTAMINATION_TIER,
        "execution_level": level_id,
        "execution_label": level["label"],
        "execution_mode": level["execution_mode"],
        "agent": agent,
        "seed": seed,
        "total_return": _round(metrics.get("total_return", 0.0)),
        "sharpe": _round(metrics.get("sharpe", 0.0)),
        "max_drawdown": _round(metrics.get("max_drawdown", 0.0)),
        "execution_fill_rate": _round(metrics.get("execution_fill_rate", 0.0)),
        "rejected_order_count": int(metrics.get("rejected_order_count", 0)),
        "total_slippage_cost": _round(metrics.get("total_slippage_cost", 0.0)),
        "intent_risk_gap_l1": _round(metrics.get("intent_risk_gap_l1", 0.0)),
        "risk_execution_gap_l1": _round(metrics.get("risk_execution_gap_l1", 0.0)),
        "intent_execution_gap_l1": _round(metrics.get("intent_execution_gap_l1", 0.0)),
        "max_intent_execution_gap_l1": _round(metrics.get("max_intent_execution_gap_l1", 0.0)),
        "trajectory_reproducibility_coverage": 1.0,
        "evidence_tier": "protocol-fixture",
        "claim_scope": level["claim_scope"],
    }


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["execution_level"]), str(row["agent"])), []).append(row)

    output: list[dict[str, Any]] = []
    for (level_id, agent), group in sorted(grouped.items()):
        sharpe_stats = summarize_metric((float(row["sharpe"]) for row in group), prefix="sharpe")
        output.append(
            {
                "scenario_id": SCENARIO_ID,
                "contamination_tier": CONTAMINATION_TIER,
                "execution_level": level_id,
                "execution_label": EXECUTION_LEVELS[level_id]["label"],
                "agent": agent,
                "run_count": len(group),
                "rank": None,
                **{key: _nullable_round(value) for key, value in sharpe_stats.items()},
                "total_return_mean": _round(mean(float(row["total_return"]) for row in group)),
                "max_drawdown_mean": _round(mean(float(row["max_drawdown"]) for row in group)),
                "execution_fill_rate_mean": _round(mean(float(row["execution_fill_rate"]) for row in group)),
                "rejected_order_count_mean": _round(mean(float(row["rejected_order_count"]) for row in group)),
                "total_slippage_cost_mean": _round(mean(float(row["total_slippage_cost"]) for row in group)),
                "intent_execution_gap_l1_mean": _round(mean(float(row["intent_execution_gap_l1"]) for row in group)),
                "intent_risk_gap_l1_mean": _round(mean(float(row["intent_risk_gap_l1"]) for row in group)),
                "risk_execution_gap_l1_mean": _round(mean(float(row["risk_execution_gap_l1"]) for row in group)),
            }
        )

    by_level: dict[str, list[dict[str, Any]]] = {}
    for row in output:
        by_level.setdefault(str(row["execution_level"]), []).append(row)
    for level_rows in by_level.values():
        level_rows.sort(key=lambda row: (-float(row["sharpe_mean"]), str(row["agent"])))
        for rank, row in enumerate(level_rows, start=1):
            row["rank"] = rank
    return sorted(output, key=lambda row: (str(row["execution_level"]), int(row["rank"]), str(row["agent"])))


def _stability_rows(aggregate_rows: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    by_level: dict[str, dict[str, dict[str, Any]]] = {}
    for row in aggregate_rows:
        by_level.setdefault(str(row["execution_level"]), {})[str(row["agent"])] = row
    if "E0" not in by_level:
        return []
    baseline = by_level["E0"]
    output: list[dict[str, Any]] = []
    for level_id in sorted(level for level in by_level if level != "E0"):
        comparison = by_level[level_id]
        shared = sorted(set(baseline) & set(comparison))
        scores_a = {agent: float(baseline[agent]["sharpe_mean"]) for agent in shared}
        scores_b = {agent: float(comparison[agent]["sharpe_mean"]) for agent in shared}
        output.append(
            {
                "scenario_id": SCENARIO_ID,
                "contamination_tier": CONTAMINATION_TIER,
                "baseline_level": "E0",
                "comparison_level": level_id,
                "agent_count": len(shared),
                "rank_metric": f"{RANK_METRIC}_mean",
                "kendall_tau": _nullable_round(kendall_tau(scores_a, scores_b)),
                "top_k": top_k,
                "top_k_jaccard": _nullable_round(top_k_jaccard(scores_a, scores_b, k=top_k)),
                "mean_return_delta_vs_e0": _delta_mean(shared, comparison, baseline, "total_return_mean"),
                "mean_fill_rate_delta_vs_e0": _delta_mean(shared, comparison, baseline, "execution_fill_rate_mean"),
                "mean_intent_execution_gap_delta_vs_e0": _delta_mean(shared, comparison, baseline, "intent_execution_gap_l1_mean"),
                "mean_slippage_delta_vs_e0": _delta_mean(shared, comparison, baseline, "total_slippage_cost_mean"),
            }
        )
    return output


def _summary(
    rows: list[dict[str, Any]],
    aggregate_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    *,
    levels: list[str],
    agents: list[str],
    seeds: list[int],
    periods: int,
    top_k: int,
) -> dict[str, Any]:
    e3_scope = EXECUTION_LEVELS["E3"]["claim_scope"] if "E3" in levels else ""
    return {
        "schema": "trellm_v0_3_execution_ladder_v0.1",
        "protocol_id": "trellm-v0.3-protocol",
        "scenario_id": SCENARIO_ID,
        "contamination_tier": CONTAMINATION_TIER,
        "execution_levels": levels,
        "agents": agents,
        "seeds": seeds,
        "periods": periods,
        "top_k": top_k,
        "row_count": len(rows),
        "aggregate_row_count": len(aggregate_rows),
        "ranking_stability_row_count": len(stability_rows),
        "rank_metric": f"{RANK_METRIC}_mean",
        "mechanism_metrics": [
            "execution_fill_rate",
            "rejected_order_count",
            "total_slippage_cost",
            "intent_risk_gap_l1",
            "risk_execution_gap_l1",
            "intent_execution_gap_l1",
        ],
        "claim_boundary": (
            "Execution ladder protocol fixture for TreLLM reliability analysis. "
            "It reports how rankings and mechanism metrics move under execution assumptions; "
            "it is not a trading-profit claim."
        ),
        "e3_boundary": e3_scope,
        "artifacts": [
            "execution_ladder_rows.csv",
            "execution_ladder_aggregate.csv",
            "execution_ladder_ranking_stability.csv",
            "execution_ladder_summary.json",
            "execution_ladder_summary.md",
        ],
    }


def _summary_markdown(
    summary: dict[str, Any],
    aggregate_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# TreLLM v0.3 Execution Ladder",
        "",
        "This artifact reports how deterministic agent rankings and mechanism metrics move across the v0.3 execution-assumption ladder.",
        "It is not a trading-profit claim.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Scenario: `{summary['scenario_id']}`",
        f"- Contamination tier: `{summary['contamination_tier']}`",
        f"- Levels: `{', '.join(summary['execution_levels'])}`",
        f"- Agents: `{', '.join(summary['agents'])}`",
        f"- Seeds: `{', '.join(str(seed) for seed in summary['seeds'])}`",
        f"- Rank metric: `{summary['rank_metric']}`",
        f"- Mechanism metrics: `{', '.join(summary['mechanism_metrics'])}`",
        f"- Claim boundary: {summary['claim_boundary']}",
    ]
    if summary.get("e3_boundary"):
        lines.append(f"- E3 boundary: {summary['e3_boundary']}")
    lines += [
        "",
        "## Ranking Stability vs E0",
        "",
        "| Baseline | Comparison | Agents | Kendall tau | Top-k Jaccard | Return delta | Fill delta | Intent-execution gap delta | Slippage delta |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in stability_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["baseline_level"]),
                    str(row["comparison_level"]),
                    str(row["agent_count"]),
                    _fmt(row["kendall_tau"]),
                    _fmt(row["top_k_jaccard"]),
                    _fmt(row["mean_return_delta_vs_e0"]),
                    _fmt(row["mean_fill_rate_delta_vs_e0"]),
                    _fmt(row["mean_intent_execution_gap_delta_vs_e0"]),
                    _fmt(row["mean_slippage_delta_vs_e0"]),
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Per-Level Summary",
        "",
        "| Level | Rank | Agent | Sharpe mean | Return mean | Fill rate | Rejected orders | Slippage | Intent-execution gap |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in aggregate_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["execution_level"]),
                    str(row["rank"]),
                    str(row["agent"]),
                    _fmt(row["sharpe_mean"]),
                    _fmt(row["total_return_mean"]),
                    _fmt(row["execution_fill_rate_mean"]),
                    _fmt(row["rejected_order_count_mean"]),
                    _fmt(row["total_slippage_cost_mean"]),
                    _fmt(row["intent_execution_gap_l1_mean"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _delta_mean(
    agents: list[str],
    comparison: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    key: str,
) -> float:
    if not agents:
        return 0.0
    return _round(mean(float(comparison[agent][key]) - float(baseline[agent][key]) for agent in agents))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_levels(value: str) -> list[str]:
    levels = _parse_list(value, "levels")
    unknown = [level for level in levels if level not in EXECUTION_LEVELS]
    if unknown:
        raise SystemExit(f"Unknown execution levels: {', '.join(unknown)}")
    return levels


def _parse_ints(value: str, label: str) -> list[int]:
    try:
        values = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise SystemExit(f"{label} must be a comma-separated list of integers") from exc
    if not values:
        raise SystemExit(f"{label} must contain at least one item")
    return values


def _parse_list(value: str, label: str) -> list[str]:
    values = [part.strip() for part in value.split(",") if part.strip()]
    if not values:
        raise SystemExit(f"{label} must contain at least one item")
    return values


def _resolve_output_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _safe(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _round(value: Any) -> float:
    return round(float(value or 0.0), 6)


def _nullable_round(value: Any) -> float | None:
    if value is None:
        return None
    return _round(value)


def _fmt(value: Any) -> str:
    if value in ("", None):
        return ""
    return f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
