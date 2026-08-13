# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| calm | E0_ideal | E1_default_stress |  | 1.000 |
| calm | E0_ideal | E2_harsh_corner |  | 1.000 |
| calm | E1_default_stress | E2_harsh_corner |  | 1.000 |
| high_vol | E0_ideal | E1_default_stress |  | 1.000 |
| high_vol | E0_ideal | E2_harsh_corner |  | 1.000 |
| high_vol | E1_default_stress | E2_harsh_corner |  | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| calm | E0_ideal | 1 | glm:glm-5+mem | 20.888 | [18.985, 22.580] | 0.0787 |
| calm | E1_default_stress | 1 | glm:glm-5+mem | 14.651 | [12.688, 16.840] | 0.0736 |
| calm | E2_harsh_corner | 1 | glm:glm-5+mem | 12.305 | [9.682, 14.709] | 0.0639 |
| high_vol | E0_ideal | 1 | glm:glm-5+mem | 9.066 | [6.478, 11.604] | 0.0712 |
| high_vol | E1_default_stress | 1 | glm:glm-5+mem | 9.483 | [7.724, 11.301] | 0.0801 |
| high_vol | E2_harsh_corner | 1 | glm:glm-5+mem | 8.121 | [5.687, 10.624] | 0.0930 |
