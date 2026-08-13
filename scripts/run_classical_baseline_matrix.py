from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_leaderboard_model_matrix import SCENARIOS as SYNTHETIC_SCENARIOS
from run_leaderboard_model_matrix import _scenario_execution_config
from run_real_market_leaderboard import (
    REAL_SCENARIOS,
    _data_hash,
)

from tradearena.factory import build_default_system

CLASSICAL_BASELINES: dict[str, dict[str, str]] = {
    "always_hold": {
        "label": "Always hold",
        "strategy": "always-hold",
        "family": "lower_anchor",
    },
    "random": {
        "label": "Random",
        "strategy": "random",
        "family": "lower_anchor",
    },
    "buy_and_hold": {
        "label": "Buy and hold",
        "strategy": "buy-and-hold",
        "family": "passive",
    },
    "equal_weight": {
        "label": "Equal weight",
        "strategy": "equal-weight",
        "family": "passive_rebalance",
    },
    "naive_momentum": {
        "label": "Naive momentum",
        "strategy": "naive-momentum",
        "family": "trend_following",
    },
    "mean_reversion": {
        "label": "Mean reversion",
        "strategy": "mean-reversion",
        "family": "contrarian",
    },
    "risk_parity": {
        "label": "Risk parity",
        "strategy": "risk-parity",
        "family": "volatility_weighted",
    },
    "min_var": {
        "label": "Minimum variance",
        "strategy": "min-var",
        "family": "covariance_weighted",
    },
    "markowitz_mvo": {
        "label": "Markowitz MVO",
        "strategy": "markowitz-mvo",
        "family": "mean_variance_weighted",
    },
}
QUALITY_FIELDS = (
    "alpha_pre_risk_total_return",
    "alpha_pre_risk_sharpe",
    "alpha_pre_risk_hit_rate",
    "alpha_pre_risk_steps",
    "alpha_quality_score",
    "risk_discipline_score",
    "execution_robustness_score",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run non-LLM classical baselines on the synthetic and real-market leaderboard scenarios."
    )
    parser.add_argument("--baselines", default=",".join(CLASSICAL_BASELINES), help="Comma-separated baseline keys.")
    parser.add_argument("--synthetic-scenarios", default=",".join(SYNTHETIC_SCENARIOS), help="Comma-separated synthetic scenarios.")
    parser.add_argument("--real-scenarios", default=",".join(REAL_SCENARIOS), help="Comma-separated real-market scenarios.")
    parser.add_argument("--synthetic-symbols", default="SYN,ALT")
    parser.add_argument("--real-symbols", default="GSPC,BTC-USD,BTC=F")
    parser.add_argument("--synthetic-periods", type=int, default=8)
    parser.add_argument("--real-max-periods", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--real-data-dir", default="data/real/yahoo_daily_leaderboard_2021_2026")
    parser.add_argument("--output-dir", default="docs/results/classical_baselines")
    args = parser.parse_args(argv)

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    baselines = [_baseline(key) for key in args.baselines.split(",") if key.strip()]
    synthetic_scenarios = [_synthetic_scenario(key) for key in args.synthetic_scenarios.split(",") if key.strip()]
    real_scenarios = [_real_scenario(key) for key in args.real_scenarios.split(",") if key.strip()]
    synthetic_symbols = tuple(symbol.strip() for symbol in args.synthetic_symbols.split(",") if symbol.strip())
    real_symbols = tuple(symbol.strip() for symbol in args.real_symbols.split(",") if symbol.strip())

    rows: list[dict[str, Any]] = []
    for scenario in synthetic_scenarios:
        for baseline in baselines:
            rows.append(
                _run_synthetic_baseline(
                    scenario=scenario,
                    baseline=baseline,
                    symbols=synthetic_symbols,
                    periods=args.synthetic_periods,
                    seed=args.seed + int(scenario["seed_offset"]),
                )
            )
    data_dir = ROOT / args.real_data_dir
    real_data_hash = _data_hash(data_dir, real_symbols)
    for scenario in real_scenarios:
        for baseline in baselines:
            rows.append(
                _run_real_baseline(
                    scenario=scenario,
                    baseline=baseline,
                    symbols=real_symbols,
                    max_periods=args.real_max_periods,
                    data_dir=data_dir,
                    data_hash=real_data_hash,
                )
            )

    comparison_rows = _comparison_rows(rows)
    aggregate_rows = _aggregate_rows(rows)
    _write_csv(output_dir / "classical_baseline_matrix.csv", rows)
    _write_csv(output_dir / "classical_baseline_aggregate.csv", aggregate_rows)
    _write_csv(output_dir / "classical_vs_llm_comparison.csv", comparison_rows)
    _write_markdown(output_dir / "classical_baselines.md", rows, aggregate_rows, comparison_rows)
    print(f"Wrote {output_dir.relative_to(ROOT) / 'classical_baseline_matrix.csv'}")
    print(f"Wrote {output_dir.relative_to(ROOT) / 'classical_baseline_aggregate.csv'}")
    print(f"Wrote {output_dir.relative_to(ROOT) / 'classical_vs_llm_comparison.csv'}")
    print(f"Wrote {output_dir.relative_to(ROOT) / 'classical_baselines.md'}")
    return 0


def _run_synthetic_baseline(
    *,
    scenario: dict[str, Any],
    baseline: dict[str, str],
    symbols: tuple[str, ...],
    periods: int,
    seed: int,
) -> dict[str, Any]:
    execution = _scenario_execution_config(scenario)
    _trajectory, metrics = build_default_system(
        name=f"classical_{scenario['key']}_{baseline['key']}",
        symbols=symbols,
        periods=periods,
        seed=seed,
        analyst_names=(),
        strategy_name=baseline["strategy"],
        risk_name="max-position",
        execution_mode="realistic",
        commission_bps=float(execution["commission_bps"]),
        slippage_bps=float(execution["base_slippage_bps"]),
        spread_bps=float(execution["spread_bps"]),
        participation_rate=float(execution["participation_rate"]),
        latency_steps=int(execution["latency_steps"]),
        market_impact=float(execution["market_impact"]),
        **scenario["synthetic"],
    ).run()
    return _row(
        universe="synthetic",
        scenario_key=str(scenario["key"]),
        scenario_id=str(scenario["scenario_id"]),
        scenario_label=str(scenario["label"]),
        baseline=baseline,
        symbols=symbols,
        data_source="synthetic-market",
        frequency="daily",
        data_hash=f"sha256:synthetic-{scenario['key']}-seed-{seed}-symbols-{'-'.join(symbols)}-periods-{periods}",
        metrics=metrics,
    )


def _run_real_baseline(
    *,
    scenario: dict[str, Any],
    baseline: dict[str, str],
    symbols: tuple[str, ...],
    max_periods: int,
    data_dir: Path,
    data_hash: str,
) -> dict[str, Any]:
    _trajectory, metrics = build_default_system(
        name=f"classical_real_{scenario['key']}_{baseline['key']}",
        symbols=symbols,
        periods=max_periods,
        seed=7,
        analyst_names=(),
        strategy_name=baseline["strategy"],
        risk_name="max-position",
        execution_mode="realistic",
        data_source="csv",
        real_data_dir=str(data_dir),
        real_data_frequency="weekly",
        real_data_start=str(scenario["start"]),
        real_data_end=str(scenario["end"]),
        real_data_max_periods=max_periods,
    ).run()
    return _row(
        universe="real_market",
        scenario_key=str(scenario["key"]),
        scenario_id=str(scenario["scenario_id"]),
        scenario_label=str(scenario["label"]),
        baseline=baseline,
        symbols=symbols,
        data_source="yahoo-finance-csv",
        frequency="weekly",
        data_hash=data_hash,
        metrics=metrics,
    )


def _row(
    *,
    universe: str,
    scenario_key: str,
    scenario_id: str,
    scenario_label: str,
    baseline: dict[str, str],
    symbols: tuple[str, ...],
    data_source: str,
    frequency: str,
    data_hash: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "universe": universe,
        "scenario_key": scenario_key,
        "scenario_id": scenario_id,
        "scenario_label": scenario_label,
        "provider": "deterministic",
        "model": baseline["key"],
        "baseline_label": baseline["label"],
        "baseline_family": baseline["family"],
        "strategy": baseline["strategy"],
        "data_source": data_source,
        "frequency": frequency,
        "symbols": ";".join(symbols),
        "data_hash": data_hash,
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


def _comparison_rows(classical_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    llm_rows = _read_llm_rows()
    grouped_classical: dict[tuple[str, str], list[dict[str, Any]]] = {}
    grouped_llm: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in classical_rows:
        grouped_classical.setdefault((str(row["universe"]), str(row["scenario_key"])), []).append(row)
    for row in llm_rows:
        grouped_llm.setdefault((str(row["universe"]), str(row["scenario_key"])), []).append(row)

    rows = []
    for key, baseline_rows in sorted(grouped_classical.items()):
        universe, scenario_key = key
        candidate_llm_rows = grouped_llm.get(key, [])
        best_baseline = max(baseline_rows, key=lambda row: float(row["total_return"]))
        best_llm = max(candidate_llm_rows, key=lambda row: float(row["total_return"])) if candidate_llm_rows else {}
        if best_llm:
            llm_return = float(best_llm["total_return"])
            llm_drawdown = float(best_llm["max_drawdown"])
            llm_model = str(best_llm["model"])
            llm_provider = str(best_llm["provider"])
        else:
            llm_return = 0.0
            llm_drawdown = 0.0
            llm_model = ""
            llm_provider = ""
        rows.append(
            {
                "universe": universe,
                "scenario_key": scenario_key,
                "scenario_label": best_baseline["scenario_label"],
                "best_classical": best_baseline["baseline_label"],
                "best_classical_return": best_baseline["total_return"],
                "best_classical_drawdown": best_baseline["max_drawdown"],
                "best_llm_provider": llm_provider,
                "best_llm_model": llm_model,
                "best_llm_return": llm_return,
                "best_llm_drawdown": llm_drawdown,
                "llm_return_minus_classical": llm_return - float(best_baseline["total_return"]) if best_llm else "",
                "llm_outperforms_classical_return": bool(best_llm and llm_return > float(best_baseline["total_return"])),
            }
        )
    return rows


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["universe"]), str(row["model"]), str(row["baseline_label"])), []).append(row)
    aggregate = []
    for (universe, model, label), group in sorted(grouped.items()):
        aggregate.append(
            {
                "universe": universe,
                "model": model,
                "baseline_label": label,
                "scenario_count": len(group),
                "avg_return": _avg(row["total_return"] for row in group),
                "worst_drawdown": min(float(row["max_drawdown"]) for row in group),
                "avg_sharpe": _avg(row["sharpe"] for row in group),
                "avg_fill_rate": _avg(row["execution_fill_rate"] for row in group),
                "total_rejected_orders": sum(int(row["rejected_order_count"]) for row in group),
                "total_risk_edits": sum(int(row["risk_clipped_decisions"]) for row in group),
                "avg_alpha_quality": _avg(row["alpha_quality_score"] for row in group),
                "avg_risk_discipline": _avg(row["risk_discipline_score"] for row in group),
                "avg_execution_robustness": _avg(row["execution_robustness_score"] for row in group),
            }
        )
    return sorted(aggregate, key=lambda row: (str(row["universe"]), -float(row["avg_return"])))


