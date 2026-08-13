# Provider Skill-Task Matrix

This report evaluates Poe-hosted models, and optionally direct DeepSeek models, as financial-audit agents rather than trading strategies.
The public artifact contains aggregate scores only; raw prompts and raw model answers stay in ignored local outputs/cache.

## Experiment Plan

- Prompt version: `provider-skill-audit-v0.1`.
- Models: `poe:gpt-5.5`, `poe:gemini-3.1-pro`, `poe:kimi-k2.5`, `poe:glm-5`, `poe:claude-opus-4.7`.
- Tasks: 12.
- Prompt variants: `standard`, `skeptical_reviewer`, `adversarial_claim_boundary`.
- Repeats: 1.
- Planned calls: 180.
- Estimated token budget: about 360,705 tokens.

## Model Aggregate

| Provider | Model | Samples | Variants | Avg tasks passed | Avg points | Avg score | Hard fails |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| `poe` | `gemini-3.1-pro` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 10.7/12 | 53.0/60 | 88.3% | 0 |
| `poe` | `gpt-5.5` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 10.3/12 | 51.0/60 | 85.0% | 3 |
| `poe` | `glm-5` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 10.0/12 | 47.7/60 | 79.4% | 5 |
| `poe` | `claude-opus-4.7` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 9.0/12 | 46.3/60 | 77.2% | 4 |
| `poe` | `kimi-k2.5` | 3 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 8.3/12 | 45.3/60 | 75.6% | 4 |

Interpretation: these are audit-skill scores, not trading-performance scores. A higher row means the model more reliably followed TreLLM's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics.

## Repeat-Level Scorecard

| Provider | Model | Variant | Repeat | Tasks passed | Points | Score | Hard fails |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `poe` | `gpt-5.5` | `standard` | 1 | 10/12 | 52/60 | 86.7% | 1 |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | 11/12 | 52/60 | 86.7% | 1 |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | 10/12 | 49/60 | 81.7% | 1 |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | 10/12 | 51/60 | 85.0% | 0 |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | 11/12 | 54/60 | 90.0% | 0 |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | 11/12 | 54/60 | 90.0% | 0 |
| `poe` | `kimi-k2.5` | `standard` | 1 | 9/12 | 48/60 | 80.0% | 1 |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | 8/12 | 42/60 | 70.0% | 2 |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | 8/12 | 46/60 | 76.7% | 1 |
| `poe` | `glm-5` | `standard` | 1 | 10/12 | 45/60 | 75.0% | 2 |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | 9/12 | 46/60 | 76.7% | 2 |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | 11/12 | 52/60 | 86.7% | 1 |
| `poe` | `claude-opus-4.7` | `standard` | 1 | 8/12 | 44/60 | 73.3% | 2 |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | 10/12 | 48/60 | 80.0% | 1 |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | 9/12 | 47/60 | 78.3% | 1 |

## Ability Breakdown

| Provider | Model | Variant | Repeat | Ability | Tasks passed | Points | Score |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `poe` | `gpt-5.5` | `standard` | 1 | Audit accuracy | 1/2 | 8/10 | 80.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Claim discipline | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Plugin engineering | 1/2 | 5/10 | 50.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Audit accuracy | 2/2 | 8/10 | 80.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Claim discipline | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Plugin engineering | 1/2 | 5/10 | 50.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Audit accuracy | 2/2 | 9/10 | 90.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Claim discipline | 1/2 | 7/10 | 70.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Plugin engineering | 1/2 | 4/10 | 40.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Audit accuracy | 1/2 | 7/10 | 70.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Execution-boundary awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Claim discipline | 1/2 | 7/10 | 70.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Reproduction awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Plugin engineering | 2/2 | 8/10 | 80.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Audit accuracy | 2/2 | 8/10 | 80.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Claim discipline | 1/2 | 7/10 | 70.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Plugin engineering | 2/2 | 10/10 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Audit accuracy | 2/2 | 8/10 | 80.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Claim discipline | 1/2 | 7/10 | 70.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Plugin engineering | 2/2 | 10/10 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Audit accuracy | 0/2 | 6/10 | 60.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Claim discipline | 2/2 | 10/10 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Reproduction awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Plugin engineering | 1/2 | 4/10 | 40.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Audit accuracy | 1/2 | 8/10 | 80.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Risk-gate understanding | 2/2 | 9/10 | 90.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 2/2 | 8/10 | 80.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Claim discipline | 1/2 | 7/10 | 70.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Plugin engineering | 0/2 | 0/10 | 0.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Audit accuracy | 0/2 | 6/10 | 60.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 2/2 | 9/10 | 90.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Claim discipline | 1/2 | 7/10 | 70.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Plugin engineering | 1/2 | 5/10 | 50.0% |
| `poe` | `glm-5` | `standard` | 1 | Audit accuracy | 2/2 | 8/10 | 80.0% |
| `poe` | `glm-5` | `standard` | 1 | Risk-gate understanding | 2/2 | 9/10 | 90.0% |
| `poe` | `glm-5` | `standard` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `glm-5` | `standard` | 1 | Claim discipline | 2/2 | 9/10 | 90.0% |
| `poe` | `glm-5` | `standard` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `glm-5` | `standard` | 1 | Plugin engineering | 0/2 | 0/10 | 0.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Audit accuracy | 1/2 | 7/10 | 70.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Claim discipline | 2/2 | 10/10 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Plugin engineering | 0/2 | 0/10 | 0.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Audit accuracy | 2/2 | 8/10 | 80.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 2/2 | 9/10 | 90.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Claim discipline | 2/2 | 10/10 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Plugin engineering | 1/2 | 5/10 | 50.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Audit accuracy | 1/2 | 7/10 | 70.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Risk-gate understanding | 2/2 | 10/10 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Claim discipline | 1/2 | 8/10 | 80.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Plugin engineering | 0/2 | 0/10 | 0.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Audit accuracy | 2/2 | 8/10 | 80.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Risk-gate understanding | 2/2 | 9/10 | 90.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Claim discipline | 1/2 | 7/10 | 70.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Plugin engineering | 1/2 | 5/10 | 50.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Audit accuracy | 1/2 | 7/10 | 70.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 2/2 | 9/10 | 90.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 2/2 | 9/10 | 90.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Claim discipline | 1/2 | 8/10 | 80.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 2/2 | 10/10 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Plugin engineering | 1/2 | 4/10 | 40.0% |

## Reproduction

```bash
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples/skill_tasks --repeats 1 --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples/skill_tasks --repeats 1 --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary --refresh-cache
python scripts/run_poe_skill_task_matrix.py --repeats 3 --include-deepseek
python scripts/score_skill_task.py --tasks-dir examples/skill_tasks --answers-dir outputs/poe_skill_task_answers/<run>/<model_repeat>
```
