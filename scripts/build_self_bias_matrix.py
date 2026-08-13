"""Assemble the FinAudit self-audit-bias matrix (audit study, experiment B).

Reads each per-producer ``audit_eval_summary.csv`` (the ALL-difficulty recall of
every auditor on that producer's task set), builds the auditor x producer recall
matrix, and computes each auditor's self-audit gap = cross_recall - self_recall
(positive => the auditor goes easier on its OWN trajectories). Writes a tidy CSV
for the study's data trail and prints the matrix + gaps. Re-run any time the
matrix cells are refilled.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "outputs" / "audit_matrix"
OUT = ROOT / "docs" / "results" / "finaudit" / "self_bias_matrix.csv"

# producer dir -> the auditor id for which this producer is the SELF cell
PRODUCERS = {
    "deepseek_v4_pro": "deepseek:deepseek-v4-pro",
    "glm_5_direct": "glm:glm-5",
    "gemini_3_1_pro": "poe:gemini-3.1-pro",
    "claude_opus_4_7": "poe:claude-opus-4.7",
}
AUDITORS = ["deepseek:deepseek-v4-pro", "glm:glm-5", "poe:gemini-3.1-pro", "poe:claude-opus-4.7"]


def all_recall(producer_dir: str) -> dict[str, float]:
    """auditor -> ALL-difficulty recall on this producer's task set."""
    f = MATRIX / producer_dir / "audit_eval_summary.csv"
    out: dict[str, float] = {}
    with f.open(encoding="utf-8") as fh:
        for row in csv.reader(fh):  # cols: model, slice, n, detected, recall, ...
            if len(row) >= 5 and row[1] == "ALL":
                out[row[0]] = float(row[4])
    return out


def main() -> int:
    recall: dict[str, dict[str, float]] = {a: {} for a in AUDITORS}
    for pdir in PRODUCERS:
        for auditor, r in all_recall(pdir).items():
            if auditor in recall:
                recall[auditor][pdir] = r

    rows = []
    for a in AUDITORS:
        self_pdir = next(p for p, aud in PRODUCERS.items() if aud == a)
        self_r = recall[a].get(self_pdir)
        cross = [recall[a][p] for p in PRODUCERS if p != self_pdir and p in recall[a]]
        cross_r = sum(cross) / len(cross) if cross else None
        gap = (cross_r - self_r) if (self_r is not None and cross_r is not None) else None
        rows.append({
            "auditor": a,
            **{f"prod_{p}": (f"{recall[a][p]:.3f}" if p in recall[a] else "") for p in PRODUCERS},
            "self": f"{self_r:.3f}" if self_r is not None else "",
            "cross": f"{cross_r:.3f}" if cross_r is not None else "",
            "gap": f"{gap:+.3f}" if gap is not None else "",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["auditor"] + [f"prod_{p}" for p in PRODUCERS] + ["self", "cross", "gap"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {OUT.relative_to(ROOT)}\n")
    print(f"{'auditor':<26}" + "".join(f"{p[:11]:>12}" for p in PRODUCERS) + f"{'self':>8}{'cross':>8}{'gap':>8}")
    for r in rows:
        print(f"{r['auditor']:<26}" + "".join(f"{r['prod_'+p]:>12}" for p in PRODUCERS)
              + f"{r['self']:>8}{r['cross']:>8}{r['gap']:>8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
