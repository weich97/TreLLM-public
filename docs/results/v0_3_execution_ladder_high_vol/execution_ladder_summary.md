# TreLLM v0.3 Execution Ladder

This artifact reports how deterministic agent rankings and mechanism metrics move across the v0.3 execution-assumption ladder.
It is not a trading-profit claim.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_high_volatility_c0_v0_3`
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
| E0 | E1 | 4 | 1.000000 | 1.000000 | -0.007557 | -0.076485 | 0.259242 | 1789.693403 |
| E0 | E2 | 4 | 0.333333 | 0.500000 | -0.034776 | -0.380738 | 0.377480 | 1952.337753 |
| E0 | E3 | 4 | 1.000000 | 1.000000 | 0.015886 | -0.291523 | 0.332703 | 1920.105635 |

## Per-Level Summary

| Level | Rank | Agent | Sharpe mean | Return mean | Fill rate | Rejected orders | Slippage | Intent-execution gap |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 | 1 | naive-momentum | 15.138098 | 0.231811 | 1.000000 | 0.000000 | 45.872930 | 0.000013 |
| E0 | 2 | risk-parity | 14.400138 | 0.258233 | 1.000000 | 0.000000 | 22.496969 | 0.000016 |
| E0 | 3 | random | 12.158801 | 0.191346 | 1.000000 | 0.000000 | 175.160273 | 0.000039 |
| E0 | 4 | signal-weighted | 10.781751 | 0.168840 | 1.000000 | 0.000000 | 29.406806 | 0.350185 |
| E1 | 1 | naive-momentum | 13.650754 | 0.232036 | 0.924812 | 1.000000 | 2052.391593 | 0.284306 |
| E1 | 2 | risk-parity | 12.912313 | 0.231909 | 0.936835 | 1.000000 | 1844.191032 | 0.257525 |
| E1 | 3 | random | 9.993047 | 0.186689 | 0.902364 | 2.500000 | 2287.888196 | 0.404554 |
| E1 | 4 | signal-weighted | 9.759031 | 0.169366 | 0.930048 | 0.500000 | 1247.239770 | 0.440835 |
| E2 | 1 | risk-parity | 11.534496 | 0.204921 | 0.614583 | 12.500000 | 1773.983649 | 0.383602 |
| E2 | 2 | naive-momentum | 10.682104 | 0.236639 | 0.578947 | 11.500000 | 3046.645183 | 0.605228 |
| E2 | 3 | signal-weighted | 8.997547 | 0.131519 | 0.651116 | 6.500000 | 1399.310228 | 0.484744 |
| E2 | 4 | random | 8.824453 | 0.138045 | 0.632400 | 10.000000 | 1862.348929 | 0.386598 |
| E3 | 1 | naive-momentum | 14.121999 | 0.281700 | 0.753663 | 6.000000 | 2897.904554 | 0.485216 |
| E3 | 2 | risk-parity | 11.944662 | 0.262692 | 0.687500 | 11.000000 | 1837.399391 | 0.326999 |
| E3 | 3 | random | 11.150984 | 0.183470 | 0.655127 | 11.000000 | 1976.529842 | 0.440177 |
| E3 | 4 | signal-weighted | 10.365478 | 0.185911 | 0.737616 | 5.500000 | 1241.525732 | 0.428673 |
