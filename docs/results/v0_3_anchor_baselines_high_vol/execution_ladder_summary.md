# TreLLM v0.3 Execution Ladder

This artifact reports how deterministic agent rankings and mechanism metrics move across the v0.3 execution-assumption ladder.
It is not a trading-profit claim.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_high_volatility_c0_v0_3`
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
| E0 | E1 | 7 | 0.809524 | 1.000000 | -0.018071 | -0.111056 | 0.208682 | 1607.587098 |
| E0 | E2 | 7 | 0.809524 | 1.000000 | -0.017136 | -0.395023 | 0.333414 | 1670.398416 |

## Per-Level Summary

| Level | Rank | Agent | Sharpe mean | Return mean | Fill rate | Rejected orders | Slippage | Intent-execution gap |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | 1 | buy-and-hold | 13.925295 | 0.248932 | 1.000000 | 0.000000 | 18.856930 | 0.299992 |
| E0 | 2 | risk-parity | 13.831815 | 0.245755 | 1.000000 | 0.000000 | 24.039453 | 0.000016 |
| E0 | 3 | minimum-variance | 13.826848 | 0.244806 | 1.000000 | 0.000000 | 26.255634 | 0.000017 |
| E0 | 4 | naive-momentum | 13.130472 | 0.200449 | 1.000000 | 0.000000 | 50.338461 | 0.000019 |
| E0 | 5 | random | 11.015969 | 0.170399 | 1.000000 | 0.000000 | 156.111472 | 0.000039 |
| E0 | 6 | signal-weighted | 10.801100 | 0.158436 | 1.000000 | 0.000000 | 36.019633 | 0.329185 |
| E0 | 7 | mean-reversion | 3.502902 | 0.021534 | 1.000000 | 0.000000 | 35.589381 | 0.000007 |
| E1 | 1 | risk-parity | 11.671616 | 0.222978 | 0.922486 | 1.700000 | 1753.285258 | 0.239943 |
| E1 | 2 | buy-and-hold | 11.550751 | 0.233732 | 0.920738 | 1.800000 | 1731.574619 | 0.405450 |
| E1 | 3 | minimum-variance | 11.259152 | 0.219712 | 0.919222 | 1.866667 | 1806.597513 | 0.246087 |
| E1 | 4 | naive-momentum | 10.063688 | 0.177286 | 0.904875 | 1.933333 | 1994.884746 | 0.275315 |
| E1 | 5 | signal-weighted | 8.676065 | 0.140927 | 0.912162 | 1.266667 | 1263.099907 | 0.418228 |
| E1 | 6 | random | 8.132734 | 0.139771 | 0.850051 | 4.666667 | 2347.733651 | 0.384845 |
| E1 | 7 | mean-reversion | 2.830863 | 0.029405 | 0.793076 | 2.066667 | 703.144956 | 0.120180 |
| E2 | 1 | risk-parity | 10.625705 | 0.209338 | 0.660358 | 10.233333 | 1704.042814 | 0.364091 |
| E2 | 2 | minimum-variance | 10.623512 | 0.209568 | 0.661010 | 10.066667 | 1764.404550 | 0.378522 |
| E2 | 3 | buy-and-hold | 10.318791 | 0.209896 | 0.611068 | 12.600000 | 1638.879334 | 0.508132 |
| E2 | 4 | naive-momentum | 8.942333 | 0.199669 | 0.594272 | 10.900000 | 2350.632857 | 0.502737 |
| E2 | 5 | random | 8.325354 | 0.157528 | 0.596535 | 11.966667 | 2083.441124 | 0.446008 |
| E2 | 6 | signal-weighted | 7.254275 | 0.119880 | 0.586016 | 9.366667 | 1474.451907 | 0.515383 |
| E2 | 7 | mean-reversion | 4.502806 | 0.064479 | 0.525579 | 6.366667 | 1024.147289 | 0.248303 |
