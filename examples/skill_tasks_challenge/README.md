# TreLLM Challenge Skill Tasks

This directory contains harder cross-examination tasks for provider-hosted
models. The tasks are designed to stress claim discipline, public-artifact
privacy, execution-calibration boundaries, reproduction evidence, and
market-rule overgeneralization.

They are not trading tasks and do not evaluate profitability.

Run a provider challenge matrix:

```bash
python scripts/run_poe_skill_task_matrix.py \
  --tasks-dir examples/skill_tasks_challenge \
  --repeats 3 \
  --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary \
  --public-output docs/results/poe_skill_challenge_matrix.md \
  --public-csv docs/results/poe_skill_challenge_matrix.csv
```

