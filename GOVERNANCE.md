# Governance

TreLLM is maintained as an LLM-driven trading audit and live-readiness control
system. TradeArena is the public leaderboard and benchmark-card surface inside
TreLLM. The project prioritizes reproducibility, safe execution boundaries,
human approval, and reviewable artifacts over short-term performance claims.

## Version Policy

- `v0.x` APIs are experimental.
- Core schemas and protocol objects receive stricter review than examples.
- Examples may evolve quickly when they improve reproducibility or onboarding.

## Review Principles

- Core protocol changes should preserve replayable trajectories and audit logs.
- Provider adapters must avoid committing raw prompt/response caches.
- Broker or execution adapters must default to offline export, dry run, paper
  sandbox, or human-approved behavior.
- New benchmark rows should include data/source notes, execution assumptions,
  risk assumptions, and a reproducibility hash.
- Advanced integrations must document their network calls, secret source,
  cache/redaction policy, and whether they can touch live accounts.
- First-run demos must remain no-key and must not depend on live model, data, or
  broker APIs.
- Future live adapters must satisfy `docs/broker_adapter_contract.md` before
  they are presented as supported integration surfaces.

## Advanced Integration Gate

Changes that add or expand DeepSeek, Poe, OpenAI-compatible, Yahoo Finance,
AkShare, broker, or account-data paths should be reviewed against this gate:

- the default code path is offline, cache replay, dry run, paper sandbox, or
  human-review;
- credentials are read from environment variables or an OS secret manager;
- generated raw caches and private data are ignored by Git;
- public docs state data provenance and execution-calibration limits;
- tests prove the default path does not submit live orders;
- live-capable broker paths include explicit approval, limits, kill switch, and
  reconciliation artifacts;
- redacted manifests are available when results need to be shared.

## Maintainer Decisions

Maintainers may reject contributions that blur the boundary between benchmark
research and live financial advice, expose credentials or private data, or make
unverifiable profitability claims.
