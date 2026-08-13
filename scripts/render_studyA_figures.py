"""Figure for Study A of the merged technical report: identifying the execution effect.

The earlier v0.3 comparison re-called the provider once at E0 and once at E1, so the
published E0-vs-E1 difference mixes the execution channel with provider sampling and
closed-loop feedback. The corrected design freezes each raw provider response tape and
replays the *same* tape into both execution destinations, which turns the destination
contrast into a within-tape comparison.

Two panels, both read from the released analysis tables (no API calls, no re-runs):

  (a) Two-by-two decomposition of total return
      (docs/results/v0_3_fixed_intent_replay/factorial_estimands.csv). The execution
      contrasts sit clearly below zero but are small next to the E0 baseline return
      level; the realized response-origin contrasts straddle zero. Filled markers mark
      intervals that exclude zero, hollow markers those that do not.

  (b) Sharpe ranking agreement between the two execution destinations under a fixed
      response tape (docs/results/v0_3_fixed_intent_replay/ranking_stability.csv),
      as Kendall tau-b with its shared-seed bootstrap interval, per scenario and per
      response origin. The bootstrap probability that the two destinations reproduce
      the *exact* order is annotated, because a tau-b point estimate of 1.000 with an
      exact-order probability of 0.26 is not a stable ranking.

Both panels carry the honest caveat that one of the five ranked models never trades:
deepseek-v4-pro is last in every published ranking and is the only model contributing
any cross-origin path agreement. That is inactivity, not robustness. The inactive-row
count in the caveat is recomputed from the released replay table rather than restated
from prose; if that table is absent the caveat drops the count instead of asserting one.

Writes figures/report/execution_identification.pdf (and .png for drafts).
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
REPLAY_DIR = ROOT / "docs/results/v0_3_fixed_intent_replay"
FACTORIAL = REPLAY_DIR / "factorial_estimands.csv"
RANKING = REPLAY_DIR / "ranking_stability.csv"
DIVERGENCE = REPLAY_DIR / "response_path_divergence.csv"
REPLAY_ROWS = REPLAY_DIR / "replay_rows.csv"
MATRIX = ROOT / "outputs/v0_3_direct_api_matrix/direct_api_submission_runs.csv"
OUT_DIR = ROOT / "figures/report"
STEM = "execution_identification"

# Okabe-Ito: safe under deuteranopia, protanopia and tritanopia, and in greyscale.
BLUE = "#0072B2"  # execution channel (identified within a fixed tape)
VERMILLION = "#D55E00"  # realized response-origin channel (descriptive only)
GREEN = "#009E73"  # interaction
GREY = "#4D4D4D"  # the confounded observed diagonal

# (row label, estimand key, colour) drawn top to bottom.
PANEL_A_ROWS = (
    ("observed diagonal\n(E0/E0 $\\rightarrow$ E1/E1)", "observed_diagonal", GREY),
    ("execution, Shapley", "execution_shapley", BLUE),
    ("execution | tape from E1", "execution_within_I1", BLUE),
    ("execution | tape from E0", "execution_within_I0", BLUE),
    ("response origin, Shapley", "response_origin_shapley", VERMILLION),
    ("response origin | replay E1", "response_origin_within_X1", VERMILLION),
    ("response origin | replay E0", "response_origin_within_X0", VERMILLION),
    ("interaction", "interaction", GREEN),
)
SCENARIO_LABEL = {
    "synthetic_calm_trend_c0_v0_3": "calm trend",
    "synthetic_high_volatility_c0_v0_3": "high volatility",
    "synthetic_jump_tail_c0_v0_3": "jump tail",
}
ORIGIN_COLOR = {"E0": BLUE, "E1": VERMILLION}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def baseline_return(path: Path) -> float | None:
    """Mean total return of the E0 arm of the source matrix, for effect-size scale."""

    if not path.exists():
        return None
    values = [
        float(row["total_return"])
        for row in read_csv(path)
        if row.get("execution_level") == "E0" and row.get("status") == "ok"
    ]
    return sum(values) / len(values) if values else None


def path_agreement_by_model(path: Path) -> dict[str, float]:
    """model -> share of its base pairs whose full parsed response path agrees across origins."""

    if not path.exists():
        return {}
    return {
        row["value"]: float(row["full_parsed_response_path_equal_rate"])
        for row in read_csv(path)
        if row["scope"] == "model"
    }


def inactive_rows_by_model(path: Path) -> dict[str, tuple[int, int]]:
    """model -> (inactive replay rows, total replay rows).

    A row is inactive when it earns nothing, holds every period, and never takes on
    gross target exposure. Recomputed here so the caveat never restates a number the
    figure has not checked; returns {} when the released replay table is unavailable.
    """

    if not path.exists():
        return {}
    counts: dict[str, list[int]] = {}
    for row in read_csv(path):
        inactive = (
            float(row["total_return"]) == 0.0
            and float(row["hold_ratio"]) == 1.0
            and float(row["mean_gross_target_exposure"]) == 0.0
        )
        tally = counts.setdefault(row["model_id"], [0, 0])
        tally[0] += int(inactive)
        tally[1] += 1
    return {model: (hit, total) for model, (hit, total) in counts.items()}


def build_caveat(ranking: list[dict[str, str]]) -> str:
    """Say plainly that the bottom-ranked model is pinned by inactivity, not robustness."""

    last_placed = {row["ranking_e0"].split(">")[-1] for row in ranking} | {
        row["ranking_e1"].split(">")[-1] for row in ranking
    }
    inactivity = inactive_rows_by_model(REPLAY_ROWS)
    agreement = path_agreement_by_model(DIVERGENCE)
    names = ", ".join(sorted(last_placed))
    text = f"Ranking caveat: {names} is last in every published ranking"
    counted = [inactivity[model] for model in sorted(last_placed) if model in inactivity]
    if counted:
        hit = sum(pair[0] for pair in counted)
        total = sum(pair[1] for pair in counted)
        text += (
            f" and is inactive in {hit}/{total} replay rows"
            " (zero return, all-hold, zero gross target exposure)"
        )
    text += (
        ". Its rank is pinned by inactivity, not robustness, and because its Sharpe is a"
        " constant it fixes 4 of the 10 ranked pairs and inflates $\\tau_b$."
    )
    if agreement:
        rates = [
            f"{model} {rate:.0%}"
            for model, rate in sorted(agreement.items())
            if rate > 0.0
        ]
        zeroed = sum(1 for rate in agreement.values() if rate == 0.0)
        if rates and zeroed:
            text += (
                f" It is also the only source of cross-origin parsed-path agreement ({', '.join(rates)});"
                f" the {zeroed} models that actually trade agree on 0% of their pairs, so panel (a)'s"
                " execution contrast is the only contrast identified within a fixed tape."
            )
    return text


def draw_panel_a(ax: plt.Axes, factorial: list[dict[str, str]], baseline: float | None) -> None:
    rows = {
        row["estimand"]: row for row in factorial if row["metric"] == "total_return"
    }
    positions = list(range(len(PANEL_A_ROWS)))[::-1]
    labels: list[str] = []
    for pos, (label, key, colour) in zip(positions, PANEL_A_ROWS, strict=True):
        row = rows[key]
        estimate = float(row["estimate"])
        low, high = float(row["ci95_low"]), float(row["ci95_high"])
        excludes_zero = low > 0.0 or high < 0.0
        ax.plot([low, high], [pos, pos], color=colour, lw=1.8, solid_capstyle="butt", zorder=2)
        for edge in (low, high):
            ax.plot([edge, edge], [pos - 0.16, pos + 0.16], color=colour, lw=1.4, zorder=2)
        ax.plot(
            [estimate],
            [pos],
            marker="o",
            markersize=6.5,
            color=colour,
            markerfacecolor=colour if excludes_zero else "white",
            markeredgewidth=1.6,
            zorder=3,
        )
        ax.annotate(
            f"{estimate:+.4f}",
            (high, pos),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            fontsize=7.5,
            color=colour if excludes_zero else "#666666",
        )
        labels.append(label)
    ax.axvline(0.0, color="#999999", lw=0.9, ls="--", zorder=1)
    ax.axhspan(3.5, 6.5, color=BLUE, alpha=0.06, zorder=0)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_ylim(-1.35, len(PANEL_A_ROWS) - 0.35)
    ax.set_xlim(-0.036, 0.030)
    ax.tick_params(axis="x", labelsize=8.5)
    xlabel = "effect on total return (seed-cluster mean, 95% CI)"
    title = "(a) With the tape fixed, execution shifts return; response origin does not"
    if baseline is not None:
        share = 100.0 * abs(float(rows["execution_shapley"]["estimate"])) / abs(baseline)
        xlabel += f"\nE0 baseline return {baseline:+.3f}; execution Shapley is {share:.0f}% of it"
        title = (
            f"(a) With the tape fixed, execution costs {share:.0f}% of baseline return;"
            " response origin does not"
        )
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_title(title, fontsize=9.5)
    ax.grid(axis="x", alpha=0.25, lw=0.4)
    ax.legend(
        handles=[
            Line2D([], [], color="#333333", marker="o", ls="", markersize=6.5,
                   markerfacecolor="#333333", label="95% CI excludes 0"),
            Line2D([], [], color="#333333", marker="o", ls="", markersize=6.5,
                   markerfacecolor="white", markeredgewidth=1.6, label="95% CI includes 0"),
        ],
        fontsize=7,
        loc="lower left",
        framealpha=0.92,
        ncol=2,
    )


def draw_panel_b(ax: plt.Axes, ranking: list[dict[str, str]]) -> None:
    ordered = sorted(
        ranking,
        key=lambda row: (row["scenario_id"], row["response_origin"]),
    )
    positions = list(range(len(ordered)))[::-1]
    labels: list[str] = []
    flipped = False
    for pos, row in zip(positions, ordered, strict=True):
        origin = row["response_origin"]
        colour = ORIGIN_COLOR[origin]
        tau = float(row["kendall_tau_b"])
        low, high = float(row["ci95_low"]), float(row["ci95_high"])
        ax.plot([low, high], [pos, pos], color=colour, lw=1.8, solid_capstyle="butt", zorder=2)
        for edge in (low, high):
            ax.plot([edge, edge], [pos - 0.16, pos + 0.16], color=colour, lw=1.4, zorder=2)
        winner_flip = row["winner_e0"] != row["winner_e1"]
        flipped = flipped or winner_flip
        ax.plot(
            [tau],
            [pos],
            marker="D" if winner_flip else "o",
            markersize=6.0,
            color=colour,
            markerfacecolor="white" if winner_flip else colour,
            markeredgewidth=1.6,
            zorder=3,
        )
        note = f"exact-order $p$={float(row['exact_order_probability']):.2f}"
        if winner_flip:
            note += f"\ntop-1 {row['winner_e0']}$\\rightarrow${row['winner_e1']}"
        ax.annotate(
            note,
            (-0.04, pos),
            va="center",
            ha="right",
            fontsize=7,
            color="#333333",
        )
        labels.append(f"{SCENARIO_LABEL.get(row['scenario_id'], row['scenario_id'])}\ntape from {origin}")
    ax.axvline(1.0, color="#999999", lw=0.9, ls="--", zorder=1)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_ylim(-1.5, len(ordered) - 0.35)
    ax.set_xlim(-0.62, 1.10)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.tick_params(axis="x", labelsize=8.5)
    ax.set_xlabel(
        "Kendall $\\tau_b$: E0 vs E1 Sharpe ranking (95% CI)"
        "\n$p$ = bootstrap probability the two orders match exactly",
        fontsize=9,
    )
    # The left of the axes is an annotation gutter, so centre the label on the data span.
    ax.xaxis.set_label_coords(0.62, -0.085)
    ax.set_title(
        "(b) The ranking barely moves, but the bootstrap order is not tight",
        fontsize=9.5,
    )
    ax.grid(axis="x", alpha=0.25, lw=0.4)
    handles = [
        Line2D([], [], color=BLUE, marker="o", ls="", markersize=6,
               markerfacecolor=BLUE, label="tape sampled at E0"),
        Line2D([], [], color=VERMILLION, marker="o", ls="", markersize=6,
               markerfacecolor=VERMILLION, label="tape sampled at E1"),
    ]
    if flipped:
        handles.append(
            Line2D([], [], color="#333333", marker="D", ls="", markersize=6,
                   markerfacecolor="white", markeredgewidth=1.6, label="top-1 model flips")
        )
    ax.legend(handles=handles, fontsize=7, loc="lower right", framealpha=0.92, ncol=3)


def main() -> int:
    missing = [path for path in (FACTORIAL, RANKING) if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing {path}; run analyze_v03_fixed_intent_replay.py first")
        return 1

    factorial = read_csv(FACTORIAL)
    ranking = read_csv(RANKING)
    baseline = baseline_return(MATRIX)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.2, 4.2))
    draw_panel_a(ax_a, factorial, baseline)
    draw_panel_b(ax_b, ranking)

    caveat = build_caveat(ranking)
    fig.tight_layout(rect=(0, 0.075, 1, 1))
    fig.text(0.012, 0.012, caveat, fontsize=6.8, color="#444444", ha="left", va="bottom", wrap=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"{STEM}.{suffix}", bbox_inches="tight", dpi=200)
    plt.close(fig)

    print(f"wrote {(OUT_DIR / f'{STEM}.pdf').relative_to(ROOT)}")
    for _label, key, _colour in PANEL_A_ROWS:
        row = next(r for r in factorial if r["metric"] == "total_return" and r["estimand"] == key)
        flag = "  *" if float(row["ci95_low"]) > 0 or float(row["ci95_high"]) < 0 else ""
        print(
            f"  total_return {key:26s} {float(row['estimate']):+.6f} "
            f"[{float(row['ci95_low']):+.6f}, {float(row['ci95_high']):+.6f}]{flag}"
        )
    for row in sorted(ranking, key=lambda r: (r["scenario_id"], r["response_origin"])):
        print(
            f"  tau_b {row['scenario_id']:34s} {row['response_origin']} "
            f"{float(row['kendall_tau_b']):+.3f} "
            f"[{float(row['ci95_low']):+.3f}, {float(row['ci95_high']):+.3f}] "
            f"exact_p={float(row['exact_order_probability']):.4f} "
            f"{row['winner_e0']}->{row['winner_e1']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
