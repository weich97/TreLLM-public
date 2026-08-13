"""Analyze the paired ambiguity experiments (audit study): tool-use and trading.

For each domain and auditor: recall of the injected constraint violation on the
clean vs confounded arm, the within-pair McNemar exact test (binomial on
discordant pairs -- the matched-pairs analogue of the observational split's
Fisher test), and, on confounded misses, the fraction mislabeled as the domain's
silent-edit kind at the exact defective step (the mechanism signature).
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["deepseek:deepseek-v4-pro", "glm:glm-5", "poe:claude-opus-4.7", "poe:gemini-3.1-pro"]

DOMAINS = {
    "toolaudit": {
        "gt": [ROOT / "outputs/toolaudit_pairs/ground_truth.jsonl"],
        "results": [ROOT / "outputs/toolaudit_pairs_eval/toolaudit_eval_results.jsonl"],
        "edit_kind": "silent_arg_edit",
        "out": ROOT / "docs/results/finaudit/paired_toolaudit.csv",
    },
    "trading": {
        "gt": [ROOT / f"outputs/audit_pairs/{p}/ground_truth.jsonl"
               for p in ("deepseek_v4_pro", "glm_5_direct")],
        "results": [ROOT / f"outputs/audit_pairs_eval/{p}/audit_eval_results.jsonl"
                    for p in ("deepseek_v4_pro", "glm_5_direct")],
        "edit_kind": "silent_risk_edit",
        "out": ROOT / "docs/results/finaudit/paired_trading.csv",
    },
}


def analyze(name: str, spec: dict) -> None:
    # task ids repeat across producers, so ground truth stays scoped to the
    # results file it was generated with.
    pair_cells: dict[tuple[str, str], dict[str, tuple[int, list, dict]]] = collections.defaultdict(dict)
    for gt_path, res_path in zip(spec["gt"], spec["results"]):
        if not gt_path.exists() or not res_path.exists():
            continue
        gt: dict[str, dict] = {}
        for line in gt_path.open(encoding="utf-8"):
            row = json.loads(line)
            gt[row["task_id"]] = row
        for line in res_path.open(encoding="utf-8"):
            r = json.loads(line)
            g = gt.get(r["task_id"])
            if not g or r["model"] not in MODELS:
                continue
            key = (r["model"], f"{res_path}:{g['detail']['pair_id']}")
            pair_cells[key][g["detail"]["ambiguity"]] = (int(r["true_positives"]), r["findings"], g)

    rows = []
    for model in MODELS:
        n = {"clean": 0, "confounded": 0}
        tp = {"clean": 0, "confounded": 0}
        discordant_cm = discordant_mc = 0  # clean-hit/conf-miss and the reverse
        conf_misses = conf_mislabels = 0
        for (m, _pid), cells in pair_cells.items():
            if m != model:
                continue
            for amb, (hit, _f, _g) in cells.items():
                n[amb] += 1
                tp[amb] += hit
                if amb == "confounded" and not hit:
                    conf_misses += 1
                    step = _g["step_index"]
                    if any(f.get("kind") == spec["edit_kind"] and f.get("step_index") == step
                           for f in _f):
                        conf_mislabels += 1
            if len(cells) == 2:  # complete pair -> McNemar cell
                ch = cells["clean"][0]
                ah = cells["confounded"][0]
                discordant_cm += int(ch == 1 and ah == 0)
                discordant_mc += int(ch == 0 and ah == 1)
        if not n["clean"] and not n["confounded"]:
            continue
        cl = tp["clean"] / n["clean"] if n["clean"] else float("nan")
        co = tp["confounded"] / n["confounded"] if n["confounded"] else float("nan")
        disc = discordant_cm + discordant_mc
        mcnemar_p = float(stats.binomtest(discordant_cm, disc, 0.5).pvalue) if disc else float("nan")
        mis = conf_mislabels / conf_misses if conf_misses else float("nan")
        rows.append({
            "auditor": model,
            "clean_recall": f"{cl:.3f}", "clean_n": n["clean"],
            "confounded_recall": f"{co:.3f}", "confounded_n": n["confounded"],
            "drop": f"{cl - co:+.3f}",
            "discordant_clean_hit": discordant_cm, "discordant_conf_hit": discordant_mc,
            "mcnemar_p": f"{mcnemar_p:.4g}",
            "conf_miss_mislabel_rate": f"{mis:.3f}" if mis == mis else "",
        })

    spec["out"].parent.mkdir(parents=True, exist_ok=True)
    with spec["out"].open("w", newline="", encoding="utf-8") as fh:
        if rows:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"\n[{name}] wrote {spec['out'].relative_to(ROOT)}")
    print(f"{'auditor':26s}{'clean':>12s}{'confound':>12s}{'drop':>8s}{'McNemar p':>12s}{'mislabel':>10s}")
    for r in rows:
        print(f"{r['auditor']:26s}{r['clean_recall']+'('+str(r['clean_n'])+')':>12s}"
              f"{r['confounded_recall']+'('+str(r['confounded_n'])+')':>12s}{r['drop']:>8s}"
              f"{r['mcnemar_p']:>12s}{r['conf_miss_mislabel_rate']:>10s}")


def main() -> int:
    for name, spec in DOMAINS.items():
        analyze(name, spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
