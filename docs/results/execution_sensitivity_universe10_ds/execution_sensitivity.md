# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 1.000 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | buy-and-hold | 13.288 | [10.568, 15.334] | 0.0746 |
| high_vol | E0_ideal | 2 | deepseek:deepseek-v4-pro | 8.959 | [7.229, 10.706] | 0.0659 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 11.394 | [8.124, 14.267] | 0.0637 |
| high_vol | E1_default_stress | 2 | deepseek:deepseek-v4-pro | 6.795 | [3.893, 9.844] | 0.0503 |
