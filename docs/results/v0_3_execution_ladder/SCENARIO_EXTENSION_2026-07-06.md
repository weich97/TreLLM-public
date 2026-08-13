# Scenario extension 2026-07-06: classical ladder across three C0 regimes

The deterministic execution ladder (four classical agents, E0-E3, seeds 7/11)
was previously reported for the calm-trend regime only. This note records its
extension to the two remaining headline regimes so the benchmark's **own**
protocol demonstrates ranking movement under execution assumptions, rather than
relying solely on the cited concurrent execution-sensitivity study.

## What changed

`scripts/run_v03_execution_ladder.py` gained a `--scenario {calm,high_vol,jump_tail}`
option (default `calm`). The scenario parameters are **byte-copied** from the
pre-registered direct-API submission runner's frozen definitions
(`scripts/run_v03_direct_api_submission.py`), so the classical board sits on the
exact same market configs as the LLM headline matrix:

| Scenario | scenario_id | Synthetic parameters |
| --- | --- | --- |
| calm | `synthetic_calm_trend_c0_v0_3` | vol 1.0, trend 1.0 (factory defaults elsewhere) |
| high_vol | `synthetic_high_volatility_c0_v0_3` | vol 2.25, trend 0.65, macro 1.4 |
| jump_tail | `synthetic_jump_tail_c0_v0_3` | vol 1.65, tail_df 3, jump_prob 0.15, jump_scale 0.08 |

## Integrity

- **Deterministic, no model calls, no keys** — every row is a classical agent on
  a seeded synthetic path; the whole board is reproducible from the script.
- **Default calm run is byte-identical** to the pre-edit script: the calm
  synthetic dict `{vol 1.0, trend 1.0}` reproduces the previous hard-coded kwargs
  exactly (verified by diffing calm output against `git show HEAD:` of the runner
  before the edit). No frozen calm value moves.
- New regimes write to sibling directories
  (`docs/results/v0_3_execution_ladder_high_vol`, `..._jump_tail`); the calm
  artifact directory is not overwritten.
- **Known pre-existing drift (unrelated to this extension):** the committed calm
  artifact's E3 (calibrated replay fixture) rows differ slightly from the current
  runner output (fill-rate 0.75 vs 0.77, one fewer rejected order) because the
  calibrated-execution path evolved after that artifact was last written. It
  affects only E3; the E0/E1 rows that back the headline ranking-stability result
  are unchanged. The replication pack carries its own internally-consistent
  frozen copy that self-verifies PASS.
