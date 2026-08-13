# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | -1.000 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | glm:glm-5 | 5.522 | [4.242, 6.712] | 0.2470 |
| high_vol | E0_ideal | 2 | buy-and-hold | 4.954 | [3.396, 6.464] | 0.2769 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 3.835 | [2.380, 5.079] | 0.2433 |
| high_vol | E1_default_stress | 2 | glm:glm-5 | 3.402 | [2.037, 4.675] | 0.1675 |
