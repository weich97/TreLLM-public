# Execution Sensitivity on Real Market Data (Deterministic Agents)

Ranking stability between idealized (E0) and stressed execution on real
Yahoo OHLCV, mirroring the synthetic-regime analysis. Low Kendall tau
means the friction-driven leaderboard reordering persists on real prices.

| Window | Level vs E0 | Kendall tau | Top-3 Jaccard |
| --- | --- | ---: | ---: |
| rates_drawdown_2022 | E1_default_stress | 0.905 | 0.500 |
| rates_drawdown_2022 | E2_harsh_corner | 0.810 | 0.500 |
| rates_drawdown_2022 | E2_latency_3 | 0.810 | 0.500 |
| rates_drawdown_2022 | E2_participation_1pct | 0.905 | 0.500 |
| rates_drawdown_2022 | E2_spread_20bps | 0.905 | 0.500 |
| recent_cross_asset | E1_default_stress | 0.905 | 0.500 |
| recent_cross_asset | E2_harsh_corner | 0.810 | 0.500 |
| recent_cross_asset | E2_latency_3 | 0.810 | 0.500 |
| recent_cross_asset | E2_participation_1pct | 0.905 | 0.500 |
| recent_cross_asset | E2_spread_20bps | 0.905 | 0.500 |
