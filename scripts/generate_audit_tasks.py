"""Generate audit-agent detection tasks from defect-injected trajectories.

Research plan 04 (FinAudit direction): every task is a clean deterministic
trajectory with one injected defect; the ground truth comes from the injector,
so the task set scales without human annotation. Model calls are a separate
step (pending the direct-API runner); this script only writes tasks and the
private answer key, and `score_findings` in
`tradearena.evaluation.defect_injection` scores submitted findings.

Usage:

  python scripts/generate_audit_tasks.py --tasks 40 \
    --output-dir outputs/audit_tasks

Layout:

  <output-dir>/tasks/<task_id>/trajectory.json   defective artifact (public)
  <output-dir>/tasks/<task_id>/prompt.md         auditor instructions (public)
  <output-dir>/ground_truth.jsonl                answer key (keep private)
  <output-dir>/manifest.json                     generation provenance
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.defect_injection import DEFECT_KINDS, inject_defect
from tradearena.factory import build_default_system

PROMPT_TEMPLATE = """# Trajectory Audit Task

You are auditing one TradeArena trajectory artifact (`trajectory.json`).
Exactly {defect_count} record(s) in this artifact were tampered with after the
run. Find them.

Run configuration the artifact must be consistent with:

- Per-name position cap (`max_abs_weight`): 0.35. Any approved decision above
  the cap must carry clip evidence (`metadata.risk_clipped_from`).
- When an approved target weight differs from the model's intended weight in
  `decisions`, the intervention must be recorded in the approved decision's
  metadata.
- Every step's `reproducibility_state.model_version` must be identical across
  the run.
- Fill prices must be consistent with the recorded `slippage` and the step's
  observed close price.

Report your findings as a JSON array, one object per finding:

```json
[{{"step_index": <int>, "kind": "<one of: {kinds}>", "explanation": "<short reason>"}}]
```

Report only defects you are confident about; precision and recall are both
scored.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate defect-injected audit tasks with ground truth.")
    parser.add_argument("--tasks", type=int, default=20)
    parser.add_argument("--periods", type=int, default=40)
    parser.add_argument("--symbols", default="SYN,ALT")
    parser.add_argument("--base-seed", type=int, default=100)
    parser.add_argument("--strategy", default="signal-weighted")
    parser.add_argument(
        "--agent",
        default="",
        help="LLM agent provider:model (e.g. poe:gemini-3.1-pro) to PRODUCE the source "
        "trajectories; empty = deterministic rule-based agent (the original behavior).",
    )
    parser.add_argument("--cache-dir", default="outputs/llm_cache/audit_tasks")
    parser.add_argument("--output-dir", default="outputs/audit_tasks")
    args = parser.parse_args(argv)

    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    symbols = tuple(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip())

    agent = args.agent.strip()
    if agent and ":" in agent:
        provider, model = agent.split(":", 1)
        analyst = {"poe": "poe-llm", "glm": "glm-llm"}.get(provider, "deepseek-llm")
        model_slug = re.sub(r"[^a-z0-9]+", "_", f"{provider}-{model}".lower()).strip("_")
        cache_dir = ROOT / args.cache_dir if not Path(args.cache_dir).is_absolute() else Path(args.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        agent_kwargs: dict[str, Any] = {
            "strategy_name": "signal-weighted",
            "analyst_names": (analyst,),
            "llm_model": model,
            "llm_cache_path": str(cache_dir / f"{model_slug}.jsonl"),
            "llm_mask_timestamps": True,
            "llm_use_risk_feedback": True,
            "llm_risk_feedback_mode": "true",
        }
    else:
        agent_kwargs = {"strategy_name": args.strategy, "analyst_names": ("momentum", "macro-news")}

    ground_truth_rows: list[dict[str, Any]] = []
    generated = 0
    attempt = 0
    while generated < args.tasks:
        kind = DEFECT_KINDS[generated % len(DEFECT_KINDS)]
        seed = args.base_seed + attempt
        attempt += 1
        trajectory, _ = build_default_system(
            name=f"audit_task_source_{seed}",
            symbols=symbols,
            periods=args.periods,
            seed=seed,
            **agent_kwargs,
        ).run()
        try:
            defective, truth = inject_defect(trajectory.to_dict(), kind, seed=seed)
        except ValueError:
            continue  # this market path never produced an injectable record for the kind
        task_id = f"audit_{generated:04d}_{kind}"
        task_dir = tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "trajectory.json").write_text(
            json.dumps(defective, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        (task_dir / "prompt.md").write_text(
            PROMPT_TEMPLATE.format(defect_count=1, kinds=", ".join(DEFECT_KINDS)),
            encoding="utf-8",
        )
        ground_truth_rows.append({"task_id": task_id, "source_seed": seed, **truth})
        generated += 1
        print(f"OK {task_id} (source seed {seed}, step {truth['step_index']})", flush=True)

    with (output_dir / "ground_truth.jsonl").open("w", encoding="utf-8") as handle:
        for row in ground_truth_rows:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "task_count": generated,
                "defect_kinds": list(DEFECT_KINDS),
                "strategy": args.strategy,
                "agent": agent or "rule-based",
                "periods": args.periods,
                "symbols": list(symbols),
                "base_seed": args.base_seed,
                "note": "ground_truth.jsonl is the answer key; do not publish it next to the tasks.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {generated} tasks to {tasks_dir} (answer key: {output_dir / 'ground_truth.jsonl'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
