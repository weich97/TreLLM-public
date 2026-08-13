# TradeArena v0.2 Benchmark Spec

`benchmarks/v0.2/spec.json` is the frozen comparison contract for the next
public benchmark card. The goal is to make model rows comparable before adding
more features or more providers.

## Frozen Surfaces

The v0.2 spec fixes:

- data windows, asset pools, frequency, and rolling-window offsets;
- market rules, risk limits, cash/leverage constraints, and default execution
  stress parameters;
- allowed information, timestamp masking, prompt/version recording, cache
  policy, and redaction requirements;
- seeds, deterministic anchors, classical baselines, and model audit fields;
- metrics, confidence intervals, paired bootstrap tests, paired sign-flip
  permutation tests, and failure accounting.

The spec boundary is explicit: v0.2 measures agent reliability and
intent-to-execution auditability. It does not claim live profitability or
broker-grade transaction-cost prediction unless a row attaches quote/fill
calibration provenance.

## Claim Classes

The spec records three claim classes:

- engineering claims: replayable trajectories, manifests, hashes, and schemas;
- benchmark claims: risk gates and paper-execution friction change outcomes
  under shared assumptions;
- scientific claims: model-specific reliability statements, which require
  stable provider provenance, repeated seeds or rolling windows, wins over
  non-LLM baselines, and failure-mode autopsy.

The fixed non-LLM baseline set is: `always-hold`, `random`, `buy_and_hold`,
`equal_weight`, `naive_momentum`, `mean_reversion`, `risk_parity`, `min_var`,
and `markowitz_mvo`.

## Market Rule Packages

The protocol prefers deeper market rules over a wider list of unsupported asset
classes. Rule packages include A-share T+1 and price limits, Hong Kong board
lots and stamp duty, crypto fee tiers and funding, futures margin and roll
windows, and suspension/circuit/liquidity halt stress. See
[`docs/market_rules.md`](market_rules.md).

## Validation

Run:

```bash
python scripts/validate_benchmark_spec.py benchmarks/v0.2/spec.json
```

The validator checks required fields and prints a canonical SHA-256 hash. Use
that hash in release notes and reproduction reports so a benchmark row can name
the exact protocol it followed.

## Failure Accounting

Failures are part of the benchmark:

- provider call failures are recorded with provider, model, scenario, seed, and
  error class;
- parser failures lower `parse_coverage` and use the declared parser fallback;
- risk blocks count as valid risk interventions;
- execution rejections count as attempted orders;
- missing data invalidates a row unless the scenario declares a data-gap rule
  before evaluation.
- failure autopsy classifies overtrading, pre-risk leverage, low-confidence
  bets, slippage or liquidity insensitivity, memory pollution,
  rationale/decision mismatch, and position-limit noncompliance.

This makes bad rows visible instead of letting leaderboard scripts quietly
select only successful runs.
