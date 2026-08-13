# Provider Skill-Task Matrix

This report evaluates Poe-hosted models, and optionally direct DeepSeek models, as financial-audit agents rather than trading strategies.
The public artifact contains aggregate scores only; raw prompts and raw model answers stay in ignored local outputs/cache.

## Experiment Plan

- Prompt version: `provider-skill-audit-v0.1`.
- Models: `poe:gpt-5.5`, `poe:gemini-3.1-pro`, `poe:kimi-k2.5`, `poe:glm-5`, `poe:claude-opus-4.7`.
- Tasks: 8.
- Prompt variants: `standard`, `skeptical_reviewer`, `adversarial_claim_boundary`.
- Repeats: 2.
- Planned calls: 240.
- Estimated token budget: about 446,670 tokens.

## Model Aggregate

| Provider | Model | Samples | Variants | Avg tasks passed | Avg points | Avg score | Hard fails |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| `poe` | `gemini-3.1-pro` | 6 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 6.7/8 | 32.2/40 | 80.4% | 6 |
| `poe` | `claude-opus-4.7` | 6 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 6.5/8 | 31.3/40 | 78.3% | 7 |
| `poe` | `gpt-5.5` | 6 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 6.5/8 | 31.2/40 | 77.9% | 7 |
| `poe` | `glm-5` | 6 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 6.2/8 | 31.0/40 | 77.5% | 7 |
| `poe` | `kimi-k2.5` | 6 | `adversarial_claim_boundary,skeptical_reviewer,standard` | 5.7/8 | 29.5/40 | 73.8% | 8 |

Interpretation: these are audit-skill scores, not trading-performance scores. A higher row means the model more reliably followed TreLLM's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics.

## Repeat-Level Scorecard

| Provider | Model | Variant | Repeat | Tasks passed | Points | Score | Hard fails |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `poe` | `gpt-5.5` | `standard` | 1 | 7/8 | 33/40 | 82.5% | 1 |
| `poe` | `gpt-5.5` | `standard` | 2 | 7/8 | 32/40 | 80.0% | 1 |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | 7/8 | 32/40 | 80.0% | 1 |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 2 | 6/8 | 32/40 | 80.0% | 1 |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | 5/8 | 27/40 | 67.5% | 2 |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 2 | 7/8 | 31/40 | 77.5% | 1 |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | 6/8 | 31/40 | 77.5% | 1 |
| `poe` | `gemini-3.1-pro` | `standard` | 2 | 6/8 | 32/40 | 80.0% | 1 |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | 7/8 | 32/40 | 80.0% | 1 |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 2 | 7/8 | 32/40 | 80.0% | 1 |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | 7/8 | 33/40 | 82.5% | 1 |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 2 | 7/8 | 33/40 | 82.5% | 1 |
| `poe` | `kimi-k2.5` | `standard` | 1 | 5/8 | 27/40 | 67.5% | 2 |
| `poe` | `kimi-k2.5` | `standard` | 2 | 6/8 | 29/40 | 72.5% | 2 |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | 6/8 | 31/40 | 77.5% | 1 |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 2 | 7/8 | 32/40 | 80.0% | 1 |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | 6/8 | 30/40 | 75.0% | 1 |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 2 | 4/8 | 28/40 | 70.0% | 1 |
| `poe` | `glm-5` | `standard` | 1 | 7/8 | 34/40 | 85.0% | 1 |
| `poe` | `glm-5` | `standard` | 2 | 6/8 | 30/40 | 75.0% | 1 |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | 6/8 | 31/40 | 77.5% | 1 |
| `poe` | `glm-5` | `skeptical_reviewer` | 2 | 5/8 | 30/40 | 75.0% | 1 |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | 6/8 | 28/40 | 70.0% | 2 |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 2 | 7/8 | 33/40 | 82.5% | 1 |
| `poe` | `claude-opus-4.7` | `standard` | 1 | 6/8 | 29/40 | 72.5% | 2 |
| `poe` | `claude-opus-4.7` | `standard` | 2 | 7/8 | 36/40 | 90.0% | 0 |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | 7/8 | 33/40 | 82.5% | 1 |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 2 | 6/8 | 28/40 | 70.0% | 2 |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | 6/8 | 27/40 | 67.5% | 2 |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 2 | 7/8 | 35/40 | 87.5% | 0 |

