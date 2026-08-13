# Deterministic anchor baselines: frozen spec (2026-07-06)

Written before the anchor runs execute. Fills the v0.3 benchmark's pre-registered design
element "deterministic baselines anchor every scenario at 30 seeds across E0,
E1, and the E2 grid" on the exact market configuration of the completed
direct-API headline matrix.

## Configuration (identical to the frozen matrix rows)

- Universe: SYN+ALT synthetic two-asset, 24 periods, $100k initial cash,
  max-position risk, contamination tier C0.
- Scenarios: the three frozen headline regimes (calm_trend, high_volatility,
  jump_tail) with synthetic parameters byte-identical to
  `scripts/run_v03_direct_api_submission.py`.
- Execution levels: E0, E1, E2 (harsh-friction corner), as defined in
  `scripts/run_v03_execution_ladder.py::EXECUTION_LEVELS` (unchanged).
- Agents (seven deterministic policies): buy-and-hold, signal-weighted,
  naive-momentum, mean-reversion, risk-parity, minimum-variance, random.

## Seeds (30, frozen here)

The 10 pre-registered matrix seeds, extended with the next 20 primes:

```
7, 11, 17, 23, 31, 37, 41, 43, 47, 53,
59, 61, 67, 71, 73, 79, 83, 89, 97, 101,
103, 107, 109, 113, 127, 131, 137, 139, 149, 151
```

The first 10 coincide exactly with the matrix seeds so that combined
LLM+anchor leaderboards can be computed on matched market paths (classical
rows restricted to those 10 seeds for any combined-board statistic); the
30-seed set is used for the anchor calibration table itself.

## Runner

`scripts/run_v03_execution_ladder.py --scenario {calm,high_vol,jump_tail}
--agents <the seven above> --seeds <the 30 above> --levels E0,E1,E2
--output-dir docs/results/v0_3_anchor_baselines_<scenario>`

Deterministic, no model calls, no keys; every row reproducible from the
command line above.
