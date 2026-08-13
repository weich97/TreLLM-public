# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E0_ideal | E1_default_stress | 0.833 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E0_ideal | 1 | naive-momentum | 3.965 | [3.125, 4.732] | 0.2982 |
| high_vol | E0_ideal | 2 | signal-weighted | 3.698 | [2.973, 4.371] | 0.2332 |
| high_vol | E0_ideal | 3 | poe:claude-opus-4.7 | 2.746 | [1.744, 3.785] | 0.2281 |
| high_vol | E0_ideal | 4 | poe:gemini-3.1-pro | 1.830 | [0.509, 3.065] | 0.1483 |
| high_vol | E0_ideal | 5 | buy-and-hold | 0.875 | [-0.317, 2.110] | 0.0985 |
| high_vol | E0_ideal | 6 | risk-parity | 0.803 | [-0.377, 2.044] | 0.0903 |
| high_vol | E0_ideal | 7 | minimum-variance | 0.741 | [-0.423, 2.003] | 0.0830 |
| high_vol | E0_ideal | 8 | random | 0.247 | [-0.694, 1.215] | 0.0249 |
| high_vol | E0_ideal | 9 | mean-reversion | -2.828 | [-3.900, -1.603] | -0.1647 |
| high_vol | E1_default_stress | 1 | signal-weighted | 2.689 | [1.691, 3.574] | 0.1973 |
| high_vol | E1_default_stress | 2 | naive-momentum | 2.402 | [1.531, 3.249] | 0.2061 |
| high_vol | E1_default_stress | 3 | poe:claude-opus-4.7 | 0.659 | [-0.223, 1.509] | 0.0638 |
| high_vol | E1_default_stress | 4 | buy-and-hold | 0.357 | [-0.736, 1.408] | 0.0494 |
| high_vol | E1_default_stress | 5 | risk-parity | 0.057 | [-1.131, 1.336] | 0.0133 |
| high_vol | E1_default_stress | 6 | poe:gemini-3.1-pro | -0.141 | [-0.853, 0.530] | -0.0168 |
| high_vol | E1_default_stress | 7 | minimum-variance | -0.143 | [-1.250, 1.060] | -0.0177 |
| high_vol | E1_default_stress | 8 | random | -0.224 | [-1.666, 1.039] | -0.0122 |
| high_vol | E1_default_stress | 9 | mean-reversion | -2.862 | [-3.558, -2.078] | -0.2046 |
