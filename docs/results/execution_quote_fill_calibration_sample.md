# Quote/Fill Execution Calibration

This report fits TreLLM's compact execution equation from top-of-book quotes and realized fills.

## Input Coverage

- Symbols: BTCUSDT
- Quote rows: 10
- Fill rows: 8
- Aligned rows: 8
- Quote file: `data/public/microstructure_sample/quotes.csv`
- Fill file: `data/public/microstructure_sample/fills.csv`

## Fitted Parameters

| Parameter | Value |
| --- | ---: |
| Median spread | 0.952592 bps |
| P90 spread | 1.364077 bps |
| P99 spread | 1.563325 bps |
| Base slippage | 0.0 bps |
| Market impact coefficient | 0.042748 |
| P90 participation | 0.00118631 |
| Median latency | 15.0 s |
| P90 latency | 19.0 s |
| Median quote event lag | not supplied |
| P90 quote event lag | not supplied |
| Median quote staleness at fill | 22.5 s |
| P90 quote staleness at fill | 43.0 s |

## Fit Quality

| Metric | Value |
| --- | ---: |
| Residual mean | -0.446571 bps |
| Residual MAE | 0.446571 bps |
| Residual P90 abs | 0.612921 bps |
| Residual max abs | 0.654595 bps |
| Median shortfall | 1.467394 bps |
| P90 shortfall | 1.646463 bps |
| P99 shortfall | 1.707969 bps |
| Mean participation cap residual | 4.219e-05 |
| Max participation cap residual | 0.0003375 |

## Calibrated vs Stress-Only Replay Error

| Model | Residual MAE | Residual P90 abs |
| --- | ---: | ---: |
| Default stress-only | 3.533257 bps | 4.130279 bps |
| Quote/fill calibrated | 0.446571 bps | 0.612921 bps |

MAE reduction versus the default stress-only model: 3.086685 bps.

## Suggested Simulator Configuration

| Parameter | Value |
| --- | ---: |
| `commission_bps` | 1.0 |
| `base_slippage_bps` | 0.0 |
| `spread_bps` | 0.952592 |
| `participation_rate` | 0.00118631 |
| `latency_steps` | 1 |
| `market_impact` | 0.042748 |

## Interpretation Boundary

This fit uses observed top-of-book spread and realized fills. It is stronger than OHLCV diagnostics, but it still depends on the fill sample, venue, order type, and reference-price definition.
