"""Generate claim-boundary review tasks from violation templates.

Research plan 04, task family T2: given an evidence context (execution mode,
seed count, provider mode, data source), judge whether each candidate claim
stays inside the evidence boundary and assign its claim-ladder level
(engineering / benchmark / scientific / execution-realism, per
docs/claim_boundaries.md). Tasks are template-generated with parameterized
numbers, so the bank scales without human annotation; every claim carries a
machine-checkable label.

Auditors answer with structured JSON (one object per claim):

  [{"claim_index": 1, "claim_level": "engineering", "supported": true}]

`score_claim_answers` grades label accuracy and boundary judgments.

Usage:

  python scripts/generate_claim_boundary_tasks.py --tasks 25 \
    --output-dir outputs/claim_boundary_tasks
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CLAIM_LEVELS = ("engineering", "benchmark", "scientific", "execution-realism")

MODELS = ("model-aurora", "model-bedrock", "model-cypress", "model-dorado")
SYMBOLS = ("SYN", "ALT", "GSPC", "BTC-USD")


def _violation_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": "stress_to_calibrated",
            "level": "execution-realism",
            "text": lambda ctx, rng: (
                f"The run shows that live trading costs for {rng.choice(SYMBOLS)} are about "
                f"{rng.randrange(8, 40)} bps per trade."
            ),
            "why_unsupported": "Default rows use the stress simulator; transaction-cost claims need quote/fill calibration evidence.",
        },
        {
            "id": "insufficient_repeats",
            "level": "scientific",
            "text": lambda ctx, rng: (
                f"{rng.choice(MODELS)} significantly outperforms buy-and-hold on this benchmark "
                f"(+{rng.randrange(3, 12)}% vs +{rng.randrange(0, 3)}%, {ctx['seeds']} seed run)."
            ),
            "why_unsupported": "Significance needs repeated seeds with confidence intervals; the exact permutation test cannot reject at all below six paired seeds.",
        },
        {
            "id": "cached_provider_overreach",
            "level": "scientific",
            "text": lambda ctx, rng: (
                f"Because the cached {rng.choice(MODELS)} row ranks first, it is the most capable "
                "trading model among those tested."
            ),
            "why_unsupported": "Cached-provider rows are reliability probes; model-skill rankings need version-pinned repeated sampling.",
        },
        {
            "id": "synthetic_to_real",
            "level": "scientific",
            "text": lambda ctx, rng: (
                f"The agent's {rng.randrange(4, 18)}% return in the synthetic "
                f"{rng.choice(['high-volatility', 'jump-tail', 'liquidity-collapse'])} regime shows it "
                "would be profitable in real markets."
            ),
            "why_unsupported": "Synthetic-regime results do not transfer to real-market profitability claims.",
        },
        {
            "id": "live_readiness_overreach",
            "level": "engineering",
            "text": lambda ctx, rng: (
                "The risk gate makes the agent safe for unattended live trading with real funds."
            ),
            "why_unsupported": "Risk checks are audit records, not a regulatory safety system; no unattended-live claim is supported.",
        },
    ]


def _control_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": "trajectory_engineering",
            "level": "engineering",
            "text": lambda ctx, rng: (
                "The run records every decision as a replayable intent-to-execution trajectory "
                "with reproducibility hashes."
            ),
        },
        {
            "id": "shared_stress_benchmark",
            "level": "benchmark",
            "text": lambda ctx, rng: (
                f"Under the shared stress simulator and identical risk budget, the two agents' fill rates "
                f"({rng.randrange(80, 95)}% vs {rng.randrange(60, 80)}%) are directly comparable."
            ),
        },
        {
            "id": "calibration_narrow",
            "level": "engineering",
            "text": lambda ctx, rng: (
                "The public Binance sample demonstrates the quote/fill calibration plumbing on a small "
                "BTCUSDT window, not venue-general cost estimates."
            ),
        },
        {
            "id": "stress_diagnostic_bounded",
            "level": "execution-realism",
            "text": lambda ctx, rng: (
                f"Under the documented stress assumptions, the agent lost {rng.randrange(5, 30)} bps to "
                "simulated slippage; this is a stress diagnostic, not a live-cost estimate."
            ),
        },
    ]


PROMPT_TEMPLATE = """# Claim Boundary Review Task

