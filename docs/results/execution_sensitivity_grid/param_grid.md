# Execution-Parameter Sensitivity Grid (high-volatility regime)

Kendall tau-b between the idealized leaderboard and each parameter cell,
spanning liquid to stressed markets. If reordering appeared only at
extreme parameters, mild cells would show tau near 1.

| Impact | Participation | Latency | Market | Kendall tau vs ideal | Top-3 Jaccard |
| ---: | ---: | ---: | --- | ---: | ---: |
| 0.05 | 10% | 0 | liquid large-cap | 1.0 | 1.0 |
| 0.1 | 5% | 1 | typical equity | 0.81 | 0.5 |
| 0.15 | 5% | 1 | default stress | 0.81 | 0.5 |
| 0.2 | 3% | 2 | small-cap / volatile | 0.524 | 0.5 |
| 0.3 | 1% | 3 | stressed / illiquid | 0.429 | 0.2 |

Even the mild 'typical equity' cell (impact 0.10, 5\% participation, 1-bar latency) reorders the leaderboard (tau 0.81), so the effect is not confined to extreme parameters.
