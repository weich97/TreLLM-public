# TreLLM v0.3 Execution Ladder

This artifact reports how deterministic agent rankings and mechanism metrics move across the v0.3 execution-assumption ladder.
It is not a trading-profit claim.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_jump_tail_c0_v0_3`
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
| E0 | E1 | 4 | 0.666667 | 1.000000 | 0.009239 | -0.087173 | 0.252871 | 2461.390983 |
| E0 | E2 | 4 | 0.333333 | 0.500000 | -0.012487 | -0.391213 | 0.395365 | 2605.092242 |
| E0 | E3 | 4 | 0.666667 | 1.000000 | -0.034942 | -0.300720 | 0.365516 | 2583.457762 |

## Per-Level Summary

| Level | Rank | Agent | Sharpe mean | Return mean | Fill rate | Rejected orders | Slippage | Intent-execution gap |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | 1 | risk-parity | 11.966456 | 0.385989 | 1.000000 | 0.000000 | 31.609323 | 0.000015 |
| E0 | 2 | naive-momentum | 10.885788 | 0.272884 | 1.000000 | 0.000000 | 49.251019 | 0.000015 |
| E0 | 3 | signal-weighted | 10.340490 | 0.260351 | 1.000000 | 0.000000 | 27.038447 | 0.379868 |
| E0 | 4 | random | 9.395163 | 0.253592 | 1.000000 | 0.000000 | 176.819717 | 0.000040 |
| E1 | 1 | risk-parity | 10.959746 | 0.444238 | 0.927083 | 1.500000 | 2706.656482 | 0.271554 |
| E1 | 2 | signal-weighted | 9.907836 | 0.225977 | 0.930048 | 0.500000 | 1461.352363 | 0.443979 |
| E1 | 3 | naive-momentum | 8.105557 | 0.236333 | 0.902924 | 2.000000 | 2546.661498 | 0.268728 |
| E1 | 4 | random | 7.903363 | 0.303223 | 0.891253 | 3.000000 | 3415.612097 | 0.407161 |
| E2 | 1 | risk-parity | 9.587675 | 0.331648 | 0.645833 | 11.000000 | 2646.795060 | 0.420766 |
| E2 | 2 | random | 7.880397 | 0.246749 | 0.609144 | 11.000000 | 2939.583383 | 0.414746 |
| E2 | 3 | naive-momentum | 7.188259 | 0.381559 | 0.596581 | 11.000000 | 3460.464641 | 0.595168 |
| E2 | 4 | signal-weighted | 6.805643 | 0.162911 | 0.583591 | 9.000000 | 1658.244390 | 0.530718 |
| E3 | 1 | risk-parity | 10.290154 | 0.281297 | 0.708333 | 10.000000 | 3120.546070 | 0.401837 |
| E3 | 2 | signal-weighted | 9.177935 | 0.174297 | 0.667183 | 8.000000 | 1321.289405 | 0.463156 |
| E3 | 3 | naive-momentum | 9.173992 | 0.289306 | 0.742695 | 6.500000 | 3667.658624 | 0.516566 |
| E3 | 4 | random | 8.893312 | 0.288148 | 0.678911 | 10.000000 | 2509.055455 | 0.460442 |
