# TreLLM v0.3 Execution Stress Grid

This artifact isolates E2 execution-assumption sensitivity against an E1 reference.
It is not a trading-profit claim or a calibrated live-cost forecast.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_calm_trend_c0_v0_3`
- Contamination tier: `C0`
- Profiles: `e1_reference, wide_spread, latency_spike, thin_liquidity, high_impact, combined_stress`
- Agents: `signal-weighted, risk-parity, random`
- Seeds: `7, 11`
- Method: `paired_seed_delta_vs_e1_reference`
- Claim boundary: This fixture isolates execution-assumption sensitivity across spread, latency, participation, and impact. It supports protocol plumbing and mechanism analysis, not live cost prediction or trading-profit claims.

## Axis Summary

| Axis | Rows | Mean absolute return delta | Mean slippage delta | Mean fill-rate delta |
| --- | ---: | ---: | ---: | ---: |
| combined | 3 | 0.024666 | -312.343427 | -0.439879 |
| impact | 3 | 0.000194 | 18.091255 | 0.000000 |
| latency | 3 | 0.022867 | -483.648008 | -0.433706 |
| participation | 3 | 0.000000 | 0.000000 | 0.000000 |
| spread | 3 | 0.003241 | 302.888565 | 0.005208 |

## Paired Sensitivity Rows

| Profile | Axis | Agent | Seeds | Return delta | Sharpe delta | Fill-rate delta | Slippage delta | Intent-execution gap delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wide_spread | spread | random | 2 | -0.004492 | -0.557698 | 0.000000 | 422.886044 | 0.000176 |
| latency_spike | latency | random | 2 | -0.008570 | 1.276060 | -0.431078 | -839.967778 | 0.085778 |
| thin_liquidity | participation | random | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| high_impact | impact | random | 2 | -0.000325 | -0.034782 | 0.000000 | 30.543382 | 0.000011 |
| combined_stress | combined | random | 2 | -0.010683 | 0.929032 | -0.449596 | -635.086491 | 0.085759 |
| wide_spread | spread | risk-parity | 2 | -0.003580 | -0.665569 | 0.015625 | 329.378857 | -0.000005 |
| latency_spike | latency | risk-parity | 2 | -0.021202 | -3.728824 | -0.437500 | -512.703021 | 0.188007 |
| thin_liquidity | participation | risk-parity | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| high_impact | impact | risk-parity | 2 | -0.000189 | -0.038921 | 0.000000 | 17.245125 | -0.000001 |
| combined_stress | combined | risk-parity | 2 | -0.023320 | -4.057731 | -0.437500 | -319.442728 | 0.188204 |
| wide_spread | spread | signal-weighted | 2 | -0.001650 | -0.165086 | 0.000000 | 156.400794 | -0.000036 |
| latency_spike | latency | signal-weighted | 2 | -0.038829 | -1.988803 | -0.432540 | -98.273224 | 0.123786 |
| thin_liquidity | participation | signal-weighted | 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| high_impact | impact | signal-weighted | 2 | -0.000069 | -0.006554 | 0.000000 | 6.485257 | -0.000001 |
| combined_stress | combined | signal-weighted | 2 | -0.039994 | -2.234437 | -0.432540 | 17.498939 | 0.123731 |
