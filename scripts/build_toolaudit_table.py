"""Per-model, per-difficulty recall on the tool-use second-domain benchmark.

Reads outputs/toolaudit_eval/toolaudit_eval_results.jsonl and writes a tidy CSV
plus a printed table, for the "generalization to a second domain" result.
Re-run any time more auditor rows land.
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs" / "toolaudit_eval" / "toolaudit_eval_results.jsonl"
OUT = ROOT / "docs" / "results" / "finaudit" / "toolaudit_by_difficulty.csv"
DIFFS = ["L1", "L2", "L3", "ALL"]


def main() -> int:
    agg: dict[tuple[str, str], list[int]] = collections.defaultdict(lambda: [0, 0])
    with RESULTS.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            model = r["model"]
            for d in (r["difficulty"], "ALL"):
                agg[(model, d)][0] += int(r["true_positives"])
                agg[(model, d)][1] += 1

    models = sorted({k[0] for k in agg})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["model"] + [f"{d}_recall" for d in DIFFS] + [f"{d}_n" for d in DIFFS]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for m in models:
            row = {"model": m}
            for d in DIFFS:
                tp, n = agg.get((m, d), [0, 0])
                row[f"{d}_recall"] = f"{tp / n:.3f}" if n else ""
                row[f"{d}_n"] = n
            w.writerow(row)

    print(f"wrote {OUT.relative_to(ROOT)}\n")
    print(f"{'model':26s}" + "".join(f"{d:>10s}" for d in DIFFS))
    for m in models:
        cells = []
        for d in DIFFS:
            tp, n = agg.get((m, d), [0, 0])
            cells.append(f"{tp / n:.2f}({n})" if n else "-")
        print(f"{m:26s}" + "".join(f"{c:>10s}" for c in cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
