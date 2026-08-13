# Task

A benchmark card currently says:

> Our stress simulator gives calibrated transaction-cost predictions because
> the public BTCUSDT sample shows lower residual MAE than the default stress
> proxy.

Public evidence:

- The public sample is a short Binance BTCUSDT quote/fill sample.
- The stability report checks rolling windows and reports calibrated residual
  MAE versus default stress residual MAE.
- It supports calibration-plumbing robustness.
- It does not support broker-grade, venue-wide, or private-fill transaction
  cost prediction.
- The default public benchmark mode remains `realistic-stress`.

Rewrite the claim and list the missing evidence needed before stronger
transaction-cost claims would be valid.

