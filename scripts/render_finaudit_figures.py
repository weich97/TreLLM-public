"""Figures for the audit study of the merged technical report.

Two panels, both driven by the corrected multi-label re-scoring of the stored
paired responses (docs/results/finaudit/corrected_key_rescore.csv):

  (a) Answer cardinality on the two-defect arm. Each auditor's responses are
      partitioned into "both true defects reported", "violation only", "edit
      only", and "neither". The single-defect benchmark can only ever observe
      the union of the first two, which is why it overstates completeness.
  (b) The estimand. Violation recall on the one-defect arm versus the
      two-defect arm, with the within-pair McNemar p-value annotated. The
      corrected key removes the double penalty and the drop survives.

Writes figures/report/audit_cardinality.pdf (and .png for drafts).
"""

from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
RESCORE = ROOT / "docs/results/finaudit/corrected_key_rescore.csv"
OUT_DIR = ROOT / "figures/report"
MODELS = ("deepseek:deepseek-v4-pro", "glm:glm-5")

DOMAINS = {
    "trading": {
        "sources": [
            (
                ROOT / f"outputs/audit_pairs/{producer}/ground_truth.jsonl",
                ROOT / f"outputs/audit_pairs_eval_v2/{producer}/audit_eval_results.jsonl",
                producer,
            )
            for producer in ("deepseek_v4_pro", "glm_5_direct")
        ],
        "violation_kind": "unclipped_position",
        "edit_kind": "silent_risk_edit",
    },
    "tooluse": {
        "sources": [
            (
                ROOT / "outputs/toolaudit_pairs/ground_truth.jsonl",
                ROOT / "outputs/toolaudit_pairs_eval_v2/toolaudit_eval_results.jsonl",
                "tooluse",
            )
        ],
        "violation_kind": "over_limit_call",
        "edit_kind": "silent_arg_edit",
    },
}

LABEL = {"deepseek:deepseek-v4-pro": "deepseek-v4-pro", "glm:glm-5": "glm-5"}
# colour-blind safe, ordered worst-to-best reading left to right in the stack
COLORS = {
    "both": "#1b7837",
    "violation_only": "#7fbf7b",
    "edit_only": "#d6604d",
    "neither": "#b2182b",
}


def cardinality_breakdown() -> dict[tuple[str, str], dict[str, float]]:
    """(domain, model) -> share of dual-arm responses in each cardinality class."""

    out: dict[tuple[str, str], dict[str, float]] = {}
    for domain, spec in DOMAINS.items():
        vkind, ekind = spec["violation_kind"], spec["edit_kind"]
        reported: dict[tuple[str, str], set[str]] = {}
        for gt_path, res_path, tag in spec["sources"]:
            if not (gt_path.exists() and res_path.exists()):
                continue
            truth = {
                json.loads(line)["task_id"]: json.loads(line)
                for line in gt_path.open(encoding="utf-8")
                if line.strip()
            }
            for line in res_path.open(encoding="utf-8"):
                if not line.strip():
                    continue
                record = json.loads(line)
                if record["model"] not in MODELS or int(record.get("sample", 0)) != 0:
                    continue
                entry = truth.get(record["task_id"])
                if not entry or entry["kind"] != vkind:
                    continue
                if entry["detail"].get("ambiguity") != "confounded":
                    continue
                step = int(entry["step_index"])
                kinds = {
                    str(f.get("kind", ""))
                    for f in record["findings"] or []
                    if str(f.get("step_index", "")) == str(step)
                }
                reported[(record["model"], f"{tag}:{entry['detail']['pair_id']}")] = kinds
        for model in MODELS:
            cells = [kinds for (m, _), kinds in reported.items() if m == model]
            if not cells:
                continue
            counts: collections.Counter[str] = collections.Counter()
            for kinds in cells:
                has_v, has_e = vkind in kinds, ekind in kinds
                if has_v and has_e:
                    counts["both"] += 1
                elif has_v:
                    counts["violation_only"] += 1
                elif has_e:
                    counts["edit_only"] += 1
                else:
                    counts["neither"] += 1
            total = sum(counts.values())
            out[(domain, model)] = {k: counts[k] / total for k in COLORS}
    return out


