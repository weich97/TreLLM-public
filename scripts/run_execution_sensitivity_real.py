"""Real-market hybrid check for execution-sensitivity ranking instability.

Reviewer external-validity ask: does the leaderboard reordering under the
execution-assumption ladder persist on real prices, or is it an artifact of
synthetic regimes? This runs the deterministic agents on real Yahoo OHLCV
across the same ladder and reports ranking stability (Kendall tau-b, top-k
Jaccard) between idealized and stressed execution, exactly as the synthetic
sweep does. Deterministic agents only: no API access, fully reproducible.
(LLM agents on real data would need live calls and a contamination
argument; the hybrid check is about whether the friction-driven reordering
survives on empirical price/volume paths, which the classical agents answer.)

Usage:
  python scripts/run_execution_sensitivity_real.py \
    --data-dir data/real/yahoo_daily_leaderboard_2021_2026 \
    --symbols GSPC,BTC-USD,BTC=F --output-dir docs/results/execution_sensitivity_real
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.statistics import kendall_tau, mean, top_k_jaccard
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
RANK_METRIC = "sharpe"

# Same ladder as the synthetic sweep.
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

# Two real-market windows mirroring the leaderboard real scenarios.
WINDOWS = {
    "rates_drawdown_2022": {"start": "2022-01-01", "end": "2022-12-31"},
    "recent_cross_asset": {"start": "2025-05-01", "end": "2026-05-14"},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Real-market execution-sensitivity ranking-stability check.")
    parser.add_argument("--data-dir", default="data/real/yahoo_daily_leaderboard_2021_2026")
    parser.add_argument("--symbols", default="GSPC,BTC-USD,BTC=F")
    parser.add_argument("--frequency", default="weekly", choices=["daily", "weekly"])
    parser.add_argument("--max-periods", type=int, default=12)
    parser.add_argument("--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS))
    parser.add_argument("--windows", default=",".join(WINDOWS))
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output-dir", default="docs/results/execution_sensitivity_real")
    args = parser.parse_args(argv)

    symbols = tuple(s.strip() for s in args.symbols.split(",") if s.strip())
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    windows = {w: WINDOWS[w] for w in args.windows.split(",") if w.strip()}
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_rows: list[dict[str, Any]] = []
    for window_key, window in windows.items():
        for level_key, level in EXECUTION_LEVELS.items():
            for agent in DEFAULT_AGENTS:
                for seed_index, seed in enumerate(seeds):
                    metrics = _run_case(
                        agent=agent,
                        level=level,
                        window=window,
                        seed=seed,
                        window_offset=seed_index,
                        data_dir=ROOT / args.data_dir,
                        symbols=symbols,
                        frequency=args.frequency,
                        max_periods=args.max_periods,
                    )
                    run_rows.append(
                        {
                            "window": window_key,
                            "level": level_key,
                            "agent": agent,
                            "seed": seed,
                            "total_return": metrics.get("total_return", 0.0),
                            "sharpe": metrics.get("sharpe", 0.0),
                            "execution_fill_rate": metrics.get("execution_fill_rate", ""),
                            "turnover_events": metrics.get("turnover_events", ""),
                        }
                    )
                print(f"OK {window_key} {level_key} {agent}", flush=True)

    _write_csv(output_dir / "real_runs.csv", run_rows, ["window", "level", "agent", "seed", "total_return", "sharpe", "execution_fill_rate", "turnover_events"])
    stability = _stability_rows(run_rows, top_k=args.top_k)
    _write_csv(output_dir / "real_rank_stability.csv", stability, ["window", "level_a", "level_b", "agent_count", "kendall_tau", f"top_{args.top_k}_jaccard"])
    _write_markdown(output_dir / "execution_sensitivity_real.md", stability, top_k=args.top_k)
    print(f"Wrote {len(run_rows)} runs, {len(stability)} stability pairs to {output_dir}")
    return 0


def _run_case(*, agent, level, window, seed, window_offset, data_dir, symbols, frequency, max_periods):
    kwargs = dict(level)
    kwargs.update({"strategy_name": agent, "analyst_names": ("momentum", "macro-news")})
    _, metrics = build_default_system(
        name=f"real_exec_{agent}_{seed}",
        symbols=symbols,
        seed=seed,
        risk_name="max-position",
        data_source="real",
        real_data_dir=str(data_dir),
        real_data_frequency=frequency,
        real_data_start=window["start"],
        real_data_end=window["end"],
        real_data_max_periods=max_periods,
        real_data_window_offset=window_offset,
        **kwargs,
    ).run()
    return metrics


def _stability_rows(run_rows, *, top_k):
    by_cell: dict[tuple[str, str, str], list[float]] = {}
    for r in run_rows:
        by_cell.setdefault((r["window"], r["level"], r["agent"]), []).append(float(r[RANK_METRIC]))
    scores: dict[tuple[str, str], dict[str, float]] = {}
    for (window, level, agent), vals in by_cell.items():
        scores.setdefault((window, level), {})[agent] = mean(vals)
    out = []
    windows = sorted({w for w, _ in scores})
    for window in windows:
        levels = sorted(lv for w, lv in scores if w == window)
        for i in range(len(levels)):
            for j in range(i + 1, len(levels)):
                a, b = scores[(window, levels[i])], scores[(window, levels[j])]
                out.append(
                    {
                        "window": window,
                        "level_a": levels[i],
                        "level_b": levels[j],
                        "agent_count": len(set(a) & set(b)),
                        "kendall_tau": kendall_tau(a, b),
                        f"top_{top_k}_jaccard": top_k_jaccard(a, b, k=top_k),
                    }
                )
    return out


def _write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _write_markdown(path, stability, *, top_k):
    lines = [
        "# Execution Sensitivity on Real Market Data (Deterministic Agents)",
        "",
        "Ranking stability between idealized (E0) and stressed execution on real",
        "Yahoo OHLCV, mirroring the synthetic-regime analysis. Low Kendall tau",
        "means the friction-driven leaderboard reordering persists on real prices.",
        "",
        f"| Window | Level vs E0 | Kendall tau | Top-{top_k} Jaccard |",
        "| --- | --- | ---: | ---: |",
    ]
    for r in stability:
        if r["level_a"] != "E0_ideal":
            continue
        tau = r["kendall_tau"]
        jac = r[f"top_{top_k}_jaccard"]
        lines.append(f"| {r['window']} | {r['level_b']} | {f'{float(tau):.3f}' if tau is not None else ''} | {f'{float(jac):.3f}' if jac is not None else ''} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
