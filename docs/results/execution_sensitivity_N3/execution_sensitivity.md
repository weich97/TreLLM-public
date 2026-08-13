# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 0.636 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | buy-and-hold | 14.387 | [10.632, 18.266] | 0.1536 |
| high_vol | E0_ideal | 2 | risk-parity | 13.906 | [10.256, 17.720] | 0.1418 |
| high_vol | E0_ideal | 3 | minimum-variance | 13.508 | [9.808, 17.740] | 0.1354 |
| high_vol | E0_ideal | 4 | poe:gpt-5.5 | 12.334 | [8.583, 15.474] | 0.1148 |
| high_vol | E0_ideal | 5 | glm:glm-5 | 12.162 | [8.266, 15.367] | 0.1134 |
| high_vol | E0_ideal | 6 | poe:claude-opus-4.7 | 12.037 | [8.324, 15.330] | 0.1121 |
| high_vol | E0_ideal | 7 | naive-momentum | 11.807 | [7.593, 15.341] | 0.1044 |
| high_vol | E0_ideal | 8 | deepseek:deepseek-v4-pro | 11.260 | [7.259, 14.908] | 0.0934 |
| high_vol | E0_ideal | 9 | poe:gemini-3.1-pro | 10.853 | [6.481, 15.064] | 0.0906 |
| high_vol | E0_ideal | 10 | random | 10.457 | [7.602, 13.277] | 0.0991 |
| high_vol | E0_ideal | 11 | signal-weighted | 8.285 | [5.839, 10.382] | 0.0297 |
| high_vol | E0_ideal | 12 | mean-reversion | 4.635 | [2.324, 6.491] | 0.0190 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 12.825 | [9.311, 16.402] | 0.1349 |
| high_vol | E1_default_stress | 2 | minimum-variance | 11.290 | [8.157, 15.170] | 0.1074 |
| high_vol | E1_default_stress | 3 | risk-parity | 11.064 | [8.087, 14.605] | 0.1049 |
| high_vol | E1_default_stress | 4 | naive-momentum | 9.301 | [4.098, 13.509] | 0.0866 |
| high_vol | E1_default_stress | 5 | deepseek:deepseek-v4-pro | 9.068 | [5.232, 13.260] | 0.0806 |
| high_vol | E1_default_stress | 6 | random | 9.034 | [6.128, 12.198] | 0.0782 |
| high_vol | E1_default_stress | 7 | glm:glm-5 | 8.755 | [4.388, 12.897] | 0.0836 |
| high_vol | E1_default_stress | 8 | poe:gpt-5.5 | 8.692 | [4.514, 12.806] | 0.0820 |
| high_vol | E1_default_stress | 9 | poe:claude-opus-4.7 | 8.685 | [4.844, 12.583] | 0.0823 |
| high_vol | E1_default_stress | 10 | poe:gemini-3.1-pro | 7.518 | [3.709, 11.395] | 0.0728 |
| high_vol | E1_default_stress | 11 | signal-weighted | 5.185 | [2.064, 7.629] | 0.0173 |
| high_vol | E1_default_stress | 12 | mean-reversion | 4.487 | [2.478, 6.348] | 0.0251 |
