# Evaluation Rigor Protocol

TradeArena leaderboards should be read as auditable reliability studies, not
single-run trading claims. The tracked protocol separates three sources of
uncertainty:

- **Multi-seed variance:** synthetic benchmarks accept repeated seeds per
  `(model, scenario)`; the tracked deterministic anchors use five seeds so every
  LLM row can be compared to `random` and `always-hold`.
- **Rolling walk-forward validation:** real-market seeds map to explicit
  `window_offset` values. The same `(scenario, seed)` keys are used for paired
  comparisons, which reduces single-window overfit.
- **Provider and cache drift:** provider-backed runs publish redacted manifests
  with provider/model labels, timestamp masking, data hashes, and cache policy.
  Raw prompts and responses remain in ignored local cache files.

## Required Statistics

Every aggregate leaderboard should report:

- raw seed rows;
- mean and sample standard deviation;
- 95% bootstrap confidence intervals;
- paired bootstrap p-values versus `always-hold` and `random`;
- paired sign-flip permutation p-values versus the same anchors.

Bootstrap intervals summarize sampling variance. The paired sign-flip
permutation test is included because small benchmark matrices can have only a
few matched windows, making distributional assumptions fragile.

## Real-Market Walk-Forward

Run the real-market matrix with:

```bash
python scripts/run_real_market_leaderboard.py --seeds 7,11,17,23,31 --update-registry
```

This writes:

- `docs/results/real_market_matrix/real_market_model_matrix.csv`
- `docs/results/real_market_matrix/real_market_model_matrix_aggregate.csv`
- `docs/results/real_market_matrix/real_market_model_matrix_significance.csv`
- `docs/results/real_market_matrix/real_market_walk_forward.csv`

`real_market_walk_forward.csv` is the audit table for rolling validation. It
records the seed set, window offsets, historical period, data frequency, cache
policy, provider-call policy, timestamp policy, and provider drift guard.

## Interpreting Rankings

A leaderboard rank is meaningful only with its uncertainty columns. Prefer
claims such as "model A has a positive paired mean return delta with bootstrap
CI excluding zero" over point estimates such as "model A ranks first." When
bootstrap and permutation tests disagree, report both and treat the result as
inconclusive until more rolling windows or seeds are available.
