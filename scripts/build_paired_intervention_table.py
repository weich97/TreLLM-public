"""Paired-intervention analysis (audit study): does the one-line constraint
instruction repair the confounded twins the auditors failed by default?

Joins the default and constraint-prompt audits of the SAME matched trading
pairs and reports, per auditor: confounded-arm recall default vs with the
instruction (within-pair McNemar exact on the flip), and the clean-arm recall
under the instruction (checking the fix costs nothing on unambiguous
violations). Writes docs/results/finaudit/paired_intervention.csv.
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/results/finaudit/paired_intervention.csv"
PRODUCERS = ("deepseek_v4_pro", "glm_5_direct")
MODELS = ["deepseek:deepseek-v4-pro", "glm:glm-5", "poe:claude-opus-4.7", "poe:gemini-3.1-pro"]


def load_hits(tree: str, producer: str) -> dict[tuple[str, str], int]:
    path = ROOT / f"outputs/{tree}/{producer}/audit_eval_results.jsonl"
    out: dict[tuple[str, str], int] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            out[(r["model"], r["task_id"])] = int(r["true_positives"])
    return out


def main() -> int:
    gt: dict[tuple[str, str], dict] = {}
    for p in PRODUCERS:
        with (ROOT / f"outputs/audit_pairs/{p}/ground_truth.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                gt[(p, r["task_id"])] = r

    default: dict[tuple[str, str, str], int] = {}
    constraint: dict[tuple[str, str, str], int] = {}
    for p in PRODUCERS:
        default.update({(p, m, t): v for (m, t), v in load_hits("audit_pairs_eval", p).items()})
        constraint.update({(p, m, t): v for (m, t), v in load_hits("audit_pairs_eval_constraint", p).items()})

    rows = []
    for model in MODELS:
        cells: dict[tuple[str, str], dict[str, dict[str, int]]] = collections.defaultdict(dict)
        for source, tag in ((default, "d"), (constraint, "c")):
            for (p, m, tid), hit in source.items():
                if m != model:
                    continue
                g = gt[(p, tid)]
                cells[(p, g["detail"]["pair_id"])].setdefault(g["detail"]["ambiguity"], {})[tag] = hit
        conf = [v["confounded"] for v in cells.values()
                if {"d", "c"} <= set(v.get("confounded", {}))]
        clean = [v["clean"] for v in cells.values() if "c" in v.get("clean", {})]
        d_rec = sum(x["d"] for x in conf) / len(conf)
        c_rec = sum(x["c"] for x in conf) / len(conf)
        cl_rec = sum(x["c"] for x in clean) / len(clean)
        fixed = sum(1 for x in conf if x["c"] == 1 and x["d"] == 0)
        broken = sum(1 for x in conf if x["c"] == 0 and x["d"] == 1)
        p_val = float(stats.binomtest(fixed, fixed + broken, 0.5).pvalue) if fixed + broken else float("nan")
        rows.append({
            "auditor": model, "n_confounded": len(conf),
            "confounded_default": f"{d_rec:.3f}", "confounded_constraint": f"{c_rec:.3f}",
            "clean_constraint": f"{cl_rec:.3f}",
            "fixed_pairs": fixed, "regressed_pairs": broken, "mcnemar_p": f"{p_val:.3g}",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in rows:
        print(f"{r['auditor']:26s} conf {r['confounded_default']}->{r['confounded_constraint']}"
              f" clean {r['clean_constraint']} McNemar p={r['mcnemar_p']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
