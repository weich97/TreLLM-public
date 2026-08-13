# TreLLM Skill Task Suite

This directory contains small, deterministic tasks for evaluating whether a
human reviewer or coding agent can use TreLLM skills without turning them
into trading prompts.

Each task includes:

- `input.md`: the instruction shown to the reviewer or model;
- one small artifact or expected-output note when useful;
- `rubric.json`: machine-readable grading criteria.

These tasks evaluate audit, reproduction, calibration, claim-boundary, and
plugin-authoring ability. They do not evaluate trading profitability. The suite
is designed to benchmark LLMs as financial-audit agents rather than stock
pickers.

## Capability Metrics

| Ability | Measurable task | Scoring |
| --- | --- | --- |
| Audit accuracy | Find risk edits, rejected orders, and partial fills in a trajectory | Rubric match against expected audit fields |
| Risk-gate understanding | Check whether a risk report is complete or misses controls | Checklist score |
| Execution-boundary awareness | Avoid describing a stress simulator as real transaction-cost evidence | Hard fail on boundary overclaim |
| Claim discipline | Classify engineering, benchmark, and scientific claims | Label accuracy |
| Reproduction awareness | Report commit, hash, command, artifact path, and data-source flags | Field coverage |
| Plugin engineering | Propose a narrow plugin with deterministic tests | Test/review checklist |

The tracked suite keeps at least two deterministic tasks for each ability so a
single easy fixture does not define the score.

Validate the rubric suite:

```bash
python scripts/score_skill_task.py --tasks-dir examples/skill_tasks --validate-only
python scripts/score_skill_task.py --tasks-dir examples/skill_tasks --answers-dir examples/skill_task_answers/reference
python scripts/score_skill_task_report.py --tasks-dir examples/skill_tasks --output docs/results/skill_task_matrix.md --check
```

Batch answer sets must include `manifest.json`; otherwise model comparisons do
not record provider, prompt, skill version, task-input version, or hidden
artifact use.

Score one answer:

```bash
python scripts/score_skill_task.py examples/skill_tasks/trajectory_audit_001 --answer answer.md
```

Reference answers live in `examples/skill_task_answers/reference/`. They are a
maintainer baseline for audit quality, not trading advice.
