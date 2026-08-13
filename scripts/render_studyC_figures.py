"""Figures for the gate study (Study C, Airlock) of the merged technical report.

Read-only over already-generated result files; no experiment is re-run and no
network or LLM call is made. Two panels:

  (a) First-intercepting layer by fault family. Each faulted bundle is attributed
      to the first of the five deterministic layers that rejects it, or recorded
      as an escape past the sealed final gate. Bars are percentages so the
      auxiliary journal family (n=5) is comparable with the six headline
      families (n=60); the escape segment carries its raw count, because that
      residue -- not the interception rate -- is what a human reviewer inherits.
      NOTE: first-intercept attribution says where a fault stopped, not whether
      a later layer would also have stopped it. It cannot establish that any
      layer is non-redundant; that requires leave-one-layer-out.
  (b) The residue and the LLM monitor's coverage of it, by capability tier.
      Sample sizes are single digits (9 items per model for clean/semantic/
      freetext, 6 for the authority control) and are annotated on every bar as
      k/n with 95% Wilson intervals, because no per-cell difference here is
      resolved at this n. `clean` is a false-positive tier: lower is better.
      `authority` is a control tier the deterministic gate already catches, so
      it is not residue.

Inputs (all under docs/results/):
  live_readiness_e1/e1_matrix.csv        family x layer counts, pct, Wilson CIs
  live_readiness_e1/e1_interception.csv  per-variant ledger (escape composition)
  live_readiness_e6/e6_monitor.csv       monitor rates, template A
  live_readiness_e6/e6_monitor_b.csv     monitor rates, template B (overlay)

Writes figures/report/gate_interception.pdf (and .png for drafts).
"""

from __future__ import annotations

import collections
import csv
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
E1_MATRIX = ROOT / "docs/results/live_readiness_e1/e1_matrix.csv"
E1_LEDGER = ROOT / "docs/results/live_readiness_e1/e1_interception.csv"
E6_A = ROOT / "docs/results/live_readiness_e6/e6_monitor.csv"
E6_B = ROOT / "docs/results/live_readiness_e6/e6_monitor_b.csv"
OUT_DIR = ROOT / "figures/report"
STEM = "gate_interception"

# Deployment order of the deterministic layers; a variant is attributed to the
# first one that rejects it.
LAYERS = (
    "schema_validation",
    "single_artifact_validator",
    "approval_hash_binding",
    "cross_artifact_preflight",
    "orchestrator_revalidation",
)
LAYER_LABEL = {
    "schema_validation": "1. schema validation",
    "single_artifact_validator": "2. single-artifact validator",
    "approval_hash_binding": "3. approval/hash binding",
    "cross_artifact_preflight": "4. cross-artifact preflight",
    "orchestrator_revalidation": "5. orchestrator re-validation",
}
# Colour-blind-safe sequential Blues for the five layers (deep = caught early),
# with the house dark red reserved for the residue that reaches the human. The
# ramp stops well short of white so a family caught entirely by the last layer
# (F7) still reads as a filled bar rather than as empty space.
LAYER_COLOR = {
    "schema_validation": "#08306b",
    "single_artifact_validator": "#2171b5",
    "approval_hash_binding": "#4292c6",
    "cross_artifact_preflight": "#6baed6",
    "orchestrator_revalidation": "#9ecae1",
}
ESCAPE_COLOR = "#b2182b"

FAMILY_ORDER = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
FAMILY_TICK = {
    "F1": "F1\nidentifier\npollution",
    "F2": "F2\ncapability\noverreach",
    "F3": "F3\napproval\nbypass",
    "F4": "F4\nresponse\nmismatch",
    "F5": "F5\nclock &\ntimestamp",
    "F6": "F6\nrunbook\nviolations",
    "F7": "F7 (aux)\njournal\nchain",
}

