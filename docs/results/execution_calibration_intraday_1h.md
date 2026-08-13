# Execution Calibration Diagnostic

This diagnostic is computed from OHLCV bars. It estimates bar-observable range and volume quantities, while spread, fees, market impact, and latency remain explicit assumptions unless quote, broker, or order-log data are supplied.

## Data Summary

- Symbols: 51
- Rows: 21212
- Median close: 242.235001
- Median volume: 812441.5
- Median dollar volume: 173587705.900314
- Median intrabar range: 67.421809 bps
- P90 intrabar range: 164.984371 bps

## Suggested Simulator Configuration

| Parameter | Value | Status |
| --- | ---: | --- |
| `commission_bps` | 1.0 | user/broker assumption |
| `base_slippage_bps` | 1.348436 | OHLCV range proxy |
| `spread_bps` | not supplied | quote data required if not supplied |
| `participation_rate` | 0.05 | policy cap |
| `latency_steps` | 1 | system/broker log assumption |
| `market_impact` | 0.15 | execution-log fit required |

## Model-Implied Slippage Components

- Median volatility component: 6.742181 bps
- Impact at participation cap: 75.0 bps
- Expected buy slippage at median range: 83.090617 bps

## Identification Warning

OHLCV bars do not contain bid-ask quotes, order-book depth, queue position, broker fees, order timestamps, or realized execution shortfall. Treat this as a bar-level diagnostic, not broker-grade calibration.
