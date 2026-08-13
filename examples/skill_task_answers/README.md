# TreLLM Skill Task Answers

This directory contains answer sets for the skill task suite.

- `reference/` is a deterministic maintainer-authored baseline. It should pass
  every tracked rubric and is used by CI.
- `boundary_violation/` contains intentionally unsafe or overclaiming examples
  used to test hard-fail behavior.

These answers evaluate financial-audit workflow quality. They are not trading
strategies, investment advice, broker integrations, or live execution tools.

To score a model or reviewer, add a sibling directory with `manifest.json` and
one Markdown file per task id:

```bash
python scripts/score_skill_task.py \
  --tasks-dir examples/skill_tasks \
  --answers-dir examples/skill_task_answers/<answer_set>
```

The manifest must follow `schemas/skill_answer_set.schema.json`. Record the
model/provider, prompt version, skill text used, task-input version, and any
hidden artifacts. A score is only comparable when every answer set saw the same
task inputs and the same skill files.