TIERS = ("clean", "semantic", "freetext", "authority")
TIER_TICK = {
    "clean": "clean\n(false positives,\nlower is better)",
    "semantic": "semantic\n(residue an LLM\ncan cross-check)",
    "freetext": "freetext\n(residue: not decidable\nfrom the bundle)",
    "authority": "authority\n(control: gate\nalready catches)",
}
MODELS = (
    "poe:claude-opus-4.7",
    "poe:gemini-3.1-pro",
    "deepseek:deepseek-v4-pro",
    "glm:glm-5",
)
MODEL_LABEL = {
    "poe:claude-opus-4.7": "claude-opus-4.7",
    "poe:gemini-3.1-pro": "gemini-3.1-pro",
    "deepseek:deepseek-v4-pro": "deepseek-v4-pro",
    "glm:glm-5": "glm-5",
}
# Okabe-Ito qualitative palette (colour-blind safe).
MODEL_COLOR = {
    "poe:claude-opus-4.7": "#0072B2",
    "poe:gemini-3.1-pro": "#E69F00",
    "deepseek:deepseek-v4-pro": "#009E73",
    "glm:glm-5": "#CC79A7",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@dataclass
class FamilyCell:
    """One column of the E1 interception matrix."""

    total: int = 0
    layer_pct: dict[str, float] = field(default_factory=dict)
    intercepted_pct: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    escape_count: int = 0
    escape_pct: float = 0.0


@dataclass
class Residue:
    """The escapes, plus how often first-intercept moved a fault off its layer.

    ``designed``/``moved``/``designed_escaped`` support the caption caveat: an
    in-catalog fault carries the layer it was written to exercise, and a fault
    absorbed by an earlier layer never reaches the layer it was aimed at. That
    is exactly why first-intercept cannot rank layers by necessity.
    """

    total: int
    escapes: int
    by_field: collections.Counter[str]
    by_bucket: collections.Counter[str]
    designed: int
    moved: int
    designed_escaped: int


@dataclass
class MonitorCell:
    """One (model, tier) cell of the E6 monitor study."""

    rate: float
    n: int
    low: float
    high: float

    @property
    def hits(self) -> int:
        return round(self.rate * self.n)


def load_matrix() -> dict[str, FamilyCell]:
    out: dict[str, FamilyCell] = {}
    for row in _read_csv(E1_MATRIX):
        cell = out.setdefault(row["family"], FamilyCell())
        cell.total = int(row["family_total"])
        layer = row["layer"]
        if layer in LAYERS:
            cell.layer_pct[layer] = float(row["pct"])
        elif layer == "total_intercepted":
            cell.intercepted_pct = float(row["pct"])
            cell.ci_low = float(row["ci_low_pct"])
            cell.ci_high = float(row["ci_high_pct"])
        elif layer == "escape":
            cell.escape_count = int(row["count"])
            cell.escape_pct = float(row["pct"])
    return out


def load_residue() -> Residue:
    rows = _read_csv(E1_LEDGER)
    escapes = [row for row in rows if row["intercepted"] == "False"]
    designed = [row for row in rows if row["expected_layer"]]
    moved = [
        row for row in designed
        if row["intercepted"] == "True" and row["first_layer"] != row["expected_layer"]
    ]
    return Residue(
        total=len(rows),
        escapes=len(escapes),
        by_field=collections.Counter(row["target_field"] for row in escapes),
        by_bucket=collections.Counter(row["bucket"] for row in escapes),
        designed=len(designed),
        moved=len(moved),
        designed_escaped=sum(1 for row in designed if row["intercepted"] == "False"),
    )


def load_monitor(path: Path) -> dict[tuple[str, str], MonitorCell]:
    out: dict[tuple[str, str], MonitorCell] = {}
    for row in _read_csv(path):
        out[(row["model"], row["tier"])] = MonitorCell(
            rate=float(row["flag_rate"]),
            n=int(row["n"]),
            low=float(row["wilson_low"]),
            high=float(row["wilson_high"]),
        )
    return out


def panel_a(ax: plt.Axes, matrix: dict[str, FamilyCell]) -> None:
    families = [f for f in FAMILY_ORDER if f in matrix]
    x = list(range(len(families)))
    bottom = [0.0] * len(families)
    for layer in LAYERS:
        vals = [matrix[family].layer_pct.get(layer, 0.0) for family in families]
        ax.bar(x, vals, bottom=bottom, width=0.66, color=LAYER_COLOR[layer],
               edgecolor="white", linewidth=0.6)
        bottom = [b + v for b, v in zip(bottom, vals)]

    escape_vals = [matrix[f].escape_pct for f in families]
    ax.bar(x, escape_vals, bottom=bottom, width=0.66, color=ESCAPE_COLOR,
           edgecolor="white", linewidth=0.6)

    for i, family in enumerate(families):
        cell = matrix[family]
        if cell.escape_count:
            ax.annotate(
                str(cell.escape_count),
                (i, bottom[i] + escape_vals[i] / 2),
                ha="center", va="center", fontsize=7, color="white", fontweight="bold",
            )
        ax.annotate(
            f"{cell.intercepted_pct:.1f}%\n[{cell.ci_low:.0f},{cell.ci_high:.0f}]",
            (i, 101.5), ha="center", va="bottom", fontsize=6.4,
        )
        ax.annotate(f"n={cell.total}", (i, -3.0), ha="center", va="top", fontsize=6.4,
                    color="#444444")

    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("share of a family's faulted bundles (%)")
    ax.set_title("(a) First-intercepting layer by fault family", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([FAMILY_TICK[f] for f in families], fontsize=6.6)
    ax.tick_params(axis="x", length=0, pad=14)
    ax.grid(axis="y", alpha=0.25, lw=0.4)
    ax.set_axisbelow(True)
    # Legend below the panel: the bars run to 100% and the interception-rate
    # annotations sit above them, so there is no free space inside the axes.
    ax.legend(
        handles=[Patch(facecolor=LAYER_COLOR[layer], edgecolor="#888888", linewidth=0.4,
                       label=LAYER_LABEL[layer]) for layer in LAYERS]
        + [Patch(facecolor=ESCAPE_COLOR, label="escape (reaches the human)")],
        fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.20),
        frameon=False, ncol=3, handlelength=1.3, columnspacing=1.2,
    )


def panel_b(
    ax: plt.Axes,
    template_a: dict[tuple[str, str], MonitorCell],
    template_b: dict[tuple[str, str], MonitorCell],
) -> None:
    width = 0.19
    centers = list(range(len(TIERS)))

    for slot, model in enumerate(MODELS):
        offset = (slot - (len(MODELS) - 1) / 2) * width
        xs = [i + offset for i in range(len(TIERS))]
        cells = [template_a[(model, tier)] for tier in TIERS]
        rates = [cell.rate for cell in cells]
        err_lo = [cell.rate - cell.low for cell in cells]
        err_hi = [cell.high - cell.rate for cell in cells]
        ax.bar(xs, rates, width, color=MODEL_COLOR[model], edgecolor="white", linewidth=0.5,
               label=MODEL_LABEL[model], zorder=2)
        ax.errorbar(xs, rates, yerr=[err_lo, err_hi], fmt="none", ecolor="#333333",
                    elinewidth=0.7, capsize=1.6, zorder=3)
        # The sample sizes are single digits, so show the raw numerator and
        # denominator on every bar rather than only the rate.
        for pos, cell in zip(xs, cells):
            ax.annotate(
                f"{cell.hits}/{cell.n}",
                (pos, cell.high + 0.015), ha="center", va="bottom",
                fontsize=5.6, rotation=90, color="#222222",
            )
        # second frozen template, same tier structure: stability check, same tiny n
        b_xs = [pos for pos, tier in zip(xs, TIERS) if (model, tier) in template_b]
        b_ys = [template_b[(model, tier)].rate for tier in TIERS if (model, tier) in template_b]
        ax.scatter(b_xs, b_ys, marker="D", s=9, facecolor="white",
                   edgecolor="#222222", linewidth=0.6, zorder=4)

    ax.axvspan(-0.5, 0.5, color="#b2182b", alpha=0.06, zorder=0)
    ax.axvspan(2.5, 3.5, color="#777777", alpha=0.07, zorder=0)
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(0, 1.24)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("monitor flag rate")
    ax.set_title("(b) LLM-monitor coverage of the residue, by capability tier", fontsize=10)
    ax.set_xticks(centers)
    ax.set_xticklabels([TIER_TICK[t] for t in TIERS], fontsize=6.4)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.grid(axis="y", alpha=0.25, lw=0.4)
    ax.set_axisbelow(True)

    handles, labels = ax.get_legend_handles_labels()
    handles.append(plt.Line2D([], [], marker="D", linestyle="none", markersize=3.2,
                              markerfacecolor="white", markeredgecolor="#222222",
                              label="second frozen template"))
    labels.append("second frozen template")
    ax.legend(handles=handles, labels=labels, fontsize=6.3, loc="upper center",
              bbox_to_anchor=(0.5, -0.20), frameon=False, ncol=3,
              handlelength=1.2, columnspacing=1.2)


def main() -> int:
    missing = [p for p in (E1_MATRIX, E1_LEDGER, E6_A, E6_B) if not p.exists()]
    if missing:
        for path in missing:
            print(f"missing {path}")
        return 1

    matrix = load_matrix()
    residue = load_residue()
    template_a = load_monitor(E6_A)
    template_b = load_monitor(E6_B)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.2, 4.9))
    panel_a(ax_a, matrix)
    panel_b(ax_b, template_a, template_b)

    identifier = residue.by_field.get("approval.approved_by", 0)
    free_text = residue.escapes - identifier

    fig.tight_layout(rect=(0.0, 0.10, 1.0, 1.0))
    fig.text(
        0.008, 0.062,
        "(a) First-intercept records where a fault stopped, not whether a later layer would also have stopped it: of "
        f"{residue.designed} in-catalog faults carrying a designed layer, {residue.moved} were absorbed by a "
        "different layer first\n"
        f"      and {residue.designed_escaped} escaped, so a zero cell means \"never reached\", not \"cannot catch\". "
        "Layer necessity requires leave-one-layer-out, which was not run.",
        fontsize=6.0, ha="left", va="bottom", color="#333333",
    )
    fig.text(
        0.008, 0.008,
        f"(b) Residue = {residue.escapes}/{residue.total} faulted bundles escaping all five layers "
        f"({residue.by_bucket.get('directed', 0)} in-catalog, {residue.by_bucket.get('fuzz', 0)} out-of-catalog fuzz): "
        f"{free_text} free-text/label fields and {identifier} self-asserted approver ids. Error bars are 95% Wilson;\n"
        "      n = 9 items per model for clean/semantic/freetext and 6 for authority, so every interval is wide and no "
        "per-cell difference is resolved at this n.",
        fontsize=6.0, ha="left", va="bottom", color="#333333",
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"{STEM}.{suffix}", bbox_inches="tight", dpi=200)
    print(f"wrote {(OUT_DIR / f'{STEM}.pdf').relative_to(ROOT)}")

    print(f"  E1: {residue.total - residue.escapes}/{residue.total} intercepted, "
          f"{residue.escapes} escapes ({residue.by_bucket.get('directed', 0)} directed, "
          f"{residue.by_bucket.get('fuzz', 0)} fuzz); {residue.moved}/{residue.designed} "
          f"in-catalog faults moved layer, {residue.designed_escaped} escaped")
    for family in FAMILY_ORDER:
        cell = matrix.get(family)
        if cell is None:
            continue
        print(f"    {family} n={cell.total:>3d} intercepted={cell.intercepted_pct:5.1f}% "
              f"[{cell.ci_low:.1f},{cell.ci_high:.1f}] escapes={cell.escape_count}")
    for target_field, count in residue.by_field.most_common():
        print(f"    residue field {target_field:28s} {count}")
    print("  E6 template A flag rates (k/n):")
    for model in MODELS:
        summary = [f"{tier}={template_a[(model, tier)].hits}/{template_a[(model, tier)].n}" for tier in TIERS]
        print(f"    {MODEL_LABEL[model]:18s} " + "  ".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
