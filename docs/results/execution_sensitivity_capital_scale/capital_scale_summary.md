# Capital-scale evidence (execution-units correction)

## 1. Cap-binding diagnostic (deterministic board, all regimes pooled)

| Capital | Level | Median order (sh) | Median part. | Max part. | Mean fill | % cap-bound | % cash/pos-bound |
|---|---|---|---|---|---|---|---|
| 100k | E1 | 170.0 | 0.00012 | 0.00056 | 0.9591 | 0.0 | 13.6 |
| 100k | harsh | 252.1 | 0.00013 | 0.00063 | 0.8867 | 0.0 | 21.3 |
| 100k | participation_1pct | 170.0 | 0.00012 | 0.00056 | 0.9591 | 0.0 | 13.6 |
| 30M | E1 | 46121.2 | 0.03523 | 0.05 | 0.8658 | 32.7 | 7.8 |
| 30M | harsh | 73229.2 | 0.01 | 0.01 | 0.2655 | 95.2 | 1.4 |
| 30M | participation_1pct | 44283.2 | 0.01 | 0.01 | 0.4305 | 83.5 | 1.3 |

## 2. Capital-scale robustness (E0 ranking vs E1 / harsh, tau_b)

| Capital | Regime | tau_b E0->E1 | tau_b E0->harsh |
|---|---|---|---|
| 100k | high_vol | 0.81 | 0.429 |
| 30M | high_vol | 0.81 | 0.333 |

## 3. Open-loop check: drawdown kill-switch rate

| Capital | Level | Kill triggers | Steps | Kill rate % |
|---|---|---|---|---|
| 100k | E0 | 0 | 840 | 0.0 |
| 100k | E1 | 0 | 840 | 0.0 |
| 100k | harsh | 0 | 840 | 0.0 |
| 100k | participation_1pct | 0 | 840 | 0.0 |
| 30M | E0 | 0 | 840 | 0.0 |
| 30M | E1 | 0 | 840 | 0.0 |
| 30M | harsh | 0 | 840 | 0.0 |
| 30M | participation_1pct | 0 | 840 | 0.0 |

Pre-gate (strategy) target-weight identity across E0/E1: max abs per-step diff = 0.00e+00; mismatched steps = 0.