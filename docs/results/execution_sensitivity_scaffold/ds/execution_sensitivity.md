# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| calm | E0_ideal | E1_default_stress | 0.930 | 0.500 |
| calm | E0_ideal | E2_harsh_corner | 0.817 | 1.000 |
| calm | E1_default_stress | E2_harsh_corner | 0.722 | 0.500 |
| high_vol | E0_ideal | E1_default_stress | 0.761 | 0.500 |
| high_vol | E0_ideal | E2_harsh_corner | 0.592 | 0.200 |
| high_vol | E1_default_stress | E2_harsh_corner | 0.444 | 0.500 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| calm | E0_ideal | 1 | buy-and-hold | 23.381 | [21.123, 25.611] | 0.0932 |
| calm | E0_ideal | 2 | minimum-variance | 23.323 | [21.096, 25.556] | 0.0932 |
| calm | E0_ideal | 3 | risk-parity | 23.113 | [20.901, 25.280] | 0.0896 |
| calm | E0_ideal | 4 | naive-momentum | 19.889 | [18.404, 21.379] | 0.0797 |
| calm | E0_ideal | 5 | random | 16.364 | [14.462, 18.053] | 0.0621 |
| calm | E0_ideal | 6 | deepseek:deepseek-v4-pro+mem | 10.926 | [7.107, 15.189] | 0.0348 |
| calm | E0_ideal | 7 | memory-aware | 8.402 | [7.120, 9.712] | 0.0203 |
| calm | E0_ideal | 8 | signal-weighted | 8.402 | [7.120, 9.712] | 0.0203 |
| calm | E0_ideal | 9 | mean-reversion | 2.258 | [0.844, 3.896] | 0.0023 |
| calm | E1_default_stress | 1 | buy-and-hold | 16.687 | [15.351, 18.130] | 0.0885 |
| calm | E1_default_stress | 2 | minimum-variance | 15.311 | [14.259, 16.463] | 0.0853 |
| calm | E1_default_stress | 3 | naive-momentum | 15.248 | [13.624, 17.040] | 0.0732 |
| calm | E1_default_stress | 4 | risk-parity | 15.226 | [13.868, 16.754] | 0.0800 |
| calm | E1_default_stress | 5 | random | 11.735 | [9.983, 13.672] | 0.0544 |
| calm | E1_default_stress | 6 | deepseek:deepseek-v4-pro+mem | 7.569 | [2.714, 11.724] | 0.0414 |
| calm | E1_default_stress | 7 | memory-aware | 6.407 | [4.963, 8.032] | 0.0103 |
| calm | E1_default_stress | 8 | signal-weighted | 6.402 | [4.959, 8.027] | 0.0103 |
| calm | E1_default_stress | 9 | mean-reversion | 2.714 | [0.918, 4.829] | 0.0041 |
| calm | E2_harsh_corner | 1 | minimum-variance | 14.954 | [13.118, 16.601] | 0.0741 |
| calm | E2_harsh_corner | 2 | risk-parity | 14.655 | [12.753, 16.401] | 0.0720 |
| calm | E2_harsh_corner | 3 | buy-and-hold | 14.494 | [12.594, 16.409] | 0.0723 |
| calm | E2_harsh_corner | 4 | naive-momentum | 13.316 | [12.039, 14.479] | 0.0776 |
| calm | E2_harsh_corner | 5 | deepseek:deepseek-v4-pro+mem | 12.176 | [9.766, 14.428] | 0.0538 |
| calm | E2_harsh_corner | 6 | random | 12.163 | [10.232, 14.174] | 0.0599 |
| calm | E2_harsh_corner | 7 | signal-weighted | 7.436 | [5.655, 9.011] | 0.0168 |
| calm | E2_harsh_corner | 8 | memory-aware | 7.433 | [5.652, 9.006] | 0.0168 |
| calm | E2_harsh_corner | 9 | mean-reversion | 3.718 | [1.478, 6.353] | 0.0106 |
| high_vol | E0_ideal | 1 | risk-parity | 11.072 | [8.796, 13.580] | 0.0900 |
| high_vol | E0_ideal | 2 | buy-and-hold | 10.951 | [8.994, 12.917] | 0.0994 |
| high_vol | E0_ideal | 3 | naive-momentum | 10.902 | [8.252, 13.783] | 0.0779 |
| high_vol | E0_ideal | 4 | minimum-variance | 10.075 | [8.040, 12.182] | 0.0855 |
| high_vol | E0_ideal | 5 | random | 9.348 | [7.264, 11.734] | 0.0733 |
| high_vol | E0_ideal | 6 | deepseek:deepseek-v4-pro+mem | 8.468 | [5.239, 11.683] | 0.0518 |
| high_vol | E0_ideal | 7 | memory-aware | 6.128 | [2.646, 8.988] | 0.0119 |
| high_vol | E0_ideal | 8 | signal-weighted | 6.128 | [2.646, 8.988] | 0.0119 |
| high_vol | E0_ideal | 9 | mean-reversion | 3.721 | [0.249, 6.729] | 0.0166 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 9.457 | [7.455, 11.574] | 0.1044 |
| high_vol | E1_default_stress | 2 | risk-parity | 8.693 | [6.575, 10.900] | 0.0872 |
| high_vol | E1_default_stress | 3 | minimum-variance | 8.559 | [6.715, 10.330] | 0.0810 |
| high_vol | E1_default_stress | 4 | deepseek:deepseek-v4-pro+mem | 8.441 | [6.350, 10.580] | 0.0548 |
| high_vol | E1_default_stress | 5 | naive-momentum | 8.260 | [6.422, 10.115] | 0.0754 |
| high_vol | E1_default_stress | 6 | random | 7.750 | [5.065, 10.033] | 0.0796 |
| high_vol | E1_default_stress | 7 | memory-aware | 4.884 | [1.382, 7.231] | 0.0121 |
| high_vol | E1_default_stress | 8 | signal-weighted | 4.849 | [1.373, 7.160] | 0.0124 |
| high_vol | E1_default_stress | 9 | mean-reversion | 3.301 | [0.243, 5.905] | 0.0279 |
| high_vol | E2_harsh_corner | 1 | minimum-variance | 10.128 | [8.375, 12.081] | 0.0986 |
| high_vol | E2_harsh_corner | 2 | risk-parity | 9.991 | [8.139, 12.026] | 0.1010 |
| high_vol | E2_harsh_corner | 3 | random | 9.494 | [7.629, 11.310] | 0.0904 |
| high_vol | E2_harsh_corner | 4 | buy-and-hold | 9.205 | [6.975, 11.763] | 0.0924 |
| high_vol | E2_harsh_corner | 5 | naive-momentum | 7.088 | [4.493, 9.250] | 0.0694 |
| high_vol | E2_harsh_corner | 6 | deepseek:deepseek-v4-pro+mem | 6.240 | [3.988, 8.219] | 0.0623 |
| high_vol | E2_harsh_corner | 7 | mean-reversion | 5.102 | [1.961, 8.107] | 0.0427 |
| high_vol | E2_harsh_corner | 8 | signal-weighted | 0.465 | [-2.792, 3.665] | 0.0112 |
| high_vol | E2_harsh_corner | 9 | memory-aware | 0.465 | [-2.795, 3.663] | 0.0112 |
