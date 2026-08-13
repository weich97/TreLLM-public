"""Render the prompt-intervention figure for the FinAudit study.

Grouped bars: L1 (constraint-tier) recall under the default prompt vs the
explicit constraint-verification prompt, for the two weak direct auditors and
the two strong routed auditors. Shows the weak overseers recovering to near the
strong models' ceiling while the strong models are unaffected.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/results/finaudit/intervention.csv"
OUT = ROOT / "figures/finaudit/intervention.pdf"

rows: dict[tuple[str, str], dict[str, str]] = {}
with SRC.open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        rows[(r["auditor"], r["condition"])] = r

MODELS = [
    ("deepseek:deepseek-v4-pro", "deepseek-v4-pro", True),
    ("glm:glm-5", "glm-5", True),
    ("poe:gemini-3.1-pro", "gemini-3.1-pro", False),
    ("poe:claude-opus-4.7", "claude-opus-4.7", False),
]
labels = [m[1] + (r"$^\dagger$" if m[2] else "") for m in MODELS]
default = [float(rows[(m[0], "default")]["L1_recall"]) for m in MODELS]
constr = [float(rows[(m[0], "constraint")]["L1_recall"]) for m in MODELS]

fig, ax = plt.subplots(figsize=(3.3, 2.3))
x = range(len(MODELS))
w = 0.38
b1 = ax.bar([i - w / 2 for i in x], default, w, label="default prompt",
           color="#bdbdbd", edgecolor="black", linewidth=0.5)
b2 = ax.bar([i + w / 2 for i in x], constr, w, label="+ constraint check",
           color="#4878a8", edgecolor="black", linewidth=0.5)
for bars in (b1, b2):
    for rect in bars:
        ax.annotate(f"{rect.get_height():.2f}", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    ha="center", va="bottom", fontsize=6, xytext=(0, 1), textcoords="offset points")
ax.axvline(1.5, color="black", linewidth=0.6, linestyle=":")
ax.text(0.5, 1.05, "weak (direct)", ha="center", fontsize=7, transform=ax.get_xaxis_transform())
ax.text(2.5, 1.05, "strong (routed)", ha="center", fontsize=7, transform=ax.get_xaxis_transform())
ax.set_ylim(0, 1.18)
ax.set_ylabel("L1 (constraint-tier) recall", fontsize=8)
ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontsize=7, rotation=20, ha="right")
ax.tick_params(axis="y", labelsize=7)
ax.legend(fontsize=6.5, loc="lower right", framealpha=0.9)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(pad=0.3)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight")
print(f"wrote {OUT.relative_to(ROOT)}")
