# TreLLM v0.3 Execution Ladder

This artifact reports how deterministic agent rankings and mechanism metrics move across the v0.3 execution-assumption ladder.
It is not a trading-profit claim.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_calm_trend_c0_v0_3`
- Contamination tier: `C0`
- Levels: `E0, E1, E2`
- Agents: `buy-and-hold, signal-weighted, naive-momentum, mean-reversion, risk-parity, minimum-variance, random`
- Seeds: `7, 11, 17, 23, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151`
- Rank metric: `sharpe_mean`
- Mechanism metrics: `execution_fill_rate, rejected_order_count, total_slippage_cost, intent_risk_gap_l1, risk_execution_gap_l1, intent_execution_gap_l1`
- Claim boundary: Execution ladder protocol fixture for TreLLM reliability analysis. It reports how rankings and mechanism metrics move under execution assumptions; it is not a trading-profit claim.

## Ranking Stability vs E0

| Baseline | Comparison | Agents | Kendall tau | Top-k Jaccard | Return delta | Fill delta | Intent-execution gap delta | Slippage delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | E1 | 7 | 0.904762 | 1.000000 | -0.012644 | -0.099502 | 0.192380 | 1148.433366 |
| E0 | E2 | 7 | 0.809524 | 1.000000 | -0.020195 | -0.381028 | 0.303808 | 1267.028981 |

## Per-Level Summary

| Level | Rank | Agent | Sharpe mean | Return mean | Fill rate | Rejected orders | Slippage | Intent-execution gap |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | 1 | buy-and-hold | 27.239169 | 0.235525 | 1.000000 | 0.000000 | 16.472595 | 0.299991 |
| E0 | 2 | minimum-variance | 27.214218 | 0.235391 | 1.000000 | 0.000000 | 16.874927 | 0.000020 |
| E0 | 3 | risk-parity | 26.912229 | 0.232497 | 1.000000 | 0.000000 | 22.383475 | 0.000021 |
| E0 | 4 | naive-momentum | 24.787840 | 0.216642 | 1.000000 | 0.000000 | 29.689765 | 0.000017 |
| E0 | 5 | random | 17.702424 | 0.157586 | 1.000000 | 0.000000 | 155.014076 | 0.000039 |
| E0 | 6 | signal-weighted | 15.874876 | 0.152676 | 1.000000 | 0.000000 | 29.375998 | 0.328059 |
| E0 | 7 | mean-reversion | 2.689171 | 0.005127 | 0.800000 | 0.000000 | 14.986521 | 0.000003 |
| E1 | 1 | minimum-variance | 21.008422 | 0.218913 | 0.933107 | 1.166667 | 1301.890161 | 0.222949 |
| E1 | 2 | buy-and-hold | 20.891904 | 0.223532 | 0.924174 | 1.600000 | 1279.098386 | 0.409015 |
| E1 | 3 | risk-parity | 20.699607 | 0.214909 | 0.928539 | 1.400000 | 1363.586912 | 0.239393 |
| E1 | 4 | naive-momentum | 19.183431 | 0.200609 | 0.933297 | 0.933333 | 1482.144256 | 0.261184 |
| E1 | 5 | random | 14.007866 | 0.141231 | 0.849825 | 4.666667 | 1786.447354 | 0.384289 |
| E1 | 6 | signal-weighted | 13.381938 | 0.140536 | 0.922479 | 0.900000 | 913.233192 | 0.407235 |
| E1 | 7 | mean-reversion | 2.497308 | 0.007203 | 0.612064 | 1.000000 | 197.430661 | 0.050744 |
| E2 | 1 | minimum-variance | 17.884702 | 0.203197 | 0.682300 | 9.166667 | 1265.744202 | 0.329207 |
| E2 | 2 | risk-parity | 17.508379 | 0.199447 | 0.664648 | 10.033333 | 1304.187570 | 0.335624 |
| E2 | 3 | buy-and-hold | 16.550668 | 0.195910 | 0.594888 | 13.400000 | 1248.193704 | 0.502964 |
| E2 | 4 | naive-momentum | 15.897986 | 0.205182 | 0.608020 | 11.200000 | 1986.365882 | 0.495788 |
| E2 | 5 | random | 12.840739 | 0.149254 | 0.596020 | 12.000000 | 1723.394146 | 0.444116 |
| E2 | 6 | signal-weighted | 10.265551 | 0.109809 | 0.579335 | 9.666667 | 1203.673083 | 0.521691 |
| E2 | 7 | mean-reversion | 4.639260 | 0.031280 | 0.407591 | 3.266667 | 422.441639 | 0.125417 |
