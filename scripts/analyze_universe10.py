"""N=10 universe robustness (reviewer Major Concern 1): does the execution-induced
leaderboard reordering survive on a 10-asset universe? Merges the deepseek+glm
direct run and the Poe-models run (same seeds/levels/symbols) and reports the
E0-vs-E1 Kendall tau-b for the full agent set, vs the N=2 headline (0.21).
"""

from __future__ import annotations

import collections
import csv
from pathlib import Path

from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[1]
# Deterministic baselines from the complete N=10 deterministic sweep; LLM rows
# from the per-model parallel runs (each shares the universe10 response cache).
DET_DIR = ROOT / "docs/results/execution_sensitivity_universe10"
LLM_DIRS = [
    ROOT / "docs/results/execution_sensitivity_universe10_ds",
    ROOT / "docs/results/execution_sensitivity_universe10_glm",
    ROOT / "docs/results/execution_sensitivity_universe10_poe",
]


def load_runs():
    rows = []
    p = DET_DIR / "execution_sensitivity_runs.csv"
    if p.exists():
        rows += [r for r in csv.DictReader(p.open(encoding="utf-8")) if ":" not in r["agent"]]
    for d in LLM_DIRS:
        p = d / "execution_sensitivity_runs.csv"
        if p.exists():
            rows += [r for r in csv.DictReader(p.open(encoding="utf-8")) if ":" in r["agent"]]
    return rows


def main():
    rows = load_runs()
    # mean sharpe per (level, agent) over seeds; keep only agents with full E0+E1 x10 coverage
    cov = collections.defaultdict(set)
    sh = collections.defaultdict(list)
    for r in rows:
        if r["scenario"] != "high_vol":
            continue
        sh[(r["level"], r["agent"])].append(float(r["sharpe"]))
        cov[(r["agent"], r["level"])].add(r["seed"])
    agents = sorted({a for (_, a) in sh})
    complete = [a for a in agents
                if len(cov.get((a, "E0_ideal"), set())) == 10 and len(cov.get((a, "E1_default_stress"), set())) == 10]
    incomplete = [a for a in agents if a not in complete]
    mean = {k: sum(v) / len(v) for k, v in sh.items()}

    print("agents with full E0+E1 x10 coverage:", len(complete))
    if incomplete:
        print("EXCLUDED (incomplete):", incomplete)

    e0 = {a: mean[("E0_ideal", a)] for a in complete}
    e1 = {a: mean[("E1_default_stress", a)] for a in complete}
    x = [e0[a] for a in complete]
    y = [e1[a] for a in complete]
    tau = kendalltau(x, y, variant="b")[0]
    print(f"\nN=10 high-vol E0->E1 Kendall tau-b ({len(complete)} agents) = {tau:.3f}")
    print("(N=2 headline 12-agent tau-b = 0.21)")

    for lvl, lab in [("E0_ideal", "E0"), ("E1_default_stress", "E1")]:
        board = sorted(((a, mean[(lvl, a)]) for a in complete), key=lambda kv: kv[1], reverse=True)
        print(f"\n-- N=10 high-vol {lab} leaderboard --")
        for i, (a, s) in enumerate(board, 1):
            print(f"  {i:2d} {a:26s} {s:.2f}{'  [LLM]' if ':' in a else ''}")


if __name__ == "__main__":
    main()
