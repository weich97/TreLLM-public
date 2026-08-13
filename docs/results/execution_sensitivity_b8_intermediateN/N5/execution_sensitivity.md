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
| high_vol | E0_ideal | 1 | buy-and-hold | 20.677 | [16.524, 24.786] | 0.1403 |
| high_vol | E0_ideal | 2 | glm:glm-5 | 15.161 | [13.329, 16.925] | 0.1128 |
| high_vol | E0_ideal | 3 | deepseek:deepseek-v4-pro | 12.885 | [10.988, 14.820] | 0.1004 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 16.588 | [13.581, 19.475] | 0.1201 |
| high_vol | E1_default_stress | 2 | deepseek:deepseek-v4-pro | 11.905 | [9.859, 13.956] | 0.0879 |
| high_vol | E1_default_stress | 3 | glm:glm-5 | 11.722 | [9.540, 13.827] | 0.0898 |
