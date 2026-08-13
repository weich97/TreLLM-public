# Quote/Fill Execution Calibration

This report fits TreLLM's compact execution equation from top-of-book quotes and realized fills.

## Input Coverage

- Symbols: BTCUSDT
- Quote rows: 884
- Fill rows: 500
- Aligned rows: 500
- Quote file: `data/public/binance_btcusdt_perp_2024_03_01_sample/quotes.csv`
- Fill file: `data/public/binance_btcusdt_perp_2024_03_01_sample/fills.csv`

## Fitted Parameters

| Parameter | Value |
| --- | ---: |
| Median spread | 0.016314 bps |
| P90 spread | 0.016335 bps |
| P99 spread | 0.049479 bps |
| Base slippage | 0.0 bps |
| Market impact coefficient | 0.008189 |
| P90 participation | 0.00098902 |
| Median latency | not supplied |
| P90 latency | not supplied |
| Median quote event lag | 0.006 s |
| P90 quote event lag | 0.01 s |
| Median quote staleness at fill | 0.5105 s |
| P90 quote staleness at fill | 0.9132 s |

## Fit Quality

| Metric | Value |
| --- | ---: |
| Residual mean | -0.576516 bps |
| Residual MAE | 0.907738 bps |
| Residual P90 abs | 1.660351 bps |
| Residual max abs | 3.471537 bps |
| Median shortfall | 0.008168 bps |
| P90 shortfall | 1.658585 bps |
| P99 shortfall | 3.631274 bps |
| Mean participation cap residual | 0.00020016 |
| Max participation cap residual | 0.01215867 |

## Calibrated vs Stress-Only Replay Error

| Model | Residual MAE | Residual P90 abs |
| --- | ---: | ---: |
| Default stress-only | 3.163166 bps | 4.456712 bps |
| Quote/fill calibrated | 0.907738 bps | 1.660351 bps |

MAE reduction versus the default stress-only model: 2.255428 bps.

## Suggested Simulator Configuration

| Parameter | Value |
| --- | ---: |
| `commission_bps` | 0.0 |
| `base_slippage_bps` | 0.0 |
| `spread_bps` | 0.016314 |
| `participation_rate` | 0.00098902 |
| `latency_steps` | 1 |
| `market_impact` | 0.008189 |

## Interpretation Boundary

This fit uses observed top-of-book spread and realized fills. It is stronger than OHLCV diagnostics, but it still depends on the fill sample, venue, order type, and reference-price definition.
