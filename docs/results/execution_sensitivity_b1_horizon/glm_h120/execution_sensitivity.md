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
| high_vol | E0_ideal | 1 | glm:glm-5 | 2.683 | [1.725, 3.641] | 0.2246 |
| high_vol | E0_ideal | 2 | buy-and-hold | 0.875 | [-0.317, 2.110] | 0.0985 |
| high_vol | E1_default_stress | 1 | glm:glm-5 | 0.486 | [-0.171, 1.116] | 0.0454 |
| high_vol | E1_default_stress | 2 | buy-and-hold | 0.357 | [-0.736, 1.408] | 0.0494 |