## Ability Breakdown

| Provider | Model | Variant | Repeat | Ability | Tasks passed | Points | Score |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `poe` | `gpt-5.5` | `standard` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Reproduction awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `standard` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `standard` | 2 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gpt-5.5` | `standard` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `standard` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 1 | Plugin engineering | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 2 | Claim discipline | 2/3 | 10/15 | 66.7% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 2 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `gpt-5.5` | `skeptical_reviewer` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 1 | Plugin engineering | 0/1 | 0/5 | 0.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 2 | Claim discipline | 2/3 | 8/15 | 53.3% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gpt-5.5` | `adversarial_claim_boundary` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 2 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 2 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `gemini-3.1-pro` | `standard` | 2 | Plugin engineering | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 2 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `skeptical_reviewer` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 1 | Plugin engineering | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 2 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `gemini-3.1-pro` | `adversarial_claim_boundary` | 2 | Plugin engineering | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Claim discipline | 1/3 | 5/15 | 33.3% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `kimi-k2.5` | `standard` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `standard` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `standard` | 2 | Claim discipline | 2/3 | 10/15 | 66.7% |
| `poe` | `kimi-k2.5` | `standard` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `standard` | 2 | Plugin engineering | 0/1 | 0/5 | 0.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Claim discipline | 1/3 | 8/15 | 53.3% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 2 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `skeptical_reviewer` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Claim discipline | 2/3 | 8/15 | 53.3% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 2 | Claim discipline | 0/3 | 6/15 | 40.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 2 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `kimi-k2.5` | `adversarial_claim_boundary` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `glm-5` | `standard` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `standard` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `standard` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `standard` | 1 | Claim discipline | 2/3 | 10/15 | 66.7% |
| `poe` | `glm-5` | `standard` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `glm-5` | `standard` | 1 | Plugin engineering | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `standard` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `standard` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `standard` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `standard` | 2 | Claim discipline | 2/3 | 8/15 | 53.3% |
| `poe` | `glm-5` | `standard` | 2 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `glm-5` | `standard` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Claim discipline | 1/3 | 8/15 | 53.3% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 2 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 2 | Reproduction awareness | 0/1 | 3/5 | 60.0% |
| `poe` | `glm-5` | `skeptical_reviewer` | 2 | Plugin engineering | 0/1 | 3/5 | 60.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 1 | Plugin engineering | 0/1 | 0/5 | 0.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 2 | Claim discipline | 2/3 | 10/15 | 66.7% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `glm-5` | `adversarial_claim_boundary` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Claim discipline | 2/3 | 9/15 | 60.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Reproduction awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 1 | Plugin engineering | 0/1 | 0/5 | 0.0% |
| `poe` | `claude-opus-4.7` | `standard` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 2 | Claim discipline | 2/3 | 12/15 | 80.0% |
| `poe` | `claude-opus-4.7` | `standard` | 2 | Reproduction awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `standard` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Claim discipline | 2/3 | 10/15 | 66.7% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 2 | Execution-boundary awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 2 | Claim discipline | 2/3 | 10/15 | 66.7% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `skeptical_reviewer` | 2 | Plugin engineering | 0/1 | 0/5 | 0.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Execution-boundary awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Claim discipline | 1/3 | 5/15 | 33.3% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 1 | Plugin engineering | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 2 | Audit accuracy | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 2 | Risk-gate understanding | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 2 | Execution-boundary awareness | 1/1 | 5/5 | 100.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 2 | Claim discipline | 2/3 | 12/15 | 80.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 2 | Reproduction awareness | 1/1 | 4/5 | 80.0% |
| `poe` | `claude-opus-4.7` | `adversarial_claim_boundary` | 2 | Plugin engineering | 1/1 | 4/5 | 80.0% |

## Reproduction

```bash
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples/skill_tasks_challenge --repeats 2 --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary
python scripts/run_poe_skill_task_matrix.py --tasks-dir examples/skill_tasks_challenge --repeats 2 --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary --refresh-cache
python scripts/run_poe_skill_task_matrix.py --repeats 3 --include-deepseek
python scripts/score_skill_task.py --tasks-dir examples/skill_tasks_challenge --answers-dir outputs/poe_skill_task_answers/<run>/<model_repeat>
```
