# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| calm | E0_ideal | E1_default_stress | 0.810 | 0.500 |
| calm | E0_ideal | E2_harsh_corner | 1.000 | 1.000 |
| calm | E0_ideal | E2_latency_3 | 1.000 | 1.000 |
| calm | E0_ideal | E2_participation_1pct | 0.810 | 0.500 |
| calm | E0_ideal | E2_spread_20bps | 0.810 | 0.500 |
| calm | E1_default_stress | E2_harsh_corner | 0.810 | 0.500 |
| calm | E1_default_stress | E2_latency_3 | 0.810 | 0.500 |
| calm | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| calm | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| calm | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| calm | E2_harsh_corner | E2_participation_1pct | 0.810 | 0.500 |
| calm | E2_harsh_corner | E2_spread_20bps | 0.810 | 0.500 |
| calm | E2_latency_3 | E2_participation_1pct | 0.810 | 0.500 |
| calm | E2_latency_3 | E2_spread_20bps | 0.810 | 0.500 |
| calm | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |
| high_vol | E0_ideal | E1_default_stress | 0.905 | 1.000 |
| high_vol | E0_ideal | E2_harsh_corner | 0.524 | 0.500 |
| high_vol | E0_ideal | E2_latency_3 | 0.524 | 0.500 |
| high_vol | E0_ideal | E2_participation_1pct | 0.905 | 1.000 |
| high_vol | E0_ideal | E2_spread_20bps | 0.905 | 1.000 |
| high_vol | E1_default_stress | E2_harsh_corner | 0.619 | 0.500 |
| high_vol | E1_default_stress | E2_latency_3 | 0.619 | 0.500 |
| high_vol | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| high_vol | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| high_vol | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| high_vol | E2_harsh_corner | E2_participation_1pct | 0.619 | 0.500 |
| high_vol | E2_harsh_corner | E2_spread_20bps | 0.619 | 0.500 |
| high_vol | E2_latency_3 | E2_participation_1pct | 0.619 | 0.500 |
| high_vol | E2_latency_3 | E2_spread_20bps | 0.619 | 0.500 |
| high_vol | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |
| jump_tail | E0_ideal | E1_default_stress | 0.333 | 0.500 |
| jump_tail | E0_ideal | E2_harsh_corner | 0.619 | 0.500 |
| jump_tail | E0_ideal | E2_latency_3 | 0.619 | 0.500 |
| jump_tail | E0_ideal | E2_participation_1pct | 0.333 | 0.500 |
| jump_tail | E0_ideal | E2_spread_20bps | 0.333 | 0.500 |
| jump_tail | E1_default_stress | E2_harsh_corner | 0.524 | 0.500 |
| jump_tail | E1_default_stress | E2_latency_3 | 0.524 | 0.500 |
| jump_tail | E1_default_stress | E2_participation_1pct | 1.000 | 1.000 |
| jump_tail | E1_default_stress | E2_spread_20bps | 1.000 | 1.000 |
| jump_tail | E2_harsh_corner | E2_latency_3 | 1.000 | 1.000 |
| jump_tail | E2_harsh_corner | E2_participation_1pct | 0.524 | 0.500 |
| jump_tail | E2_harsh_corner | E2_spread_20bps | 0.524 | 0.500 |
| jump_tail | E2_latency_3 | E2_participation_1pct | 0.524 | 0.500 |
| jump_tail | E2_latency_3 | E2_spread_20bps | 0.524 | 0.500 |
| jump_tail | E2_participation_1pct | E2_spread_20bps | 1.000 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| calm | E0_ideal | 1 | naive-momentum | 8.475 | [7.901, 9.098] | 0.3948 |
| calm | E0_ideal | 2 | signal-weighted | 7.194 | [6.619, 7.788] | 0.2640 |
| calm | E0_ideal | 3 | buy-and-hold | 2.213 | [1.884, 2.617] | 0.1393 |
| calm | E0_ideal | 4 | minimum-variance | 2.212 | [1.882, 2.616] | 0.1392 |
| calm | E0_ideal | 5 | risk-parity | 2.179 | [1.868, 2.567] | 0.1361 |
| calm | E0_ideal | 6 | random | 1.956 | [1.543, 2.351] | 0.1004 |
| calm | E0_ideal | 7 | mean-reversion | -6.378 | [-6.929, -5.850] | -0.1967 |
| calm | E1_default_stress | 1 | naive-momentum | 6.489 | [5.754, 7.256] | 0.3301 |
| calm | E1_default_stress | 2 | signal-weighted | 5.820 | [5.305, 6.325] | 0.2293 |
| calm | E1_default_stress | 3 | minimum-variance | 1.517 | [1.134, 1.948] | 0.0975 |
| calm | E1_default_stress | 4 | risk-parity | 1.359 | [0.960, 1.821] | 0.0866 |
| calm | E1_default_stress | 5 | buy-and-hold | 1.228 | [0.890, 1.593] | 0.0785 |
| calm | E1_default_stress | 6 | random | 0.782 | [0.349, 1.262] | 0.0408 |
| calm | E1_default_stress | 7 | mean-reversion | -6.110 | [-6.767, -5.511] | -0.2207 |
| calm | E2_harsh_corner | 1 | naive-momentum | 4.536 | [3.697, 5.485] | 0.3054 |
| calm | E2_harsh_corner | 2 | signal-weighted | 3.648 | [3.149, 4.137] | 0.1629 |
| calm | E2_harsh_corner | 3 | buy-and-hold | 0.628 | [0.227, 1.051] | 0.0380 |
| calm | E2_harsh_corner | 4 | minimum-variance | -0.028 | [-0.611, 0.686] | -0.0106 |
| calm | E2_harsh_corner | 5 | risk-parity | -0.144 | [-0.800, 0.606] | -0.0154 |
| calm | E2_harsh_corner | 6 | random | -0.196 | [-0.878, 0.495] | -0.0161 |
| calm | E2_harsh_corner | 7 | mean-reversion | -5.161 | [-5.729, -4.635] | -0.2499 |
| calm | E2_latency_3 | 1 | naive-momentum | 4.944 | [4.117, 5.891] | 0.3377 |
| calm | E2_latency_3 | 2 | signal-weighted | 3.995 | [3.498, 4.491] | 0.1796 |
| calm | E2_latency_3 | 3 | buy-and-hold | 1.045 | [0.612, 1.519] | 0.0701 |
| calm | E2_latency_3 | 4 | minimum-variance | 0.387 | [-0.202, 1.088] | 0.0201 |
| calm | E2_latency_3 | 5 | risk-parity | 0.368 | [-0.307, 1.112] | 0.0236 |
| calm | E2_latency_3 | 6 | random | 0.305 | [-0.390, 1.013] | 0.0171 |
| calm | E2_latency_3 | 7 | mean-reversion | -4.806 | [-5.384, -4.277] | -0.2336 |
| calm | E2_participation_1pct | 1 | naive-momentum | 6.489 | [5.754, 7.256] | 0.3301 |
| calm | E2_participation_1pct | 2 | signal-weighted | 5.820 | [5.305, 6.325] | 0.2293 |
| calm | E2_participation_1pct | 3 | minimum-variance | 1.517 | [1.134, 1.948] | 0.0975 |
| calm | E2_participation_1pct | 4 | risk-parity | 1.359 | [0.960, 1.821] | 0.0866 |
| calm | E2_participation_1pct | 5 | buy-and-hold | 1.228 | [0.890, 1.593] | 0.0785 |
| calm | E2_participation_1pct | 6 | random | 0.782 | [0.349, 1.262] | 0.0408 |
| calm | E2_participation_1pct | 7 | mean-reversion | -6.110 | [-6.767, -5.511] | -0.2207 |
| calm | E2_spread_20bps | 1 | naive-momentum | 5.980 | [5.219, 6.759] | 0.2997 |
| calm | E2_spread_20bps | 2 | signal-weighted | 5.471 | [4.956, 5.986] | 0.2125 |
| calm | E2_spread_20bps | 3 | minimum-variance | 1.123 | [0.743, 1.553] | 0.0701 |
| calm | E2_spread_20bps | 4 | risk-parity | 0.956 | [0.550, 1.428] | 0.0590 |
| calm | E2_spread_20bps | 5 | buy-and-hold | 0.837 | [0.503, 1.194] | 0.0514 |
| calm | E2_spread_20bps | 6 | random | 0.098 | [-0.341, 0.588] | 0.0029 |
| calm | E2_spread_20bps | 7 | mean-reversion | -6.521 | [-7.177, -5.933] | -0.2362 |
| high_vol | E0_ideal | 1 | naive-momentum | 3.965 | [3.125, 4.732] | 0.2982 |
| high_vol | E0_ideal | 2 | signal-weighted | 3.698 | [2.973, 4.371] | 0.2332 |
| high_vol | E0_ideal | 3 | buy-and-hold | 0.875 | [-0.317, 2.110] | 0.0985 |
| high_vol | E0_ideal | 4 | risk-parity | 0.803 | [-0.377, 2.044] | 0.0903 |
| high_vol | E0_ideal | 5 | minimum-variance | 0.741 | [-0.423, 2.003] | 0.0830 |
| high_vol | E0_ideal | 6 | random | 0.247 | [-0.694, 1.215] | 0.0249 |
| high_vol | E0_ideal | 7 | mean-reversion | -2.828 | [-3.900, -1.603] | -0.1647 |
| high_vol | E1_default_stress | 1 | signal-weighted | 2.689 | [1.691, 3.574] | 0.1973 |
| high_vol | E1_default_stress | 2 | naive-momentum | 2.402 | [1.531, 3.249] | 0.2061 |
| high_vol | E1_default_stress | 3 | buy-and-hold | 0.357 | [-0.736, 1.408] | 0.0494 |
| high_vol | E1_default_stress | 4 | risk-parity | 0.057 | [-1.131, 1.336] | 0.0133 |
| high_vol | E1_default_stress | 5 | minimum-variance | -0.143 | [-1.250, 1.060] | -0.0177 |
| high_vol | E1_default_stress | 6 | random | -0.224 | [-1.666, 1.039] | -0.0122 |
| high_vol | E1_default_stress | 7 | mean-reversion | -2.862 | [-3.558, -2.078] | -0.2046 |
| high_vol | E2_harsh_corner | 1 | signal-weighted | 1.868 | [0.922, 2.784] | 0.1454 |
| high_vol | E2_harsh_corner | 2 | naive-momentum | 1.213 | [0.371, 2.115] | 0.1303 |
| high_vol | E2_harsh_corner | 3 | risk-parity | -0.360 | [-1.504, 0.648] | -0.0395 |
| high_vol | E2_harsh_corner | 4 | random | -0.437 | [-1.565, 0.623] | -0.0395 |
| high_vol | E2_harsh_corner | 5 | minimum-variance | -0.590 | [-1.656, 0.297] | -0.0757 |
| high_vol | E2_harsh_corner | 6 | buy-and-hold | -0.982 | [-1.717, -0.250] | -0.1388 |
| high_vol | E2_harsh_corner | 7 | mean-reversion | -2.178 | [-3.476, -0.844] | -0.2039 |
| high_vol | E2_latency_3 | 1 | signal-weighted | 2.062 | [1.114, 2.977] | 0.1617 |
| high_vol | E2_latency_3 | 2 | naive-momentum | 1.456 | [0.616, 2.364] | 0.1582 |
| high_vol | E2_latency_3 | 3 | risk-parity | -0.152 | [-1.276, 0.851] | -0.0089 |
| high_vol | E2_latency_3 | 4 | random | -0.170 | [-1.297, 0.891] | -0.0074 |
| high_vol | E2_latency_3 | 5 | minimum-variance | -0.376 | [-1.410, 0.497] | -0.0462 |
| high_vol | E2_latency_3 | 6 | buy-and-hold | -0.717 | [-1.453, 0.027] | -0.1048 |
| high_vol | E2_latency_3 | 7 | mean-reversion | -1.935 | [-3.236, -0.597] | -0.1821 |
| high_vol | E2_participation_1pct | 1 | signal-weighted | 2.689 | [1.691, 3.574] | 0.1973 |
| high_vol | E2_participation_1pct | 2 | naive-momentum | 2.402 | [1.531, 3.249] | 0.2061 |
| high_vol | E2_participation_1pct | 3 | buy-and-hold | 0.357 | [-0.736, 1.408] | 0.0494 |
| high_vol | E2_participation_1pct | 4 | risk-parity | 0.057 | [-1.131, 1.336] | 0.0133 |
| high_vol | E2_participation_1pct | 5 | minimum-variance | -0.143 | [-1.250, 1.060] | -0.0177 |
| high_vol | E2_participation_1pct | 6 | random | -0.224 | [-1.666, 1.039] | -0.0122 |
| high_vol | E2_participation_1pct | 7 | mean-reversion | -2.862 | [-3.558, -2.078] | -0.2046 |
| high_vol | E2_spread_20bps | 1 | signal-weighted | 2.455 | [1.434, 3.358] | 0.1802 |
| high_vol | E2_spread_20bps | 2 | naive-momentum | 2.074 | [1.194, 2.918] | 0.1755 |
| high_vol | E2_spread_20bps | 3 | buy-and-hold | 0.118 | [-0.978, 1.174] | 0.0223 |
| high_vol | E2_spread_20bps | 4 | risk-parity | -0.196 | [-1.396, 1.075] | -0.0142 |
| high_vol | E2_spread_20bps | 5 | minimum-variance | -0.425 | [-1.531, 0.764] | -0.0477 |
| high_vol | E2_spread_20bps | 6 | random | -0.632 | [-2.066, 0.622] | -0.0488 |
| high_vol | E2_spread_20bps | 7 | mean-reversion | -3.171 | [-3.870, -2.382] | -0.2241 |
| jump_tail | E0_ideal | 1 | naive-momentum | 1.529 | [0.643, 2.389] | 0.2053 |
| jump_tail | E0_ideal | 2 | signal-weighted | 1.253 | [0.773, 1.697] | 0.1307 |
| jump_tail | E0_ideal | 3 | random | 1.062 | [0.174, 1.826] | 0.1686 |
| jump_tail | E0_ideal | 4 | minimum-variance | 1.020 | [0.337, 1.663] | 0.1719 |
| jump_tail | E0_ideal | 5 | risk-parity | 1.019 | [0.321, 1.666] | 0.1688 |
| jump_tail | E0_ideal | 6 | buy-and-hold | 1.007 | [0.316, 1.648] | 0.1717 |
| jump_tail | E0_ideal | 7 | mean-reversion | -0.260 | [-0.917, 0.452] | -0.0474 |
| jump_tail | E1_default_stress | 1 | signal-weighted | 0.653 | [-0.208, 1.493] | 0.0953 |
| jump_tail | E1_default_stress | 2 | naive-momentum | 0.512 | [-0.280, 1.189] | 0.0681 |
| jump_tail | E1_default_stress | 3 | buy-and-hold | 0.424 | [-0.229, 1.041] | 0.0617 |
| jump_tail | E1_default_stress | 4 | risk-parity | 0.366 | [-0.216, 0.920] | 0.0389 |
| jump_tail | E1_default_stress | 5 | minimum-variance | 0.110 | [-0.531, 0.750] | -0.0019 |
| jump_tail | E1_default_stress | 6 | random | -0.332 | [-0.949, 0.375] | -0.0510 |
| jump_tail | E1_default_stress | 7 | mean-reversion | -0.948 | [-1.632, -0.210] | -0.1260 |
| jump_tail | E2_harsh_corner | 1 | signal-weighted | 0.000 | [-0.694, 0.676] | -0.0098 |
| jump_tail | E2_harsh_corner | 2 | naive-momentum | -0.048 | [-0.829, 0.753] | -0.0139 |
| jump_tail | E2_harsh_corner | 3 | minimum-variance | -0.156 | [-0.687, 0.423] | -0.0858 |
| jump_tail | E2_harsh_corner | 4 | random | -0.194 | [-1.286, 0.941] | -0.0471 |
| jump_tail | E2_harsh_corner | 5 | buy-and-hold | -0.423 | [-1.064, 0.149] | -0.1449 |
| jump_tail | E2_harsh_corner | 6 | mean-reversion | -0.547 | [-1.264, 0.087] | -0.1206 |
| jump_tail | E2_harsh_corner | 7 | risk-parity | -0.640 | [-1.460, 0.114] | -0.1695 |
| jump_tail | E2_latency_3 | 1 | signal-weighted | 0.141 | [-0.560, 0.823] | 0.0117 |
| jump_tail | E2_latency_3 | 2 | naive-momentum | 0.104 | [-0.678, 0.901] | 0.0130 |
| jump_tail | E2_latency_3 | 3 | minimum-variance | -0.007 | [-0.535, 0.579] | -0.0525 |
| jump_tail | E2_latency_3 | 4 | random | -0.019 | [-1.112, 1.118] | -0.0125 |
| jump_tail | E2_latency_3 | 5 | buy-and-hold | -0.262 | [-0.900, 0.303] | -0.1105 |
| jump_tail | E2_latency_3 | 6 | mean-reversion | -0.408 | [-1.134, 0.232] | -0.0941 |
| jump_tail | E2_latency_3 | 7 | risk-parity | -0.463 | [-1.298, 0.307] | -0.1347 |
| jump_tail | E2_participation_1pct | 1 | signal-weighted | 0.653 | [-0.208, 1.493] | 0.0953 |
| jump_tail | E2_participation_1pct | 2 | naive-momentum | 0.512 | [-0.280, 1.189] | 0.0681 |
| jump_tail | E2_participation_1pct | 3 | buy-and-hold | 0.424 | [-0.229, 1.041] | 0.0617 |
| jump_tail | E2_participation_1pct | 4 | risk-parity | 0.366 | [-0.216, 0.920] | 0.0389 |
| jump_tail | E2_participation_1pct | 5 | minimum-variance | 0.110 | [-0.531, 0.750] | -0.0019 |
| jump_tail | E2_participation_1pct | 6 | random | -0.332 | [-0.949, 0.375] | -0.0510 |
| jump_tail | E2_participation_1pct | 7 | mean-reversion | -0.948 | [-1.632, -0.210] | -0.1260 |
| jump_tail | E2_spread_20bps | 1 | signal-weighted | 0.479 | [-0.380, 1.310] | 0.0715 |
| jump_tail | E2_spread_20bps | 2 | naive-momentum | 0.312 | [-0.470, 0.986] | 0.0377 |
| jump_tail | E2_spread_20bps | 3 | buy-and-hold | 0.267 | [-0.387, 0.880] | 0.0320 |
| jump_tail | E2_spread_20bps | 4 | risk-parity | 0.215 | [-0.355, 0.761] | 0.0122 |
| jump_tail | E2_spread_20bps | 5 | minimum-variance | -0.063 | [-0.715, 0.581] | -0.0324 |
| jump_tail | E2_spread_20bps | 6 | random | -0.591 | [-1.226, 0.143] | -0.0868 |
| jump_tail | E2_spread_20bps | 7 | mean-reversion | -1.155 | [-1.834, -0.417] | -0.1489 |
