# Execution-Assumption Sensitivity (Deterministic Agents)

How much the agent ranking reorders between execution-assumption levels.
Rankings use mean Sharpe over seeds within each (scenario, level) cell.
Kendall tau-b of 1.0 means the ladder level did not reorder the leaderboard;
lower values mean execution assumptions change conclusions.

## Ranking Stability

| Scenario | Level A | Level B | Kendall tau | Top-3 Jaccard |
| --- | --- | --- | ---: | ---: |
| high_vol | E2_harsh_corner | E2_latency_3 | 0.782 | 1.000 |
| high_vol | E2_harsh_corner | E2_participation_1pct | 0.527 | 0.500 |
| high_vol | E2_harsh_corner | E2_spread_20bps | 0.382 | 0.500 |
| high_vol | E2_latency_3 | E2_participation_1pct | 0.600 | 0.500 |
| high_vol | E2_latency_3 | E2_spread_20bps | 0.600 | 0.500 |
| high_vol | E2_participation_1pct | E2_spread_20bps | 0.782 | 1.000 |

## Per-Level Leaderboards

| Scenario | Level | Rank | Agent | Sharpe mean | Sharpe 95% CI | Return mean |
| --- | --- | ---: | --- | ---: | --- | ---: |
| high_vol | E2_harsh_corner | 1 | buy-and-hold | 10.822 | [8.868, 12.571] | 0.0573 |
| high_vol | E2_harsh_corner | 2 | random | 9.818 | [7.770, 11.876] | 0.0570 |
| high_vol | E2_harsh_corner | 3 | minimum-variance | 9.171 | [7.187, 11.162] | 0.0511 |
| high_vol | E2_harsh_corner | 4 | risk-parity | 9.074 | [4.497, 12.600] | 0.0490 |
| high_vol | E2_harsh_corner | 5 | deepseek:deepseek-v4-pro | 8.380 | [6.188, 10.657] | 0.0577 |
| high_vol | E2_harsh_corner | 6 | poe:gemini-3.1-pro | 8.345 | [5.435, 10.762] | 0.0547 |
| high_vol | E2_harsh_corner | 7 | glm:glm-5 | 8.076 | [5.326, 10.522] | 0.0571 |
| high_vol | E2_harsh_corner | 8 | poe:claude-opus-4.7 | 8.013 | [5.303, 10.360] | 0.0581 |
| high_vol | E2_harsh_corner | 9 | naive-momentum | 7.993 | [5.028, 10.816] | 0.0536 |
| high_vol | E2_harsh_corner | 10 | signal-weighted | 6.278 | [4.665, 8.043] | 0.0446 |
| high_vol | E2_harsh_corner | 11 | mean-reversion | 3.080 | [0.506, 5.496] | 0.0239 |
| high_vol | E2_latency_3 | 1 | buy-and-hold | 11.303 | [9.293, 13.103] | 0.0588 |
| high_vol | E2_latency_3 | 2 | random | 10.472 | [8.399, 12.637] | 0.0601 |
| high_vol | E2_latency_3 | 3 | minimum-variance | 9.752 | [7.732, 11.749] | 0.0536 |
| high_vol | E2_latency_3 | 4 | risk-parity | 9.612 | [5.044, 13.201] | 0.0512 |
| high_vol | E2_latency_3 | 5 | glm:glm-5 | 8.781 | [6.156, 11.218] | 0.0620 |
| high_vol | E2_latency_3 | 6 | poe:claude-opus-4.7 | 8.482 | [6.103, 10.676] | 0.0583 |
| high_vol | E2_latency_3 | 7 | naive-momentum | 8.459 | [5.492, 11.343] | 0.0564 |
| high_vol | E2_latency_3 | 8 | deepseek:deepseek-v4-pro | 7.862 | [5.301, 10.344] | 0.0565 |
| high_vol | E2_latency_3 | 9 | poe:gemini-3.1-pro | 7.355 | [5.563, 9.317] | 0.0522 |
| high_vol | E2_latency_3 | 10 | signal-weighted | 6.714 | [5.078, 8.471] | 0.0479 |
| high_vol | E2_latency_3 | 11 | mean-reversion | 3.513 | [0.934, 5.936] | 0.0268 |
| high_vol | E2_participation_1pct | 1 | buy-and-hold | 14.081 | [11.692, 16.412] | 0.0739 |
| high_vol | E2_participation_1pct | 2 | naive-momentum | 11.620 | [8.679, 14.749] | 0.0824 |
| high_vol | E2_participation_1pct | 3 | minimum-variance | 9.932 | [7.849, 11.937] | 0.0587 |
| high_vol | E2_participation_1pct | 4 | risk-parity | 9.633 | [7.223, 12.008] | 0.0534 |
| high_vol | E2_participation_1pct | 5 | random | 8.903 | [7.010, 10.956] | 0.0430 |
| high_vol | E2_participation_1pct | 6 | poe:gemini-3.1-pro | 8.112 | [4.973, 11.645] | 0.0505 |
| high_vol | E2_participation_1pct | 7 | poe:claude-opus-4.7 | 8.049 | [4.721, 11.090] | 0.0475 |
| high_vol | E2_participation_1pct | 8 | glm:glm-5 | 7.977 | [4.976, 10.853] | 0.0489 |
| high_vol | E2_participation_1pct | 9 | deepseek:deepseek-v4-pro | 7.428 | [4.392, 10.054] | 0.0465 |
| high_vol | E2_participation_1pct | 10 | signal-weighted | 6.961 | [4.023, 9.716] | 0.0349 |
| high_vol | E2_participation_1pct | 11 | mean-reversion | 1.057 | [-1.869, 4.119] | 0.0106 |
| high_vol | E2_spread_20bps | 1 | buy-and-hold | 13.558 | [11.250, 15.794] | 0.0724 |
| high_vol | E2_spread_20bps | 2 | naive-momentum | 10.876 | [7.864, 14.023] | 0.0778 |
| high_vol | E2_spread_20bps | 3 | minimum-variance | 9.154 | [7.089, 11.162] | 0.0546 |
| high_vol | E2_spread_20bps | 4 | risk-parity | 8.619 | [6.235, 10.896] | 0.0485 |
| high_vol | E2_spread_20bps | 5 | poe:claude-opus-4.7 | 7.671 | [4.531, 10.801] | 0.0455 |
| high_vol | E2_spread_20bps | 6 | random | 7.605 | [5.673, 9.681] | 0.0374 |
| high_vol | E2_spread_20bps | 7 | glm:glm-5 | 6.609 | [3.642, 9.392] | 0.0400 |
| high_vol | E2_spread_20bps | 8 | signal-weighted | 6.152 | [3.277, 8.782] | 0.0305 |
| high_vol | E2_spread_20bps | 9 | deepseek:deepseek-v4-pro | 5.872 | [1.598, 9.570] | 0.0350 |
| high_vol | E2_spread_20bps | 10 | poe:gemini-3.1-pro | 5.379 | [3.178, 7.600] | 0.0345 |
| high_vol | E2_spread_20bps | 11 | mean-reversion | 0.405 | [-2.585, 3.507] | 0.0061 |
