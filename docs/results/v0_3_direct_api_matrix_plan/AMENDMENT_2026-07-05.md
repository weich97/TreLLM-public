# Amendment 2026-07-05: scenario set expanded before any expanded-scenario run

This amendment expands the pre-registered direct-API matrix from one C0 scenario
to three. It is committed (git-timestamped) **before any row of the two added
scenarios is executed**; the original `synthetic_calm_trend_c0_v0_3` rows were
already collected under the 2026-07-02 provider amendment and are unchanged.

| Field | Before (2026-07-02) | After (this amendment) |
| --- | --- | --- |
| Scenarios | `synthetic_calm_trend_c0_v0_3` | `synthetic_calm_trend_c0_v0_3`, `synthetic_high_volatility_c0_v0_3`, `synthetic_jump_tail_c0_v0_3` |
| Models | deepseek-v4-pro, deepseek-v4-flash, glm-5 (api-pinned-2026-07-02) | unchanged |
| Seeds × samples | 10 × 3 | unchanged |
| Execution level | E1 | unchanged |
| Planned rows | 90 | 270 (90 already collected + 180 new) |

## What changed and why

Only the C0 scenario set is expanded. The two added regimes reuse the **same**
universe (SYN+ALT), periods (24), initial cash ($100k), contamination tier (C0),
execution ladder (E1), prompt template, and decoding parameters as the original
scenario; only the synthetic-generator knobs differ. Those knobs are **not
invented for this amendment** -- they are the exact high-volatility and
jump/tail regimes already validated in the execution-sensitivity study
(`scripts/run_execution_sensitivity_sweep.py`):

- `synthetic_high_volatility_c0_v0_3`: volatility_scale 2.25, trend_scale 0.65,
  macro_scale 1.4.
- `synthetic_jump_tail_c0_v0_3`: volatility_scale 1.65, tail_df 3,
  jump_probability 0.15, jump_scale 0.08.

The four exotic regimes named aspirationally in the experiment plan
(crash_recovery, mean_reversion, regime_switch, sideways_chop) are **not** added
here: they have no validated generator parameterization, and inventing one at
freeze time would be weaker science than expanding to three regimes each already
grounded in a companion study. They remain future work behind a deliberate
generator-design step.

## Integrity

- No `high_volatility` or `jump_tail` provider manifest or submission exists at
  the time of this commit; the expansion is registered before it is measured.
- The 90 `calm_trend` rows retain their bytes; their gate already reads
  `headline_scientific_claim_ready: true`.
- Post-freeze edits to the added scenarios' generator parameters are
  prohibited; any change requires a further amendment.
