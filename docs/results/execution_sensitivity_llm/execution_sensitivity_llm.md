# Execution Sensitivity With LLM Agents

Provider-routed LLM agents and deterministic baselines in identical
(scenario, execution level, seed) cells. Positive friction-fragility
DiD means the agent loses more return to execution frictions than the
baseline anchor does on the same market paths.

## Friction Fragility (DiD vs baseline, BH-FDR)

| Agent | Type | Stress level | Mean DiD | 95% CI | q | Cohen's d |
| --- | --- | --- | ---: | --- | ---: | ---: |
| deepseek:deepseek-v4-pro | llm | E1_default_stress | -0.0246 | [-0.0415, -0.0093] | 0.0293 | -0.54 |
| mean-reversion | classical | E1_default_stress | -0.0068 | [-0.0206, +0.0090] | 0.5346 | -0.15 |
| minimum-variance | classical | E1_default_stress | +0.0052 | [-0.0073, +0.0178] | 0.5349 | 0.15 |
| naive-momentum | classical | E1_default_stress | -0.0037 | [-0.0171, +0.0082] | 0.6767 | -0.10 |
| poe:claude-opus-4.7 | llm | E1_default_stress | -0.0065 | [-0.0192, +0.0071] | 0.5346 | -0.18 |
| poe:gemini-3.1-pro | llm | E1_default_stress | -0.0057 | [-0.0223, +0.0109] | 0.6554 | -0.12 |
| poe:glm-5 | llm | E1_default_stress | -0.0054 | [-0.0158, +0.0068] | 0.5346 | -0.17 |
| poe:gpt-5.5 | llm | E1_default_stress | -0.0037 | [-0.0167, +0.0098] | 0.6767 | -0.10 |
| random | classical | E1_default_stress | +0.0025 | [-0.0073, +0.0132] | 0.6864 | 0.08 |
| risk-parity | classical | E1_default_stress | +0.0058 | [-0.0041, +0.0155] | 0.4482 | 0.21 |
| signal-weighted | classical | E1_default_stress | +0.0014 | [-0.0083, +0.0113] | 0.7891 | 0.05 |
| deepseek:deepseek-v4-pro | llm | E2_harsh_corner | -0.0397 | [-0.0584, -0.0205] | 0.0055 | -0.71 |
| mean-reversion | classical | E2_harsh_corner | -0.0448 | [-0.0654, -0.0250] | 0.0055 | -0.78 |
| minimum-variance | classical | E2_harsh_corner | -0.0095 | [-0.0196, +0.0009] | 0.2663 | -0.31 |
| naive-momentum | classical | E2_harsh_corner | -0.0139 | [-0.0299, +0.0019] | 0.2663 | -0.30 |
| poe:claude-opus-4.7 | llm | E2_harsh_corner | -0.0193 | [-0.0416, +0.0018] | 0.2663 | -0.31 |
| poe:gemini-3.1-pro | llm | E2_harsh_corner | -0.0230 | [-0.0501, +0.0020] | 0.2663 | -0.31 |
| poe:glm-5 | llm | E2_harsh_corner | -0.0170 | [-0.0415, +0.0073] | 0.4098 | -0.24 |
| poe:gpt-5.5 | llm | E2_harsh_corner | -0.0142 | [-0.0381, +0.0083] | 0.4482 | -0.22 |
| random | classical | E2_harsh_corner | -0.0176 | [-0.0346, +0.0049] | 0.2663 | -0.32 |
| risk-parity | classical | E2_harsh_corner | -0.0096 | [-0.0202, +0.0007] | 0.2663 | -0.31 |
| signal-weighted | classical | E2_harsh_corner | -0.0131 | [-0.0298, +0.0044] | 0.2947 | -0.28 |

## Provider-Sampling Variance Decomposition

Within-seed share is the fraction of total-return variance due to
provider sampling at a fixed market path; the remainder is market
variation across seeds.

