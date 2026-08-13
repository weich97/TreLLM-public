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
| high_vol | E0_ideal | 2 | poe:gpt-5.5 | 9.985 | [8.003, 12.142] | 0.0698 |
| high_vol | E0_ideal | 3 | poe:claude-opus-4.7 | 9.865 | [8.019, 11.882] | 0.0696 |
| high_vol | E0_ideal | 4 | poe:gemini-3.1-pro | 8.794 | [7.858, 9.689] | 0.0637 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 11.394 | [8.124, 14.267] | 0.0637 |
| high_vol | E1_default_stress | 2 | poe:gpt-5.5 | 7.611 | [5.017, 10.124] | 0.0577 |
| high_vol | E1_default_stress | 3 | poe:claude-opus-4.7 | 7.427 | [4.887, 9.854] | 0.0564 |
| high_vol | E1_default_stress | 4 | poe:gemini-3.1-pro | 6.764 | [4.839, 8.646] | 0.0500 |
