# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 0.333 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | buy-and-hold | 14.387 | [10.632, 18.266] | 0.1536 |
| high_vol | E0_ideal | 2 | glm:glm-5 | 12.292 | [10.309, 14.127] | 0.1103 |
| high_vol | E0_ideal | 3 | deepseek:deepseek-v4-pro | 10.944 | [8.733, 13.020] | 0.0955 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 12.825 | [9.311, 16.402] | 0.1349 |
| high_vol | E1_default_stress | 2 | deepseek:deepseek-v4-pro | 9.027 | [6.595, 11.400] | 0.0826 |
| high_vol | E1_default_stress | 3 | glm:glm-5 | 8.537 | [6.213, 10.824] | 0.0833 |
