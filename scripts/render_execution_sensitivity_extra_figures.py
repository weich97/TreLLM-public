"""Render the additional execution-sensitivity paper figures from released CSVs.

Figure A: rank bump chart across the execution ladder (high-volatility regime).
Figure B: contender-compression scatter (top-5 Sharpe gap vs. Kendall tau-b).
Figure C: buy-and-hold anchor cold-vs-warm initialization-cost gap.
Figure D: external robustness (parameter grid + real-market vs. synthetic).

Usage:

  python scripts/render_execution_sensitivity_extra_figures.py \
    --input-dir docs/results \
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

LLM_COLOR = "#1f5fa8"
CLS_COLOR = "#9aa0a6"
ACCENT = "#b22222"
REGIME_COLOR = {"calm": "#2e8b57", "high_vol": "#b22222", "jump_tail": "#d4860b"}

LADDER = [
    "E0_ideal",
    "E1_default_stress",
    "E2_spread_20bps",
    "E2_latency_3",
    "E2_participation_1pct",
    "E2_harsh_corner",
]
LADDER_SHORT = ["E0\nideal", "E1\ndefault", "spread", "latency", "partic.", "harsh"]
AGENT_LABELS = {
    "poe:gpt-5.5": "gpt-5.5",
    "poe:gemini-3.1-pro": "gemini-3.1-pro",
    "poe:claude-opus-4.7": "claude-opus-4.7",
    "poe:glm-5": "glm-5",
    "deepseek:deepseek-v4-pro": "deepseek-v4-pro",
}


def _label(agent: str) -> str:
    return AGENT_LABELS.get(agent, agent)


def _is_llm(agent: str) -> bool:
    return ":" in agent


def render_rank_bump(input_dir: Path, output_dir: Path) -> Path:
    rows = [
        r
        for r in csv.DictReader((input_dir / "execution_sensitivity_llm" / "merged_aggregate.csv").open(encoding="utf-8"))
        if r["scenario"] == "high_vol"
    ]
    agents = sorted({r["agent"] for r in rows})
    rank = {(r["agent"], r["level"]): int(r["rank"]) for r in rows}

    fig, ax = plt.subplots(figsize=(3.4, 3.2))
    xs = list(range(len(LADDER)))
    for agent in agents:
        ys = [rank.get((agent, lv)) for lv in LADDER]
        if any(y is None for y in ys):
            continue
        llm = _is_llm(agent)
        ax.plot(
            xs,
            ys,
            marker="o",
            markersize=3,
            linewidth=1.8 if llm else 1.0,
            color=LLM_COLOR if llm else CLS_COLOR,
            alpha=0.95 if llm else 0.7,
            zorder=3 if llm else 2,
        )
        ax.text(len(LADDER) - 1 + 0.15, ys[-1], _label(agent), ha="left", va="center", fontsize=6.5,
                color=LLM_COLOR if llm else "#555555")

    ax.set_xticks(xs, LADDER_SHORT, fontsize=7)
    ax.set_yticks(range(1, len(agents) + 1))
    ax.set_ylabel("leaderboard rank", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.invert_yaxis()
    ax.set_xlim(-0.4, len(LADDER) - 1 + 2.7)
    ax.set_title("Rank trajectories under stress (high vol.)", fontsize=9)
    ax.grid(axis="y", linewidth=0.3, alpha=0.4)
    handles = [
        plt.Line2D([], [], color=LLM_COLOR, linewidth=1.8, marker="o", markersize=3, label="LLM agent"),
        plt.Line2D([], [], color=CLS_COLOR, linewidth=1.0, marker="o", markersize=3, label="classical"),
    ]
    ax.legend(handles=handles, fontsize=6.5, loc="upper center", ncol=2, frameon=False,
              bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    path = output_dir / "rank_bump.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def render_compression(input_dir: Path, output_dir: Path) -> Path:
    agg = list(csv.DictReader((input_dir / "execution_sensitivity_llm" / "merged_aggregate.csv").open(encoding="utf-8")))
    stab = [
        r
        for r in csv.DictReader((input_dir / "execution_sensitivity_llm" / "rank_stability.csv").open(encoding="utf-8"))
        if r["level_a"] == "E0_ideal"
    ]

    def top5_gap(scenario: str, level: str) -> float:
        sharpes = sorted(
            (float(r["sharpe_mean"]) for r in agg if r["scenario"] == scenario and r["level"] == level),
            reverse=True,
        )
        return sharpes[0] - sharpes[4]

    xs, ys, colors = [], [], []
    for r in stab:
        xs.append(top5_gap(r["scenario"], r["level_b"]))
        ys.append(float(r["kendall_tau"]))
        colors.append(REGIME_COLOR[r["scenario"]])

    # Pearson r and least-squares line.
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    r = cov / (sxx ** 0.5 * sum((y - my) ** 2 for y in ys) ** 0.5)
    slope = cov / sxx
    intercept = my - slope * mx

    fig, ax = plt.subplots(figsize=(3.3, 2.7))
    ax.scatter(xs, ys, c=colors, s=26, edgecolors="white", linewidths=0.4, zorder=3)
    line_x = [min(xs), max(xs)]
    ax.plot(line_x, [slope * x + intercept for x in line_x], color="#333333", linewidth=1.0, linestyle="--", zorder=2)
    ax.text(0.04, 0.10, f"Pearson $r={r:.2f}$", transform=ax.transAxes, fontsize=8)
    ax.set_xlabel("top-5 Sharpe gap (rank 1 $-$ rank 5)", fontsize=8)
    ax.set_ylabel("Kendall $\\tau_b$ vs. E0", fontsize=8)
    ax.set_title("Reordering tracks contender compression", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(linewidth=0.3, alpha=0.4)
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=REGIME_COLOR[s],
                   markersize=5, label={"calm": "calm", "high_vol": "high vol.", "jump_tail": "jump/tail"}[s])
        for s in ("calm", "high_vol", "jump_tail")
    ]
    ax.legend(handles=handles, fontsize=6.5, loc="upper left", frameon=False)
    fig.tight_layout()
    path = output_dir / "contender_compression.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def render_anchor(input_dir: Path, output_dir: Path) -> Path:
    rows = list(csv.DictReader((input_dir / "execution_sensitivity_anchor" / "anchor_robustness.csv").open(encoding="utf-8")))
    levels = ["E0_ideal", "E1_default_stress", "E2_harsh_corner"]
    level_labels = ["E0 ideal", "E1 default", "harsh corner"]
    regimes = ["calm", "high_vol", "jump_tail"]
    gap = {(r["regime"], r["level"]): float(r["init_cost_gap"]) for r in rows}

    fig, ax = plt.subplots(figsize=(3.3, 2.5))
    xs = list(range(len(levels)))
    for regime in regimes:
        ys = [gap[(regime, lv)] for lv in levels]
        ax.plot(xs, ys, marker="o", markersize=4, linewidth=1.4, color=REGIME_COLOR[regime],
                label={"calm": "calm", "high_vol": "high vol.", "jump_tail": "jump/tail"}[regime])
    ax.axhline(0.0, color="black", linewidth=0.6, linestyle=":")
    ax.set_xticks(xs, level_labels, fontsize=7.5)
    ax.set_ylabel("warm-start $-$ cold return", fontsize=8)
    ax.set_title("Anchor construction cost grows with stress", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", linewidth=0.3, alpha=0.4)
    ax.legend(fontsize=6.5, loc="upper left", frameon=False)
    fig.tight_layout()
    path = output_dir / "anchor_initcost.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def render_external(input_dir: Path, output_dir: Path) -> Path:
    grid = list(csv.DictReader((input_dir / "execution_sensitivity_grid" / "param_grid.csv").open(encoding="utf-8")))
    real = [
        r
        for r in csv.DictReader((input_dir / "execution_sensitivity_real_etf" / "real_rank_stability.csv").open(encoding="utf-8"))
        if r["level_a"] == "E0_ideal"
    ]
    synth = [
        r
        for r in csv.DictReader((input_dir / "execution_sensitivity_llm" / "rank_stability.csv").open(encoding="utf-8"))
        if r["level_a"] == "E0_ideal" and r["scenario"] == "high_vol"
    ]

    fig, axes = plt.subplots(1, 2, figsize=(6.7, 2.6))

    # Left: parameter-grid tau vs. severity.
    ax = axes[0]
    short = ["Liquid", "Typical", "Default", "Small-cap", "Illiquid"]
    labels = short[: len(grid)]
    taus = [float(r["kendall_tau_vs_ideal"]) for r in grid]
    xs = list(range(len(grid)))
    ax.plot(xs, taus, marker="o", markersize=5, linewidth=1.6, color=LLM_COLOR)
    ax.set_xticks(xs, labels, fontsize=7, rotation=0)
    ax.set_ylabel("Kendall $\\tau_b$ vs. E0", fontsize=8)
    ax.set_ylim(0.0, 1.05)
    ax.set_title("(a) Parameter grid: liquid $\\to$ illiquid", fontsize=8.5)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", linewidth=0.3, alpha=0.4)

    # Right: real-market vs. synthetic, grouped bars by stressed level.
    ax = axes[1]
    levels = ["E1_default_stress", "E2_spread_20bps", "E2_latency_3", "E2_participation_1pct", "E2_harsh_corner"]
    lab = ["E1", "spread", "latency", "partic.", "harsh"]

    def tau_of(rows, level, window=None):
        for r in rows:
            if r["level_b"] == level and (window is None or r["window"] == window):
                return float(r["kendall_tau"])
        return 0.0

    series = [
        ("synthetic\nhigh vol.", REGIME_COLOR["high_vol"], [tau_of(synth, lv) for lv in levels]),
        ("real 2022", "#1f5fa8", [tau_of(real, lv, "rates_drawdown_2022") for lv in levels]),
        ("real recent", "#2e8b57", [tau_of(real, lv, "recent_cross_asset") for lv in levels]),
    ]
    width = 0.26
    base = list(range(len(levels)))
    for i, (name, color, vals) in enumerate(series):
        ax.bar([b + (i - 1) * width for b in base], vals, width, label=name, color=color, alpha=0.9)
    ax.set_xticks(base, lab, fontsize=7)
    ax.set_ylim(0.0, 1.05)
    ax.set_title("(b) Synthetic vs. real markets", fontsize=8.5)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", linewidth=0.3, alpha=0.4)
    ax.legend(fontsize=6.0, loc="lower right", frameon=False, ncol=1)

    fig.tight_layout()
    path = output_dir / "external_robustness.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def render_sampling_variance(input_dir: Path, output_dir: Path) -> Path:
    rows = [
        r
        for r in csv.DictReader((input_dir / "execution_sensitivity_llm" / "sampling_variance.csv").open(encoding="utf-8"))
        if r["agent"] == "deepseek:deepseek-v4-pro"
    ]
    regimes = ["calm", "high_vol", "jump_tail"]
    regime_lab = {"calm": "calm", "high_vol": "high vol.", "jump_tail": "jump/tail"}
    levels = ["E0_ideal", "E1_default_stress", "E2_harsh_corner"]
    level_lab = ["E0 ideal", "E1 default", "harsh corner"]
    level_color = ["#9aa0a6", "#1f5fa8", "#b22222"]
    share = {(r["scenario"], r["level"]): float(r["within_seed_share"]) for r in rows}

    fig, ax = plt.subplots(figsize=(3.3, 2.5))
    width = 0.26
    base = list(range(len(regimes)))
    for i, (lv, lab, color) in enumerate(zip(levels, level_lab, level_color)):
        vals = [share[(rg, lv)] for rg in regimes]
        ax.bar([b + (i - 1) * width for b in base], vals, width, label=lab, color=color, alpha=0.9)
    ax.axhline(0.5, color="black", linewidth=0.6, linestyle=":")
    ax.set_xticks(base, [regime_lab[rg] for rg in regimes], fontsize=8)
    ax.set_ylabel("within-seed (provider) variance share", fontsize=7.5)
    ax.set_ylim(0.0, 0.6)
    ax.set_title("Provider sampling is a minority of variance", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", linewidth=0.3, alpha=0.4)
    ax.legend(fontsize=6.5, loc="upper right", frameon=False, ncol=1)
    fig.tight_layout()
    path = output_dir / "sampling_variance.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render additional execution-sensitivity figures.")
    parser.add_argument("--input-dir", default="docs/results")
    parser.add_argument("--output-dir", default="figures/execution_sensitivity")
    args = parser.parse_args(argv)
    input_dir = ROOT / args.input_dir if not Path(args.input_dir).is_absolute() else Path(args.input_dir)
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print("wrote", render_rank_bump(input_dir, output_dir))
    print("wrote", render_compression(input_dir, output_dir))
    print("wrote", render_anchor(input_dir, output_dir))
    print("wrote", render_external(input_dir, output_dir))
    print("wrote", render_sampling_variance(input_dir, output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
