"""Intervention-ablation family (audit study): default vs constraint vs cot vs
self-consistency on the matched trading pairs, direct-API auditors.

The constraint variant names the check to run ("verify approvals against
caps"); the cot variant asks for generic step-by-step deliberation and never
names constraints; self-consistency majority-votes three temperature-0.7
samples of the default prompt. Comparing the three against the default run
separates "any extra thinking helps" from "the prompt must point at the rule".

Confounded/clean recall per variant, within-pair McNemar (exact binomial on
discordant pairs) vs default on the confounded arm. Writes
docs/results/finaudit/ablation_family.csv.
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/results/finaudit/ablation_family.csv"
PRODUCERS = ("deepseek_v4_pro", "glm_5_direct")
MODELS = ["deepseek:deepseek-v4-pro", "glm:glm-5"]
VARIANTS = {
    "default": "audit_pairs_eval",
    "constraint": "audit_pairs_eval_constraint",
    "cot": "audit_pairs_eval_cot",
    "selfcons": "audit_pairs_eval_sc",
}


def load_hits(tree: str, producer: str, vote: bool) -> dict[tuple[str, str], int]:
    """(model, task_id) -> 0/1 hit; majority vote over samples when vote=True."""
    path = ROOT / f"outputs/{tree}/{producer}/audit_eval_results.jsonl"
    samples: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            samples[(r["model"], r["task_id"])].append(1 if int(r["true_positives"]) > 0 else 0)
    if vote:
        return {k: (1 if sum(v) * 2 > len(v) else 0) for k, v in samples.items()}
    return {k: v[0] for k, v in samples.items()}


def main() -> int:
    gt: dict[tuple[str, str], dict] = {}
    for p in PRODUCERS:
        with (ROOT / f"outputs/audit_pairs/{p}/ground_truth.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                gt[(p, r["task_id"])] = r

    hits: dict[str, dict[tuple[str, str, str], int]] = {}
    for name, tree in VARIANTS.items():
        hits[name] = {}
        for p in PRODUCERS:
            hits[name].update(
                {(p, m, t): v for (m, t), v in load_hits(tree, p, vote=name == "selfcons").items()}
            )

    rows = []
    for model in MODELS:
        cells: dict[tuple[str, str], dict[str, dict[str, int]]] = collections.defaultdict(dict)
        for name, source in hits.items():
            for (p, m, tid), hit in source.items():
                if m != model:
                    continue
                g = gt[(p, tid)]
                cells[(p, g["detail"]["pair_id"])].setdefault(g["detail"]["ambiguity"], {})[name] = hit
        for name in VARIANTS:
            conf = [v["confounded"] for v in cells.values()
                    if {"default", name} <= set(v.get("confounded", {}))]
            clean = [v["clean"] for v in cells.values() if name in v.get("clean", {})]
            conf_rec = sum(x[name] for x in conf) / len(conf)
            clean_rec = sum(x[name] for x in clean) / len(clean)
            fixed = sum(1 for x in conf if x[name] == 1 and x["default"] == 0)
            broken = sum(1 for x in conf if x[name] == 0 and x["default"] == 1)
            if name == "default":
                p_val = float("nan")
            else:
                p_val = float(stats.binomtest(fixed, fixed + broken, 0.5).pvalue) if fixed + broken else 1.0
            rows.append({
                "auditor": model, "variant": name, "n_pairs": len(conf),
                "confounded_recall": f"{conf_rec:.3f}", "clean_recall": f"{clean_rec:.3f}",
                "fixed_pairs": fixed, "regressed_pairs": broken,
                "mcnemar_p": "" if name == "default" else f"{p_val:.3g}",
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in rows:
        extra = f" fixed={r['fixed_pairs']} regr={r['regressed_pairs']} p={r['mcnemar_p']}" if r["mcnemar_p"] else ""
        print(f"{r['auditor']:26s} {r['variant']:10s} conf={r['confounded_recall']} "
              f"clean={r['clean_recall']}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
