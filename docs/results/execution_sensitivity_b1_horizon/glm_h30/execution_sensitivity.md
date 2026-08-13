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
| high_vol | E0_ideal | 1 | buy-and-hold | 13.094 | [10.520, 15.897] | 0.3266 |
| high_vol | E0_ideal | 2 | glm:glm-5 | 11.255 | [9.098, 13.358] | 0.2521 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 10.938 | [8.529, 13.498] | 0.3210 |
| high_vol | E1_default_stress | 2 | glm:glm-5 | 10.178 | [7.468, 13.162] | 0.2362 |
