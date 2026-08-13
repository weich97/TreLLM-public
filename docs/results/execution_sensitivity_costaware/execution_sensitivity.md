# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| calm | E0_ideal | E1_default_stress | 0.857 | 0.500 |
| calm | E0_ideal | E2_harsh_corner | 0.714 | 0.500 |
| calm | E0_ideal | E2_latency_3 | 0.714 | 0.500 |
| calm | E0_ideal | E2_participation_1pct | 0.857 | 0.500 |
| calm | E0_ideal | E2_spread_20bps | 0.857 | 0.500 |
| calm | E1_default_stress | E2_harsh_corner | 0.571 | 0.200 |
| calm | E1_default_stress | E2_latency_3 | 0.571 | 0.200 |
| calm | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| calm | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| calm | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| calm | E2_harsh_corner | E2_participation_1pct | 0.571 | 0.200 |
| calm | E2_harsh_corner | E2_spread_20bps | 0.571 | 0.200 |
| calm | E2_latency_3 | E2_participation_1pct | 0.571 | 0.200 |
| calm | E2_latency_3 | E2_spread_20bps | 0.571 | 0.200 |
| calm | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |
| high_vol | E0_ideal | E1_default_stress | 0.786 | 1.000 |
| high_vol | E0_ideal | E2_harsh_corner | 0.500 | 0.500 |
| high_vol | E0_ideal | E2_latency_3 | 0.500 | 0.500 |
| high_vol | E0_ideal | E2_participation_1pct | 0.786 | 1.000 |
| high_vol | E0_ideal | E2_spread_20bps | 0.786 | 1.000 |
| high_vol | E1_default_stress | E2_harsh_corner | 0.429 | 0.500 |
| high_vol | E1_default_stress | E2_latency_3 | 0.429 | 0.500 |
| high_vol | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| high_vol | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| high_vol | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| high_vol | E2_harsh_corner | E2_participation_1pct | 0.429 | 0.500 |
| high_vol | E2_harsh_corner | E2_spread_20bps | 0.429 | 0.500 |
| high_vol | E2_latency_3 | E2_participation_1pct | 0.429 | 0.500 |
| high_vol | E2_latency_3 | E2_spread_20bps | 0.429 | 0.500 |
| high_vol | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |
| jump_tail | E0_ideal | E1_default_stress | 0.714 | 0.500 |
| jump_tail | E0_ideal | E2_harsh_corner | 0.500 | 0.200 |
| jump_tail | E0_ideal | E2_latency_3 | 0.500 | 0.200 |
| jump_tail | E0_ideal | E2_participation_1pct | 0.714 | 0.500 |
| jump_tail | E0_ideal | E2_spread_20bps | 0.714 | 0.500 |
| jump_tail | E1_default_stress | E2_harsh_corner | 0.786 | 0.500 |
| jump_tail | E1_default_stress | E2_latency_3 | 0.786 | 0.500 |
| jump_tail | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| jump_tail | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| jump_tail | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| jump_tail | E2_harsh_corner | E2_participation_1pct | 0.786 | 0.500 |
| jump_tail | E2_harsh_corner | E2_spread_20bps | 0.786 | 0.500 |
| jump_tail | E2_latency_3 | E2_participation_1pct | 0.786 | 0.500 |
| jump_tail | E2_latency_3 | E2_spread_20bps | 0.786 | 0.500 |
| jump_tail | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| calm | E0_ideal | 1 | buy-and-hold | 23.381 | [21.123, 25.611] | 0.0932 |
| calm | E0_ideal | 2 | minimum-variance | 23.323 | [21.096, 25.556] | 0.0932 |
| calm | E0_ideal | 3 | risk-parity | 23.113 | [20.901, 25.280] | 0.0896 |
| calm | E0_ideal | 4 | no-trade-band | 23.083 | [20.893, 25.256] | 0.0896 |
| calm | E0_ideal | 5 | naive-momentum | 19.889 | [18.404, 21.379] | 0.0797 |
| calm | E0_ideal | 6 | random | 16.364 | [14.462, 18.053] | 0.0621 |
| calm | E0_ideal | 7 | signal-weighted | 8.402 | [7.120, 9.712] | 0.0203 |
| calm | E0_ideal | 8 | mean-reversion | 2.258 | [0.844, 3.896] | 0.0023 |
| calm | E1_default_stress | 1 | buy-and-hold | 16.687 | [15.351, 18.130] | 0.0885 |
| calm | E1_default_stress | 2 | minimum-variance | 15.311 | [14.259, 16.463] | 0.0853 |
| calm | E1_default_stress | 3 | naive-momentum | 15.248 | [13.624, 17.040] | 0.0732 |
| calm | E1_default_stress | 4 | risk-parity | 15.226 | [13.868, 16.754] | 0.0800 |
| calm | E1_default_stress | 5 | no-trade-band | 15.201 | [13.843, 16.734] | 0.0803 |
| calm | E1_default_stress | 6 | random | 11.735 | [9.983, 13.672] | 0.0544 |
| calm | E1_default_stress | 7 | signal-weighted | 6.402 | [4.959, 8.027] | 0.0103 |
| calm | E1_default_stress | 8 | mean-reversion | 2.714 | [0.918, 4.829] | 0.0041 |
| calm | E2_harsh_corner | 1 | minimum-variance | 14.954 | [13.118, 16.601] | 0.0741 |
| calm | E2_harsh_corner | 2 | no-trade-band | 14.658 | [12.757, 16.403] | 0.0721 |
| calm | E2_harsh_corner | 3 | risk-parity | 14.655 | [12.753, 16.401] | 0.0720 |
| calm | E2_harsh_corner | 4 | buy-and-hold | 14.494 | [12.594, 16.409] | 0.0723 |
| calm | E2_harsh_corner | 5 | naive-momentum | 13.316 | [12.039, 14.479] | 0.0776 |
| calm | E2_harsh_corner | 6 | random | 12.163 | [10.232, 14.174] | 0.0599 |
| calm | E2_harsh_corner | 7 | signal-weighted | 7.436 | [5.655, 9.011] | 0.0168 |
| calm | E2_harsh_corner | 8 | mean-reversion | 3.718 | [1.478, 6.353] | 0.0106 |
| calm | E2_latency_3 | 1 | minimum-variance | 15.452 | [13.593, 17.095] | 0.0760 |
| calm | E2_latency_3 | 2 | no-trade-band | 15.154 | [13.225, 16.926] | 0.0740 |
| calm | E2_latency_3 | 3 | risk-parity | 15.152 | [13.221, 16.924] | 0.0740 |
| calm | E2_latency_3 | 4 | buy-and-hold | 14.992 | [13.050, 16.947] | 0.0742 |
| calm | E2_latency_3 | 5 | naive-momentum | 13.685 | [12.409, 14.851] | 0.0800 |
| calm | E2_latency_3 | 6 | random | 12.646 | [10.693, 14.661] | 0.0621 |
| calm | E2_latency_3 | 7 | signal-weighted | 7.900 | [6.127, 9.485] | 0.0177 |
| calm | E2_latency_3 | 8 | mean-reversion | 3.948 | [1.569, 6.710] | 0.0113 |
| calm | E2_participation_1pct | 1 | buy-and-hold | 16.687 | [15.351, 18.130] | 0.0885 |
| calm | E2_participation_1pct | 2 | minimum-variance | 15.311 | [14.259, 16.463] | 0.0853 |
| calm | E2_participation_1pct | 3 | naive-momentum | 15.248 | [13.624, 17.040] | 0.0732 |
| calm | E2_participation_1pct | 4 | risk-parity | 15.226 | [13.868, 16.754] | 0.0800 |
| calm | E2_participation_1pct | 5 | no-trade-band | 15.201 | [13.843, 16.734] | 0.0803 |
| calm | E2_participation_1pct | 6 | random | 11.735 | [9.983, 13.672] | 0.0544 |
| calm | E2_participation_1pct | 7 | signal-weighted | 6.402 | [4.959, 8.027] | 0.0103 |
| calm | E2_participation_1pct | 8 | mean-reversion | 2.714 | [0.918, 4.829] | 0.0041 |
| calm | E2_spread_20bps | 1 | buy-and-hold | 15.941 | [14.635, 17.359] | 0.0855 |
| calm | E2_spread_20bps | 2 | minimum-variance | 14.605 | [13.610, 15.688] | 0.0822 |
| calm | E2_spread_20bps | 3 | naive-momentum | 14.487 | [12.920, 16.203] | 0.0700 |
| calm | E2_spread_20bps | 4 | risk-parity | 14.462 | [13.143, 15.945] | 0.0767 |
| calm | E2_spread_20bps | 5 | no-trade-band | 14.444 | [13.117, 15.939] | 0.0770 |
| calm | E2_spread_20bps | 6 | random | 10.924 | [9.168, 12.850] | 0.0507 |
| calm | E2_spread_20bps | 7 | signal-weighted | 5.672 | [4.268, 7.157] | 0.0089 |
| calm | E2_spread_20bps | 8 | mean-reversion | 2.347 | [0.563, 4.297] | 0.0035 |
| high_vol | E0_ideal | 1 | no-trade-band | 11.154 | [8.898, 13.605] | 0.0899 |
| high_vol | E0_ideal | 2 | risk-parity | 11.072 | [8.796, 13.580] | 0.0900 |
| high_vol | E0_ideal | 3 | buy-and-hold | 10.951 | [8.994, 12.917] | 0.0994 |
| high_vol | E0_ideal | 4 | naive-momentum | 10.902 | [8.252, 13.783] | 0.0779 |
| high_vol | E0_ideal | 5 | minimum-variance | 10.075 | [8.040, 12.182] | 0.0855 |
| high_vol | E0_ideal | 6 | random | 9.348 | [7.264, 11.734] | 0.0733 |
| high_vol | E0_ideal | 7 | signal-weighted | 6.128 | [2.646, 8.988] | 0.0119 |
| high_vol | E0_ideal | 8 | mean-reversion | 3.721 | [0.249, 6.729] | 0.0166 |
| high_vol | E1_default_stress | 1 | buy-and-hold | 9.457 | [7.455, 11.574] | 0.1044 |
| high_vol | E1_default_stress | 2 | no-trade-band | 8.729 | [6.523, 11.005] | 0.0873 |
| high_vol | E1_default_stress | 3 | risk-parity | 8.693 | [6.575, 10.900] | 0.0872 |
| high_vol | E1_default_stress | 4 | minimum-variance | 8.559 | [6.715, 10.330] | 0.0810 |
| high_vol | E1_default_stress | 5 | naive-momentum | 8.260 | [6.422, 10.115] | 0.0754 |
| high_vol | E1_default_stress | 6 | random | 7.750 | [5.065, 10.033] | 0.0796 |
| high_vol | E1_default_stress | 7 | signal-weighted | 4.849 | [1.373, 7.160] | 0.0124 |
| high_vol | E1_default_stress | 8 | mean-reversion | 3.301 | [0.243, 5.905] | 0.0279 |
| high_vol | E2_harsh_corner | 1 | minimum-variance | 10.128 | [8.375, 12.081] | 0.0986 |
| high_vol | E2_harsh_corner | 2 | no-trade-band | 9.997 | [8.172, 11.990] | 0.1011 |
| high_vol | E2_harsh_corner | 3 | risk-parity | 9.991 | [8.139, 12.026] | 0.1010 |
| high_vol | E2_harsh_corner | 4 | random | 9.494 | [7.629, 11.310] | 0.0904 |
| high_vol | E2_harsh_corner | 5 | buy-and-hold | 9.205 | [6.975, 11.763] | 0.0924 |
| high_vol | E2_harsh_corner | 6 | naive-momentum | 7.088 | [4.493, 9.250] | 0.0694 |
| high_vol | E2_harsh_corner | 7 | mean-reversion | 5.102 | [1.961, 8.107] | 0.0427 |
| high_vol | E2_harsh_corner | 8 | signal-weighted | 0.465 | [-2.792, 3.665] | 0.0112 |
| high_vol | E2_latency_3 | 1 | minimum-variance | 10.346 | [8.575, 12.318] | 0.1006 |
| high_vol | E2_latency_3 | 2 | no-trade-band | 10.201 | [8.357, 12.186] | 0.1031 |
| high_vol | E2_latency_3 | 3 | risk-parity | 10.200 | [8.347, 12.230] | 0.1030 |
| high_vol | E2_latency_3 | 4 | random | 9.716 | [7.853, 11.532] | 0.0928 |
| high_vol | E2_latency_3 | 5 | buy-and-hold | 9.415 | [7.170, 11.984] | 0.0943 |
| high_vol | E2_latency_3 | 6 | naive-momentum | 7.280 | [4.670, 9.434] | 0.0712 |
| high_vol | E2_latency_3 | 7 | mean-reversion | 5.330 | [2.185, 8.360] | 0.0445 |
| high_vol | E2_latency_3 | 8 | signal-weighted | 0.880 | [-2.295, 3.967] | 0.0119 |
| high_vol | E2_participation_1pct | 1 | buy-and-hold | 9.457 | [7.455, 11.574] | 0.1044 |
| high_vol | E2_participation_1pct | 2 | no-trade-band | 8.729 | [6.523, 11.005] | 0.0873 |
| high_vol | E2_participation_1pct | 3 | risk-parity | 8.693 | [6.575, 10.900] | 0.0872 |
| high_vol | E2_participation_1pct | 4 | minimum-variance | 8.559 | [6.715, 10.330] | 0.0810 |
| high_vol | E2_participation_1pct | 5 | naive-momentum | 8.260 | [6.422, 10.115] | 0.0754 |
| high_vol | E2_participation_1pct | 6 | random | 7.750 | [5.065, 10.033] | 0.0796 |
| high_vol | E2_participation_1pct | 7 | signal-weighted | 4.849 | [1.373, 7.160] | 0.0124 |
| high_vol | E2_participation_1pct | 8 | mean-reversion | 3.301 | [0.243, 5.905] | 0.0279 |
| high_vol | E2_spread_20bps | 1 | buy-and-hold | 9.154 | [7.142, 11.243] | 0.1013 |
| high_vol | E2_spread_20bps | 2 | no-trade-band | 8.367 | [6.147, 10.624] | 0.0839 |
| high_vol | E2_spread_20bps | 3 | risk-parity | 8.328 | [6.211, 10.519] | 0.0837 |
| high_vol | E2_spread_20bps | 4 | minimum-variance | 8.176 | [6.342, 9.901] | 0.0776 |
| high_vol | E2_spread_20bps | 5 | naive-momentum | 7.956 | [6.142, 9.774] | 0.0724 |
| high_vol | E2_spread_20bps | 6 | random | 7.317 | [4.604, 9.653] | 0.0756 |
| high_vol | E2_spread_20bps | 7 | signal-weighted | 4.323 | [0.847, 6.585] | 0.0112 |
| high_vol | E2_spread_20bps | 8 | mean-reversion | 3.010 | [-0.022, 5.587] | 0.0260 |
| jump_tail | E0_ideal | 1 | minimum-variance | 8.879 | [4.685, 13.774] | 0.1060 |
| jump_tail | E0_ideal | 2 | risk-parity | 8.650 | [4.180, 13.782] | 0.1016 |
| jump_tail | E0_ideal | 3 | no-trade-band | 8.514 | [4.147, 13.428] | 0.0998 |
| jump_tail | E0_ideal | 4 | buy-and-hold | 8.493 | [3.722, 13.979] | 0.1036 |
| jump_tail | E0_ideal | 5 | naive-momentum | 8.042 | [5.070, 10.896] | 0.0793 |
| jump_tail | E0_ideal | 6 | random | 7.546 | [4.040, 10.900] | 0.0839 |
| jump_tail | E0_ideal | 7 | signal-weighted | 7.132 | [5.850, 8.525] | 0.0279 |
| jump_tail | E0_ideal | 8 | mean-reversion | 0.991 | [-0.760, 2.788] | 0.0061 |
| jump_tail | E1_default_stress | 1 | naive-momentum | 7.773 | [4.849, 10.847] | 0.0829 |
| jump_tail | E1_default_stress | 2 | minimum-variance | 7.346 | [3.316, 11.661] | 0.0863 |
| jump_tail | E1_default_stress | 3 | risk-parity | 7.135 | [3.613, 11.340] | 0.0802 |
| jump_tail | E1_default_stress | 4 | no-trade-band | 7.031 | [3.553, 11.105] | 0.0799 |
| jump_tail | E1_default_stress | 5 | buy-and-hold | 6.920 | [3.581, 11.139] | 0.0870 |
| jump_tail | E1_default_stress | 6 | random | 5.751 | [3.300, 7.957] | 0.0616 |
| jump_tail | E1_default_stress | 7 | signal-weighted | 4.622 | [1.216, 7.604] | 0.0168 |
| jump_tail | E1_default_stress | 8 | mean-reversion | 0.793 | [-2.276, 3.917] | -0.0032 |
| jump_tail | E2_harsh_corner | 1 | naive-momentum | 5.067 | [2.716, 7.243] | 0.0608 |
| jump_tail | E2_harsh_corner | 2 | minimum-variance | 4.810 | [1.818, 8.034] | 0.0699 |
| jump_tail | E2_harsh_corner | 3 | buy-and-hold | 4.654 | [1.405, 7.865] | 0.0609 |
| jump_tail | E2_harsh_corner | 4 | risk-parity | 4.593 | [1.619, 7.817] | 0.0663 |
| jump_tail | E2_harsh_corner | 5 | no-trade-band | 4.573 | [1.557, 7.777] | 0.0656 |
| jump_tail | E2_harsh_corner | 6 | random | 3.606 | [-0.307, 7.120] | 0.0512 |
| jump_tail | E2_harsh_corner | 7 | mean-reversion | 2.605 | [-0.834, 6.220] | 0.0352 |
| jump_tail | E2_harsh_corner | 8 | signal-weighted | 0.628 | [-2.375, 3.460] | 0.0006 |
| jump_tail | E2_latency_3 | 1 | naive-momentum | 5.251 | [2.884, 7.452] | 0.0631 |
| jump_tail | E2_latency_3 | 2 | minimum-variance | 4.983 | [2.030, 8.211] | 0.0720 |
| jump_tail | E2_latency_3 | 3 | buy-and-hold | 4.828 | [1.607, 8.056] | 0.0629 |
| jump_tail | E2_latency_3 | 4 | risk-parity | 4.768 | [1.780, 7.985] | 0.0685 |
| jump_tail | E2_latency_3 | 5 | no-trade-band | 4.746 | [1.743, 7.941] | 0.0677 |
| jump_tail | E2_latency_3 | 6 | random | 3.807 | [-0.117, 7.304] | 0.0533 |
| jump_tail | E2_latency_3 | 7 | mean-reversion | 2.763 | [-0.670, 6.378] | 0.0368 |
| jump_tail | E2_latency_3 | 8 | signal-weighted | 1.025 | [-2.064, 3.877] | 0.0015 |
| jump_tail | E2_participation_1pct | 1 | naive-momentum | 7.773 | [4.849, 10.847] | 0.0829 |
| jump_tail | E2_participation_1pct | 2 | minimum-variance | 7.346 | [3.316, 11.661] | 0.0863 |
| jump_tail | E2_participation_1pct | 3 | risk-parity | 7.135 | [3.613, 11.340] | 0.0802 |
| jump_tail | E2_participation_1pct | 4 | no-trade-band | 7.031 | [3.553, 11.105] | 0.0799 |
| jump_tail | E2_participation_1pct | 5 | buy-and-hold | 6.920 | [3.581, 11.139] | 0.0870 |
| jump_tail | E2_participation_1pct | 6 | random | 5.751 | [3.300, 7.957] | 0.0616 |
| jump_tail | E2_participation_1pct | 7 | signal-weighted | 4.622 | [1.216, 7.604] | 0.0168 |
| jump_tail | E2_participation_1pct | 8 | mean-reversion | 0.793 | [-2.276, 3.917] | -0.0032 |
| jump_tail | E2_spread_20bps | 1 | naive-momentum | 7.472 | [4.575, 10.482] | 0.0799 |
| jump_tail | E2_spread_20bps | 2 | minimum-variance | 7.034 | [3.029, 11.305] | 0.0827 |
| jump_tail | E2_spread_20bps | 3 | risk-parity | 6.823 | [3.332, 10.933] | 0.0767 |
| jump_tail | E2_spread_20bps | 4 | no-trade-band | 6.723 | [3.283, 10.699] | 0.0765 |
| jump_tail | E2_spread_20bps | 5 | buy-and-hold | 6.673 | [3.366, 10.823] | 0.0839 |
| jump_tail | E2_spread_20bps | 6 | random | 5.364 | [2.888, 7.575] | 0.0578 |
| jump_tail | E2_spread_20bps | 7 | signal-weighted | 4.282 | [0.841, 7.253] | 0.0153 |
| jump_tail | E2_spread_20bps | 8 | mean-reversion | 0.606 | [-2.439, 3.715] | -0.0050 |
