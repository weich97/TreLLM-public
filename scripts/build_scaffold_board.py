"""Build the memory-scaffold board comparison (execution-sensitivity study).

Question: does the execution-assumption ladder rerank a *memory-scaffolded*
agent family the way it reranks the plain signal-wrapper family? The scaffold
arm runs the two direct-API LLM rows through the memory-aware exposure overlay
(``+mem`` rows in run_execution_sensitivity_sweep.py) in fresh cells alongside
the same seven classical baselines plus the deterministic memory-aware agent.

Statistical conventions match build_v03_result_tables.py: cell = mean Sharpe
over seeds; Kendall tau_b between level boards; 95% cluster bootstrap over
seeds (10,000 draws, fixed RNG seed). The plain-board reference recomputes the
9-agent direct board from the b1 horizon arm's h12 cells with the identical
estimator so the scaffold-vs-plain comparison is method-invariant.

Outputs docs/results/execution_sensitivity_scaffold/{scaffold_board_taus.csv,scaffold_board.md}.
"""
from __future__ import annotations

import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.statistics import kendall_tau

SCAFFOLD_DIRS = (
    ROOT / "docs/results/execution_sensitivity_scaffold/ds",
    ROOT / "docs/results/execution_sensitivity_scaffold/glm",
)
PLAIN_DIRS = (
    ROOT / "docs/results/execution_sensitivity_b1_horizon/ds_h12",
    ROOT / "docs/results/execution_sensitivity_b1_horizon/glm_h12",
)
OUT_DIR = ROOT / "docs/results/execution_sensitivity_scaffold"
LEVEL_PAIRS = (("E0_ideal", "E1_default_stress"), ("E0_ideal", "E2_harsh_corner"))
DRAWS = 10_000


def load_runs(dirs: tuple[Path, ...]) -> dict[str, dict[str, dict[str, dict[int, float]]]]:
    """scenario -> level -> agent -> seed -> sharpe (sample-0 rows, deduped)."""
    table: dict[str, dict[str, dict[str, dict[int, float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    for d in dirs:
        path = d / "execution_sensitivity_runs.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if int(row.get("sample", 0) or 0) != 0:
                    continue
                table[row["scenario"]][row["level"]][row["agent"]][int(row["seed"])] = float(
                    row["sharpe"]
                )
    return table


def board_tau(
    level_a: dict[str, dict[int, float]],
    level_b: dict[str, dict[int, float]],
    agents: list[str],
    seeds: list[int],
) -> float:
    mean_a = {a: sum(level_a[a][s] for s in seeds) / len(seeds) for a in agents}
    mean_b = {a: sum(level_b[a][s] for s in seeds) / len(seeds) for a in agents}
    tau = kendall_tau(mean_a, mean_b)
    return 0.0 if tau is None else tau


def tau_with_ci(
    level_a: dict[str, dict[int, float]],
    level_b: dict[str, dict[int, float]],
) -> tuple[int, int, float, float, float] | None:
    agents = sorted(set(level_a) & set(level_b))
    seeds: list[int] = []
    if agents:
        shared: set[int] = set(level_a[agents[0]])
        for a in agents:
            shared &= set(level_a[a])
            shared &= set(level_b[a])
        seeds = sorted(shared)
    if len(agents) < 4 or len(seeds) < 3:
        return None
    point = board_tau(level_a, level_b, agents, seeds)
    rng = random.Random(20260717)
    draws = sorted(
        board_tau(level_a, level_b, agents, [rng.choice(seeds) for _ in seeds])
        for _ in range(DRAWS)
    )
    return len(agents), len(seeds), point, draws[int(0.025 * DRAWS)], draws[int(0.975 * DRAWS)]


def main() -> int:
    scaffold = load_runs(SCAFFOLD_DIRS)
    # Same-membership variant: drop the deterministic memory-aware row so the
    # board is 9 agents exactly like the plain direct reference.
    matched = {
        scen: {lvl: {a: sv for a, sv in agents.items() if a != "memory-aware"}
               for lvl, agents in levels.items()}
        for scen, levels in scaffold.items()
    }
    boards = {
        "scaffold": scaffold,
        "scaffold_matched9": matched,
        "plain_direct": load_runs(PLAIN_DIRS),
    }
    rows = []
    for board_name, table in boards.items():
        for scenario in sorted(table):
            for lo, hi in LEVEL_PAIRS:
                if lo not in table[scenario] or hi not in table[scenario]:
                    continue
                fit = tau_with_ci(table[scenario][lo], table[scenario][hi])
                if fit is None:
                    continue
                n_agents, n_seeds, tau, ci_lo, ci_hi = fit
                rows.append(
                    {
                        "board": board_name,
                        "scenario": scenario,
                        "level_a": lo,
                        "level_b": hi,
                        "agents": n_agents,
                        "seeds": n_seeds,
                        "kendall_tau_b": round(tau, 3),
                        "ci_low": round(ci_lo, 3),
                        "ci_high": round(ci_hi, 3),
                    }
                )
    if not rows:
        print("no complete boards yet (scaffold arm still running?)")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUT_DIR / "scaffold_board_taus.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Memory-Scaffold Board vs Plain Direct Board",
        "",
        "Scaffold board = 7 classical baselines + deterministic memory-aware agent",
        "+ deepseek-v4-pro+mem + glm-5+mem (direct APIs, memory-aware exposure",
        "overlay wrapping the LLM signal). Plain reference = the b1 9-agent direct",
        "board at 12 steps, recomputed with the identical estimator. Cells are",
        "mean Sharpe over seeds; 95% cluster bootstrap over seeds, 10,000 draws.",
        "",
        "| Board | Scenario | Levels | Agents | Seeds | tau_b | 95% CI |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for r in rows:
        lines.append(
            f"| {r['board']} | {r['scenario']} | {r['level_a']}->{r['level_b']} "
            f"| {r['agents']} | {r['seeds']} | {r['kendall_tau_b']:+.3f} "
            f"| [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] |"
        )
    (OUT_DIR / "scaffold_board.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_csv.relative_to(ROOT)} ({len(rows)} board rows)")
    for r in rows:
        print(
            f"{r['board']:12s} {r['scenario']:9s} {r['level_a']}->{r['level_b']}: "
            f"tau={r['kendall_tau_b']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] "
            f"(agents={r['agents']}, seeds={r['seeds']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
