# Provider Skill-Task Matrix

This report evaluates Poe-hosted models, and optionally direct DeepSeek models, as financial-audit agents rather than trading strategies.
The public artifact contains aggregate scores only; raw prompts and raw model answers stay in ignored local outputs/cache.

## Experiment Plan

- Prompt version: `provider-skill-audit-v0.1`.
- Models: `poe:gpt-5.5`, `poe:gemini-3.1-pro`, `poe:kimi-k2.5`.
- Tasks: 8.
- Prompt variants: `standard`, `skeptical_reviewer`, `adversarial_claim_boundary`.
- Repeats: 1.
- Sample start index: 3.
- Planned calls: 72.
- Estimated token budget: about 134,097 tokens.

## Model Aggregate

| Provider | Model | Samples | Variants | Avg tasks passed | Avg points | Avg score | Hard fails |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| `poe` | `gemini-3.1-pro` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 6.7/8 | 33.0/40 | 82.5% | 2 |
| `poe` | `kimi-k2.5` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 6.3/8 | 32.0/40 | 80.0% | 3 |
| `poe` | `gpt-5.5` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 6.0/8 | 29.0/40 | 72.5% | 5 |

Interpretation: these are audit-skill scores, not trading-performance scores. A higher row means the model more reliably followed TreLLM's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics.

## Repeat-Level Scorecard

| Provider | Model | Variant | Repeat | Tasks passed | Points | Score | Hard fails |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `poe` | `gpt-5.5` | `standard` | 3 | 6/8 | 28/40 | 70.0% | 2 |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 3 | 6/8 | 28/40 | 70.0% | 2 |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 3 | 6/8 | 31/40 | 77.5% | 1 |
| `poe` | `gemini-3.1-pro` | `standard` | 3 | 6/8 | 32/40 | 80.0% | 1 |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 3 | 7/8 | 32/40 | 80.0% | 1 |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 3 | 7/8 | 35/40 | 87.5% | 0 |
| `poe` | `kimi-k2.5` | `standard` | 3 | 6/8 | 31/40 | 77.5% | 1 |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 3 | 7/8 | 32/40 | 80.0% | 1 |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 3 | 6/8 | 33/40 | 82.5% | 1 |

## Ability Breakdown

| Provider | Model | Variant | Repeat | Ability | Tasks passed | Points | Score |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `poe` | `gpt-5.5` | `standard` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 3 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gpt-5.5` | `standard` | 3 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `standard` | 3 | Plugin engineering | 0/1 | 0/5 | 0.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 3 | Claim discipline | 1/3 | 5/15 | 33.3% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 3 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 3 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 3 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 3 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 3 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 3 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 3 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 3 | Plugin engineering | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 3 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 3 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 3 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 3 | Claim discipline | 2/3 | 11/15 | 73.3% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 3 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 3 | Plugin engineering | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 3 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `kimi-k2.5` | `standard` | 3 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `kimi-k2.5` | `standard` | 3 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 3 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 3 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 3 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 3 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 3 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 3 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 3 | Claim discipline | 2/3 | 10/15 | 66.7% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 3 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 3 | Plugin engineering | 1/1 | 5/5 | 100.0% |

## Reproduction

```bash
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples\skill_tasks_challenge --repeats 1 --sample-start-index 3 --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples\skill_tasks_challenge --repeats 1 --sample-start-index 3 --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary --refresh-cache
python scripts/run_poe_skill_task_matrix.py --repeats 3 --include-deepseek
python scripts/score_skill_task.py --tasks-dir examples\skill_tasks_challenge --answers-dir outputs/poe_skill_task_answers/<run>/<model_repeat>
```
