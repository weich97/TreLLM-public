# Execution Model Boundaries

TreLLM separates execution assumptions into explicit import surfaces:

| Surface | Module | Intended claim |
| --- | --- | --- |
| Idealized fills | `tradearena.execution.simple` | Unit tests and lower-bound control runs |
| Stress simulator | `tradearena.execution.stress` | Reliability stress testing under transparent assumptions |
| Quote replay | `tradearena.execution.stress.QuoteReplayOrderSimulator` | Replay against observed bid/ask and optional depth |
| Fill replay | `tradearena.execution.fill_replay` | Audit replay against realized fills |
| Calibration | `tradearena.execution.calibration` | Fit or summarize execution parameters from evidence |

Rows without quote/order-book/fill provenance should be labeled `stress-only`.
Rows should use `quote-calibrated` or `fill-replay-validated` only when the
input report includes source, venue, date range, aligned sample size, fitted
parameters, residuals, and output hashes.

`tradearena.tools.simulator` remains a compatibility re-export. It should not be
the target path for new execution work.
