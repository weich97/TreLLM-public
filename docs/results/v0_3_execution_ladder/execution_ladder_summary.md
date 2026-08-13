# TreLLM v0.3 Execution Ladder

This artifact reports how deterministic agent rankings and mechanism metrics move across the v0.3 execution-assumption ladder.
It is not a trading-profit claim.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_calm_trend_c0_v0_3`
- Contamination tier: `C0`
- Levels: `E0, E1, E2, E3`
- Agents: `signal-weighted, naive-momentum, risk-parity, random`
- Seeds: `7, 11`
- Rank metric: `sharpe_mean`
- Mechanism metrics: `execution_fill_rate, rejected_order_count, total_slippage_cost, intent_risk_gap_l1, risk_execution_gap_l1, intent_execution_gap_l1`
- Claim boundary: Execution ladder protocol fixture for TreLLM reliability analysis. It reports how rankings and mechanism metrics move under execution assumptions; it is not a trading-profit claim.
- E3 boundary: Calibrated replay fixture path. Venue-wide E3 claims require external quote/fill provenance.

## Ranking Stability vs E0

| Baseline | Comparison | Agents | Kendall tau | Top-k Jaccard | Return delta | Fill delta | Intent-execution gap delta | Slippage delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | E1 | 4 | 0.666667 | 1.000000 | -0.011962 | -0.083412 | 0.238384 | 1337.253542 |
| E0 | E2 | 4 | 0.666667 | 1.000000 | -0.022168 | -0.395934 | 0.400826 | 1719.727213 |
| E0 | E3 | 4 | 0.666667 | 1.000000 | -0.001662 | -0.295780 | 0.374592 | 1736.345569 |

## Per-Level Summary

| Level | Rank | Agent | Sharpe mean | Return mean | Fill rate | Rejected orders | Slippage | Intent-execution gap |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | 1 | risk-parity | 26.766609 | 0.230906 | 1.000000 | 0.000000 | 23.304574 | 0.000021 |
| E0 | 2 | naive-momentum | 26.201349 | 0.226279 | 1.000000 | 0.000000 | 23.288527 | 0.000015 |
| E0 | 3 | random | 16.819584 | 0.162091 | 1.000000 | 0.000000 | 172.886789 | 0.000042 |
| E0 | 4 | signal-weighted | 15.440080 | 0.155232 | 1.000000 | 0.000000 | 24.142586 | 0.354569 |
| E1 | 1 | naive-momentum | 23.306530 | 0.205878 | 0.917497 | 1.500000 | 1410.091026 | 0.240793 |
| E1 | 2 | risk-parity | 21.128348 | 0.209964 | 0.927083 | 1.500000 | 1466.246279 | 0.247316 |
| E1 | 3 | random | 14.109159 | 0.159438 | 0.891725 | 3.000000 | 1848.323993 | 0.402850 |
| E1 | 4 | signal-weighted | 13.908388 | 0.151381 | 0.930048 | 0.500000 | 867.975345 | 0.417223 |
| E2 | 1 | naive-momentum | 19.113120 | 0.253711 | 0.576689 | 12.000000 | 2759.256923 | 0.674061 |
| E2 | 2 | risk-parity | 17.604933 | 0.189750 | 0.625000 | 12.000000 | 1539.249332 | 0.371451 |
| E2 | 3 | random | 12.220041 | 0.131728 | 0.616279 | 10.500000 | 1695.387551 | 0.396463 |
| E2 | 4 | signal-weighted | 10.275841 | 0.110647 | 0.598297 | 8.500000 | 1128.637524 | 0.515976 |
| E3 | 1 | naive-momentum | 19.661623 | 0.256009 | 0.729236 | 7.500000 | 2899.091785 | 0.630240 |
| E3 | 2 | risk-parity | 17.902551 | 0.211178 | 0.729167 | 9.000000 | 1631.534978 | 0.350021 |
| E3 | 3 | random | 14.729365 | 0.160608 | 0.689746 | 9.500000 | 1684.255453 | 0.437679 |
| E3 | 4 | signal-weighted | 12.131230 | 0.140064 | 0.668731 | 8.000000 | 974.122537 | 0.435075 |
