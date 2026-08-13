# TreLLM v0.3 Execution Ladder

This artifact reports how deterministic agent rankings and mechanism metrics move across the v0.3 execution-assumption ladder.
It is not a trading-profit claim.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_jump_tail_c0_v0_3`
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
| E0 | E1 | 7 | 0.809524 | 1.000000 | -0.014688 | -0.121348 | 0.226890 | 2373.646022 |
| E0 | E2 | 7 | 0.714286 | 1.000000 | -0.016316 | -0.407670 | 0.364642 | 2193.266356 |

## Per-Level Summary

| Level | Rank | Agent | Sharpe mean | Return mean | Fill rate | Rejected orders | Slippage | Intent-execution gap |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | 1 | buy-and-hold | 7.376081 | 0.245912 | 1.000000 | 0.000000 | 22.179042 | 0.299992 |
| E0 | 2 | risk-parity | 7.298880 | 0.235983 | 1.000000 | 0.000000 | 31.578087 | 0.000016 |
| E0 | 3 | minimum-variance | 7.186873 | 0.232931 | 1.000000 | 0.000000 | 34.876176 | 0.000018 |
| E0 | 4 | random | 5.956617 | 0.150285 | 1.000000 | 0.000000 | 156.327778 | 0.000039 |
| E0 | 5 | naive-momentum | 5.822904 | 0.154356 | 1.000000 | 0.000000 | 62.445882 | 0.000020 |
| E0 | 6 | signal-weighted | 5.817991 | 0.127795 | 1.000000 | 0.000000 | 42.093068 | 0.299703 |
| E0 | 7 | mean-reversion | 4.892527 | 0.051431 | 1.000000 | 0.000000 | 50.927961 | 0.000010 |
| E1 | 1 | buy-and-hold | 6.872543 | 0.228199 | 0.924022 | 1.633333 | 2297.427967 | 0.401201 |
| E1 | 2 | risk-parity | 5.789942 | 0.213648 | 0.912929 | 2.166667 | 2707.379412 | 0.262764 |
| E1 | 3 | minimum-variance | 5.741919 | 0.215414 | 0.909851 | 2.266667 | 2797.577962 | 0.279810 |
| E1 | 4 | naive-momentum | 5.049010 | 0.155881 | 0.868496 | 3.333333 | 2895.137420 | 0.299736 |
| E1 | 5 | signal-weighted | 4.831133 | 0.107146 | 0.907401 | 1.333333 | 1816.736483 | 0.398193 |
| E1 | 6 | random | 4.267536 | 0.122970 | 0.846843 | 4.800000 | 3128.950894 | 0.385562 |
| E1 | 7 | mean-reversion | 3.744654 | 0.052622 | 0.781022 | 2.666667 | 1372.740012 | 0.160761 |
| E2 | 1 | risk-parity | 6.065836 | 0.193579 | 0.616903 | 12.366667 | 2268.871206 | 0.392952 |
| E2 | 2 | minimum-variance | 5.989240 | 0.183960 | 0.631908 | 11.433333 | 2257.849307 | 0.393714 |
| E2 | 3 | buy-and-hold | 5.360634 | 0.191699 | 0.623818 | 12.000000 | 2242.836954 | 0.537078 |
| E2 | 4 | random | 4.934765 | 0.135711 | 0.592501 | 12.333333 | 2594.128898 | 0.457419 |
| E2 | 5 | signal-weighted | 4.906749 | 0.127532 | 0.588822 | 9.033333 | 1750.286699 | 0.489163 |
| E2 | 6 | naive-momentum | 4.628619 | 0.167677 | 0.579669 | 11.266667 | 2942.876806 | 0.529594 |
| E2 | 7 | mean-reversion | 3.048437 | 0.084320 | 0.512691 | 7.200000 | 1696.442616 | 0.352369 |
