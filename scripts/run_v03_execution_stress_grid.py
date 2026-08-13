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

from tradearena.evaluation.statistics import mean
from tradearena.factory import build_default_system

PROTOCOL_ID = "trellm-v0.3-protocol"
SCENARIO_ID = "synthetic_calm_trend_c0_v0_3"
CONTAMINATION_TIER = "C0"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_execution_stress_grid"
DEFAULT_AGENTS = ("signal-weighted", "risk-parity", "random")
DEFAULT_SEEDS = (7, 11)
DEFAULT_PROFILES = (
    "e1_reference",
    "wide_spread",
    "latency_spike",
    "thin_liquidity",
    "high_impact",
    "combined_stress",
)
STRESS_PROFILES: dict[str, dict[str, Any]] = {
    "e1_reference": {
        "spread_bps": 8.0,
        "latency_steps": 1,
        "participation_rate": 0.05,
        "market_impact": 0.15,
        "axis": "reference",
        "claim_scope": "Default E1 paper-stress reference for paired E2 grid deltas.",
    },
    "wide_spread": {
        "spread_bps": 24.0,
        "latency_steps": 1,
        "participation_rate": 0.05,
        "market_impact": 0.15,
        "axis": "spread",
        "claim_scope": "Spread-only stress probe; not a venue-wide spread forecast.",
    },
    "latency_spike": {
        "spread_bps": 8.0,
        "latency_steps": 4,
        "participation_rate": 0.05,
        "market_impact": 0.15,
        "axis": "latency",
        "claim_scope": "Latency-only stress probe; not a broker latency guarantee.",
    },
    "thin_liquidity": {
        "spread_bps": 8.0,
        "latency_steps": 1,
        "participation_rate": 0.01,
        "market_impact": 0.15,
        "axis": "participation",
        "claim_scope": "Participation-cap stress probe; not a market-depth calibration.",
    },
    "high_impact": {
        "spread_bps": 8.0,
        "latency_steps": 1,
        "participation_rate": 0.05,
        "market_impact": 0.35,
        "axis": "impact",
        "claim_scope": "Market-impact stress probe; not a transaction-cost model fit.",
    },
    "combined_stress": {
        "spread_bps": 24.0,
        "latency_steps": 4,
        "participation_rate": 0.01,
        "market_impact": 0.35,
        "axis": "combined",
        "claim_scope": "Combined E2 stress corner for execution-assumption sensitivity.",
    },
}

