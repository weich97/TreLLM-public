# Claim Boundaries

TreLLM separates three kinds of claims. Mixing them makes TradeArena
leaderboard rows look stronger than the evidence supports.

| Claim class | Supported statement | Required evidence | Not enough evidence |
| --- | --- | --- | --- |
| Engineering claim | The system records replayable market observations, decisions, risk reports, fills, memory, metrics, and hashes. | A trajectory JSON, manifest, schema validation, and reproduction command. | A return table without the trajectory and hash. |
| Benchmark claim | Risk gates and paper-execution frictions change measured agent outcomes under a frozen protocol. | Shared scenarios, seeds or rolling windows, fixed baselines, costs, risk settings, and confidence intervals. | One run, one provider response, or an unversioned prompt. |
| Scientific claim | A model or agent class is more reliable for financial decision making. | Repeated runs, stable provider/version records, redaction policy, non-LLM baselines, p-values or CIs, failure-mode autopsy, and independent replication. | Cache-first/live-call mixtures, provider-drifted rows, or redacted prompts alone. |

## Reporting Rule

For public results, every table should say which claim class it supports.
For a contributor-facing review checklist, see
[`claim_boundary_review_quickstart.md`](claim_boundary_review_quickstart.md).

- Engineering rows can say that an artifact is replayable or auditable.
- Benchmark rows can say that the protocol exposes risk, execution, or
  calibration differences.
- Scientific rows should be rare and conservative. A model should first beat
  fixed non-LLM baselines such as buy-and-hold, equal weight, momentum, mean
  reversion, risk parity, minimum variance, Markowitz/MVO, random, and
  always-hold under the same market and execution assumptions.

## Redaction And Provider Drift

Redacted benchmark rows are useful for participation, but they weaken model
skill claims. Provider-hosted APIs may change routing, wrapper prompts,
context truncation, rate limits, and model aliases. Cache-first and live-call
rows must therefore be labeled separately, and they should not be pooled into a
scientific claim unless the protocol declares how cache provenance is handled.

## Evidence Labels

The TradeArena leaderboard rows carry explicit evidence labels:
`stress-only`, `direct-api`, `protocol-fixture`, `cached-provider`,
`live-provider`, `deterministic-baseline`, `external-submitted`,
`quote-calibrated`, `fill-replay-validated`, `redacted-prompt`, and
`fully-auditable`. These labels are the row-level version of the claim
boundary: they describe whether a result is a stress benchmark, a direct API
manifest, a protocol plumbing fixture, a cached or live provider run, a
deterministic anchor, an external submission, or a quote/fill-validated
execution row. See
[`docs/evidence_labels.md`](evidence_labels.md).
