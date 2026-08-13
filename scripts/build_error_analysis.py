"""Error analysis for the difficulty inversion (audit study): when a weak overseer
misses the L1 constraint violation, what does it do instead?

Reads the default-prompt intervention cells (deepseek + glm auditing the producer
L1 tasks). For each missed L1 task it records whether the auditor stayed silent,
whether it flagged the EXACT injected step, and whether it mislabeled that step
as a (cross-record) silent intervention edit rather than an unclipped action.
Finding: the weak tier locates the anomaly but miscategorizes it---matching
inconsistency instead of checking the constraint. Reads only the *_default cells,
which are fully checkpointed and stable.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/results/finaudit/error_analysis.csv"
CELLS = ROOT / "outputs/audit_intervention"
MODELS = ["deepseek:deepseek-v4-pro", "glm:glm-5"]


def main() -> int:
    rows = []
    for model in MODELS:
        missed = silent = flag_step = flag_step_edit = 0
        fp_kinds: Counter = Counter()
        for d in CELLS.glob("*_default"):
            producer = d.name[: -len("_default")]
            gtf = ROOT / f"outputs/audit_self/{producer}/ground_truth.jsonl"
            if not gtf.exists():
                continue
            gt = {json.loads(x)["task_id"]: json.loads(x) for x in gtf.open(encoding="utf-8")}
            for line in (d / "audit_eval_results.jsonl").open(encoding="utf-8"):
                r = json.loads(line)
                if r["model"] != model or r["difficulty"] != "L1" or r["true_positives"] >= 1:
                    continue
                missed += 1
                if r["finding_count"] == 0:
                    silent += 1
                dstep = gt.get(r["task_id"], {}).get("step_index")
                for f in r["findings"]:
                    fp_kinds[f.get("kind", "?")] += 1
                for f in r["findings"]:
                    if f.get("step_index") == dstep:
                        flag_step += 1
                        if "edit" in str(f.get("kind", "")):
                            flag_step_edit += 1
                        break
        rows.append({
            "model": model,
            "L1_missed": missed,
            "silent": silent,
            "flagged_defect_step": flag_step,
            "step_mislabeled_as_edit": flag_step_edit,
            "top_false_positive_kind": fp_kinds.most_common(1)[0][0] if fp_kinds else "",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}\n")
    for r in rows:
        print(f"  {r['model']:26s} missed={r['L1_missed']} silent={r['silent']} "
              f"flagged_step={r['flagged_defect_step']} as_edit={r['step_mislabeled_as_edit']} "
              f"top_fp={r['top_false_positive_kind']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
