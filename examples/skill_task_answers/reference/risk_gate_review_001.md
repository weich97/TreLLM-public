# Risk Gate Review

The risk report shows a low-confidence block through the min_confidence or
confidence floor check.

It also shows target-weight clipping: a requested position was clipped by the
max_abs_weight control. Other risk budget fields to check include
max_gross_exposure, turnover, drawdown, participation, latency, and slippage.

Warnings must be separated from error or hard block outcomes. A warning can
flag elevated turnover or monitoring risk, while a hard block rejects or changes
the approved decision.

Missing evidence: without the full trajectory and execution report, the review
cannot conclude portfolio-level effectiveness.
