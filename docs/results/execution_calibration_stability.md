# Execution Calibration Stability

This report checks stability of a public quote/fill calibration sample across rolling windows. It supports calibration-plumbing robustness, not venue-wide or broker-grade execution claims.

## Summary

- Windows: 5
- Mean calibrated residual MAE: 0.905927 bps
- Mean stress residual MAE: 3.163166 bps
- Mean MAE reduction vs stress: 2.257239 bps
- Windows where calibrated beats stress: 5 / 5

## Window Results

| Window | Fill window | Fills | Spread median | Calibrated MAE | Stress MAE | Reduction | P90 participation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2024-03-01T00:00:00.019000Z to 2024-03-01T00:01:37.984000Z | 100 | 0.016327 bps | 1.155006 bps | 3.023066 bps | 1.868060 bps | 0.00088348 |
| 2 | 2024-03-01T00:01:40.018000Z to 2024-03-01T00:04:34.696000Z | 100 | 0.016330 bps | 0.961625 bps | 3.342327 bps | 2.380702 bps | 0.00066177 |
| 3 | 2024-03-01T00:04:38.131000Z to 2024-03-01T00:07:22.142000Z | 100 | 0.016312 bps | 0.887058 bps | 3.331391 bps | 2.444333 bps | 0.00053073 |
| 4 | 2024-03-01T00:07:23.873000Z to 2024-03-01T00:11:07.235000Z | 100 | 0.016290 bps | 0.799949 bps | 3.045434 bps | 2.245485 bps | 0.00182691 |
| 5 | 2024-03-01T00:11:08.097000Z to 2024-03-01T00:14:59.998000Z | 100 | 0.016306 bps | 0.725995 bps | 3.073612 bps | 2.347617 bps | 0.00100744 |

## Reproduce

```bash
python scripts/run_execution_calibration_stability.py
```
