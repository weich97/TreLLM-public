"""Generate the TRADING paired ambiguity experiment (audit study).

Turns the observational clean/confounded split into a controlled one. For every
unclipped_position task in the producer sets, emit two variants of the SAME
defective trajectory that differ only in the agent's recorded intent for the
defective symbol:

- clean variant:      intent := the injected approved weight (pure breach)
- confounded variant: intent  = an under-cap value != approved (breach that also
                      reads as a silent edit)

Whichever variant equals the existing task is written byte-identically under the
ORIGINAL task id, so the audit runner's (task_id, prompt-hash) cache replays the
already-collected default-cell responses for all four auditors at zero cost;
only the edited sibling (suffix ``_alt``) needs fresh calls. Within-pair recall
comparison is then a matched-pairs test of the ambiguity effect.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCERS = ["deepseek_v4_pro", "glm_5_direct"]
EPS = 1e-9


def load_gt(producer: str) -> list[dict]:
    rows = []
    with (ROOT / f"outputs/audit_self/{producer}/ground_truth.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rows.append(json.loads(line))
    return rows


def weights(step: dict, key: str, symbol: str) -> tuple[int, float] | None:
    """(index, target_weight) of the entry for ``symbol`` in step[key]."""
    for i, d in enumerate(step.get(key, [])):
        if d.get("symbol") == symbol and d.get("target_weight") is not None:
            return i, float(d["target_weight"])
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate paired trading ambiguity tasks.")
    parser.add_argument("--output-root", default="outputs/audit_pairs")
    args = parser.parse_args(argv)

    for producer in PRODUCERS:
        src_root = ROOT / f"outputs/audit_self/{producer}"
        out = ROOT / args.output_root / producer
        tasks_dir = out / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        gt_lines: list[str] = []
        pairs = 0
        for gt in load_gt(producer):
            if gt["kind"] != "unclipped_position":
                continue
            task_id = gt["task_id"]
            symbol = gt["detail"]["symbol"]
            original_weight = float(gt["detail"]["original_target_weight"])
            src_task = src_root / "tasks" / task_id
            traj = json.loads((src_task / "trajectory.json").read_text(encoding="utf-8"))
            step = traj["steps"][gt["step_index"]]

            approved = weights(step, "approved_decisions", symbol)
            intent = weights(step, "decisions", symbol)
            if approved is None or intent is None:
                print(f"skip {producer}/{task_id}: missing intent or approved entry")
                continue
            _, approved_w = approved
            intent_idx, intent_w = intent
            base_is_clean = abs(intent_w - approved_w) <= EPS

            # counterfactual intent for the edited sibling: the injected approved
            # weight if the base is confounded, else the pre-injection approved
            # weight (always under the cap, never equal to the injected value).
            alt_intent = approved_w if not base_is_clean else original_weight
            alt = copy.deepcopy(traj)
            alt["steps"][gt["step_index"]]["decisions"][intent_idx]["target_weight"] = alt_intent

            alt_id = f"{task_id}_alt"
            for tid, is_copy, payload in ((task_id, True, None), (alt_id, False, alt)):
                tdir = tasks_dir / tid
                tdir.mkdir(parents=True, exist_ok=True)
                if is_copy:  # byte-identical so the response cache replays
                    shutil.copyfile(src_task / "trajectory.json", tdir / "trajectory.json")
                else:
                    (tdir / "trajectory.json").write_text(json.dumps(payload), encoding="utf-8")
                shutil.copyfile(src_task / "prompt.md", tdir / "prompt.md")

            base_amb = "clean" if base_is_clean else "confounded"
            alt_amb = "confounded" if base_is_clean else "clean"
            for tid, amb in ((task_id, base_amb), (alt_id, alt_amb)):
                gt_lines.append(json.dumps({
                    "task_id": tid,
                    "kind": gt["kind"],
                    "difficulty": gt["difficulty"],
                    "step_index": gt["step_index"],
                    "detail": {**gt["detail"], "ambiguity": amb, "pair_id": task_id},
                }))
            pairs += 1

        (out / "ground_truth.jsonl").write_text("\n".join(gt_lines) + "\n", encoding="utf-8")
        print(f"{producer}: wrote {pairs} pairs ({2 * pairs} tasks) to {tasks_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
