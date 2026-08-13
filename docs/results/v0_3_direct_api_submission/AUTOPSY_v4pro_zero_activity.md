# Autopsy: deepseek-v4-pro shows zero market activity across the registered matrix

**Date:** 2026-07-04 · **Scope:** all 30 registered (seed, sample) rows for
`deepseek-v4-pro` on `synthetic_calm_trend_c0_v0_3` / C0 / E1.

## Observation

Every `deepseek-v4-pro` row reports `total_return = 0.0`, `sharpe = 0.0`,
`execution_fill_rate = 0.0`, while `deepseek-v4-flash` and `glm-5` trade
normally on the identical packets (mean return ≈ +20% in the calm-trend
scenario).

## Verification trail (this is model behavior, not a harness fault)

1. All 720 pro calls (24 steps × 30 runs) returned HTTP success and **valid
   JSON in the pinned response shape** — no parse fallbacks, no refusals, no
   truncation.
2. The responses are explicit: `"target_weight": 0.0, "confidence": 0.0` for
   both symbols, at **every** step (verified 0/24 non-zero calls on sampled
   runs; fill rate 0.0 across all 30).
3. The same transport, prompt template, decoding parameters (pinned
   temperature 0.2 / top_p 1.0 / max_tokens 1200) produced non-zero trading
   from `deepseek-v4-flash` (same vendor, same endpoint family) and `glm-5`.
4. Plausible mechanism: the protocol's pinned system prompt instructs a
   "cautious trading research analyst" returning "calibrated" weights; the
   initial state carries no track record (`lookback_steps: 0`). v4-pro
   calibrates to zero confidence and never enters; since it never trades, its
   subsequent state stays flat and the hold loop self-reinforces. Its sibling
   model breaks out of the same loop within a few steps.

## Disposition

- The 90-row registered matrix stands as collected: the plan froze at the
  first executed row, and this is an honest, reproducible behavioral outcome
  under the registered protocol — exactly the kind of per-model
  *reliability-profile* datapoint the benchmark is designed to surface
  ("declines to act" is a reportable profile, distinct from "cannot act").
- Any prompt/protocol change intended to coax activity would be a NEW
  registration (amendment before its first row), not a rerun of these rows.
- Reporting rule: report the row with its zero-activity profile, with this
  autopsy as supporting material; do not present per-return rankings that
  silently include a non-participating agent without flagging it.
