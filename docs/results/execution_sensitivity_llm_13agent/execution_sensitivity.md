# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| calm | E0_ideal | E1_default_stress | 0.692 | 0.200 |
| calm | E0_ideal | E2_harsh_corner | 0.718 | 0.500 |
| calm | E0_ideal | E2_latency_3 | 0.692 | 0.500 |
| calm | E0_ideal | E2_participation_1pct | 0.692 | 0.200 |
| calm | E0_ideal | E2_spread_20bps | 0.769 | 0.500 |
| calm | E1_default_stress | E2_harsh_corner | 0.513 | 0.000 |
| calm | E1_default_stress | E2_latency_3 | 0.487 | 0.000 |
| calm | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| calm | E1_default_stress | E2_spread_20bps | 0.923 | 0.500 |
| calm | E2_harsh_corner | E2_latency_3 | 0.974 | 1.000 |
| calm | E2_harsh_corner | E2_participation_1pct | 0.513 | 0.000 |
| calm | E2_harsh_corner | E2_spread_20bps | 0.590 | 0.200 |
| calm | E2_latency_3 | E2_participation_1pct | 0.487 | 0.000 |
| calm | E2_latency_3 | E2_spread_20bps | 0.564 | 0.200 |
| calm | E2_participation_1pct | E2_spread_20bps | 0.923 | 0.500 |
| high_vol | E0_ideal | E1_default_stress | 0.231 | 0.200 |
| high_vol | E0_ideal | E2_harsh_corner | 0.590 | 0.500 |
| high_vol | E0_ideal | E2_latency_3 | 0.590 | 0.500 |
| high_vol | E0_ideal | E2_participation_1pct | 0.231 | 0.200 |
| high_vol | E0_ideal | E2_spread_20bps | 0.410 | 0.200 |
| high_vol | E1_default_stress | E2_harsh_corner | 0.128 | 0.000 |
| high_vol | E1_default_stress | E2_latency_3 | 0.179 | 0.000 |
| high_vol | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| high_vol | E1_default_stress | E2_spread_20bps | 0.821 | 1.000 |
| high_vol | E2_harsh_corner | E2_latency_3 | 0.846 | 1.000 |
| high_vol | E2_harsh_corner | E2_participation_1pct | 0.128 | 0.000 |
| high_vol | E2_harsh_corner | E2_spread_20bps | 0.308 | 0.000 |
| high_vol | E2_latency_3 | E2_participation_1pct | 0.179 | 0.000 |
| high_vol | E2_latency_3 | E2_spread_20bps | 0.308 | 0.000 |
| high_vol | E2_participation_1pct | E2_spread_20bps | 0.821 | 1.000 |
| jump_tail | E0_ideal | E1_default_stress | 0.513 | 0.500 |
| jump_tail | E0_ideal | E2_harsh_corner | 0.410 | 0.200 |
| jump_tail | E0_ideal | E2_latency_3 | 0.462 | 0.200 |
| jump_tail | E0_ideal | E2_participation_1pct | 0.513 | 0.500 |
| jump_tail | E0_ideal | E2_spread_20bps | 0.564 | 0.500 |
| jump_tail | E1_default_stress | E2_harsh_corner | 0.744 | 0.500 |
| jump_tail | E1_default_stress | E2_latency_3 | 0.846 | 0.500 |
| jump_tail | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| jump_tail | E1_default_stress | E2_spread_20bps | 0.846 | 1.000 |
| jump_tail | E2_harsh_corner | E2_latency_3 | 0.897 | 1.000 |
| jump_tail | E2_harsh_corner | E2_participation_1pct | 0.744 | 0.500 |
| jump_tail | E2_harsh_corner | E2_spread_20bps | 0.692 | 0.500 |
| jump_tail | E2_latency_3 | E2_participation_1pct | 0.846 | 0.500 |
| jump_tail | E2_latency_3 | E2_spread_20bps | 0.744 | 0.500 |
| jump_tail | E2_participation_1pct | E2_spread_20bps | 0.846 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| calm | E0_ideal | 1 | buy-and-hold | 23.381 | [21.123, 25.611] | 0.0932 |
| calm | E0_ideal | 2 | minimum-variance | 23.323 | [21.096, 25.556] | 0.0932 |
| calm | E0_ideal | 3 | risk-parity | 23.113 | [20.901, 25.280] | 0.0896 |
| calm | E0_ideal | 4 | no-trade-band | 23.083 | [20.893, 25.256] | 0.0896 |
| calm | E0_ideal | 5 | poe:gpt-5.5 | 21.633 | [20.300, 23.135] | 0.0826 |
| calm | E0_ideal | 6 | poe:glm-5 | 21.294 | [19.401, 23.200] | 0.0792 |
| calm | E0_ideal | 7 | poe:claude-opus-4.7 | 21.245 | [19.441, 23.002] | 0.0813 |
| calm | E0_ideal | 8 | naive-momentum | 19.889 | [18.404, 21.379] | 0.0797 |
| calm | E0_ideal | 9 | poe:gemini-3.1-pro | 18.731 | [15.578, 21.982] | 0.0608 |
| calm | E0_ideal | 10 | random | 16.364 | [14.462, 18.053] | 0.0621 |
| calm | E0_ideal | 11 | deepseek:deepseek-v4-pro | 10.063 | [6.677, 13.633] | 0.0343 |
| calm | E0_ideal | 12 | signal-weighted | 8.402 | [7.120, 9.712] | 0.0203 |
| calm | E0_ideal | 13 | mean-reversion | 2.258 | [0.844, 3.896] | 0.0023 |
| calm | E1_default_stress | 1 | buy-and-hold | 16.687 | [15.351, 18.130] | 0.0885 |
| calm | E1_default_stress | 2 | poe:gpt-5.5 | 15.435 | [13.375, 17.695] | 0.0758 |
| calm | E1_default_stress | 3 | poe:claude-opus-4.7 | 15.392 | [13.210, 17.778] | 0.0754 |
| calm | E1_default_stress | 4 | minimum-variance | 15.311 | [14.259, 16.463] | 0.0853 |
| calm | E1_default_stress | 5 | naive-momentum | 15.248 | [13.624, 17.040] | 0.0732 |
| calm | E1_default_stress | 6 | poe:glm-5 | 15.242 | [13.178, 17.687] | 0.0740 |
| calm | E1_default_stress | 7 | risk-parity | 15.226 | [13.868, 16.754] | 0.0800 |
| calm | E1_default_stress | 8 | no-trade-band | 15.201 | [13.843, 16.734] | 0.0803 |
| calm | E1_default_stress | 9 | poe:gemini-3.1-pro | 13.671 | [11.695, 15.659] | 0.0660 |
| calm | E1_default_stress | 10 | random | 11.735 | [9.983, 13.672] | 0.0544 |
| calm | E1_default_stress | 11 | deepseek:deepseek-v4-pro | 10.484 | [7.524, 13.115] | 0.0437 |
| calm | E1_default_stress | 12 | signal-weighted | 6.402 | [4.959, 8.027] | 0.0103 |
| calm | E1_default_stress | 13 | mean-reversion | 2.714 | [0.918, 4.829] | 0.0041 |
| calm | E2_harsh_corner | 1 | minimum-variance | 14.954 | [13.118, 16.601] | 0.0741 |
| calm | E2_harsh_corner | 2 | no-trade-band | 14.658 | [12.757, 16.403] | 0.0721 |
| calm | E2_harsh_corner | 3 | risk-parity | 14.655 | [12.753, 16.401] | 0.0720 |
| calm | E2_harsh_corner | 4 | buy-and-hold | 14.494 | [12.594, 16.409] | 0.0723 |
| calm | E2_harsh_corner | 5 | naive-momentum | 13.316 | [12.039, 14.479] | 0.0776 |
| calm | E2_harsh_corner | 6 | poe:claude-opus-4.7 | 12.743 | [10.252, 14.944] | 0.0665 |
| calm | E2_harsh_corner | 7 | poe:gpt-5.5 | 12.659 | [10.206, 14.851] | 0.0666 |
| calm | E2_harsh_corner | 8 | poe:glm-5 | 12.193 | [9.435, 14.716] | 0.0636 |
| calm | E2_harsh_corner | 9 | random | 12.163 | [10.232, 14.174] | 0.0599 |
| calm | E2_harsh_corner | 10 | deepseek:deepseek-v4-pro | 12.040 | [10.520, 13.765] | 0.0572 |
| calm | E2_harsh_corner | 11 | poe:gemini-3.1-pro | 11.416 | [9.312, 13.242] | 0.0580 |
| calm | E2_harsh_corner | 12 | signal-weighted | 7.436 | [5.655, 9.011] | 0.0168 |
| calm | E2_harsh_corner | 13 | mean-reversion | 3.718 | [1.478, 6.353] | 0.0106 |
| calm | E2_latency_3 | 1 | minimum-variance | 15.452 | [13.593, 17.095] | 0.0760 |
| calm | E2_latency_3 | 2 | no-trade-band | 15.154 | [13.225, 16.926] | 0.0740 |
| calm | E2_latency_3 | 3 | risk-parity | 15.152 | [13.221, 16.924] | 0.0740 |
| calm | E2_latency_3 | 4 | buy-and-hold | 14.992 | [13.050, 16.947] | 0.0742 |
| calm | E2_latency_3 | 5 | naive-momentum | 13.685 | [12.409, 14.851] | 0.0800 |
| calm | E2_latency_3 | 6 | poe:claude-opus-4.7 | 13.257 | [10.840, 15.420] | 0.0692 |
| calm | E2_latency_3 | 7 | poe:gpt-5.5 | 13.177 | [10.761, 15.343] | 0.0694 |
| calm | E2_latency_3 | 8 | poe:glm-5 | 12.826 | [10.215, 15.178] | 0.0668 |
| calm | E2_latency_3 | 9 | deepseek:deepseek-v4-pro | 12.810 | [11.069, 14.645] | 0.0606 |
| calm | E2_latency_3 | 10 | random | 12.646 | [10.693, 14.661] | 0.0621 |
| calm | E2_latency_3 | 11 | poe:gemini-3.1-pro | 12.016 | [9.831, 13.978] | 0.0608 |
| calm | E2_latency_3 | 12 | signal-weighted | 7.900 | [6.127, 9.485] | 0.0177 |
| calm | E2_latency_3 | 13 | mean-reversion | 3.948 | [1.569, 6.710] | 0.0113 |
| calm | E2_participation_1pct | 1 | buy-and-hold | 16.687 | [15.351, 18.130] | 0.0885 |
| calm | E2_participation_1pct | 2 | poe:gpt-5.5 | 15.435 | [13.375, 17.695] | 0.0758 |
| calm | E2_participation_1pct | 3 | poe:claude-opus-4.7 | 15.392 | [13.210, 17.778] | 0.0754 |
| calm | E2_participation_1pct | 4 | minimum-variance | 15.311 | [14.259, 16.463] | 0.0853 |
| calm | E2_participation_1pct | 5 | naive-momentum | 15.248 | [13.624, 17.040] | 0.0732 |
| calm | E2_participation_1pct | 6 | poe:glm-5 | 15.242 | [13.178, 17.687] | 0.0740 |
| calm | E2_participation_1pct | 7 | risk-parity | 15.226 | [13.868, 16.754] | 0.0800 |
| calm | E2_participation_1pct | 8 | no-trade-band | 15.201 | [13.843, 16.734] | 0.0803 |
| calm | E2_participation_1pct | 9 | poe:gemini-3.1-pro | 13.671 | [11.695, 15.659] | 0.0660 |
| calm | E2_participation_1pct | 10 | random | 11.735 | [9.983, 13.672] | 0.0544 |
| calm | E2_participation_1pct | 11 | deepseek:deepseek-v4-pro | 10.484 | [7.524, 13.115] | 0.0437 |
| calm | E2_participation_1pct | 12 | signal-weighted | 6.402 | [4.959, 8.027] | 0.0103 |
| calm | E2_participation_1pct | 13 | mean-reversion | 2.714 | [0.918, 4.829] | 0.0041 |
| calm | E2_spread_20bps | 1 | buy-and-hold | 15.941 | [14.635, 17.359] | 0.0855 |
| calm | E2_spread_20bps | 2 | poe:gpt-5.5 | 14.609 | [12.613, 16.784] | 0.0721 |
| calm | E2_spread_20bps | 3 | minimum-variance | 14.605 | [13.610, 15.688] | 0.0822 |
| calm | E2_spread_20bps | 4 | poe:claude-opus-4.7 | 14.528 | [12.453, 16.825] | 0.0717 |
| calm | E2_spread_20bps | 5 | naive-momentum | 14.487 | [12.920, 16.203] | 0.0700 |
| calm | E2_spread_20bps | 6 | risk-parity | 14.462 | [13.143, 15.945] | 0.0767 |
| calm | E2_spread_20bps | 7 | no-trade-band | 14.444 | [13.117, 15.939] | 0.0770 |
| calm | E2_spread_20bps | 8 | poe:glm-5 | 13.854 | [11.770, 16.133] | 0.0648 |
| calm | E2_spread_20bps | 9 | poe:gemini-3.1-pro | 12.371 | [10.641, 14.314] | 0.0629 |
| calm | E2_spread_20bps | 10 | random | 10.924 | [9.168, 12.850] | 0.0507 |
| calm | E2_spread_20bps | 11 | deepseek:deepseek-v4-pro | 9.686 | [7.809, 11.694] | 0.0401 |
| calm | E2_spread_20bps | 12 | signal-weighted | 5.672 | [4.268, 7.157] | 0.0089 |
| calm | E2_spread_20bps | 13 | mean-reversion | 2.347 | [0.563, 4.297] | 0.0035 |
| high_vol | E0_ideal | 1 | no-trade-band | 11.154 | [8.898, 13.605] | 0.0899 |
| high_vol | E0_ideal | 2 | risk-parity | 11.072 | [8.796, 13.580] | 0.0900 |
| high_vol | E0_ideal | 3 | buy-and-hold | 10.951 | [8.994, 12.917] | 0.0994 |
| high_vol | E0_ideal | 4 | naive-momentum | 10.902 | [8.252, 13.783] | 0.0779 |
| high_vol | E0_ideal | 5 | minimum-variance | 10.075 | [8.040, 12.182] | 0.0855 |
| high_vol | E0_ideal | 6 | random | 9.348 | [7.264, 11.734] | 0.0733 |
| high_vol | E0_ideal | 7 | poe:glm-5 | 9.224 | [6.335, 12.023] | 0.0690 |
| high_vol | E0_ideal | 8 | poe:gpt-5.5 | 9.023 | [6.159, 11.865] | 0.0713 |
| high_vol | E0_ideal | 9 | poe:claude-opus-4.7 | 9.016 | [6.096, 11.880] | 0.0710 |
| high_vol | E0_ideal | 10 | poe:gemini-3.1-pro | 7.708 | [4.562, 10.753] | 0.0567 |
| high_vol | E0_ideal | 11 | deepseek:deepseek-v4-pro | 7.574 | [4.829, 10.347] | 0.0466 |
| high_vol | E0_ideal | 12 | signal-weighted | 6.128 | [2.646, 8.988] | 0.0119 |
| high_vol | E0_ideal | 13 | mean-reversion | 3.721 | [0.249, 6.729] | 0.0166 |
| high_vol | E1_default_stress | 1 | poe:glm-5 | 9.592 | [7.829, 11.455] | 0.0789 |
| high_vol | E1_default_stress | 2 | buy-and-hold | 9.457 | [7.455, 11.574] | 0.1044 |
| high_vol | E1_default_stress | 3 | poe:claude-opus-4.7 | 9.218 | [7.588, 10.837] | 0.0818 |
| high_vol | E1_default_stress | 4 | deepseek:deepseek-v4-pro | 9.201 | [7.548, 10.858] | 0.0761 |
| high_vol | E1_default_stress | 5 | poe:gpt-5.5 | 9.062 | [7.340, 10.823] | 0.0777 |
| high_vol | E1_default_stress | 6 | no-trade-band | 8.729 | [6.523, 11.005] | 0.0873 |
| high_vol | E1_default_stress | 7 | risk-parity | 8.693 | [6.575, 10.900] | 0.0872 |
| high_vol | E1_default_stress | 8 | poe:gemini-3.1-pro | 8.649 | [6.848, 10.595] | 0.0733 |
| high_vol | E1_default_stress | 9 | minimum-variance | 8.559 | [6.715, 10.330] | 0.0810 |
| high_vol | E1_default_stress | 10 | naive-momentum | 8.260 | [6.422, 10.115] | 0.0754 |
| high_vol | E1_default_stress | 11 | random | 7.750 | [5.065, 10.033] | 0.0796 |
| high_vol | E1_default_stress | 12 | signal-weighted | 4.849 | [1.373, 7.160] | 0.0124 |
| high_vol | E1_default_stress | 13 | mean-reversion | 3.301 | [0.243, 5.905] | 0.0279 |
| high_vol | E2_harsh_corner | 1 | minimum-variance | 10.128 | [8.375, 12.081] | 0.0986 |
| high_vol | E2_harsh_corner | 2 | no-trade-band | 9.997 | [8.172, 11.990] | 0.1011 |
| high_vol | E2_harsh_corner | 3 | risk-parity | 9.991 | [8.139, 12.026] | 0.1010 |
| high_vol | E2_harsh_corner | 4 | random | 9.494 | [7.629, 11.310] | 0.0904 |
| high_vol | E2_harsh_corner | 5 | buy-and-hold | 9.205 | [6.975, 11.763] | 0.0924 |
| high_vol | E2_harsh_corner | 6 | poe:gemini-3.1-pro | 8.390 | [5.865, 10.829] | 0.0933 |
| high_vol | E2_harsh_corner | 7 | poe:gpt-5.5 | 8.198 | [5.736, 10.716] | 0.0936 |
| high_vol | E2_harsh_corner | 8 | poe:glm-5 | 8.130 | [5.670, 10.647] | 0.0916 |
| high_vol | E2_harsh_corner | 9 | poe:claude-opus-4.7 | 8.010 | [5.711, 10.258] | 0.0972 |
| high_vol | E2_harsh_corner | 10 | deepseek:deepseek-v4-pro | 7.672 | [5.152, 10.301] | 0.0845 |
| high_vol | E2_harsh_corner | 11 | naive-momentum | 7.088 | [4.493, 9.250] | 0.0694 |
| high_vol | E2_harsh_corner | 12 | mean-reversion | 5.102 | [1.961, 8.107] | 0.0427 |
| high_vol | E2_harsh_corner | 13 | signal-weighted | 0.465 | [-2.792, 3.665] | 0.0112 |
| high_vol | E2_latency_3 | 1 | minimum-variance | 10.346 | [8.575, 12.318] | 0.1006 |
| high_vol | E2_latency_3 | 2 | no-trade-band | 10.201 | [8.357, 12.186] | 0.1031 |
| high_vol | E2_latency_3 | 3 | risk-parity | 10.200 | [8.347, 12.230] | 0.1030 |
| high_vol | E2_latency_3 | 4 | random | 9.716 | [7.853, 11.532] | 0.0928 |
| high_vol | E2_latency_3 | 5 | buy-and-hold | 9.415 | [7.170, 11.984] | 0.0943 |
| high_vol | E2_latency_3 | 6 | poe:gpt-5.5 | 8.423 | [5.992, 10.932] | 0.0962 |
| high_vol | E2_latency_3 | 7 | deepseek:deepseek-v4-pro | 8.326 | [5.742, 10.867] | 0.0916 |
| high_vol | E2_latency_3 | 8 | poe:glm-5 | 8.245 | [5.833, 10.756] | 0.0932 |
| high_vol | E2_latency_3 | 9 | poe:claude-opus-4.7 | 8.235 | [5.951, 10.474] | 0.0999 |
| high_vol | E2_latency_3 | 10 | poe:gemini-3.1-pro | 8.013 | [5.572, 10.646] | 0.0901 |
| high_vol | E2_latency_3 | 11 | naive-momentum | 7.280 | [4.670, 9.434] | 0.0712 |
| high_vol | E2_latency_3 | 12 | mean-reversion | 5.330 | [2.185, 8.360] | 0.0445 |
| high_vol | E2_latency_3 | 13 | signal-weighted | 0.880 | [-2.295, 3.967] | 0.0119 |
| high_vol | E2_participation_1pct | 1 | poe:glm-5 | 9.592 | [7.829, 11.455] | 0.0789 |
| high_vol | E2_participation_1pct | 2 | buy-and-hold | 9.457 | [7.455, 11.574] | 0.1044 |
| high_vol | E2_participation_1pct | 3 | poe:claude-opus-4.7 | 9.218 | [7.588, 10.837] | 0.0818 |
| high_vol | E2_participation_1pct | 4 | deepseek:deepseek-v4-pro | 9.201 | [7.548, 10.858] | 0.0761 |
| high_vol | E2_participation_1pct | 5 | poe:gpt-5.5 | 9.062 | [7.340, 10.823] | 0.0777 |
| high_vol | E2_participation_1pct | 6 | no-trade-band | 8.729 | [6.523, 11.005] | 0.0873 |
| high_vol | E2_participation_1pct | 7 | risk-parity | 8.693 | [6.575, 10.900] | 0.0872 |
| high_vol | E2_participation_1pct | 8 | poe:gemini-3.1-pro | 8.649 | [6.848, 10.595] | 0.0733 |
| high_vol | E2_participation_1pct | 9 | minimum-variance | 8.559 | [6.715, 10.330] | 0.0810 |
| high_vol | E2_participation_1pct | 10 | naive-momentum | 8.260 | [6.422, 10.115] | 0.0754 |
| high_vol | E2_participation_1pct | 11 | random | 7.750 | [5.065, 10.033] | 0.0796 |
| high_vol | E2_participation_1pct | 12 | signal-weighted | 4.849 | [1.373, 7.160] | 0.0124 |
| high_vol | E2_participation_1pct | 13 | mean-reversion | 3.301 | [0.243, 5.905] | 0.0279 |
| high_vol | E2_spread_20bps | 1 | buy-and-hold | 9.154 | [7.142, 11.243] | 0.1013 |
| high_vol | E2_spread_20bps | 2 | poe:glm-5 | 8.921 | [7.239, 10.705] | 0.0735 |
| high_vol | E2_spread_20bps | 3 | poe:claude-opus-4.7 | 8.691 | [6.939, 10.530] | 0.0766 |
| high_vol | E2_spread_20bps | 4 | poe:gpt-5.5 | 8.666 | [6.910, 10.421] | 0.0744 |
| high_vol | E2_spread_20bps | 5 | no-trade-band | 8.367 | [6.147, 10.624] | 0.0839 |
| high_vol | E2_spread_20bps | 6 | risk-parity | 8.328 | [6.211, 10.519] | 0.0837 |
| high_vol | E2_spread_20bps | 7 | minimum-variance | 8.176 | [6.342, 9.901] | 0.0776 |
| high_vol | E2_spread_20bps | 8 | poe:gemini-3.1-pro | 7.991 | [6.171, 9.943] | 0.0731 |
| high_vol | E2_spread_20bps | 9 | deepseek:deepseek-v4-pro | 7.963 | [6.163, 9.738] | 0.0598 |
| high_vol | E2_spread_20bps | 10 | naive-momentum | 7.956 | [6.142, 9.774] | 0.0724 |
| high_vol | E2_spread_20bps | 11 | random | 7.317 | [4.604, 9.653] | 0.0756 |
| high_vol | E2_spread_20bps | 12 | signal-weighted | 4.323 | [0.847, 6.585] | 0.0112 |
| high_vol | E2_spread_20bps | 13 | mean-reversion | 3.010 | [-0.022, 5.587] | 0.0260 |
| jump_tail | E0_ideal | 1 | minimum-variance | 8.879 | [4.685, 13.774] | 0.1060 |
| jump_tail | E0_ideal | 2 | risk-parity | 8.650 | [4.180, 13.782] | 0.1016 |
| jump_tail | E0_ideal | 3 | no-trade-band | 8.514 | [4.147, 13.428] | 0.0998 |
| jump_tail | E0_ideal | 4 | buy-and-hold | 8.493 | [3.722, 13.979] | 0.1036 |
| jump_tail | E0_ideal | 5 | naive-momentum | 8.042 | [5.070, 10.896] | 0.0793 |
| jump_tail | E0_ideal | 6 | random | 7.546 | [4.040, 10.900] | 0.0839 |
| jump_tail | E0_ideal | 7 | signal-weighted | 7.132 | [5.850, 8.525] | 0.0279 |
| jump_tail | E0_ideal | 8 | poe:gemini-3.1-pro | 6.958 | [3.644, 10.174] | 0.0793 |
| jump_tail | E0_ideal | 9 | poe:gpt-5.5 | 6.841 | [2.947, 10.444] | 0.0801 |
| jump_tail | E0_ideal | 10 | poe:claude-opus-4.7 | 6.675 | [2.805, 10.323] | 0.0762 |
| jump_tail | E0_ideal | 11 | poe:glm-5 | 6.323 | [2.135, 10.155] | 0.0705 |
| jump_tail | E0_ideal | 12 | deepseek:deepseek-v4-pro | 6.010 | [2.527, 9.334] | 0.0428 |
| jump_tail | E0_ideal | 13 | mean-reversion | 0.991 | [-0.760, 2.788] | 0.0061 |
| jump_tail | E1_default_stress | 1 | naive-momentum | 7.773 | [4.849, 10.847] | 0.0829 |
| jump_tail | E1_default_stress | 2 | minimum-variance | 7.346 | [3.316, 11.661] | 0.0863 |
| jump_tail | E1_default_stress | 3 | risk-parity | 7.135 | [3.613, 11.340] | 0.0802 |
| jump_tail | E1_default_stress | 4 | no-trade-band | 7.031 | [3.553, 11.105] | 0.0799 |
| jump_tail | E1_default_stress | 5 | buy-and-hold | 6.920 | [3.581, 11.139] | 0.0870 |
| jump_tail | E1_default_stress | 6 | deepseek:deepseek-v4-pro | 6.411 | [3.769, 9.521] | 0.0657 |
| jump_tail | E1_default_stress | 7 | poe:claude-opus-4.7 | 6.009 | [3.127, 9.303] | 0.0748 |
| jump_tail | E1_default_stress | 8 | poe:gpt-5.5 | 5.882 | [2.689, 9.318] | 0.0752 |
| jump_tail | E1_default_stress | 9 | random | 5.751 | [3.300, 7.957] | 0.0616 |
| jump_tail | E1_default_stress | 10 | poe:glm-5 | 5.111 | [2.950, 7.156] | 0.0658 |
| jump_tail | E1_default_stress | 11 | signal-weighted | 4.622 | [1.216, 7.604] | 0.0168 |
| jump_tail | E1_default_stress | 12 | poe:gemini-3.1-pro | 4.279 | [1.613, 7.414] | 0.0575 |
| jump_tail | E1_default_stress | 13 | mean-reversion | 0.793 | [-2.276, 3.917] | -0.0032 |
| jump_tail | E2_harsh_corner | 1 | naive-momentum | 5.067 | [2.716, 7.243] | 0.0608 |
| jump_tail | E2_harsh_corner | 2 | minimum-variance | 4.810 | [1.818, 8.034] | 0.0699 |
| jump_tail | E2_harsh_corner | 3 | buy-and-hold | 4.654 | [1.405, 7.865] | 0.0609 |
| jump_tail | E2_harsh_corner | 4 | risk-parity | 4.593 | [1.619, 7.817] | 0.0663 |
| jump_tail | E2_harsh_corner | 5 | no-trade-band | 4.573 | [1.557, 7.777] | 0.0656 |
| jump_tail | E2_harsh_corner | 6 | poe:claude-opus-4.7 | 4.469 | [1.148, 8.112] | 0.0521 |
| jump_tail | E2_harsh_corner | 7 | poe:glm-5 | 4.316 | [0.726, 8.236] | 0.0446 |
| jump_tail | E2_harsh_corner | 8 | poe:gpt-5.5 | 4.000 | [0.473, 7.809] | 0.0458 |
| jump_tail | E2_harsh_corner | 9 | deepseek:deepseek-v4-pro | 3.874 | [0.946, 6.950] | 0.0433 |
| jump_tail | E2_harsh_corner | 10 | poe:gemini-3.1-pro | 3.816 | [0.558, 7.444] | 0.0434 |
| jump_tail | E2_harsh_corner | 11 | random | 3.606 | [-0.307, 7.120] | 0.0512 |
| jump_tail | E2_harsh_corner | 12 | mean-reversion | 2.605 | [-0.834, 6.220] | 0.0352 |
| jump_tail | E2_harsh_corner | 13 | signal-weighted | 0.628 | [-2.375, 3.460] | 0.0006 |
| jump_tail | E2_latency_3 | 1 | naive-momentum | 5.251 | [2.884, 7.452] | 0.0631 |
| jump_tail | E2_latency_3 | 2 | minimum-variance | 4.983 | [2.030, 8.211] | 0.0720 |
| jump_tail | E2_latency_3 | 3 | buy-and-hold | 4.828 | [1.607, 8.056] | 0.0629 |
| jump_tail | E2_latency_3 | 4 | risk-parity | 4.768 | [1.780, 7.985] | 0.0685 |
| jump_tail | E2_latency_3 | 5 | no-trade-band | 4.746 | [1.743, 7.941] | 0.0677 |
| jump_tail | E2_latency_3 | 6 | poe:claude-opus-4.7 | 4.668 | [1.336, 8.338] | 0.0546 |
| jump_tail | E2_latency_3 | 7 | poe:gpt-5.5 | 4.218 | [0.678, 8.093] | 0.0489 |
| jump_tail | E2_latency_3 | 8 | deepseek:deepseek-v4-pro | 4.170 | [0.887, 7.641] | 0.0486 |
| jump_tail | E2_latency_3 | 9 | random | 3.807 | [-0.117, 7.304] | 0.0533 |
| jump_tail | E2_latency_3 | 10 | poe:glm-5 | 3.600 | [0.428, 7.061] | 0.0409 |
| jump_tail | E2_latency_3 | 11 | poe:gemini-3.1-pro | 3.517 | [0.486, 6.926] | 0.0352 |
| jump_tail | E2_latency_3 | 12 | mean-reversion | 2.763 | [-0.670, 6.378] | 0.0368 |
| jump_tail | E2_latency_3 | 13 | signal-weighted | 1.025 | [-2.064, 3.877] | 0.0015 |
| jump_tail | E2_participation_1pct | 1 | naive-momentum | 7.773 | [4.849, 10.847] | 0.0829 |
| jump_tail | E2_participation_1pct | 2 | minimum-variance | 7.346 | [3.316, 11.661] | 0.0863 |
| jump_tail | E2_participation_1pct | 3 | risk-parity | 7.135 | [3.613, 11.340] | 0.0802 |
| jump_tail | E2_participation_1pct | 4 | no-trade-band | 7.031 | [3.553, 11.105] | 0.0799 |
| jump_tail | E2_participation_1pct | 5 | buy-and-hold | 6.920 | [3.581, 11.139] | 0.0870 |
| jump_tail | E2_participation_1pct | 6 | deepseek:deepseek-v4-pro | 6.411 | [3.769, 9.521] | 0.0657 |
| jump_tail | E2_participation_1pct | 7 | poe:claude-opus-4.7 | 6.009 | [3.127, 9.303] | 0.0748 |
| jump_tail | E2_participation_1pct | 8 | poe:gpt-5.5 | 5.882 | [2.689, 9.318] | 0.0752 |
| jump_tail | E2_participation_1pct | 9 | random | 5.751 | [3.300, 7.957] | 0.0616 |
| jump_tail | E2_participation_1pct | 10 | poe:glm-5 | 5.111 | [2.950, 7.156] | 0.0658 |
| jump_tail | E2_participation_1pct | 11 | signal-weighted | 4.622 | [1.216, 7.604] | 0.0168 |
| jump_tail | E2_participation_1pct | 12 | poe:gemini-3.1-pro | 4.279 | [1.613, 7.414] | 0.0575 |
| jump_tail | E2_participation_1pct | 13 | mean-reversion | 0.793 | [-2.276, 3.917] | -0.0032 |
| jump_tail | E2_spread_20bps | 1 | naive-momentum | 7.472 | [4.575, 10.482] | 0.0799 |
| jump_tail | E2_spread_20bps | 2 | minimum-variance | 7.034 | [3.029, 11.305] | 0.0827 |
| jump_tail | E2_spread_20bps | 3 | risk-parity | 6.823 | [3.332, 10.933] | 0.0767 |
| jump_tail | E2_spread_20bps | 4 | no-trade-band | 6.723 | [3.283, 10.699] | 0.0765 |
| jump_tail | E2_spread_20bps | 5 | buy-and-hold | 6.673 | [3.366, 10.823] | 0.0839 |
| jump_tail | E2_spread_20bps | 6 | poe:gemini-3.1-pro | 6.590 | [3.571, 10.500] | 0.0730 |
| jump_tail | E2_spread_20bps | 7 | deepseek:deepseek-v4-pro | 6.184 | [3.583, 9.187] | 0.0632 |
| jump_tail | E2_spread_20bps | 8 | poe:claude-opus-4.7 | 5.702 | [2.714, 9.039] | 0.0719 |
| jump_tail | E2_spread_20bps | 9 | poe:gpt-5.5 | 5.537 | [2.243, 9.023] | 0.0717 |
| jump_tail | E2_spread_20bps | 10 | random | 5.364 | [2.888, 7.575] | 0.0578 |
| jump_tail | E2_spread_20bps | 11 | poe:glm-5 | 4.650 | [1.456, 8.161] | 0.0561 |
| jump_tail | E2_spread_20bps | 12 | signal-weighted | 4.282 | [0.841, 7.253] | 0.0153 |
| jump_tail | E2_spread_20bps | 13 | mean-reversion | 0.606 | [-2.439, 3.715] | -0.0050 |