def _read_llm_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    synthetic_path = ROOT / "docs/results/model_matrix/leaderboard_model_matrix.csv"
    if synthetic_path.exists():
        for row in _read_csv(synthetic_path):
            if row.get("provider") == "baseline":
                continue
            row["universe"] = "synthetic"
            rows.append(row)
    real_path = ROOT / "docs/results/real_market_matrix/real_market_model_matrix.csv"
    if real_path.exists():
        for row in _read_csv(real_path):
            if row.get("provider") == "baseline":
                continue
            row["universe"] = "real_market"
            rows.append(row)
    return rows


def _write_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    aggregate_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# Classical Baseline Matrix",
        "",
        "This table is generated by `python scripts/run_classical_baseline_matrix.py`.",
        "It adds non-LLM baselines to the synthetic and real-market model matrices so the benchmark can ask whether LLM agents beat classical strategies, not only other LLMs.",
        "",
        "## Baselines",
        "",
        "- Naive momentum: long recent winners.",
        "- Mean reversion: long recent underperformers.",
        "- Risk parity: rolling inverse-volatility allocation.",
        "- Minimum variance: rolling covariance-driven minimum-variance allocation.",
        "- Markowitz MVO: rolling expected-return and covariance allocation.",
        "- Passive anchors: buy-and-hold, equal-weight rebalance, random, and always-hold.",
        "",
        "## Does The Best LLM Outperform The Best Classical Baseline?",
        "",
        "| Universe | Scenario | Best classical | Classical return | Best LLM | LLM return | Return gap | LLM wins? |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | --- |",
    ]
    for row in comparison_rows:
        llm_label = f"{row['best_llm_provider']}:{row['best_llm_model']}" if row["best_llm_model"] else "no LLM row"
        gap = row["llm_return_minus_classical"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["universe"]),
                    str(row["scenario_label"]),
                    str(row["best_classical"]),
                    _fmt(row["best_classical_return"]),
                    llm_label,
                    _fmt(row["best_llm_return"]),
                    _fmt(gap) if gap != "" else "",
                    "yes" if row["llm_outperforms_classical_return"] else "no",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Classical Aggregate",
            "",
            "| Universe | Baseline | Scenarios | Avg return | Worst DD | Avg Sharpe | Avg fill | Alpha | Risk | Execution | Rejected | Risk edits |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in aggregate_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["universe"]),
                    str(row["baseline_label"]),
                    str(row["scenario_count"]),
                    _fmt(row["avg_return"]),
                    _fmt(row["worst_drawdown"]),
                    _fmt(row["avg_sharpe"]),
                    _fmt(row["avg_fill_rate"]),
                    _fmt(row["avg_alpha_quality"]),
                    _fmt(row["avg_risk_discipline"]),
                    _fmt(row["avg_execution_robustness"]),
                    str(row["total_rejected_orders"]),
                    str(row["total_risk_edits"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Scenario Rows",
            "",
            "| Universe | Scenario | Baseline | Return | Max DD | Sharpe | Alpha | Risk | Execution | Fill | Rejected | Risk edits |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["universe"]),
                    str(row["scenario_label"]),
                    str(row["baseline_label"]),
                    _fmt(row["total_return"]),
                    _fmt(row["max_drawdown"]),
                    _fmt(row["sharpe"]),
                    _fmt(row["alpha_quality_score"]),
                    _fmt(row["risk_discipline_score"]),
                    _fmt(row["execution_robustness_score"]),
                    _fmt(row["execution_fill_rate"]),
                    str(row["rejected_order_count"]),
                    str(row["risk_clipped_decisions"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _baseline(key: str) -> dict[str, str]:
    normalized = key.strip()
    if normalized not in CLASSICAL_BASELINES:
        raise ValueError(f"Unknown baseline: {normalized}. Available: {', '.join(CLASSICAL_BASELINES)}")
    baseline = dict(CLASSICAL_BASELINES[normalized])
    baseline["key"] = normalized
    return baseline


def _synthetic_scenario(key: str) -> dict[str, Any]:
    normalized = key.strip()
    if normalized not in SYNTHETIC_SCENARIOS:
        raise ValueError(f"Unknown synthetic scenario: {normalized}. Available: {', '.join(SYNTHETIC_SCENARIOS)}")
    scenario = dict(SYNTHETIC_SCENARIOS[normalized])
    scenario["key"] = normalized
    scenario["synthetic"] = dict(scenario["synthetic"])
    scenario["execution"] = dict(scenario.get("execution", {}))
    return scenario


def _real_scenario(key: str) -> dict[str, Any]:
    normalized = key.strip()
    if normalized not in REAL_SCENARIOS:
        raise ValueError(f"Unknown real-market scenario: {normalized}. Available: {', '.join(REAL_SCENARIOS)}")
    scenario = dict(REAL_SCENARIOS[normalized])
    scenario["key"] = normalized
    return scenario


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0]) if rows else ["universe", "scenario_key", "model"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def _fmt(value: Any) -> str:
    return f"{float(value):.4f}"


def _avg(values: Any) -> float:
    numbers = [float(value) for value in values]
    return sum(numbers) / len(numbers) if numbers else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
