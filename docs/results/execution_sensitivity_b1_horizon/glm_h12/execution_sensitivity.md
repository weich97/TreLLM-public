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
| high_vol | E0_ideal | 1 | buy-and-hold | 10.951 | [8.994, 12.917] | 0.0994 |
| high_vol | E0_ideal | 2 | glm:glm-5 | 8.902 | [6.108, 11.622] | 0.0697 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 9.457 | [7.455, 11.574] | 0.1044 |
| high_vol | E1_default_stress | 2 | glm:glm-5 | 9.343 | [7.645, 11.245] | 0.0777 |
