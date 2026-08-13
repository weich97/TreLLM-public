"""Generate the tool-use PAIRED ambiguity experiment (audit study).

Each pair is two variants of the same trajectory and same defective step, both
with the same over-cap approved value and no clip record, differing ONLY in the
requested argument: clean (requested == approved, an unambiguous breach) vs
confounded (requested keeps its under-cap value, so the defect also reads as a
silent edit). Within-pair comparison of over_limit_call recall is therefore a
controlled test of the ambiguity effect -- the confounded pole the trading
domain could only measure observationally.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradearena.evaluation.toolaudit import (
    constraints_text,
    generate_trajectory,
    inject_over_limit_pair,
)

_spec = importlib.util.spec_from_file_location(
    "generate_toolaudit_tasks", ROOT / "scripts" / "generate_toolaudit_tasks.py"
)
assert _spec and _spec.loader
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)
PROMPT = _gen.PROMPT  # identical auditor instructions as the main tool-use benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate paired tool-use ambiguity tasks.")
    parser.add_argument("--pairs", type=int, default=40)
    parser.add_argument("--base-seed", type=int, default=9000)
    parser.add_argument("--output-dir", default="outputs/toolaudit_pairs")
    args = parser.parse_args(argv)

    out = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    tasks_dir = out / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    gt_lines: list[str] = []
    made = 0
    seed = args.base_seed
    while made < args.pairs:
        trajectory = generate_trajectory(seed)
        try:
            (clean, gt_clean), (conf, gt_conf) = inject_over_limit_pair(trajectory, seed=seed)
        except ValueError:
            seed += 1
            continue
        pair_id = f"pair_{made:04d}"
        for variant, (defective, gt) in (("clean", (clean, gt_clean)), ("conf", (conf, gt_conf))):
            task_id = f"{pair_id}_{variant}"
            tdir = tasks_dir / task_id
            tdir.mkdir(parents=True, exist_ok=True)
            (tdir / "trajectory.json").write_text(json.dumps(defective), encoding="utf-8")
            (tdir / "prompt.md").write_text(
                PROMPT.format(constraints=constraints_text(defective)), encoding="utf-8"
            )
            gt_lines.append(json.dumps({
                "task_id": task_id,
                "kind": gt["kind"],
                "difficulty": gt["difficulty"],
                "step_index": gt["step_index"],
                "detail": {**gt["detail"], "pair_id": pair_id},
            }))
        made += 1
        seed += 1

    (out / "ground_truth.jsonl").write_text("\n".join(gt_lines) + "\n", encoding="utf-8")
    print(f"wrote {made} pairs ({2 * made} tasks) to {tasks_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
