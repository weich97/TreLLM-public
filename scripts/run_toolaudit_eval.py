"""Run LLM auditors on the tool-use second-domain benchmark (audit study).

Same evaluation protocol as run_audit_eval.py but on the tool-use substrate: the
overseer receives the run's stated constraints and a compact action log and
returns JSON findings, scored against the injected defect. Reuses the trading
eval's model transport (caching), finding parser, and summary writer; supplies a
tool-use compact view. Resumable: checkpoints per (model, task, sample).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("run_audit_eval", ROOT / "scripts" / "run_audit_eval.py")
assert _spec and _spec.loader
run_audit_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_audit_eval)

from tradearena.evaluation.defect_injection import score_findings
from tradearena.evaluation.toolaudit import tool_compact_view

COMPACT_NOTE = (
    "The action log below is the run's compact view: per step it lists the tool, "
    "the requested and approved arguments, the approval metadata, the result, the "
    "tool_version, and any recorded policy flags."
)


def build_prompt(task_dir: Path) -> str:
    instructions = (task_dir / "prompt.md").read_text(encoding="utf-8")
    trajectory = json.loads((task_dir / "trajectory.json").read_text(encoding="utf-8"))
    compact = tool_compact_view(trajectory)
    return (
        f"{instructions}\n\n{COMPACT_NOTE}\n\n```json\n"
        + json.dumps(compact, sort_keys=True, default=str)
        + "\n```\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate LLM auditors on the tool-use benchmark.")
    parser.add_argument("--tasks-dir", default="outputs/toolaudit_tasks")
    parser.add_argument("--models", default="deepseek:deepseek-v4-pro")
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--samples-per-task", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--cache-dir", default="outputs/llm_cache/toolaudit_eval")
    parser.add_argument("--output-dir", default="outputs/toolaudit_eval")
    args = parser.parse_args(argv)

    tasks_root = ROOT / args.tasks_dir if not Path(args.tasks_dir).is_absolute() else Path(args.tasks_dir)
    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    cache_dir = ROOT / args.cache_dir if not Path(args.cache_dir).is_absolute() else Path(args.cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    truth_by_task: dict[str, dict[str, Any]] = {}
    with (tasks_root / "ground_truth.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            truth_by_task[row["task_id"]] = row
    task_dirs = sorted(p for p in (tasks_root / "tasks").iterdir() if p.is_dir())
    if args.max_tasks:
        task_dirs = task_dirs[: args.max_tasks]

    results_path = output_dir / "toolaudit_eval_results.jsonl"
    done: set[tuple[str, str, int]] = set()
    if results_path.exists():
        with results_path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                done.add((row["model"], row["task_id"], int(row.get("sample", 0))))
    if done:
        print(f"Resuming: {len(done)} (model, task, sample) results already checkpointed", flush=True)

    samples = max(1, int(args.samples_per_task))
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    with results_path.open("a", encoding="utf-8") as results_handle:
        for spec in models:
            provider, model = spec.split(":", 1)
            for task_dir in task_dirs:
                task_id = task_dir.name
                truth = truth_by_task[task_id]
                prompt = build_prompt(task_dir)
                for sample in range(samples):
                    if (spec, task_id, sample) in done:
                        continue
                    try:
                        response = run_audit_eval.call_model(
                            provider, model, prompt, cache_dir, task_id,
                            sample=sample, temperature=args.temperature,
                        )
                    except Exception as exc:  # provider failures should not lose the run
                        print(f"FAILED {spec} {task_id} s{sample}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                        continue
                    findings = run_audit_eval.parse_findings(response)
                    scores = score_findings(findings, [truth])
                    record = {
                        "model": spec,
                        "task_id": task_id,
                        "sample": sample,
                        "kind": truth["kind"],
                        "difficulty": truth["difficulty"],
                        "parsed": bool(findings) or "[]" in response,
                        "true_positives": scores["true_positives"],
                        "precision": scores["precision"],
                        "recall": scores["recall"],
                        "f1": scores["f1"],
                        "finding_count": len(findings),
                        "findings": findings,
                    }
                    results_handle.write(json.dumps(record, sort_keys=True) + "\n")
                    results_handle.flush()
                    print(f"OK {spec} {task_id} s{sample} recall={scores['recall']:.0%}", flush=True)

    run_audit_eval._write_summary(results_path, output_dir / "toolaudit_eval_summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
