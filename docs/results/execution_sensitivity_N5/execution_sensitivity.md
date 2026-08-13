# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 0.697 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | buy-and-hold | 20.677 | [16.524, 24.786] | 0.1403 |
| high_vol | E0_ideal | 2 | risk-parity | 19.706 | [15.837, 23.468] | 0.1367 |
| high_vol | E0_ideal | 3 | minimum-variance | 18.973 | [16.316, 21.569] | 0.1385 |
| high_vol | E0_ideal | 4 | naive-momentum | 16.737 | [12.698, 20.752] | 0.1077 |
| high_vol | E0_ideal | 5 | poe:gpt-5.5 | 15.351 | [12.210, 18.608] | 0.1114 |
| high_vol | E0_ideal | 6 | glm:glm-5 | 15.174 | [12.007, 18.419] | 0.1119 |
| high_vol | E0_ideal | 7 | poe:claude-opus-4.7 | 14.947 | [11.547, 18.465] | 0.1098 |
| high_vol | E0_ideal | 8 | random | 14.250 | [10.865, 17.467] | 0.0983 |
| high_vol | E0_ideal | 9 | deepseek:deepseek-v4-pro | 12.490 | [9.500, 15.505] | 0.0953 |
| high_vol | E0_ideal | 10 | poe:gemini-3.1-pro | 11.773 | [8.367, 15.072] | 0.0866 |
| high_vol | E0_ideal | 11 | signal-weighted | 6.528 | [4.318, 8.762] | 0.0291 |
| high_vol | E0_ideal | 12 | mean-reversion | 5.202 | [3.630, 6.846] | 0.0285 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 16.588 | [13.581, 19.475] | 0.1201 |
| high_vol | E1_default_stress | 2 | minimum-variance | 13.871 | [11.015, 16.693] | 0.1026 |
| high_vol | E1_default_stress | 3 | risk-parity | 13.412 | [10.366, 16.094] | 0.1007 |
| high_vol | E1_default_stress | 4 | deepseek:deepseek-v4-pro | 12.244 | [8.608, 15.838] | 0.0948 |
| high_vol | E1_default_stress | 5 | poe:gpt-5.5 | 12.165 | [8.383, 16.280] | 0.0924 |
| high_vol | E1_default_stress | 6 | poe:claude-opus-4.7 | 11.920 | [8.219, 15.808] | 0.0895 |
| high_vol | E1_default_stress | 7 | naive-momentum | 11.618 | [8.567, 14.603] | 0.0873 |
| high_vol | E1_default_stress | 8 | glm:glm-5 | 11.593 | [8.083, 15.320] | 0.0880 |
| high_vol | E1_default_stress | 9 | poe:gemini-3.1-pro | 10.354 | [7.355, 13.046] | 0.0707 |
| high_vol | E1_default_stress | 10 | random | 10.320 | [8.083, 12.538] | 0.0731 |
| high_vol | E1_default_stress | 11 | signal-weighted | 5.043 | [2.762, 7.242] | 0.0236 |
| high_vol | E1_default_stress | 12 | mean-reversion | 4.228 | [2.285, 6.138] | 0.0236 |
