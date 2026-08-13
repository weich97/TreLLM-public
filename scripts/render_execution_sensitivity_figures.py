"""Render the execution-sensitivity paper figures from the released CSVs.

Figure 1: annotated heatmap of Kendall tau-b between the idealized level
and each stressed level, per market regime.
Figure 2: friction-fragility DiD forest plot (mean and 95% CI per agent at
the default-stress and harsh-corner levels).

Usage:

  python scripts/render_execution_sensitivity_figures.py \
    --input-dir docs/results/execution_sensitivity_llm \
    --output-dir figures/execution_sensitivity
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

LEVEL_LABELS = {
    "E1_default_stress": "E1 default",
    "E2_spread_20bps": "E2 spread",
    "E2_latency_3": "E2 latency",
    "E2_participation_1pct": "E2 partic.",
    "E2_harsh_corner": "E2 harsh",
}
SCENARIO_LABELS = {"calm": "calm", "high_vol": "high vol.", "jump_tail": "jump/tail"}
AGENT_LABELS = {
    "poe:gpt-5.5": "gpt-5.5",
    "poe:gemini-3.1-pro": "gemini-3.1-pro",
    "poe:claude-opus-4.7": "claude-opus-4.7",
    "poe:glm-5": "glm-5",
    "deepseek:deepseek-v4-pro": "deepseek-v4-pro",
}


def render_tau_heatmap(input_dir: Path, output_dir: Path) -> Path:
    rows = [
        row
        for row in csv.DictReader((input_dir / "rank_stability.csv").open(encoding="utf-8"))
        if row["level_a"] == "E0_ideal" and row["level_b"] in LEVEL_LABELS
    ]
    scenarios = [s for s in SCENARIO_LABELS if any(r["scenario"] == s for r in rows)]
    levels = [lvl for lvl in LEVEL_LABELS if any(r["level_b"] == lvl for r in rows)]
    grid = [
        [
            next(float(r["kendall_tau"]) for r in rows if r["scenario"] == s and r["level_b"] == lvl)
            for lvl in levels
        ]
        for s in scenarios
    ]
    fig, ax = plt.subplots(figsize=(5.2, 2.4))
    image = ax.imshow(grid, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(levels)), [LEVEL_LABELS[lvl] for lvl in levels], fontsize=8)
    ax.set_yticks(range(len(scenarios)), [SCENARIO_LABELS[s] for s in scenarios], fontsize=8)
    for i in range(len(scenarios)):
        for j in range(len(levels)):
            ax.text(j, i, f"{grid[i][j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Kendall $\\tau_b$ vs. idealized execution (E0)", fontsize=9)
    fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    path = output_dir / "tau_heatmap.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def render_did_forest(input_dir: Path, output_dir: Path) -> Path:
    rows = list(csv.DictReader((input_dir / "fragility_did.csv").open(encoding="utf-8")))
    agents = [a for a in AGENT_LABELS if any(r["agent"] == a for r in rows)]
    agents += sorted({r["agent"] for r in rows if r["agent"] not in AGENT_LABELS})
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.2), sharey=True)
    for ax, level, title in zip(
        axes,
        ("E1_default_stress", "E2_harsh_corner"),
        ("E1 default stress", "E2 harsh corner"),
    ):
        for index, agent in enumerate(agents):
            row = next((r for r in rows if r["agent"] == agent and r["stress_level"] == level), None)
            if row is None:
                continue
            mean = float(row["mean_did"])
            low, high = float(row["did_ci_low"]), float(row["did_ci_high"])
            significant = row["q_value"] not in ("", None) and float(row["q_value"]) < 0.05
            is_llm = ":" in agent
            color = "#b22222" if significant else ("#1f5fa8" if is_llm else "#666666")
            ax.errorbar(
                mean,
                index,
                xerr=[[mean - low], [high - mean]],
                fmt="o",
                markersize=4,
                color=color,
                elinewidth=1.2,
                capsize=2,
            )
        ax.axvline(0.0, color="black", linewidth=0.7, linestyle="--")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("DiD vs. buy-and-hold (total return)", fontsize=8)
        ax.tick_params(labelsize=8)
        ax.grid(axis="x", linewidth=0.3, alpha=0.5)
    axes[0].set_yticks(range(len(agents)), [AGENT_LABELS.get(a, a) for a in agents])
    axes[0].invert_yaxis()
    fig.tight_layout()
    path = output_dir / "did_forest.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render execution-sensitivity paper figures.")
    parser.add_argument("--input-dir", default="docs/results/execution_sensitivity_llm")
    parser.add_argument("--output-dir", default="figures/execution_sensitivity")
    args = parser.parse_args(argv)
    input_dir = ROOT / args.input_dir if not Path(args.input_dir).is_absolute() else Path(args.input_dir)
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print("wrote", render_tau_heatmap(input_dir, output_dir))
    print("wrote", render_did_forest(input_dir, output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
