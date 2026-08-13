# Amendment 2026-07-05b: execution level E0 added before any E0 run

This amendment adds the idealized execution level E0 alongside the already-run
E1, so the headline ranking-stability result (E0-vs-E1 Kendall tau) can be
computed on the direct-API matrix -- the benchmark's core question, mirroring
the execution-sensitivity study. Committed (git-timestamped) **before any E0
row is executed**; every existing E1 row is unchanged and retains its bytes.

| Field | Before (2026-07-05 scenario amendment) | After (this amendment) |
| --- | --- | --- |
| Execution levels | E1 | E0, E1 |
| Scenarios | calm_trend, high_volatility, jump_tail | unchanged |
| Models | deepseek-v4-pro, deepseek-v4-flash, glm-5 | unchanged |
| Seeds x samples | 10 x 3 | unchanged |
| Planned rows | 270 (all collected) | 540 (270 E1 collected + 270 E0 new) |

## What changed and why

Only the execution level set is expanded. E0 is the idealized-fill convention
(complete fills at close, fixed 2 bps slippage + 1 bps commission, no latency /
participation cap / impact); its parameters are the ones already defined in the
submission runner's `EXECUTION_LEVELS` and used by the execution-sensitivity
study, not invented here. E0 and E1 share the same universe, periods, cash,
tier, scenarios, prompt template, and decoding parameters; only the execution
model differs, which is exactly the axis the ranking-stability measurement
isolates. E2/E3 remain out of scope for the headline matrix (a separate stress
grid, if run, is a further amendment).

## Integrity

- No E0 provider manifest or submission exists at the time of this commit.
- The 270 E1 rows (three scenarios) retain their bytes; their gate already
  reads `headline_scientific_claim_ready: true` with 9 main-threshold groups.
- Post-freeze edits to the E0 execution parameters are prohibited; any change
  requires a further amendment.