ROW_FIELDS = [
    "protocol_id",
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "stress_profile",
    "stress_axis",
    "agent",
    "seed",
    "spread_bps",
    "latency_steps",
    "participation_rate",
    "market_impact",
    "total_return",
    "sharpe",
    "max_drawdown",
    "execution_fill_rate",
    "rejected_order_count",
    "total_slippage_cost",
    "intent_execution_gap_l1",
    "risk_execution_gap_l1",
    "evidence_tier",
    "claim_scope",
]
SENSITIVITY_FIELDS = [
    "protocol_id",
    "scenario_id",
    "contamination_tier",
    "baseline_profile",
    "stress_profile",
    "stress_axis",
    "agent",
    "paired_seed_count",
    "spread_bps",
    "latency_steps",
    "participation_rate",
    "market_impact",
    "total_return_delta_mean",
    "sharpe_delta_mean",
    "max_drawdown_delta_mean",
    "fill_rate_delta_mean",
    "rejected_order_delta_mean",
    "slippage_delta_mean",
    "intent_execution_gap_delta_mean",
    "absolute_return_delta_mean",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the TreLLM v0.3 E2 execution stress-grid artifact.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--agents", default=",".join(DEFAULT_AGENTS))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--profiles", default=",".join(DEFAULT_PROFILES))
    parser.add_argument("--periods", type=int, default=16)
    parser.add_argument("--symbols", default="SYN,ALT")
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    agents = _parse_list(args.agents, "agents")
    seeds = _parse_ints(args.seeds, "seeds")
    profiles = _parse_profiles(args.profiles)
    symbols = tuple(_parse_list(args.symbols, "symbols"))

    rows = [
        _run_case(agent=agent, seed=seed, profile_id=profile_id, profile=STRESS_PROFILES[profile_id], periods=args.periods, symbols=symbols)
        for profile_id in profiles
        for agent in agents
        for seed in seeds
    ]
    sensitivity_rows = _sensitivity_rows(rows)
    summary = _summary(rows, sensitivity_rows, agents=agents, seeds=seeds, profiles=profiles, periods=args.periods)

    _write_csv(output_dir / "execution_stress_grid_rows.csv", rows, ROW_FIELDS)
    _write_csv(output_dir / "execution_stress_grid_sensitivity.csv", sensitivity_rows, SENSITIVITY_FIELDS)
    _write_json(output_dir / "execution_stress_grid_summary.json", summary)
    (output_dir / "execution_stress_grid_summary.md").write_text(
        _summary_markdown(summary, sensitivity_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display(output_dir / 'execution_stress_grid_rows.csv')}")
    print(f"Wrote {_display(output_dir / 'execution_stress_grid_sensitivity.csv')}")
    print(f"Wrote {_display(output_dir / 'execution_stress_grid_summary.json')}")
    print(f"Wrote {_display(output_dir / 'execution_stress_grid_summary.md')}")
    print(f"Rows: {len(rows)}")
    print(f"Sensitivity rows: {len(sensitivity_rows)}")
    return 0


def _run_case(
    *,
    agent: str,
    seed: int,
    profile_id: str,
    profile: dict[str, Any],
    periods: int,
    symbols: tuple[str, ...],
) -> dict[str, Any]:
    _, metrics = build_default_system(
        name=f"v03_execution_stress_grid_{_safe(agent)}_{profile_id}_{seed}",
        strategy_name=agent,
        analyst_names=("momentum", "macro-news"),
        symbols=symbols,
        periods=periods,
        seed=seed,
        risk_name="max-position",
        synthetic_volatility_scale=1.0,
        synthetic_trend_scale=1.0,
        execution_mode="realistic",
        spread_bps=float(profile["spread_bps"]),
        latency_steps=int(profile["latency_steps"]),
        participation_rate=float(profile["participation_rate"]),
        market_impact=float(profile["market_impact"]),
    ).run()
    return {
        "protocol_id": PROTOCOL_ID,
        "scenario_id": SCENARIO_ID,
        "contamination_tier": CONTAMINATION_TIER,
        "execution_level": "E1" if profile_id == "e1_reference" else "E2",
        "stress_profile": profile_id,
        "stress_axis": profile["axis"],
        "agent": agent,
        "seed": seed,
        "spread_bps": profile["spread_bps"],
        "latency_steps": profile["latency_steps"],
        "participation_rate": profile["participation_rate"],
        "market_impact": profile["market_impact"],
        "total_return": _round(metrics.get("total_return", 0.0)),
        "sharpe": _round(metrics.get("sharpe", 0.0)),
        "max_drawdown": _round(metrics.get("max_drawdown", 0.0)),
        "execution_fill_rate": _round(metrics.get("execution_fill_rate", 0.0)),
        "rejected_order_count": int(metrics.get("rejected_order_count", 0)),
        "total_slippage_cost": _round(metrics.get("total_slippage_cost", 0.0)),
        "intent_execution_gap_l1": _round(metrics.get("intent_execution_gap_l1", 0.0)),
        "risk_execution_gap_l1": _round(metrics.get("risk_execution_gap_l1", 0.0)),
        "evidence_tier": "protocol-fixture",
        "claim_scope": profile["claim_scope"],
    }


def _sensitivity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(str(row["agent"]), int(row["seed"]), str(row["stress_profile"])): row for row in rows}
    agents = sorted({str(row["agent"]) for row in rows})
    profiles = [profile for profile in DEFAULT_PROFILES if profile != "e1_reference"]
    output: list[dict[str, Any]] = []
    for agent in agents:
        for profile_id in profiles:
            profile = STRESS_PROFILES[profile_id]
            paired: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for seed in sorted({int(row["seed"]) for row in rows if str(row["agent"]) == agent}):
                baseline = by_key.get((agent, seed, "e1_reference"))
                stressed = by_key.get((agent, seed, profile_id))
                if baseline and stressed:
                    paired.append((baseline, stressed))
            if not paired:
                continue
            output.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "scenario_id": SCENARIO_ID,
                    "contamination_tier": CONTAMINATION_TIER,
                    "baseline_profile": "e1_reference",
                    "stress_profile": profile_id,
                    "stress_axis": profile["axis"],
                    "agent": agent,
                    "paired_seed_count": len(paired),
                    "spread_bps": profile["spread_bps"],
                    "latency_steps": profile["latency_steps"],
                    "participation_rate": profile["participation_rate"],
                    "market_impact": profile["market_impact"],
                    "total_return_delta_mean": _delta_mean(paired, "total_return"),
                    "sharpe_delta_mean": _delta_mean(paired, "sharpe"),
                    "max_drawdown_delta_mean": _delta_mean(paired, "max_drawdown"),
                    "fill_rate_delta_mean": _delta_mean(paired, "execution_fill_rate"),
                    "rejected_order_delta_mean": _delta_mean(paired, "rejected_order_count"),
                    "slippage_delta_mean": _delta_mean(paired, "total_slippage_cost"),
                    "intent_execution_gap_delta_mean": _delta_mean(paired, "intent_execution_gap_l1"),
                    "absolute_return_delta_mean": _round(mean(abs(float(stressed["total_return"]) - float(baseline["total_return"])) for baseline, stressed in paired)),
                }
            )
    return output


