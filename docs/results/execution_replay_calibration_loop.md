# Execution Replay Calibration Loop

This is a small execution evidence loop. Stress mode is a conservative proxy under shared OHLCV assumptions, not ground truth. Quote replay uses observed top-of-book and available best-size constraints. Fill replay applies realized sample fills for audit replay; public exchange trades are not broker-specific private fills.

## Samples

| Sample | Symbols | Fills | Quote rows | Source | Boundary |
| --- | --- | ---: | ---: | --- | --- |
| BTCUSDT redistributable microstructure fixture | BTCUSDT | 8 | 10 | tradearena_public_microstructure_fixture_v1 | Checked-in redistributable fixture for calibration plumbing; not a venue-wide cost claim. |
| BTCUSDT Binance USD-M public sample | BTCUSDT | 50 | 884 | Binance public-data USD-M futures daily files | Public Binance bookTicker/trades sample; stronger than OHLCV stress, but not broker-specific private-fill evidence. |

## Mode Comparison

| Sample | Mode | Evidence | Orders | Fill ratio | Reject rate | Partials | Median spread | Mean slippage | P90 abs slippage | Latency | Slippage cost |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| fixture | `ohlcv_stress` | `stress-only`, `conservative-proxy` | 8 | 1.000 | 0.000 | 0 | 0.9526 bps | 4.2152 bps | 4.8195 bps | 1.000 steps | 37.8771 |
| fixture | `quote_replay` | `quote-replay`, `public-top-of-book`, `depth-constrained` | 8 | 0.950 | 0.000 | 1 | 0.9526 bps | 1.7518 bps | 1.9751 bps | 0.000 steps | 15.3359 |
| fixture | `fill_replay` | `fill-replay`, `sample-realized-fills` | 8 | 1.000 | 0.000 | 0 | 0.9526 bps | 1.4241 bps | 1.6465 bps | 15.000 s | 13.4560 |
| binance | `ohlcv_stress` | `stress-only`, `conservative-proxy` | 50 | 1.000 | 0.000 | 0 | 0.0163 bps | 5.4570 bps | 13.9341 bps | 1.000 steps | 98.2182 |
| binance | `quote_replay` | `quote-replay`, `public-top-of-book`, `depth-constrained` | 50 | 0.570 | 0.000 | 12 | 0.0163 bps | 1.2586 bps | 1.2802 bps | market-data lag 0.008 s | 15.7244 |
| binance | `fill_replay` | `fill-replay`, `sample-realized-fills` | 50 | 1.000 | 0.000 | 0 | 0.0163 bps | 0.2996 bps | 1.3976 bps | market-data lag 0.008 s | 6.6714 |

## Interpretation

- `ohlcv_stress` is the conservative proxy used by default benchmark rows. It is useful for shared stress comparisons, not for ground-truth transaction-cost prediction.
- `quote_replay` upgrades the evidence by using observed top-of-book spread and best-size constraints, but it still lacks hidden queue position and broker-routing outcomes.
- `fill_replay` applies realized sample fills. In the Binance row these are public exchange trades, not private broker fills, so the row supports calibration plumbing rather than venue-wide execution claims.

## Reproduce

```bash
python scripts/run_execution_replay_calibration_loop.py
```
