# Audit corpus artifacts: what is here, and what is not

These files let a reader re-score the audit study without holding the task
trees, and check that a task set they hold is the one the analysis used. They
are the small, releasable half of the corpus; the large half is described at the
bottom.

## In this directory

| File | What it is |
| --- | --- |
| `analysis_plan.json` | The frozen design: auditors, primary estimand, primary test, multiplicity correction, parsing rule, temperature, samples per task, stop rule, and the pre-declared secondary outcomes. Fixed before collection. |
| `ground_truth.jsonl` | One record per task: which defects were injected, of what kind, at which step, with the pre-edit values. This is the answer key the recall figures are computed against. |
| `task_manifest.json` | Per-task digests plus `analysis_plan_sha256`, binding the corpus to the plan above. |
| `analysis_manifest.json` | Manifest of the analysis run itself (pre-existing; not part of this addition). |

## In `../finaudit/`

| File | What it is |
| --- | --- |
| `ground_truth_pairs_deepseek_v4_pro.jsonl` | Answer key for the matched trading pairs generated from that producer. |
| `ground_truth_pairs_glm_5_direct.jsonl` | The same, for the other producer. |
| `ground_truth_toolaudit_pairs.jsonl` | Answer key for the tool-use second-domain pairs. |

## What these deliberately do not contain

No prompts, no model responses, no rationales, no free text of any kind. Every
record is structured: identifiers, defect kinds, step indices, numeric
pre-edit values, and digests. That is not an oversight — the release path
excludes raw prompt and response text on purpose, so what a reader can verify is
the scoring, not the generation.

## The part that is not in git

The task trees themselves — the faulted trajectories a model is asked to audit,
together with the producer trees they were generated from — are about 1 GB and
are not in this repository. They are hosted at
<https://huggingface.co/datasets/Sunsincer97/trellm-audit-corpora>.

Regeneration is possible but not from this repository alone, and it is worth
being exact about why. The generators are tracked here
(`scripts/generate_multilabel_audit_tasks.py`,
`scripts/generate_trading_pairs.py`, `scripts/generate_toolaudit_pairs.py`) and
they are deterministic: every random draw is seeded from the task's own
identifiers. But `generate_multilabel_audit_tasks.py` reads its source
trajectories from `--trading-source-root` (default `outputs/audit_self/`), a
further ~684 MB tree that is also outside version control. So a reader holding
only this repository cannot regenerate the corpus; a reader who obtains both
trees can, and `task_manifest.json` carries the per-task digests to check the
result against.

If a regenerated digest disagrees with the manifest, the regeneration is not the
one the analysis used, and the difference should be reported rather than
absorbed.
