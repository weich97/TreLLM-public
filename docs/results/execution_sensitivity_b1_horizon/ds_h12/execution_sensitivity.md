# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 0.571 | 0.500 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | risk-parity | 11.072 | [8.796, 13.580] | 0.0900 |
| high_vol | E0_ideal | 2 | buy-and-hold | 10.951 | [8.994, 12.917] | 0.0994 |
| high_vol | E0_ideal | 3 | naive-momentum | 10.902 | [8.252, 13.783] | 0.0779 |
| high_vol | E0_ideal | 4 | minimum-variance | 10.075 | [8.040, 12.182] | 0.0855 |
| high_vol | E0_ideal | 5 | random | 9.348 | [7.264, 11.734] | 0.0733 |
| high_vol | E0_ideal | 6 | deepseek:deepseek-v4-pro | 7.574 | [4.829, 10.347] | 0.0466 |
| high_vol | E0_ideal | 7 | signal-weighted | 6.128 | [2.646, 8.988] | 0.0119 |
| high_vol | E0_ideal | 8 | mean-reversion | 3.721 | [0.249, 6.729] | 0.0166 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 9.457 | [7.455, 11.574] | 0.1044 |
| high_vol | E1_default_stress | 2 | deepseek:deepseek-v4-pro | 9.201 | [7.548, 10.858] | 0.0761 |
| high_vol | E1_default_stress | 3 | risk-parity | 8.693 | [6.575, 10.900] | 0.0872 |
| high_vol | E1_default_stress | 4 | minimum-variance | 8.559 | [6.715, 10.330] | 0.0810 |
| high_vol | E1_default_stress | 5 | naive-momentum | 8.260 | [6.422, 10.115] | 0.0754 |
| high_vol | E1_default_stress | 6 | random | 7.750 | [5.065, 10.033] | 0.0796 |
| high_vol | E1_default_stress | 7 | signal-weighted | 4.849 | [1.373, 7.160] | 0.0124 |
| high_vol | E1_default_stress | 8 | mean-reversion | 3.301 | [0.243, 5.905] | 0.0279 |
