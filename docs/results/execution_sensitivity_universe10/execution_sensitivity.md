# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| calm | E0_ideal | E1_default_stress | 0.857 | 0.500 |
| calm | E0_ideal | E2_harsh_corner | 1.000 | 1.000 |
| calm | E0_ideal | E2_latency_3 | 1.000 | 1.000 |
| calm | E0_ideal | E2_participation_1pct | 0.857 | 0.500 |
| calm | E0_ideal | E2_spread_20bps | 0.857 | 0.500 |
| calm | E1_default_stress | E2_harsh_corner | 0.857 | 0.500 |
| calm | E1_default_stress | E2_latency_3 | 0.857 | 0.500 |
| calm | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| calm | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| calm | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| calm | E2_harsh_corner | E2_participation_1pct | 0.857 | 0.500 |
| calm | E2_harsh_corner | E2_spread_20bps | 0.857 | 0.500 |
| calm | E2_latency_3 | E2_participation_1pct | 0.857 | 0.500 |
| calm | E2_latency_3 | E2_spread_20bps | 0.857 | 0.500 |
| calm | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |
| high_vol | E0_ideal | E1_default_stress | 0.929 | 0.500 |
| high_vol | E0_ideal | E2_harsh_corner | 0.786 | 0.500 |
| high_vol | E0_ideal | E2_latency_3 | 0.786 | 0.500 |
| high_vol | E0_ideal | E2_participation_1pct | 0.929 | 0.500 |
| high_vol | E0_ideal | E2_spread_20bps | 0.929 | 0.500 |
| high_vol | E1_default_stress | E2_harsh_corner | 0.857 | 0.500 |
| high_vol | E1_default_stress | E2_latency_3 | 0.857 | 0.500 |
| high_vol | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| high_vol | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| high_vol | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| high_vol | E2_harsh_corner | E2_participation_1pct | 0.857 | 0.500 |
| high_vol | E2_harsh_corner | E2_spread_20bps | 0.857 | 0.500 |
| high_vol | E2_latency_3 | E2_participation_1pct | 0.857 | 0.500 |
| high_vol | E2_latency_3 | E2_spread_20bps | 0.857 | 0.500 |
| high_vol | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |
| jump_tail | E0_ideal | E1_default_stress | 0.786 | 1.000 |
| jump_tail | E0_ideal | E2_harsh_corner | 0.286 | 0.500 |
| jump_tail | E0_ideal | E2_latency_3 | 0.286 | 0.500 |
| jump_tail | E0_ideal | E2_participation_1pct | 0.786 | 1.000 |
| jump_tail | E0_ideal | E2_spread_20bps | 0.786 | 1.000 |
| jump_tail | E1_default_stress | E2_harsh_corner | 0.357 | 0.500 |
| jump_tail | E1_default_stress | E2_latency_3 | 0.357 | 0.500 |
| jump_tail | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| jump_tail | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| jump_tail | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| jump_tail | E2_harsh_corner | E2_participation_1pct | 0.357 | 0.500 |
| jump_tail | E2_harsh_corner | E2_spread_20bps | 0.357 | 0.500 |
| jump_tail | E2_latency_3 | E2_participation_1pct | 0.357 | 0.500 |
| jump_tail | E2_latency_3 | E2_spread_20bps | 0.357 | 0.500 |
| jump_tail | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| calm | E0_ideal | 1 | buy-and-hold | 47.371 | [43.421, 51.234] | 0.0961 |
| calm | E0_ideal | 2 | minimum-variance | 44.253 | [39.478, 49.511] | 0.0950 |
| calm | E0_ideal | 3 | no-trade-band | 38.193 | [33.263, 43.304] | 0.0867 |
| calm | E0_ideal | 4 | risk-parity | 37.824 | [32.922, 42.506] | 0.0900 |
| calm | E0_ideal | 5 | naive-momentum | 33.381 | [31.655, 34.969] | 0.1236 |
| calm | E0_ideal | 6 | random | 22.573 | [19.778, 26.747] | 0.0687 |
| calm | E0_ideal | 7 | signal-weighted | 13.767 | [11.736, 15.915] | 0.0391 |
| calm | E0_ideal | 8 | mean-reversion | -2.905 | [-5.375, -0.404] | -0.0068 |
| calm | E1_default_stress | 1 | buy-and-hold | 28.363 | [26.995, 29.616] | 0.0847 |
| calm | E1_default_stress | 2 | minimum-variance | 25.140 | [22.531, 27.532] | 0.0772 |
| calm | E1_default_stress | 3 | naive-momentum | 22.735 | [21.504, 23.845] | 0.0988 |
| calm | E1_default_stress | 4 | no-trade-band | 22.421 | [20.188, 24.690] | 0.0698 |
| calm | E1_default_stress | 5 | risk-parity | 22.322 | [19.413, 24.917] | 0.0672 |
| calm | E1_default_stress | 6 | random | 17.743 | [15.865, 19.738] | 0.0558 |
| calm | E1_default_stress | 7 | signal-weighted | 10.563 | [8.290, 13.027] | 0.0424 |
| calm | E1_default_stress | 8 | mean-reversion | -3.994 | [-6.102, -1.495] | -0.0109 |
| calm | E2_harsh_corner | 1 | buy-and-hold | 17.650 | [17.007, 18.309] | 0.0636 |
| calm | E2_harsh_corner | 2 | minimum-variance | 17.167 | [16.431, 17.899] | 0.0611 |
| calm | E2_harsh_corner | 3 | no-trade-band | 16.996 | [15.843, 17.905] | 0.0606 |
| calm | E2_harsh_corner | 4 | risk-parity | 16.007 | [14.030, 17.468] | 0.0579 |
| calm | E2_harsh_corner | 5 | naive-momentum | 14.503 | [13.509, 15.359] | 0.0698 |
| calm | E2_harsh_corner | 6 | random | 12.135 | [10.605, 13.437] | 0.0475 |
| calm | E2_harsh_corner | 7 | signal-weighted | 9.553 | [7.881, 11.157] | 0.0373 |
| calm | E2_harsh_corner | 8 | mean-reversion | 1.452 | [-1.766, 4.710] | 0.0033 |
| calm | E2_latency_3 | 1 | buy-and-hold | 18.636 | [18.006, 19.280] | 0.0650 |
| calm | E2_latency_3 | 2 | minimum-variance | 18.213 | [17.510, 18.937] | 0.0631 |
| calm | E2_latency_3 | 3 | no-trade-band | 18.026 | [16.871, 18.903] | 0.0625 |
| calm | E2_latency_3 | 4 | risk-parity | 17.074 | [15.050, 18.533] | 0.0603 |
| calm | E2_latency_3 | 5 | naive-momentum | 15.251 | [14.295, 16.079] | 0.0723 |
| calm | E2_latency_3 | 6 | random | 13.311 | [11.731, 14.654] | 0.0509 |
| calm | E2_latency_3 | 7 | signal-weighted | 10.449 | [8.873, 11.996] | 0.0405 |
| calm | E2_latency_3 | 8 | mean-reversion | 2.438 | [-0.767, 5.678] | 0.0061 |
| calm | E2_participation_1pct | 1 | buy-and-hold | 28.363 | [26.995, 29.616] | 0.0847 |
| calm | E2_participation_1pct | 2 | minimum-variance | 25.140 | [22.531, 27.532] | 0.0772 |
| calm | E2_participation_1pct | 3 | naive-momentum | 22.735 | [21.504, 23.845] | 0.0988 |
| calm | E2_participation_1pct | 4 | no-trade-band | 22.421 | [20.188, 24.690] | 0.0698 |
| calm | E2_participation_1pct | 5 | risk-parity | 22.322 | [19.413, 24.917] | 0.0672 |
| calm | E2_participation_1pct | 6 | random | 17.743 | [15.865, 19.738] | 0.0558 |
| calm | E2_participation_1pct | 7 | signal-weighted | 10.563 | [8.290, 13.027] | 0.0424 |
| calm | E2_participation_1pct | 8 | mean-reversion | -3.994 | [-6.102, -1.495] | -0.0109 |
| calm | E2_spread_20bps | 1 | buy-and-hold | 26.474 | [25.195, 27.671] | 0.0834 |
| calm | E2_spread_20bps | 2 | minimum-variance | 22.985 | [20.532, 25.245] | 0.0737 |
| calm | E2_spread_20bps | 3 | naive-momentum | 21.471 | [20.213, 22.596] | 0.0948 |
| calm | E2_spread_20bps | 4 | no-trade-band | 20.393 | [18.318, 22.503] | 0.0654 |
| calm | E2_spread_20bps | 5 | risk-parity | 20.001 | [17.116, 22.510] | 0.0619 |
| calm | E2_spread_20bps | 6 | random | 15.203 | [13.523, 17.156] | 0.0496 |
| calm | E2_spread_20bps | 7 | signal-weighted | 9.332 | [7.047, 11.778] | 0.0378 |
| calm | E2_spread_20bps | 8 | mean-reversion | -5.202 | [-7.290, -2.724] | -0.0144 |
| high_vol | E0_ideal | 1 | buy-and-hold | 13.288 | [10.568, 15.334] | 0.0746 |
| high_vol | E0_ideal | 2 | no-trade-band | 13.220 | [9.879, 16.287] | 0.0705 |
| high_vol | E0_ideal | 3 | risk-parity | 13.083 | [9.756, 16.043] | 0.0727 |
| high_vol | E0_ideal | 4 | minimum-variance | 11.907 | [8.884, 14.644] | 0.0669 |
| high_vol | E0_ideal | 5 | naive-momentum | 10.126 | [7.464, 12.667] | 0.0753 |
| high_vol | E0_ideal | 6 | random | 8.288 | [5.601, 11.158] | 0.0476 |
| high_vol | E0_ideal | 7 | signal-weighted | 7.348 | [4.537, 9.842] | 0.0343 |
| high_vol | E0_ideal | 8 | mean-reversion | 2.988 | [-0.895, 7.279] | 0.0146 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 11.394 | [8.124, 14.267] | 0.0637 |
| high_vol | E1_default_stress | 2 | no-trade-band | 8.253 | [4.942, 11.294] | 0.0475 |
| high_vol | E1_default_stress | 3 | minimum-variance | 7.838 | [4.097, 11.540] | 0.0447 |
| high_vol | E1_default_stress | 4 | risk-parity | 7.503 | [4.636, 10.188] | 0.0424 |
| high_vol | E1_default_stress | 5 | naive-momentum | 6.813 | [4.377, 8.918] | 0.0541 |
| high_vol | E1_default_stress | 6 | random | 5.904 | [2.569, 9.088] | 0.0321 |
| high_vol | E1_default_stress | 7 | signal-weighted | 5.107 | [2.945, 7.320] | 0.0346 |
| high_vol | E1_default_stress | 8 | mean-reversion | 1.773 | [-1.215, 4.748] | 0.0127 |
| high_vol | E2_harsh_corner | 1 | buy-and-hold | 8.573 | [6.024, 10.951] | 0.0501 |
| high_vol | E2_harsh_corner | 2 | minimum-variance | 7.768 | [5.003, 10.475] | 0.0473 |
| high_vol | E2_harsh_corner | 3 | risk-parity | 7.101 | [3.784, 9.702] | 0.0455 |
| high_vol | E2_harsh_corner | 4 | no-trade-band | 6.999 | [3.764, 9.838] | 0.0425 |
| high_vol | E2_harsh_corner | 5 | naive-momentum | 6.912 | [4.705, 9.101] | 0.0492 |
| high_vol | E2_harsh_corner | 6 | random | 5.311 | [2.913, 7.487] | 0.0303 |
| high_vol | E2_harsh_corner | 7 | signal-weighted | 2.547 | [-0.408, 5.368] | 0.0174 |
| high_vol | E2_harsh_corner | 8 | mean-reversion | 1.720 | [-2.615, 6.001] | 0.0091 |
| high_vol | E2_latency_3 | 1 | buy-and-hold | 8.944 | [6.373, 11.376] | 0.0515 |
| high_vol | E2_latency_3 | 2 | minimum-variance | 8.262 | [5.466, 10.993] | 0.0496 |
| high_vol | E2_latency_3 | 3 | risk-parity | 7.518 | [4.186, 10.155] | 0.0477 |
| high_vol | E2_latency_3 | 4 | no-trade-band | 7.366 | [4.102, 10.207] | 0.0440 |
| high_vol | E2_latency_3 | 5 | naive-momentum | 7.342 | [5.180, 9.509] | 0.0521 |
| high_vol | E2_latency_3 | 6 | random | 5.936 | [3.541, 8.094] | 0.0334 |
| high_vol | E2_latency_3 | 7 | signal-weighted | 3.048 | [0.041, 5.877] | 0.0204 |
| high_vol | E2_latency_3 | 8 | mean-reversion | 2.235 | [-2.177, 6.624] | 0.0121 |
| high_vol | E2_participation_1pct | 1 | buy-and-hold | 11.394 | [8.124, 14.267] | 0.0637 |
| high_vol | E2_participation_1pct | 2 | no-trade-band | 8.253 | [4.942, 11.294] | 0.0475 |
| high_vol | E2_participation_1pct | 3 | minimum-variance | 7.838 | [4.097, 11.540] | 0.0447 |
| high_vol | E2_participation_1pct | 4 | risk-parity | 7.503 | [4.636, 10.188] | 0.0424 |
| high_vol | E2_participation_1pct | 5 | naive-momentum | 6.813 | [4.377, 8.918] | 0.0541 |
| high_vol | E2_participation_1pct | 6 | random | 5.904 | [2.569, 9.088] | 0.0321 |
| high_vol | E2_participation_1pct | 7 | signal-weighted | 5.107 | [2.945, 7.320] | 0.0346 |
| high_vol | E2_participation_1pct | 8 | mean-reversion | 1.773 | [-1.215, 4.748] | 0.0127 |
| high_vol | E2_spread_20bps | 1 | buy-and-hold | 10.950 | [7.773, 13.739] | 0.0623 |
| high_vol | E2_spread_20bps | 2 | no-trade-band | 7.201 | [4.151, 9.831] | 0.0424 |
| high_vol | E2_spread_20bps | 3 | minimum-variance | 7.106 | [3.392, 10.687] | 0.0410 |
| high_vol | E2_spread_20bps | 4 | risk-parity | 6.520 | [3.713, 9.161] | 0.0372 |
| high_vol | E2_spread_20bps | 5 | naive-momentum | 6.089 | [3.585, 8.212] | 0.0489 |
| high_vol | E2_spread_20bps | 6 | random | 4.768 | [1.463, 7.907] | 0.0263 |
| high_vol | E2_spread_20bps | 7 | signal-weighted | 4.466 | [2.257, 6.748] | 0.0303 |
| high_vol | E2_spread_20bps | 8 | mean-reversion | 1.175 | [-1.763, 4.135] | 0.0079 |
| jump_tail | E0_ideal | 1 | naive-momentum | 11.315 | [7.447, 16.179] | 0.1182 |
| jump_tail | E0_ideal | 2 | minimum-variance | 11.091 | [4.878, 18.355] | 0.0854 |
| jump_tail | E0_ideal | 3 | buy-and-hold | 10.912 | [5.674, 17.164] | 0.0836 |
| jump_tail | E0_ideal | 4 | risk-parity | 9.651 | [4.776, 14.855] | 0.0869 |
| jump_tail | E0_ideal | 5 | no-trade-band | 9.193 | [4.238, 13.986] | 0.0815 |
| jump_tail | E0_ideal | 6 | random | 5.126 | [1.812, 8.870] | 0.0417 |
| jump_tail | E0_ideal | 7 | signal-weighted | 4.878 | [1.990, 7.683] | 0.0398 |
| jump_tail | E0_ideal | 8 | mean-reversion | 1.233 | [-1.498, 4.307] | 0.0094 |
| jump_tail | E1_default_stress | 1 | buy-and-hold | 8.653 | [4.735, 13.013] | 0.0708 |
| jump_tail | E1_default_stress | 2 | minimum-variance | 7.897 | [3.879, 12.102] | 0.0766 |
| jump_tail | E1_default_stress | 3 | naive-momentum | 5.911 | [2.867, 9.822] | 0.0677 |
| jump_tail | E1_default_stress | 4 | risk-parity | 5.055 | [0.662, 9.619] | 0.0366 |
| jump_tail | E1_default_stress | 5 | no-trade-band | 4.757 | [0.076, 9.679] | 0.0348 |
| jump_tail | E1_default_stress | 6 | random | 3.699 | [0.475, 6.935] | 0.0284 |
| jump_tail | E1_default_stress | 7 | signal-weighted | 2.576 | [-1.506, 6.275] | 0.0187 |
| jump_tail | E1_default_stress | 8 | mean-reversion | 0.210 | [-2.756, 3.861] | 0.0112 |
| jump_tail | E2_harsh_corner | 1 | minimum-variance | 6.966 | [4.376, 9.848] | 0.0619 |
| jump_tail | E2_harsh_corner | 2 | buy-and-hold | 6.893 | [4.776, 9.131] | 0.0565 |
| jump_tail | E2_harsh_corner | 3 | random | 5.650 | [3.007, 8.276] | 0.0486 |
| jump_tail | E2_harsh_corner | 4 | no-trade-band | 5.300 | [2.189, 8.208] | 0.0472 |
| jump_tail | E2_harsh_corner | 5 | risk-parity | 4.645 | [1.621, 7.447] | 0.0450 |
| jump_tail | E2_harsh_corner | 6 | mean-reversion | 4.305 | [0.515, 7.695] | 0.0577 |
| jump_tail | E2_harsh_corner | 7 | naive-momentum | 3.996 | [0.799, 7.067] | 0.0454 |
| jump_tail | E2_harsh_corner | 8 | signal-weighted | 1.600 | [-0.773, 4.096] | 0.0192 |
| jump_tail | E2_latency_3 | 1 | minimum-variance | 7.282 | [4.673, 10.190] | 0.0642 |
| jump_tail | E2_latency_3 | 2 | buy-and-hold | 7.158 | [5.033, 9.422] | 0.0581 |
| jump_tail | E2_latency_3 | 3 | random | 6.043 | [3.366, 8.672] | 0.0517 |
| jump_tail | E2_latency_3 | 4 | no-trade-band | 5.580 | [2.458, 8.538] | 0.0494 |
| jump_tail | E2_latency_3 | 5 | risk-parity | 4.921 | [1.894, 7.736] | 0.0475 |
| jump_tail | E2_latency_3 | 6 | mean-reversion | 4.588 | [0.827, 7.966] | 0.0608 |
| jump_tail | E2_latency_3 | 7 | naive-momentum | 4.288 | [1.044, 7.363] | 0.0484 |
| jump_tail | E2_latency_3 | 8 | signal-weighted | 1.969 | [-0.432, 4.568] | 0.0223 |
| jump_tail | E2_participation_1pct | 1 | buy-and-hold | 8.653 | [4.735, 13.013] | 0.0708 |
| jump_tail | E2_participation_1pct | 2 | minimum-variance | 7.897 | [3.879, 12.102] | 0.0766 |
| jump_tail | E2_participation_1pct | 3 | naive-momentum | 5.911 | [2.867, 9.822] | 0.0677 |
| jump_tail | E2_participation_1pct | 4 | risk-parity | 5.055 | [0.662, 9.619] | 0.0366 |
| jump_tail | E2_participation_1pct | 5 | no-trade-band | 4.757 | [0.076, 9.679] | 0.0348 |
| jump_tail | E2_participation_1pct | 6 | random | 3.699 | [0.475, 6.935] | 0.0284 |
| jump_tail | E2_participation_1pct | 7 | signal-weighted | 2.576 | [-1.506, 6.275] | 0.0187 |
| jump_tail | E2_participation_1pct | 8 | mean-reversion | 0.210 | [-2.756, 3.861] | 0.0112 |
| jump_tail | E2_spread_20bps | 1 | buy-and-hold | 8.361 | [4.509, 12.611] | 0.0692 |
| jump_tail | E2_spread_20bps | 2 | minimum-variance | 7.466 | [3.507, 11.598] | 0.0727 |
| jump_tail | E2_spread_20bps | 3 | naive-momentum | 5.499 | [2.489, 9.390] | 0.0629 |
| jump_tail | E2_spread_20bps | 4 | risk-parity | 4.478 | [0.289, 8.866] | 0.0314 |
| jump_tail | E2_spread_20bps | 5 | no-trade-band | 4.301 | [-0.234, 9.051] | 0.0307 |
| jump_tail | E2_spread_20bps | 6 | random | 3.075 | [-0.123, 6.195] | 0.0229 |
| jump_tail | E2_spread_20bps | 7 | signal-weighted | 2.053 | [-2.017, 5.762] | 0.0139 |
| jump_tail | E2_spread_20bps | 8 | mean-reversion | -0.190 | [-3.201, 3.476] | 0.0064 |