| Scenario | Level | Agent | Seeds | Runs | Within-seed share |
| --- | --- | --- | ---: | ---: | ---: |
| calm | E0_ideal | deepseek:deepseek-v4-pro | 10 | 30 | 0.447 |
| calm | E0_ideal | poe:claude-opus-4.7 | 10 | 30 | 0.002 |
| calm | E0_ideal | poe:gemini-3.1-pro | 10 | 30 | 0.392 |
| calm | E0_ideal | poe:glm-5 | 10 | 30 | 0.117 |
| calm | E0_ideal | poe:gpt-5.5 | 10 | 30 | 0.000 |
| calm | E1_default_stress | deepseek:deepseek-v4-pro | 10 | 30 | 0.320 |
| calm | E1_default_stress | poe:claude-opus-4.7 | 10 | 19 | 0.018 |
| calm | E1_default_stress | poe:gemini-3.1-pro | 10 | 21 | 0.030 |
| calm | E1_default_stress | poe:glm-5 | 10 | 11 | 0.439 |
| calm | E1_default_stress | poe:gpt-5.5 | 10 | 30 | 0.003 |
| calm | E2_harsh_corner | deepseek:deepseek-v4-pro | 10 | 30 | 0.188 |
| calm | E2_harsh_corner | poe:gpt-5.5 | 10 | 11 | 0.000 |
| high_vol | E0_ideal | deepseek:deepseek-v4-pro | 10 | 30 | 0.142 |
| high_vol | E1_default_stress | deepseek:deepseek-v4-pro | 10 | 30 | 0.136 |
| high_vol | E2_harsh_corner | deepseek:deepseek-v4-pro | 10 | 30 | 0.027 |
| jump_tail | E0_ideal | deepseek:deepseek-v4-pro | 10 | 30 | 0.311 |
| jump_tail | E1_default_stress | deepseek:deepseek-v4-pro | 10 | 30 | 0.084 |
| jump_tail | E2_harsh_corner | deepseek:deepseek-v4-pro | 10 | 30 | 0.025 |

