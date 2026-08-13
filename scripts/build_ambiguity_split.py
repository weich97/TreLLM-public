"""The core result of the reframed audit study: constraint-violation recall split by
whether the injected over-limit is UNAMBIGUOUS or is also confusable with a
cross-record silent edit.

An unclipped_position defect sets an approved value over its cap. The injector
does not touch the model's intent, so when the original intent differs from the
injected approved value the step ALSO reads as a silent intervention edit
(approved != intent, no record). We classify each L1 task as:

- clean:      approved == intent  -> the defect is only a constraint violation.
- confounded: approved != intent  -> it is both a violation and a silent edit.

and report, per auditor, the constraint-violation recall on each subset. Strong
overseers are robust to the ambiguity; weak ones collapse on the confounded
subset -- they resolve the ambiguity toward the inconsistency label. Reads the
default-prompt cells (both direct and routed auditors), which are stable.

Statistics: a per-auditor Fisher exact test (clean vs confounded x hit vs miss)
and a pooled tier-x-ambiguity interaction test -- under H0 (hit rate independent
of subset within each auditor) the clean-subset hit count is hypergeometric, so
we Monte-Carlo the null of T = mean(weak drop) - mean(strong drop).
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

WEAK = ["deepseek:deepseek-v4-pro", "glm:glm-5"]
STRONG = ["poe:claude-opus-4.7", "poe:gemini-3.1-pro"]

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "results" / "finaudit" / "ambiguity_split.csv"
TREES = ["audit_intervention", "audit_intervention_poe"]
ORDER = ["poe:gpt-5.5", "poe:claude-opus-4.7", "poe:gemini-3.1-pro",
         "deepseek:deepseek-v4-pro", "glm:glm-5"]


def classify(producer: str, task_id: str, step_index: int, symbol: str) -> str:
    traj = json.loads((ROOT / f"outputs/audit_self/{producer}/tasks/{task_id}/trajectory.json").read_text(encoding="utf-8"))
    step = traj["steps"][step_index]
    intent = {d.get("symbol"): d.get("target_weight") for d in step.get("decisions", [])}.get(symbol)
    approved = {d.get("symbol"): d.get("target_weight") for d in step.get("approved_decisions", [])}.get(symbol)
    if intent is None or approved is None:
        return "unknown"
    return "confounded" if abs(float(intent) - float(approved)) > 1e-9 else "clean"


def main() -> int:
    gt: dict[tuple[str, str], dict] = {}
    for p in ("deepseek_v4_pro", "glm_5_direct"):
        for line in (ROOT / f"outputs/audit_self/{p}/ground_truth.jsonl").open(encoding="utf-8"):
            r = json.loads(line)
            gt[(p, r["task_id"])] = r

    agg: dict[tuple[str, str], list[int]] = collections.defaultdict(lambda: [0, 0])
    for tree in TREES:
        for cell in (ROOT / "outputs" / tree).glob("*_default"):
            producer = cell.name[: -len("_default")]
            rp = cell / "audit_eval_results.jsonl"
            if not rp.exists():
                continue
            for line in rp.open(encoding="utf-8"):
                r = json.loads(line)
                if r["difficulty"] != "L1":
                    continue
                g = gt.get((producer, r["task_id"]))
                if not g:
                    continue
                subset = classify(producer, r["task_id"], g["step_index"], g["detail"].get("symbol"))
                if subset == "unknown":
                    continue
                agg[(r["model"], subset)][0] += int(r["true_positives"])
                agg[(r["model"], subset)][1] += 1

    models = [m for m in ORDER if (m, "clean") in agg or (m, "confounded") in agg]

    def cells(m: str) -> tuple[int, int, int, int]:
        cl_tp, cl_n = agg[(m, "clean")]
        co_tp, co_n = agg[(m, "confounded")]
        return cl_tp, cl_n, co_tp, co_n

    fisher: dict[str, float] = {}
    for m in models:
        cl_tp, cl_n, co_tp, co_n = cells(m)
        table = [[cl_tp, cl_n - cl_tp], [co_tp, co_n - co_tp]]
        fisher[m] = float(stats.fisher_exact(table, alternative="two-sided")[1])

    # Interaction: is the weak tier's ambiguity drop larger than the strong tier's?
    # Under H0 each auditor's clean-subset hits are Hypergeom(N, total_hits, n_clean).
    rng = np.random.default_rng(0)
    draws = 200_000
    null_t = np.zeros(draws)
    obs_t = 0.0
    for m in WEAK + STRONG:
        cl_tp, cl_n, co_tp, co_n = cells(m)
        total, hits = cl_n + co_n, cl_tp + co_tp
        sign = 1.0 if m in WEAK else -1.0
        obs_t += sign * ((cl_tp / cl_n) - (co_tp / co_n)) / 2.0
        sim_cl = rng.hypergeometric(hits, total - hits, cl_n, size=draws)
        null_t += sign * (sim_cl / cl_n - (hits - sim_cl) / co_n) / 2.0
    p_interaction = float((np.abs(null_t) >= abs(obs_t) - 1e-12).mean())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["auditor", "clean_recall", "clean_n", "confounded_recall",
                    "confounded_n", "ambiguity_drop", "fisher_p"])
        for m in models:
            cl_tp, cl_n, co_tp, co_n = cells(m)
            cl = cl_tp / cl_n if cl_n else 0.0
            co = co_tp / co_n if co_n else 0.0
            w.writerow([m, f"{cl:.3f}", cl_n, f"{co:.3f}", co_n, f"{cl - co:+.3f}", f"{fisher[m]:.4g}"])
        w.writerow(["interaction_weak_vs_strong_drop", "", "", "", "",
                    f"{obs_t:+.3f}", f"{p_interaction:.4g}"])

    print(f"wrote {OUT.relative_to(ROOT)}\n")
    print(f"{'auditor':26s}{'clean':>14s}{'confounded':>14s}{'drop':>8s}{'Fisher p':>12s}")
    for m in models:
        cl_tp, cl_n, co_tp, co_n = cells(m)
        cl = cl_tp / cl_n if cl_n else 0.0
        co = co_tp / co_n if co_n else 0.0
        print(f"{m:26s}{f'{cl:.2f}({cl_n})':>14s}{f'{co:.2f}({co_n})':>14s}{cl - co:>+8.2f}{fisher[m]:>12.4g}")
    print(f"\ninteraction (mean weak drop - mean strong drop) = {obs_t:+.3f}, "
          f"Monte-Carlo p = {p_interaction:.4g} ({draws:,} draws)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
