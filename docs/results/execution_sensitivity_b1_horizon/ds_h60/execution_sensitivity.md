# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 0.571 | 0.500 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | naive-momentum | 5.901 | [4.514, 7.324] | 0.2495 |
| high_vol | E0_ideal | 2 | signal-weighted | 5.379 | [4.228, 6.446] | 0.2011 |
| high_vol | E0_ideal | 3 | deepseek:deepseek-v4-pro | 5.033 | [3.686, 6.300] | 0.1870 |
| high_vol | E0_ideal | 4 | buy-and-hold | 4.954 | [3.396, 6.464] | 0.2769 |
| high_vol | E0_ideal | 5 | risk-parity | 4.870 | [3.327, 6.380] | 0.2667 |
| high_vol | E0_ideal | 6 | minimum-variance | 4.737 | [3.166, 6.322] | 0.2590 |
| high_vol | E0_ideal | 7 | random | 4.080 | [2.697, 5.262] | 0.1849 |
| high_vol | E0_ideal | 8 | mean-reversion | 0.153 | [-1.293, 1.585] | 0.0012 |
| high_vol | E1_default_stress | 1 | naive-momentum | 4.377 | [2.748, 5.847] | 0.2083 |
| high_vol | E1_default_stress | 2 | signal-weighted | 4.249 | [2.787, 5.520] | 0.1837 |
| high_vol | E1_default_stress | 3 | minimum-variance | 4.024 | [2.329, 5.684] | 0.2282 |
| high_vol | E1_default_stress | 4 | risk-parity | 3.954 | [2.384, 5.571] | 0.2365 |
| high_vol | E1_default_stress | 5 | buy-and-hold | 3.835 | [2.380, 5.079] | 0.2433 |
| high_vol | E1_default_stress | 6 | deepseek:deepseek-v4-pro | 3.604 | [1.850, 5.231] | 0.1684 |
| high_vol | E1_default_stress | 7 | random | 3.236 | [1.229, 4.727] | 0.1694 |
| high_vol | E1_default_stress | 8 | mean-reversion | -0.246 | [-1.203, 0.701] | -0.0142 |