def _summary(
    rows: list[dict[str, Any]],
    sensitivity_rows: list[dict[str, Any]],
    *,
    agents: list[str],
    seeds: list[int],
    profiles: list[str],
    periods: int,
) -> dict[str, Any]:
    max_abs_return_delta = max((abs(float(row["total_return_delta_mean"])) for row in sensitivity_rows), default=0.0)
    max_slippage_delta = max((float(row["slippage_delta_mean"]) for row in sensitivity_rows), default=0.0)
    return {
        "schema": "trellm_v0_3_execution_stress_grid_v0.1",
        "protocol_id": PROTOCOL_ID,
        "scenario_id": SCENARIO_ID,
        "contamination_tier": CONTAMINATION_TIER,
        "execution_levels": ["E1", "E2"],
        "baseline_profile": "e1_reference",
        "stress_profiles": profiles,
        "stress_axes": sorted({STRESS_PROFILES[profile]["axis"] for profile in profiles}),
        "agents": agents,
        "seeds": seeds,
        "periods": periods,
        "row_count": len(rows),
        "sensitivity_row_count": len(sensitivity_rows),
        "max_abs_return_delta_mean": _round(max_abs_return_delta),
        "max_slippage_delta_mean": _round(max_slippage_delta),
        "method": "paired_seed_delta_vs_e1_reference",
        "claim_boundary": (
            "This fixture isolates execution-assumption sensitivity across spread, latency, participation, and impact. "
            "It supports protocol plumbing and mechanism analysis, not live cost prediction or trading-profit claims."
        ),
        "artifacts": [
            "execution_stress_grid_rows.csv",
            "execution_stress_grid_sensitivity.csv",
            "execution_stress_grid_summary.json",
            "execution_stress_grid_summary.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], sensitivity_rows: list[dict[str, Any]]) -> str:
    axis_rows = _axis_summary(sensitivity_rows)
    lines = [
        "# TreLLM v0.3 Execution Stress Grid",
        "",
        "This artifact isolates E2 execution-assumption sensitivity against an E1 reference.",
        "It is not a trading-profit claim or a calibrated live-cost forecast.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Scenario: `{summary['scenario_id']}`",
        f"- Contamination tier: `{summary['contamination_tier']}`",
        f"- Profiles: `{', '.join(summary['stress_profiles'])}`",
        f"- Agents: `{', '.join(summary['agents'])}`",
        f"- Seeds: `{', '.join(str(seed) for seed in summary['seeds'])}`",
        f"- Method: `{summary['method']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Axis Summary",
        "",
        "| Axis | Rows | Mean absolute return delta | Mean slippage delta | Mean fill-rate delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in axis_rows:
        lines.append(
            f"| {row['stress_axis']} | {row['row_count']} | {_fmt(row['mean_abs_return_delta'])} | "
            f"{_fmt(row['mean_slippage_delta'])} | {_fmt(row['mean_fill_rate_delta'])} |"
        )
    lines += [
        "",
        "## Paired Sensitivity Rows",
        "",
        "| Profile | Axis | Agent | Seeds | Return delta | Sharpe delta | Fill-rate delta | Slippage delta | Intent-execution gap delta |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sensitivity_rows:
        lines.append(
            f"| {row['stress_profile']} | {row['stress_axis']} | {row['agent']} | {row['paired_seed_count']} | "
            f"{_fmt(row['total_return_delta_mean'])} | {_fmt(row['sharpe_delta_mean'])} | "
            f"{_fmt(row['fill_rate_delta_mean'])} | {_fmt(row['slippage_delta_mean'])} | "
            f"{_fmt(row['intent_execution_gap_delta_mean'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def _axis_summary(sensitivity_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in sensitivity_rows:
        grouped.setdefault(str(row["stress_axis"]), []).append(row)
    output = []
    for axis, rows in sorted(grouped.items()):
        output.append(
            {
                "stress_axis": axis,
                "row_count": len(rows),
                "mean_abs_return_delta": _round(mean(abs(float(row["total_return_delta_mean"])) for row in rows)),
                "mean_slippage_delta": _round(mean(float(row["slippage_delta_mean"]) for row in rows)),
                "mean_fill_rate_delta": _round(mean(float(row["fill_rate_delta_mean"]) for row in rows)),
            }
        )
    return output


def _delta_mean(paired: list[tuple[dict[str, Any], dict[str, Any]]], metric: str) -> float:
    return _round(mean(float(stressed[metric]) - float(baseline[metric]) for baseline, stressed in paired))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_profiles(value: str) -> list[str]:
    profiles = _parse_list(value, "profiles")
    unknown = [profile for profile in profiles if profile not in STRESS_PROFILES]
    if unknown:
        raise SystemExit(f"Unknown stress profiles: {', '.join(unknown)}")
    if "e1_reference" not in profiles:
        raise SystemExit("profiles must include e1_reference for paired deltas")
    return profiles


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


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _safe(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _round(value: Any) -> float:
    return round(float(value or 0.0), 6)


def _fmt(value: Any) -> str:
    if value in ("", None):
        return ""
    return f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
