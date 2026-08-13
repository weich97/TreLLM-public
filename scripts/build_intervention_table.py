"""Merge both prompt-intervention arms into the unified 4-model table (audit study).

Reads the free arm (outputs/audit_intervention -- deepseek, glm) and the Poe arm
(outputs/audit_intervention_poe -- gemini, claude), pools each producer set, and
reports recall AND precision by difficulty under the default vs constraint
prompt. The story: does the explicit constraint-check prompt recover the weak
auditors' L1 recall, and at what precision cost, without hurting the strong ones?
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREES = [ROOT / "outputs/audit_intervention", ROOT / "outputs/audit_intervention_poe"]
OUT = ROOT / "docs/results/finaudit/intervention.csv"
MODELS = ["deepseek:deepseek-v4-pro", "glm:glm-5", "poe:gemini-3.1-pro", "poe:claude-opus-4.7"]
DIFFS = ["ALL", "L1", "L2", "L3"]


def main() -> int:
    # (model, condition, difficulty) -> [(tp, finding_count), ...]
    agg: dict[tuple[str, str, str], list[tuple[int, int]]] = defaultdict(list)
    for tree in TREES:
        if not tree.exists():
            continue
        for results in tree.glob("*/audit_eval_results.jsonl"):
            if results.parent.name.startswith("_"):
                continue  # _smoke and other unregistered cells must not pollute the table
            cond = "constraint" if results.parent.name.endswith("_constraint") else "default"
            for line in results.open(encoding="utf-8"):
                r = json.loads(line)
                cell = (int(r["true_positives"]), int(r["finding_count"]))
                agg[(r["model"], cond, r["difficulty"])].append(cell)
                agg[(r["model"], cond, "ALL")].append(cell)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    header = "auditor,condition," + ",".join(f"{d}_recall,{d}_prec,{d}_n" for d in DIFFS)
    lines = [header]
    for model in MODELS:
        for cond in ("default", "constraint"):
            cells = []
            for d in DIFFS:
                v = agg.get((model, cond, d), [])
                n = len(v)
                tp = sum(a for a, _ in v)
                fc = sum(b for _, b in v)
                rec = tp / n if n else 0.0
                prec = tp / fc if fc else 0.0
                cells.append(f"{rec:.3f},{prec:.3f},{n}")
            lines.append(f"{model},{cond}," + ",".join(cells))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}\n")

    # headline: L1 recall (and precision) default -> constraint per model
    print(f"{'auditor':<26}{'L1 default':>22}{'L1 constraint':>22}")
    for model in MODELS:
        d = agg.get((model, "default", "L1"), [])
        c = agg.get((model, "constraint", "L1"), [])
        if not (d and c):
            print(f"{model:<26}{'(missing)':>22}")
            continue
        dr, dp = sum(a for a, _ in d) / len(d), (sum(b for _, b in d) or 0)
        cr, cp = sum(a for a, _ in c) / len(c), (sum(b for _, b in c) or 0)
        dprec = sum(a for a, _ in d) / dp if dp else 0.0
        cprec = sum(a for a, _ in c) / cp if cp else 0.0
        print(f"{model:<26}{f'r={dr:.2f} p={dprec:.2f} (n={len(d)})':>22}"
              f"{f'r={cr:.2f} p={cprec:.2f} (n={len(c)})':>22}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
