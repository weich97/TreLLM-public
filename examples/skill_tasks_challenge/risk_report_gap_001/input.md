# Task

Review this proposed risk report summary:

> The risk gate worked because it clipped large positions.

Configuration and observed events:

- `max_abs_weight = 0.35`
- `min_confidence = 0.50`
- `max_gross_exposure = 1.0`
- `max_single_step_turnover = 0.60`
- `max_drawdown = 0.12`
- observed rolling drawdown: `0.158`
- observed decision confidence values: `0.41`, `0.35`
- observed post-trade slippage: `28.4 bps`
- observed latency: `3 steps`

The summary only mentions position clipping. Identify which risk lifecycle
checks are missing from the explanation and propose a more complete report.

