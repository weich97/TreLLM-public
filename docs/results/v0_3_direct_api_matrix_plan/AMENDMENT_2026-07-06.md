# Amendment 2026-07-06: two GLM model rows added before any of their rows run

This amendment adds two direct-API model rows to the headline matrix:
**glm-5-turbo** (a second GLM-5 capacity tier) and **glm-5.2** (the provider's
current flagship generation). Committed (git-timestamped) **before any row of
either model executes**; every existing row of the 540-row completed matrix is
unchanged and retains its bytes.

| Field | Before (2026-07-05b amendment) | After (this amendment) |
| --- | --- | --- |
| Models | deepseek-v4-pro, deepseek-v4-flash, glm-5 | + glm-5-turbo, glm-5.2 (both `glm`, `GLM_API_KEY`, chat-completions, api-pinned-2026-07-06) |
| Scenarios | calm_trend, high_volatility, jump_tail | unchanged |
| Execution levels | E0, E1 | unchanged |
| Seeds x samples | 10 x 3 | unchanged |
| Planned rows | 540 (all collected) | 900 (540 collected + 360 new) |

## Selection criteria (stated before any result exists)

Candidates were the models listed by the two existing direct-API credentials'
`/models` endpoints on 2026-07-06 (DeepSeek: no additional models beyond the
two already in the matrix; Zhipu: glm-4.5/-air, glm-4.6, glm-4.7, glm-5,
glm-5-turbo, glm-5.1, glm-5.2). Selection is outcome-blind, on two criteria:

1. **glm-5-turbo** -- the second capacity tier of the generation already in
   the matrix. The original registration carried a provision for exactly this
   row; the provision lapsed unexercised, so it re-enters by this fresh
   pre-run amendment rather than by resurrecting a lapsed clause.
2. **glm-5.2** -- the newest flagship generation on the credential, widening
   the capability axis upward.

No performance information about either model on this benchmark existed at
selection time (neither has ever been called by this harness). Older
generations (glm-4.x, glm-5.1) are excluded to bound cost; a further
amendment may add them.

## Acknowledged trade-off

Provider concentration worsens (three of five rows from one vendor). We accept
this deliberately: the pre-registered question is ranking stability across
execution assumptions, which needs capability spread more than vendor spread;
vendor diversity remains addressed by the open external-submission path, and
the concentration is disclosed in the study's limitations.

## Integrity

- No provider manifest or submission exists for either new model at the time
  of this commit (verified: neither id appears under
  `outputs/v0_3_direct_api_matrix/`).
- The 540 collected rows retain their bytes; their gate remains
  `headline_scientific_claim_ready: true` (18/18 groups) independent of this
  expansion, and the new rows form 12 additional threshold groups
  (2 models x 3 scenarios x 2 levels).
- Prompt template (`trellm-allocation-v0.3` / `v0.3.0`), decoding
  (temperature 0.2, top_p 1.0, max_tokens 1200), universe, periods, cash,
  tier, and seeds are all unchanged; post-freeze edits to any of these
  require a further amendment.