Evidence context for the run being discussed:

- Execution mode: {execution_mode} (stress assumptions, no quote/fill calibration attached)
- Seeds: {seeds}
- Provider rows: {provider_mode}
- Market data: {data_source}

For each candidate claim below, decide (a) its claim-ladder level - one of
engineering, benchmark, scientific, execution-realism - and (b) whether the
evidence context supports it as stated.

{claims}

Answer with a JSON array, one object per claim:

```json
[{{"claim_index": 1, "claim_level": "engineering", "supported": true}}]
```
"""


def generate_task(task_index: int, *, seed: int) -> tuple[str, list[dict[str, Any]]]:
    """Return (prompt_markdown, ground_truth_rows) for one generated task."""

    rng = random.Random(seed)
    context = {
        "execution_mode": "realistic-stress",
        "seeds": rng.choice([1, 3, 5]),
        "provider_mode": "cached",
        "data_source": rng.choice(["synthetic regimes", "one masked real-market window"]),
    }
    violations = rng.sample(_violation_templates(), 3)
    controls = rng.sample(_control_templates(), 2)
    claims = [
        {"template": template, "supported": False}
        for template in violations
    ] + [
        {"template": template, "supported": True}
        for template in controls
    ]
    rng.shuffle(claims)

    lines = []
    truth_rows = []
    for index, claim in enumerate(claims, start=1):
        template = claim["template"]
        text = template["text"](context, rng)
        lines.append(f"{index}. {text}")
        truth_rows.append(
            {
                "claim_index": index,
                "template_id": template["id"],
                "claim_level": template["level"],
                "supported": claim["supported"],
                "why_unsupported": template.get("why_unsupported", ""),
            }
        )
    prompt = PROMPT_TEMPLATE.format(claims="\n".join(lines), **context)
    return prompt, truth_rows


def score_claim_answers(
    answers: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
) -> dict[str, float | int]:
    """Grade structured claim judgments against the generated labels."""

    truth_by_index = {int(row["claim_index"]): row for row in ground_truth}
    level_hits = 0
    support_hits = 0
    graded = 0
    violation_total = 0
    violation_caught = 0
    for answer in answers:
        index = answer.get("claim_index")
        if not isinstance(index, int) or index not in truth_by_index:
            continue
        truth = truth_by_index.pop(index)
        graded += 1
        if str(answer.get("claim_level", "")).strip().lower() == truth["claim_level"]:
            level_hits += 1
        if isinstance(answer.get("supported"), bool) and answer["supported"] == truth["supported"]:
            support_hits += 1
        if not truth["supported"]:
            violation_total += 1
            if answer.get("supported") is False:
                violation_caught += 1
    # Unanswered claims count against recall-style scores.
    for truth in truth_by_index.values():
        if not truth["supported"]:
            violation_total += 1
    total = graded + len(truth_by_index)
    return {
        "claims": total,
        "graded": graded,
        "level_accuracy": level_hits / total if total else 0.0,
        "support_accuracy": support_hits / total if total else 0.0,
        "violation_recall": violation_caught / violation_total if violation_total else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate claim-boundary review tasks with answer keys.")
    parser.add_argument("--tasks", type=int, default=25)
    parser.add_argument("--base-seed", type=int, default=500)
    parser.add_argument("--output-dir", default="outputs/claim_boundary_tasks")
    args = parser.parse_args(argv)

    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    all_truth: list[dict[str, Any]] = []
    for task_index in range(args.tasks):
        task_id = f"claim_boundary_gen_{task_index:04d}"
        prompt, truth_rows = generate_task(task_index, seed=args.base_seed + task_index)
        task_dir = tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        for row in truth_rows:
            all_truth.append({"task_id": task_id, **row})
        print(f"OK {task_id} ({len(truth_rows)} claims)", flush=True)

    with (output_dir / "ground_truth.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_truth:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "task_count": args.tasks,
                "claims_per_task": 5,
                "claim_levels": list(CLAIM_LEVELS),
                "base_seed": args.base_seed,
                "note": "ground_truth.jsonl is the answer key; do not publish it next to the tasks.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.tasks} tasks to {tasks_dir} (answer key: {output_dir / 'ground_truth.jsonl'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