def main() -> int:
    if not RESCORE.exists():
        print(f"missing {RESCORE}; run build_corrected_key_rescore.py first")
        return 1
    rescore = {(r["domain"], r["auditor"]): r for r in csv.DictReader(RESCORE.open(encoding="utf-8"))}
    breakdown = cardinality_breakdown()
    cells = [(d, m) for d in DOMAINS for m in MODELS if (d, m) in breakdown]
    ticks = [f"{LABEL[m]}\n({d})" for d, m in cells]
    x = range(len(cells))

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(10.4, 3.9))

    bottom = [0.0] * len(cells)
    for key in ("both", "violation_only", "edit_only", "neither"):
        vals = [breakdown[c][key] for c in cells]
        ax_a.bar(x, vals, bottom=bottom, color=COLORS[key], width=0.62,
                 edgecolor="white", linewidth=0.6)
        bottom = [b + v for b, v in zip(bottom, vals)]
    # the "both reported" share is the headline and is nearly invisible in the
    # stack precisely because it is small; label it explicitly.
    for i, cell in enumerate(cells):
        ax_a.annotate(
            f"both: {breakdown[cell]['both'] * 100:.0f}%",
            (i, 1.02), ha="center", fontsize=8, fontweight="bold",
        )
    ax_a.set_ylim(0, 1.12)
    ax_a.set_ylabel("share of two-defect responses")
    ax_a.set_title("(a) Answer cardinality when two defects are true", fontsize=10)
    ax_a.set_xticks(list(x)); ax_a.set_xticklabels(ticks, fontsize=8)
    ax_a.legend(
        handles=[
            Patch(facecolor=COLORS["both"], label="both reported"),
            Patch(facecolor=COLORS["violation_only"], label="violation only"),
            Patch(facecolor=COLORS["edit_only"], label="edit only"),
            Patch(facecolor=COLORS["neither"], label="neither"),
        ],
        fontsize=7, loc="lower left", framealpha=0.92, ncol=2,
    )

    width = 0.34
    single = [float(rescore[c]["single_violation_recall"]) for c in cells]
    dual = [float(rescore[c]["dual_violation_recall"]) for c in cells]
    ax_b.bar([i - width / 2 for i in x], single, width, label="one true defect",
             color="#4393c3", edgecolor="white")
    ax_b.bar([i + width / 2 for i in x], dual, width, label="two true defects",
             color="#f4a582", edgecolor="white")
    for i, c in enumerate(cells):
        top = max(single[i], dual[i])
        ax_b.annotate(f"$p$={float(rescore[c]['mcnemar_p']):.0e}",
                      (i, min(1.0, top + 0.06)), ha="center", fontsize=7)
    ax_b.set_ylim(0, 1.16)
    ax_b.set_ylabel("violation recall")
    ax_b.set_title("(b) The violation is reported less when a second defect is true", fontsize=10)
    ax_b.set_xticks(list(x)); ax_b.set_xticklabels(ticks, fontsize=8)
    ax_b.legend(fontsize=7, loc="lower left", framealpha=0.92)
    ax_b.grid(axis="y", alpha=0.25, lw=0.4)

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"audit_cardinality.{suffix}", bbox_inches="tight", dpi=200)
    print(f"wrote {(OUT_DIR / 'audit_cardinality.pdf').relative_to(ROOT)}")
    for cell in cells:
        share = breakdown[cell]
        print(f"  {cell[0]:8s} {LABEL[cell[1]]:18s} both={share['both']:.2f} "
              f"v-only={share['violation_only']:.2f} e-only={share['edit_only']:.2f} "
              f"neither={share['neither']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