## Ranking Stability Between Levels

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| calm | E0_ideal | E1_default_stress | 0.818 | 0.200 |
| calm | E0_ideal | E2_harsh_corner | 0.758 | 1.000 |
| calm | E0_ideal | E2_latency_3 | 0.727 | 1.000 |
| calm | E0_ideal | E2_participation_1pct | 0.788 | 0.200 |
| calm | E0_ideal | E2_spread_20bps | 0.848 | 0.500 |
| calm | E1_default_stress | E2_harsh_corner | 0.636 | 0.200 |
| calm | E1_default_stress | E2_latency_3 | 0.606 | 0.200 |
| calm | E1_default_stress | E2_participation_1pct | 0.970 | 1.000 |
| calm | E1_default_stress | E2_spread_20bps | 0.970 | 0.500 |
| calm | E2_harsh_corner | E2_latency_3 | 0.970 | 1.000 |
| calm | E2_harsh_corner | E2_participation_1pct | 0.606 | 0.200 |
| calm | E2_harsh_corner | E2_spread_20bps | 0.667 | 0.500 |
| calm | E2_latency_3 | E2_participation_1pct | 0.576 | 0.200 |
| calm | E2_latency_3 | E2_spread_20bps | 0.636 | 0.500 |
| calm | E2_participation_1pct | E2_spread_20bps | 0.939 | 0.500 |
| high_vol | E0_ideal | E1_default_stress | 0.212 | 0.200 |
| high_vol | E0_ideal | E2_harsh_corner | 0.515 | 0.200 |
| high_vol | E0_ideal | E2_latency_3 | 0.576 | 0.200 |
| high_vol | E0_ideal | E2_participation_1pct | 0.273 | 0.200 |
| high_vol | E0_ideal | E2_spread_20bps | 0.394 | 0.200 |
| high_vol | E1_default_stress | E2_harsh_corner | 0.091 | 0.000 |
| high_vol | E1_default_stress | E2_latency_3 | 0.212 | 0.000 |
| high_vol | E1_default_stress | E2_participation_1pct | 0.939 | 0.500 |
| high_vol | E1_default_stress | E2_spread_20bps | 0.758 | 0.500 |
| high_vol | E2_harsh_corner | E2_latency_3 | 0.818 | 1.000 |
| high_vol | E2_harsh_corner | E2_participation_1pct | 0.152 | 0.000 |
| high_vol | E2_harsh_corner | E2_spread_20bps | 0.333 | 0.000 |
| high_vol | E2_latency_3 | E2_participation_1pct | 0.212 | 0.000 |
| high_vol | E2_latency_3 | E2_spread_20bps | 0.333 | 0.000 |
| high_vol | E2_participation_1pct | E2_spread_20bps | 0.818 | 1.000 |
| jump_tail | E0_ideal | E1_default_stress | 0.515 | 0.500 |
| jump_tail | E0_ideal | E2_harsh_corner | 0.303 | 0.500 |
| jump_tail | E0_ideal | E2_latency_3 | 0.424 | 0.500 |
| jump_tail | E0_ideal | E2_participation_1pct | 0.515 | 0.500 |
| jump_tail | E0_ideal | E2_spread_20bps | 0.576 | 0.500 |
| jump_tail | E1_default_stress | E2_harsh_corner | 0.727 | 0.500 |
| jump_tail | E1_default_stress | E2_latency_3 | 0.848 | 0.500 |
| jump_tail | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| jump_tail | E1_default_stress | E2_spread_20bps | 0.818 | 1.000 |
| jump_tail | E2_harsh_corner | E2_latency_3 | 0.879 | 1.000 |
| jump_tail | E2_harsh_corner | E2_participation_1pct | 0.727 | 0.500 |
| jump_tail | E2_harsh_corner | E2_spread_20bps | 0.667 | 0.500 |
| jump_tail | E2_latency_3 | E2_participation_1pct | 0.848 | 0.500 |
| jump_tail | E2_latency_3 | E2_spread_20bps | 0.727 | 0.500 |
| jump_tail | E2_participation_1pct | E2_spread_20bps | 0.818 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Type | Sharpe mean | Return mean | Fill rate |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| calm | E0_ideal | 1 | buy-and-hold | classical | 23.381 | 0.0932 | 1.00 |
| calm | E0_ideal | 2 | minimum-variance | classical | 23.323 | 0.0932 | 1.00 |
| calm | E0_ideal | 3 | risk-parity | classical | 23.113 | 0.0896 | 1.00 |
| calm | E0_ideal | 4 | poe:gpt-5.5 | llm | 21.627 | 0.0826 | 1.00 |
| calm | E0_ideal | 5 | poe:claude-opus-4.7 | llm | 21.366 | 0.0815 | 1.00 |
| calm | E0_ideal | 6 | poe:glm-5 | llm | 21.231 | 0.0800 | 1.00 |
| calm | E0_ideal | 7 | naive-momentum | classical | 19.889 | 0.0797 | 1.00 |
| calm | E0_ideal | 8 | poe:gemini-3.1-pro | llm | 18.537 | 0.0605 | 1.00 |
| calm | E0_ideal | 9 | random | classical | 16.364 | 0.0621 | 1.00 |
| calm | E0_ideal | 10 | deepseek:deepseek-v4-pro | llm | 9.063 | 0.0285 | 1.00 |
| calm | E0_ideal | 11 | signal-weighted | classical | 8.402 | 0.0203 | 1.00 |
| calm | E0_ideal | 12 | mean-reversion | classical | 2.258 | 0.0023 | 0.50 |
| calm | E1_default_stress | 1 | buy-and-hold | classical | 16.687 | 0.0885 | 0.88 |
| calm | E1_default_stress | 2 | poe:gpt-5.5 | llm | 15.423 | 0.0759 | 0.86 |
| calm | E1_default_stress | 3 | poe:claude-opus-4.7 | llm | 15.400 | 0.0755 | 0.88 |
| calm | E1_default_stress | 4 | minimum-variance | classical | 15.311 | 0.0853 | 0.87 |
| calm | E1_default_stress | 5 | naive-momentum | classical | 15.248 | 0.0732 | 0.86 |
| calm | E1_default_stress | 6 | risk-parity | classical | 15.226 | 0.0800 | 0.87 |
| calm | E1_default_stress | 7 | poe:glm-5 | llm | 15.188 | 0.0746 | 0.86 |
| calm | E1_default_stress | 8 | poe:gemini-3.1-pro | llm | 13.479 | 0.0663 | 0.80 |
| calm | E1_default_stress | 9 | random | classical | 11.735 | 0.0544 | 0.86 |
| calm | E1_default_stress | 10 | deepseek:deepseek-v4-pro | llm | 10.287 | 0.0461 | 0.79 |
| calm | E1_default_stress | 11 | signal-weighted | classical | 6.402 | 0.0103 | 0.77 |
| calm | E1_default_stress | 12 | mean-reversion | classical | 2.714 | 0.0041 | 0.38 |
| calm | E2_harsh_corner | 1 | minimum-variance | classical | 14.954 | 0.0741 | 0.51 |
| calm | E2_harsh_corner | 2 | risk-parity | classical | 14.655 | 0.0720 | 0.50 |
| calm | E2_harsh_corner | 3 | buy-and-hold | classical | 14.494 | 0.0723 | 0.51 |
| calm | E2_harsh_corner | 4 | naive-momentum | classical | 13.316 | 0.0776 | 0.51 |
| calm | E2_harsh_corner | 5 | poe:claude-opus-4.7 | llm | 12.743 | 0.0665 | 0.49 |
| calm | E2_harsh_corner | 6 | poe:gpt-5.5 | llm | 12.659 | 0.0666 | 0.48 |
| calm | E2_harsh_corner | 7 | poe:glm-5 | llm | 12.193 | 0.0636 | 0.46 |
| calm | E2_harsh_corner | 8 | random | classical | 12.163 | 0.0599 | 0.51 |
| calm | E2_harsh_corner | 9 | deepseek:deepseek-v4-pro | llm | 11.709 | 0.0531 | 0.48 |
| calm | E2_harsh_corner | 10 | poe:gemini-3.1-pro | llm | 11.416 | 0.0580 | 0.45 |
| calm | E2_harsh_corner | 11 | signal-weighted | classical | 7.436 | 0.0168 | 0.33 |
| calm | E2_harsh_corner | 12 | mean-reversion | classical | 3.718 | 0.0106 | 0.27 |
| calm | E2_latency_3 | 1 | minimum-variance | classical | 15.452 | 0.0760 | 0.50 |
| calm | E2_latency_3 | 2 | risk-parity | classical | 15.152 | 0.0740 | 0.50 |
| calm | E2_latency_3 | 3 | buy-and-hold | classical | 14.992 | 0.0742 | 0.51 |
| calm | E2_latency_3 | 4 | naive-momentum | classical | 13.685 | 0.0800 | 0.52 |
| calm | E2_latency_3 | 5 | poe:claude-opus-4.7 | llm | 13.257 | 0.0692 | 0.49 |
| calm | E2_latency_3 | 6 | poe:gpt-5.5 | llm | 13.177 | 0.0694 | 0.49 |
| calm | E2_latency_3 | 7 | poe:glm-5 | llm | 12.826 | 0.0668 | 0.47 |
| calm | E2_latency_3 | 8 | deepseek:deepseek-v4-pro | llm | 12.810 | 0.0606 | 0.50 |
| calm | E2_latency_3 | 9 | random | classical | 12.646 | 0.0621 | 0.53 |
| calm | E2_latency_3 | 10 | poe:gemini-3.1-pro | llm | 12.016 | 0.0608 | 0.44 |
| calm | E2_latency_3 | 11 | signal-weighted | classical | 7.900 | 0.0177 | 0.33 |
| calm | E2_latency_3 | 12 | mean-reversion | classical | 3.948 | 0.0113 | 0.27 |
| calm | E2_participation_1pct | 1 | buy-and-hold | classical | 16.687 | 0.0885 | 0.88 |
| calm | E2_participation_1pct | 2 | poe:gpt-5.5 | llm | 15.435 | 0.0758 | 0.86 |
| calm | E2_participation_1pct | 3 | poe:claude-opus-4.7 | llm | 15.392 | 0.0754 | 0.87 |
| calm | E2_participation_1pct | 4 | minimum-variance | classical | 15.311 | 0.0853 | 0.87 |
| calm | E2_participation_1pct | 5 | naive-momentum | classical | 15.248 | 0.0732 | 0.86 |
| calm | E2_participation_1pct | 6 | poe:glm-5 | llm | 15.242 | 0.0740 | 0.86 |
| calm | E2_participation_1pct | 7 | risk-parity | classical | 15.226 | 0.0800 | 0.87 |
| calm | E2_participation_1pct | 8 | poe:gemini-3.1-pro | llm | 13.671 | 0.0660 | 0.78 |
| calm | E2_participation_1pct | 9 | random | classical | 11.735 | 0.0544 | 0.86 |
| calm | E2_participation_1pct | 10 | deepseek:deepseek-v4-pro | llm | 10.484 | 0.0437 | 0.80 |
| calm | E2_participation_1pct | 11 | signal-weighted | classical | 6.402 | 0.0103 | 0.77 |
| calm | E2_participation_1pct | 12 | mean-reversion | classical | 2.714 | 0.0041 | 0.38 |
| calm | E2_spread_20bps | 1 | buy-and-hold | classical | 15.941 | 0.0855 | 0.88 |
| calm | E2_spread_20bps | 2 | poe:gpt-5.5 | llm | 14.609 | 0.0721 | 0.86 |
| calm | E2_spread_20bps | 3 | minimum-variance | classical | 14.605 | 0.0822 | 0.87 |
| calm | E2_spread_20bps | 4 | poe:claude-opus-4.7 | llm | 14.528 | 0.0717 | 0.87 |
| calm | E2_spread_20bps | 5 | naive-momentum | classical | 14.487 | 0.0700 | 0.87 |
| calm | E2_spread_20bps | 6 | risk-parity | classical | 14.462 | 0.0767 | 0.88 |
| calm | E2_spread_20bps | 7 | poe:glm-5 | llm | 13.854 | 0.0648 | 0.86 |
| calm | E2_spread_20bps | 8 | poe:gemini-3.1-pro | llm | 12.371 | 0.0629 | 0.82 |
| calm | E2_spread_20bps | 9 | random | classical | 10.924 | 0.0507 | 0.87 |
| calm | E2_spread_20bps | 10 | deepseek:deepseek-v4-pro | llm | 9.686 | 0.0401 | 0.80 |
| calm | E2_spread_20bps | 11 | signal-weighted | classical | 5.672 | 0.0089 | 0.77 |
| calm | E2_spread_20bps | 12 | mean-reversion | classical | 2.347 | 0.0035 | 0.38 |
| high_vol | E0_ideal | 1 | risk-parity | classical | 11.072 | 0.0900 | 1.00 |
| high_vol | E0_ideal | 2 | buy-and-hold | classical | 10.951 | 0.0994 | 1.00 |
| high_vol | E0_ideal | 3 | naive-momentum | classical | 10.902 | 0.0779 | 1.00 |
| high_vol | E0_ideal | 4 | minimum-variance | classical | 10.075 | 0.0855 | 1.00 |
| high_vol | E0_ideal | 5 | random | classical | 9.348 | 0.0733 | 1.00 |
| high_vol | E0_ideal | 6 | poe:glm-5 | llm | 9.224 | 0.0690 | 1.00 |
| high_vol | E0_ideal | 7 | poe:gpt-5.5 | llm | 9.023 | 0.0713 | 1.00 |
| high_vol | E0_ideal | 8 | poe:claude-opus-4.7 | llm | 9.016 | 0.0710 | 1.00 |
| high_vol | E0_ideal | 9 | deepseek:deepseek-v4-pro | llm | 8.186 | 0.0502 | 1.00 |
| high_vol | E0_ideal | 10 | poe:gemini-3.1-pro | llm | 7.708 | 0.0567 | 1.00 |
| high_vol | E0_ideal | 11 | signal-weighted | classical | 6.128 | 0.0119 | 1.00 |
| high_vol | E0_ideal | 12 | mean-reversion | classical | 3.721 | 0.0166 | 1.00 |
| high_vol | E1_default_stress | 1 | poe:glm-5 | llm | 9.592 | 0.0789 | 0.85 |
| high_vol | E1_default_stress | 2 | deepseek:deepseek-v4-pro | llm | 9.512 | 0.0762 | 0.83 |
| high_vol | E1_default_stress | 3 | buy-and-hold | classical | 9.457 | 0.1044 | 0.83 |
| high_vol | E1_default_stress | 4 | poe:claude-opus-4.7 | llm | 9.218 | 0.0818 | 0.86 |
| high_vol | E1_default_stress | 5 | poe:gpt-5.5 | llm | 9.062 | 0.0777 | 0.85 |
| high_vol | E1_default_stress | 6 | risk-parity | classical | 8.693 | 0.0872 | 0.85 |
| high_vol | E1_default_stress | 7 | poe:gemini-3.1-pro | llm | 8.649 | 0.0733 | 0.80 |
| high_vol | E1_default_stress | 8 | minimum-variance | classical | 8.559 | 0.0810 | 0.84 |
| high_vol | E1_default_stress | 9 | naive-momentum | classical | 8.260 | 0.0754 | 0.84 |
| high_vol | E1_default_stress | 10 | random | classical | 7.750 | 0.0796 | 0.80 |
| high_vol | E1_default_stress | 11 | signal-weighted | classical | 4.849 | 0.0124 | 0.78 |
| high_vol | E1_default_stress | 12 | mean-reversion | classical | 3.301 | 0.0279 | 0.81 |
| high_vol | E2_harsh_corner | 1 | minimum-variance | classical | 10.128 | 0.0986 | 0.47 |
| high_vol | E2_harsh_corner | 2 | risk-parity | classical | 9.991 | 0.1010 | 0.46 |
| high_vol | E2_harsh_corner | 3 | random | classical | 9.494 | 0.0904 | 0.48 |
| high_vol | E2_harsh_corner | 4 | buy-and-hold | classical | 9.205 | 0.0924 | 0.49 |
| high_vol | E2_harsh_corner | 5 | poe:gemini-3.1-pro | llm | 8.390 | 0.0933 | 0.51 |
| high_vol | E2_harsh_corner | 6 | poe:gpt-5.5 | llm | 8.198 | 0.0936 | 0.54 |
| high_vol | E2_harsh_corner | 7 | poe:glm-5 | llm | 8.130 | 0.0916 | 0.53 |
| high_vol | E2_harsh_corner | 8 | poe:claude-opus-4.7 | llm | 8.010 | 0.0972 | 0.54 |
| high_vol | E2_harsh_corner | 9 | deepseek:deepseek-v4-pro | llm | 7.474 | 0.0870 | 0.52 |
| high_vol | E2_harsh_corner | 10 | naive-momentum | classical | 7.088 | 0.0694 | 0.47 |
| high_vol | E2_harsh_corner | 11 | mean-reversion | classical | 5.102 | 0.0427 | 0.45 |
| high_vol | E2_harsh_corner | 12 | signal-weighted | classical | 0.465 | 0.0112 | 0.37 |
| high_vol | E2_latency_3 | 1 | minimum-variance | classical | 10.346 | 0.1006 | 0.47 |
| high_vol | E2_latency_3 | 2 | risk-parity | classical | 10.200 | 0.1030 | 0.47 |
| high_vol | E2_latency_3 | 3 | random | classical | 9.716 | 0.0928 | 0.47 |
| high_vol | E2_latency_3 | 4 | buy-and-hold | classical | 9.415 | 0.0943 | 0.48 |
| high_vol | E2_latency_3 | 5 | poe:gpt-5.5 | llm | 8.423 | 0.0962 | 0.52 |
| high_vol | E2_latency_3 | 6 | deepseek:deepseek-v4-pro | llm | 8.326 | 0.0916 | 0.54 |
| high_vol | E2_latency_3 | 7 | poe:glm-5 | llm | 8.245 | 0.0932 | 0.51 |
| high_vol | E2_latency_3 | 8 | poe:claude-opus-4.7 | llm | 8.235 | 0.0999 | 0.52 |
| high_vol | E2_latency_3 | 9 | poe:gemini-3.1-pro | llm | 8.013 | 0.0901 | 0.49 |
| high_vol | E2_latency_3 | 10 | naive-momentum | classical | 7.280 | 0.0712 | 0.46 |
| high_vol | E2_latency_3 | 11 | mean-reversion | classical | 5.330 | 0.0445 | 0.43 |
| high_vol | E2_latency_3 | 12 | signal-weighted | classical | 0.880 | 0.0119 | 0.37 |
| high_vol | E2_participation_1pct | 1 | poe:glm-5 | llm | 9.592 | 0.0789 | 0.85 |
| high_vol | E2_participation_1pct | 2 | buy-and-hold | classical | 9.457 | 0.1044 | 0.83 |
| high_vol | E2_participation_1pct | 3 | poe:claude-opus-4.7 | llm | 9.218 | 0.0818 | 0.86 |
| high_vol | E2_participation_1pct | 4 | deepseek:deepseek-v4-pro | llm | 9.201 | 0.0761 | 0.83 |
| high_vol | E2_participation_1pct | 5 | poe:gpt-5.5 | llm | 9.062 | 0.0777 | 0.85 |
| high_vol | E2_participation_1pct | 6 | risk-parity | classical | 8.693 | 0.0872 | 0.85 |
| high_vol | E2_participation_1pct | 7 | poe:gemini-3.1-pro | llm | 8.649 | 0.0733 | 0.80 |
| high_vol | E2_participation_1pct | 8 | minimum-variance | classical | 8.559 | 0.0810 | 0.84 |
| high_vol | E2_participation_1pct | 9 | naive-momentum | classical | 8.260 | 0.0754 | 0.84 |
| high_vol | E2_participation_1pct | 10 | random | classical | 7.750 | 0.0796 | 0.80 |
| high_vol | E2_participation_1pct | 11 | signal-weighted | classical | 4.849 | 0.0124 | 0.78 |
| high_vol | E2_participation_1pct | 12 | mean-reversion | classical | 3.301 | 0.0279 | 0.81 |
| high_vol | E2_spread_20bps | 1 | buy-and-hold | classical | 9.154 | 0.1013 | 0.84 |
| high_vol | E2_spread_20bps | 2 | poe:glm-5 | llm | 8.921 | 0.0735 | 0.84 |
| high_vol | E2_spread_20bps | 3 | poe:claude-opus-4.7 | llm | 8.691 | 0.0766 | 0.87 |
| high_vol | E2_spread_20bps | 4 | poe:gpt-5.5 | llm | 8.666 | 0.0744 | 0.86 |
| high_vol | E2_spread_20bps | 5 | risk-parity | classical | 8.328 | 0.0837 | 0.86 |
| high_vol | E2_spread_20bps | 6 | minimum-variance | classical | 8.176 | 0.0776 | 0.84 |
| high_vol | E2_spread_20bps | 7 | poe:gemini-3.1-pro | llm | 7.991 | 0.0731 | 0.83 |
| high_vol | E2_spread_20bps | 8 | deepseek:deepseek-v4-pro | llm | 7.963 | 0.0598 | 0.82 |
| high_vol | E2_spread_20bps | 9 | naive-momentum | classical | 7.956 | 0.0724 | 0.85 |
| high_vol | E2_spread_20bps | 10 | random | classical | 7.317 | 0.0756 | 0.81 |
| high_vol | E2_spread_20bps | 11 | signal-weighted | classical | 4.323 | 0.0112 | 0.78 |
| high_vol | E2_spread_20bps | 12 | mean-reversion | classical | 3.010 | 0.0260 | 0.81 |
| jump_tail | E0_ideal | 1 | minimum-variance | classical | 8.879 | 0.1060 | 1.00 |
| jump_tail | E0_ideal | 2 | risk-parity | classical | 8.650 | 0.1016 | 1.00 |
| jump_tail | E0_ideal | 3 | buy-and-hold | classical | 8.493 | 0.1036 | 1.00 |
| jump_tail | E0_ideal | 4 | naive-momentum | classical | 8.042 | 0.0793 | 1.00 |
| jump_tail | E0_ideal | 5 | random | classical | 7.546 | 0.0839 | 1.00 |
| jump_tail | E0_ideal | 6 | signal-weighted | classical | 7.132 | 0.0279 | 1.00 |
| jump_tail | E0_ideal | 7 | poe:gemini-3.1-pro | llm | 6.958 | 0.0793 | 1.00 |
| jump_tail | E0_ideal | 8 | poe:gpt-5.5 | llm | 6.841 | 0.0801 | 1.00 |
| jump_tail | E0_ideal | 9 | deepseek:deepseek-v4-pro | llm | 6.721 | 0.0539 | 1.00 |
| jump_tail | E0_ideal | 10 | poe:claude-opus-4.7 | llm | 6.675 | 0.0762 | 1.00 |
| jump_tail | E0_ideal | 11 | poe:glm-5 | llm | 6.323 | 0.0705 | 1.00 |
| jump_tail | E0_ideal | 12 | mean-reversion | classical | 0.991 | 0.0061 | 0.90 |
| jump_tail | E1_default_stress | 1 | naive-momentum | classical | 7.773 | 0.0829 | 0.84 |
| jump_tail | E1_default_stress | 2 | minimum-variance | classical | 7.346 | 0.0863 | 0.84 |
| jump_tail | E1_default_stress | 3 | risk-parity | classical | 7.135 | 0.0802 | 0.85 |
| jump_tail | E1_default_stress | 4 | buy-and-hold | classical | 6.920 | 0.0870 | 0.85 |
| jump_tail | E1_default_stress | 5 | deepseek:deepseek-v4-pro | llm | 6.693 | 0.0679 | 0.84 |
| jump_tail | E1_default_stress | 6 | poe:claude-opus-4.7 | llm | 6.009 | 0.0748 | 0.87 |
| jump_tail | E1_default_stress | 7 | poe:gpt-5.5 | llm | 5.882 | 0.0752 | 0.86 |
| jump_tail | E1_default_stress | 8 | random | classical | 5.751 | 0.0616 | 0.79 |
| jump_tail | E1_default_stress | 9 | poe:glm-5 | llm | 5.111 | 0.0658 | 0.86 |
| jump_tail | E1_default_stress | 10 | signal-weighted | classical | 4.622 | 0.0168 | 0.77 |
| jump_tail | E1_default_stress | 11 | poe:gemini-3.1-pro | llm | 4.279 | 0.0575 | 0.81 |
| jump_tail | E1_default_stress | 12 | mean-reversion | classical | 0.793 | -0.0032 | 0.71 |
| jump_tail | E2_harsh_corner | 1 | naive-momentum | classical | 5.067 | 0.0608 | 0.48 |
| jump_tail | E2_harsh_corner | 2 | minimum-variance | classical | 4.810 | 0.0699 | 0.48 |
| jump_tail | E2_harsh_corner | 3 | buy-and-hold | classical | 4.654 | 0.0609 | 0.50 |
| jump_tail | E2_harsh_corner | 4 | risk-parity | classical | 4.593 | 0.0663 | 0.47 |
| jump_tail | E2_harsh_corner | 5 | poe:claude-opus-4.7 | llm | 4.469 | 0.0521 | 0.50 |
| jump_tail | E2_harsh_corner | 6 | poe:glm-5 | llm | 4.316 | 0.0446 | 0.49 |
| jump_tail | E2_harsh_corner | 7 | poe:gpt-5.5 | llm | 4.000 | 0.0458 | 0.51 |
| jump_tail | E2_harsh_corner | 8 | deepseek:deepseek-v4-pro | llm | 3.863 | 0.0407 | 0.49 |
| jump_tail | E2_harsh_corner | 9 | poe:gemini-3.1-pro | llm | 3.816 | 0.0434 | 0.46 |
| jump_tail | E2_harsh_corner | 10 | random | classical | 3.606 | 0.0512 | 0.49 |
| jump_tail | E2_harsh_corner | 11 | mean-reversion | classical | 2.605 | 0.0352 | 0.41 |
| jump_tail | E2_harsh_corner | 12 | signal-weighted | classical | 0.628 | 0.0006 | 0.36 |
| jump_tail | E2_latency_3 | 1 | naive-momentum | classical | 5.251 | 0.0631 | 0.49 |
| jump_tail | E2_latency_3 | 2 | minimum-variance | classical | 4.983 | 0.0720 | 0.48 |
| jump_tail | E2_latency_3 | 3 | buy-and-hold | classical | 4.828 | 0.0629 | 0.50 |
| jump_tail | E2_latency_3 | 4 | risk-parity | classical | 4.768 | 0.0685 | 0.47 |
| jump_tail | E2_latency_3 | 5 | poe:claude-opus-4.7 | llm | 4.668 | 0.0546 | 0.49 |
| jump_tail | E2_latency_3 | 6 | poe:gpt-5.5 | llm | 4.218 | 0.0489 | 0.50 |
| jump_tail | E2_latency_3 | 7 | deepseek:deepseek-v4-pro | llm | 4.170 | 0.0486 | 0.49 |
| jump_tail | E2_latency_3 | 8 | random | classical | 3.807 | 0.0533 | 0.48 |
| jump_tail | E2_latency_3 | 9 | poe:glm-5 | llm | 3.600 | 0.0409 | 0.49 |
| jump_tail | E2_latency_3 | 10 | poe:gemini-3.1-pro | llm | 3.517 | 0.0352 | 0.44 |
| jump_tail | E2_latency_3 | 11 | mean-reversion | classical | 2.763 | 0.0368 | 0.43 |
| jump_tail | E2_latency_3 | 12 | signal-weighted | classical | 1.025 | 0.0015 | 0.36 |
| jump_tail | E2_participation_1pct | 1 | naive-momentum | classical | 7.773 | 0.0829 | 0.84 |
| jump_tail | E2_participation_1pct | 2 | minimum-variance | classical | 7.346 | 0.0863 | 0.84 |
| jump_tail | E2_participation_1pct | 3 | risk-parity | classical | 7.135 | 0.0802 | 0.85 |
| jump_tail | E2_participation_1pct | 4 | buy-and-hold | classical | 6.920 | 0.0870 | 0.85 |
| jump_tail | E2_participation_1pct | 5 | deepseek:deepseek-v4-pro | llm | 6.411 | 0.0657 | 0.84 |
| jump_tail | E2_participation_1pct | 6 | poe:claude-opus-4.7 | llm | 6.009 | 0.0748 | 0.87 |
| jump_tail | E2_participation_1pct | 7 | poe:gpt-5.5 | llm | 5.882 | 0.0752 | 0.86 |
| jump_tail | E2_participation_1pct | 8 | random | classical | 5.751 | 0.0616 | 0.79 |
| jump_tail | E2_participation_1pct | 9 | poe:glm-5 | llm | 5.111 | 0.0658 | 0.86 |
| jump_tail | E2_participation_1pct | 10 | signal-weighted | classical | 4.622 | 0.0168 | 0.77 |
| jump_tail | E2_participation_1pct | 11 | poe:gemini-3.1-pro | llm | 4.279 | 0.0575 | 0.81 |
| jump_tail | E2_participation_1pct | 12 | mean-reversion | classical | 0.793 | -0.0032 | 0.71 |
| jump_tail | E2_spread_20bps | 1 | naive-momentum | classical | 7.472 | 0.0799 | 0.85 |
| jump_tail | E2_spread_20bps | 2 | minimum-variance | classical | 7.034 | 0.0827 | 0.84 |
| jump_tail | E2_spread_20bps | 3 | risk-parity | classical | 6.823 | 0.0767 | 0.85 |
| jump_tail | E2_spread_20bps | 4 | buy-and-hold | classical | 6.673 | 0.0839 | 0.85 |
| jump_tail | E2_spread_20bps | 5 | poe:gemini-3.1-pro | llm | 6.590 | 0.0730 | 0.82 |
| jump_tail | E2_spread_20bps | 6 | deepseek:deepseek-v4-pro | llm | 6.184 | 0.0632 | 0.85 |
| jump_tail | E2_spread_20bps | 7 | poe:claude-opus-4.7 | llm | 5.702 | 0.0719 | 0.87 |
| jump_tail | E2_spread_20bps | 8 | poe:gpt-5.5 | llm | 5.537 | 0.0717 | 0.86 |
| jump_tail | E2_spread_20bps | 9 | random | classical | 5.364 | 0.0578 | 0.79 |
| jump_tail | E2_spread_20bps | 10 | poe:glm-5 | llm | 4.650 | 0.0561 | 0.85 |
| jump_tail | E2_spread_20bps | 11 | signal-weighted | classical | 4.282 | 0.0153 | 0.77 |
| jump_tail | E2_spread_20bps | 12 | mean-reversion | classical | 0.606 | -0.0050 | 0.71 |
