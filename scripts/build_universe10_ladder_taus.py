"""Ten-asset full-ladder ranking stability (execution-sensitivity study).

The N=10 board previously existed only at E0/E1. The ladder extension ran the
three E2 single-axis stressors and the harsh corner (labeled high-vol, but due
to a double scenario offset the stored E2 seed IDs are 201-210 while E0/E1 are
101-110),
7 classical + gemini + claude routed + deepseek + glm direct). This joins the
existing N=10 E0 baseline with the new levels and reports the E0-vs-level
Kendall tau_b on the common agent set, alongside the E0-vs-E1 value from the
original arm. Writes docs/results/execution_sensitivity_universe10_ladder/
ladder_taus.csv.
"""
from __future__ import annotations

import argparse
import collections
import csv
import math
import statistics as st
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
LADDER = ROOT / "docs/results/execution_sensitivity_universe10_ladder/execution_sensitivity_runs.csv"
E0_SOURCES = [
    ROOT / "docs/results/execution_sensitivity_universe10/execution_sensitivity_runs.csv",
    ROOT / "docs/results/execution_sensitivity_universe10_poe/execution_sensitivity_runs.csv",
    ROOT / "docs/results/execution_sensitivity_universe10_ds/execution_sensitivity_runs.csv",
    ROOT / "docs/results/execution_sensitivity_universe10_glm/execution_sensitivity_runs.csv",
]
OUT = ROOT / "docs/results/execution_sensitivity_universe10_ladder/ladder_taus.csv"
SCENARIO = "high_vol"


Cell = tuple[str, str, int, int]


def load(path: Path, *, scenario: str = SCENARIO) -> dict[Cell, float]:
    """Load one scenario without allowing duplicate cells to change weights."""

    cells: dict[Cell, float] = {}
    if not path.exists():
        return cells
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["scenario"] != scenario:
                continue
            key = (r["level"], r["agent"], int(r["seed"]), int(r["sample"]))
            value = float(r["sharpe"])
            previous = cells.get(key)
            if previous is not None and not math.isclose(previous, value, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(f"conflicting duplicate {key} in {path}")
            cells[key] = value
    return cells


def merge_sources(paths: list[Path], *, scenario: str = SCENARIO) -> dict[Cell, float]:
    merged: dict[Cell, float] = {}
    for path in paths:
        for key, value in load(path, scenario=scenario).items():
            previous = merged.get(key)
            if previous is not None and not math.isclose(previous, value, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(f"conflicting duplicate {key} across E0 sources")
            merged[key] = value
    return merged


def aggregate(cells: dict[Cell, float]) -> dict[tuple[str, str], list[float]]:
    sharpe: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    for (level, agent, _seed, _sample), value in cells.items():
        sharpe[(level, agent)].append(value)
    return sharpe


def seeds_for(cells: dict[Cell, float], level: str, agents: list[str]) -> set[int]:
    wanted = set(agents)
    return {seed for (cell_level, agent, seed, _sample) in cells if cell_level == level and agent in wanted}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-unpaired-descriptive",
        action="store_true",
        help="Write cross-seed-set E2 tau values as descriptive diagnostics.",
    )
    args = parser.parse_args(argv)
    base_cells = merge_sources(E0_SOURCES)
    ladder_cells = load(LADDER)
    base = aggregate(base_cells)
    ladder = aggregate(ladder_cells)

    e0_agents = {a for (lv, a) in base if lv == "E0_ideal"}
    ladder_levels = sorted({lv for (lv, _a) in ladder})
    common_agents = e0_agents & {a for (lv, a) in base if lv == "E1_default_stress"}
    for level in ladder_levels:
        common_agents &= {a for (lv, a) in ladder if lv == level}
    rows = []
    levels = ladder_levels + ["E1_default_stress"]
    for lv in levels:
        src = base if lv == "E1_default_stress" else ladder
        agents = sorted(common_agents)
        if len(agents) < 5:
            continue
        e0 = [st.mean(base[("E0_ideal", a)]) for a in agents]
        e1 = [st.mean(src[(lv, a)]) for a in agents]
        tau = stats.kendalltau(e0, e1).statistic
        stress_cells = base_cells if lv == "E1_default_stress" else ladder_cells
        e0_seeds = seeds_for(base_cells, "E0_ideal", agents)
        stress_seeds = seeds_for(stress_cells, lv, agents)
        rows.append(
            {
                "scenario": SCENARIO,
                "level": lv,
                "n_agents": len(agents),
                "tau_b_vs_E0": f"{tau:.3f}",
                "e0_seed_count": len(e0_seeds),
                "stress_seed_count": len(stress_seeds),
                "same_seed_ids": e0_seeds == stress_seeds,
            }
        )

    unpaired = [row["level"] for row in rows if not row["same_seed_ids"]]
    if unpaired and not args.allow_unpaired_descriptive:
        joined = ", ".join(str(level) for level in unpaired)
        raise SystemExit(
            "Refusing to treat unmatched seed grids as a paired ladder "
            f"({joined}). Re-run the arm on matching paths, or pass "
            "--allow-unpaired-descriptive to emit explicitly labeled diagnostics."
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "scenario",
                "level",
                "n_agents",
                "tau_b_vs_E0",
                "e0_seed_count",
                "stress_seed_count",
                "same_seed_ids",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in rows:
        print(
            f"  {r['level']:24s} agents={r['n_agents']} tau={r['tau_b_vs_E0']} "
            f"same_seed_ids={r['same_seed_ids']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
