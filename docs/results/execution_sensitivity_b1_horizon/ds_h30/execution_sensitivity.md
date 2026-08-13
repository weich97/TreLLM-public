# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 0.786 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | naive-momentum | 13.210 | [11.077, 15.753] | 0.2785 |
| high_vol | E0_ideal | 2 | buy-and-hold | 13.094 | [10.520, 15.897] | 0.3266 |
| high_vol | E0_ideal | 3 | risk-parity | 13.059 | [10.404, 15.920] | 0.3146 |
| high_vol | E0_ideal | 4 | minimum-variance | 12.670 | [9.829, 15.646] | 0.3083 |
| high_vol | E0_ideal | 5 | random | 10.829 | [8.897, 12.715] | 0.2362 |
| high_vol | E0_ideal | 6 | signal-weighted | 10.615 | [8.523, 12.813] | 0.2170 |
| high_vol | E0_ideal | 7 | deepseek:deepseek-v4-pro | 9.565 | [7.462, 11.477] | 0.1866 |
| high_vol | E0_ideal | 8 | mean-reversion | 2.575 | [0.424, 4.412] | 0.0202 |
| high_vol | E1_default_stress | 1 | naive-momentum | 11.091 | [8.525, 13.439] | 0.2571 |
| high_vol | E1_default_stress | 2 | risk-parity | 11.064 | [8.782, 13.746] | 0.3030 |
| high_vol | E1_default_stress | 3 | buy-and-hold | 10.938 | [8.529, 13.498] | 0.3210 |
| high_vol | E1_default_stress | 4 | minimum-variance | 10.626 | [8.361, 12.731] | 0.2877 |
| high_vol | E1_default_stress | 5 | deepseek:deepseek-v4-pro | 9.103 | [6.944, 11.489] | 0.2068 |
| high_vol | E1_default_stress | 6 | random | 8.863 | [6.238, 11.164] | 0.2253 |
| high_vol | E1_default_stress | 7 | signal-weighted | 8.738 | [6.405, 10.978] | 0.2044 |
| high_vol | E1_default_stress | 8 | mean-reversion | 3.754 | [2.885, 4.566] | 0.0445 |
