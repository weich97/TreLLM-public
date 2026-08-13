# Provider Skill-Task Matrix

This report evaluates Poe-hosted models, and optionally direct DeepSeek models, as financial-audit agents rather than trading strategies.
The public artifact contains aggregate scores only; raw prompts and raw model answers stay in ignored local outputs/cache.

## Experiment Plan

- Prompt version: `provider-skill-audit-v0.1`.
- Models: `poe:claude-opus-4.7`.
- Tasks: 8.
- Prompt variants: `adversarial_claim_boundary`.
- Repeats: 1.
- Sample start index: 3.
- Planned calls: 8.
- Estimated token budget: about 14,955 tokens.

## Model Aggregate

| Provider | Model | Samples | Variants | Avg tasks passed | Avg points | Avg score | Hard fails |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| `poe` | `claude-opus-4.7` | 1 | `adversarial_claim_boundary` | 8.0/8 | 38.0/40 | 95.0% | 0 |

Interpretation: these are audit-skill scores, not trading-performance scores. A higher row means the model more reliably followed TreLLM's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics.

## Repeat-Level Scorecard

| Provider | Model | Variant | Repeat | Tasks passed | Points | Score | Hard fails |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 3 | 8/8 | 38/40 | 95.0% | 0 |

## Ability Breakdown

| Provider | Model | Variant | Repeat | Ability | Tasks passed | Points | Score |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 3 | Claim discipline | 3/3 | 14/15 | 93.3% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 3 | Reproduction awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 3 | Plugin engineering | 1/1 | 4/5 | 80.0% |

## Reproduction

```bash
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples\skill_tasks_challenge --repeats 1 --sample-start-index 3 --prompt-variants adversarial_claim_boundary
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples\skill_tasks_challenge --repeats 1 --sample-start-index 3 --prompt-variants adversarial_claim_boundary --refresh-cache
python scripts/run_poe_skill_task_matrix.py --repeats 3 --include-deepseek
python scripts/score_skill_task.py --tasks-dir examples\skill_tasks_challenge --answers-dir outputs/poe_skill_task_answers/<run>/<model_repeat>
```
