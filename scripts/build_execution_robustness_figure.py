"""Build the two-panel robustness figure used in the execution-sensitivity study.

The panels answer different questions and deliberately use different fixed
policy boards:

* universe size: 11 policies observed at every N in {2, 3, 5, 10};
* horizon: the reproducible nine-policy direct board at {12, 30, 60, 120} steps.

No experiment is run here. The script reads frozen run records, averages repeat
provider samples within seed, bootstraps seeds, writes the plotted values, and
renders a vector PDF.
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[1]
E0 = "E0_ideal"
E1 = "E1_default_stress"
SEED = 20260717
DRAWS = 10_000

CLASSICAL = (
    "buy-and-hold",
    "signal-weighted",
    "naive-momentum",
    "mean-reversion",
    "risk-parity",
    "minimum-variance",
    "random",
)
UNIVERSE_BOARD = CLASSICAL + (
    "deepseek:deepseek-v4-pro",
    "poe:gpt-5.5",
    "poe:claude-opus-4.7",
    "poe:gemini-3.1-pro",
)

UNIVERSE_SOURCES: dict[int, tuple[tuple[Path, frozenset[str]], ...]] = {
    2: (
        (
            ROOT / "docs/results/execution_sensitivity_llm/merged_runs.csv",
            frozenset(UNIVERSE_BOARD),
        ),
    ),
    3: (
        (
            ROOT / "docs/results/execution_sensitivity_N3/execution_sensitivity_runs.csv",
            frozenset(UNIVERSE_BOARD),
        ),
    ),
    5: (
        (
            ROOT / "docs/results/execution_sensitivity_N5/execution_sensitivity_runs.csv",
            frozenset(UNIVERSE_BOARD),
        ),
    ),
    10: (
        (
            ROOT / "docs/results/execution_sensitivity_universe10/execution_sensitivity_runs.csv",
            frozenset(CLASSICAL),
        ),
        (
            ROOT / "docs/results/execution_sensitivity_universe10_ds/execution_sensitivity_runs.csv",
            frozenset({"deepseek:deepseek-v4-pro"}),
        ),
        (
            ROOT / "docs/results/execution_sensitivity_universe10_poe/execution_sensitivity_runs.csv",
            frozenset(UNIVERSE_BOARD) - frozenset(CLASSICAL) - {"deepseek:deepseek-v4-pro"},
        ),
    ),
}


SeedTable = dict[str, dict[str, dict[int, float]]]


def load_seed_table(sources: tuple[tuple[Path, frozenset[str]], ...]) -> SeedTable:
    """Return level -> policy -> seed -> mean Sharpe over repeated samples."""
    samples: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for path, wanted in sources:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["scenario"] != "high_vol" or row["level"] not in {E0, E1}:
                    continue
                if row["agent"] not in wanted:
                    continue
                key = (row["level"], row["agent"], int(row["seed"]))
                samples[key].append(float(row["sharpe"]))

    table: SeedTable = {E0: {}, E1: {}}
    for level in (E0, E1):
        for agent in UNIVERSE_BOARD:
            per_seed = {
                seed: statistics.mean(values)
                for (row_level, row_agent, seed), values in samples.items()
                if row_level == level and row_agent == agent
            }
            if per_seed:
                table[level][agent] = per_seed
    return table


def board_tau(table: SeedTable, seeds: list[int]) -> float:
    e0 = [statistics.mean(table[E0][agent][seed] for seed in seeds) for agent in UNIVERSE_BOARD]
    e1 = [statistics.mean(table[E1][agent][seed] for seed in seeds) for agent in UNIVERSE_BOARD]
    value = kendalltau(e0, e1, variant="b").statistic
    if value is None:
        raise ValueError("Kendall tau is undefined")
    return float(value)


def bootstrap_universe(n_assets: int) -> dict[str, object]:
    table = load_seed_table(UNIVERSE_SOURCES[n_assets])
    missing = [agent for agent in UNIVERSE_BOARD if agent not in table[E0] or agent not in table[E1]]
    if missing:
        raise ValueError(f"N={n_assets} is missing policies: {missing}")

    shared = set(table[E0][UNIVERSE_BOARD[0]])
    for level in (E0, E1):
        for agent in UNIVERSE_BOARD:
            shared &= set(table[level][agent])
    seeds = sorted(shared)
    if len(seeds) != 10:
        raise ValueError(f"N={n_assets} has {len(seeds)} shared seeds, expected 10")

    point = board_tau(table, seeds)
    rng = random.Random(SEED + n_assets)
    draws = sorted(board_tau(table, [rng.choice(seeds) for _ in seeds]) for _ in range(DRAWS))
    return {
        "curve": "universe",
        "x": n_assets,
        "tau_b": round(point, 3),
        "ci_low": round(draws[int(0.025 * DRAWS)], 3),
        "ci_high": round(draws[int(0.975 * DRAWS)], 3),
        "agents": len(UNIVERSE_BOARD),
        "seeds": len(seeds),
        "board": "fixed 11-policy board",
    }


def load_horizon_rows() -> list[dict[str, object]]:
    source = ROOT / "docs/results/execution_sensitivity_scaffold/tau_curve_cis.csv"
    wanted = {f"direct_h{steps}": steps for steps in (12, 30, 60, 120)}
    rows: list[dict[str, object]] = []
    with source.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["board"] not in wanted or row["scenario"] != "high_vol":
                continue
            rows.append(
                {
                    "curve": "horizon",
                    "x": wanted[row["board"]],
                    "tau_b": float(row["kendall_tau_b"]),
                    "ci_low": float(row["ci_low"]),
                    "ci_high": float(row["ci_high"]),
                    "agents": int(row["agents"]),
                    "seeds": int(row["seeds"]),
                    "board": "direct 9-policy board",
                }
            )
    rows.sort(key=lambda row: int(row["x"]))
    if [row["x"] for row in rows] != [12, 30, 60, 120]:
        raise ValueError("direct horizon curve is incomplete")
    return rows


def write_rows(rows: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render(rows: list[dict[str, object]], output: Path) -> None:
    grouped = {
        curve: sorted((row for row in rows if row["curve"] == curve), key=lambda row: int(row["x"]))
        for curve in ("universe", "horizon")
    }
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.35), sharey=True)
    color = "#315f8d"
    specifications = (
        (axes[0], grouped["universe"], "(a) Fixed 11-policy board", "number of assets"),
        (axes[1], grouped["horizon"], "(b) Direct 9-policy board", "decision steps"),
    )
    for ax, series, title, xlabel in specifications:
        xs = [int(row["x"]) for row in series]
        ys = [float(row["tau_b"]) for row in series]
        lower = [y - float(row["ci_low"]) for y, row in zip(ys, series)]
        upper = [float(row["ci_high"]) - y for y, row in zip(ys, series)]
        ax.errorbar(
            xs,
            ys,
            yerr=[lower, upper],
            color=color,
            marker="o",
            markersize=4.5,
            linewidth=1.3,
            capsize=3,
            elinewidth=0.9,
        )
        for x, y in zip(xs, ys):
            offset = 0.045 if y < 0.75 else -0.075
            ax.text(x, y + offset, f"{y:.2f}", ha="center", va="center", fontsize=7)
        ax.set_xticks(xs)
        ax.set_xlabel(xlabel, fontsize=8)
        ax.set_title(title, fontsize=8.5)
        ax.set_ylim(-0.02, 1.04)
        ax.grid(axis="y", linewidth=0.35, alpha=0.35)
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Kendall $\\tau_b$ (E0 vs. E1)", fontsize=8)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(w_pad=2.0)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--table",
        type=Path,
        default=ROOT / "docs/results/execution_sensitivity_scaffold/execution_robustness_curves.csv",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=ROOT / "figures/execution_sensitivity/robustness_curves.pdf",
    )
    args = parser.parse_args()

    universe = [bootstrap_universe(n_assets) for n_assets in (2, 3, 5, 10)]
    expected = {2: 0.236, 3: 0.709, 5: 0.709, 10: 0.855}
    for row in universe:
        if abs(float(row["tau_b"]) - expected[int(row["x"])]) > 0.001:
            raise ValueError(f"universe point changed unexpectedly: {row}")
    rows = universe + load_horizon_rows()
    write_rows(rows, args.table.resolve())
    render(rows, args.figure.resolve())
    print(f"wrote {args.table.resolve()}")
    print(f"wrote {args.figure.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
