"""Cost-aware-baseline robustness check (reviewer Major Concern 2).

Does adding a transaction-cost-aware classical baseline (no-trade-band risk
parity) eliminate execution-induced leaderboard fragility? We recompute the
deterministic-arm Kendall tau-b (E0 vs E1) per regime with and without the
cost-aware agent, confirm the band actually cuts turnover, and report how the
cost-aware agent itself moves under stress. Deterministic; reads released CSVs.
"""

from __future__ import annotations

import collections
import csv
from pathlib import Path

from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs/results/execution_sensitivity_costaware"
REGIMES = ["calm", "high_vol", "jump_tail"]
COST = "no-trade-band"


def load():
    return list(csv.DictReader((D / "execution_sensitivity_runs.csv").open(encoding="utf-8")))


def mean_by(runs, metric, level=None):
    acc = collections.defaultdict(list)
    for r in runs:
        if level and r["level"] != level:
            continue
        acc[(r["scenario"], r["level"], r["agent"])].append(float(r[metric]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def taub(d_a, d_b, agents):
    ks = [a for a in agents if a in d_a and a in d_b]
    if len(ks) < 2:
        return None
    t, _ = kendalltau([d_a[a] for a in ks], [d_b[a] for a in ks], variant="b")
    return t


def main():
    runs = load()
    sharpe = mean_by(runs, "sharpe")
    all_agents = sorted({r["agent"] for r in runs})
    base7 = [a for a in all_agents if a != COST]
    print("agents:", all_agents)

    print("\n=== (1) Deterministic-arm tau-b(E0,E1) per regime ===")
    print(f"{'regime':10s} {'7 baselines':>12s} {'+cost-aware':>12s}")
    for rg in REGIMES:
        e0 = {a: sharpe[(rg, 'E0_ideal', a)] for a in all_agents if (rg, 'E0_ideal', a) in sharpe}
        e1 = {a: sharpe[(rg, 'E1_default_stress', a)] for a in all_agents if (rg, 'E1_default_stress', a) in sharpe}
        t7 = taub(e0, e1, base7)
        t8 = taub(e0, e1, all_agents)
        print(f"{rg:10s} {t7:12.3f} {t8:12.3f}")

    print("\n=== (2) Mean E1 turnover_events: cost-aware vs risk-parity ===")
    t_e1 = mean_by(runs, "turnover_events", level="E1_default_stress")
    for rg in REGIMES:
        c = t_e1.get((rg, 'E1_default_stress', COST))
        rp = t_e1.get((rg, 'E1_default_stress', 'risk-parity'))
        print(f"  {rg:10s} no-trade-band={c:6.1f}  risk-parity={rp:6.1f}")

    print("\n=== (3) Cost-aware agent rank E0 -> E1 (high_vol) and Sharpe ===")
    for rg in REGIMES:
        for lvl in ['E0_ideal', 'E1_default_stress']:
            cell = {a: sharpe[(rg, lvl, a)] for a in all_agents if (rg, lvl, a) in sharpe}
            order = sorted(cell, key=lambda a: cell[a], reverse=True)
            rank = order.index(COST) + 1
            print(f"  {rg:10s} {lvl:18s} cost-aware rank={rank}/{len(order)} sharpe={cell[COST]:.2f}")


if __name__ == "__main__":
    main()
