# Contributor Roadmap

TreLLM grows best when contributions make financial AI agents easier to
evaluate, audit, reproduce, control, or extend. TradeArena is the public
leaderboard module and benchmark-card layer inside that system. This roadmap groups good
issues and research extensions by contributor profile so newcomers do not need
to infer where they fit.

For concrete issue-sized tasks, use
[`docs/community_tasks.md`](community_tasks.md).

## Route A: Newcomer / First PR

Good first contributions should be small, offline-friendly, and easy to review.

- Reproduce a documented command and submit an external validation issue.
- Add a holdings CSV importer for the retail planning sandbox.
- Add another execution stress preset after the v0.1.1 high-spread example.
- Improve alt text, captions, and keyboard-readable HTML for generated reports.
- Add one new deterministic scenario to `examples/quickstart_core_benchmark.py`.

Expected shape: one example, one small doc update, and one test or smoke check.

## Route B: Quant / Finance

These contributions add market-specific realism while keeping the TreLLM audit
trail inspectable.

- Futures roll, expiry, and margin-risk demos.
- Corporate-action calendar sidecars for splits, dividends, and trading halts.
- Crypto microstructure stress presets with fee tiers and spread shocks.
- A-share board-specific rule extensions beyond T+1 and price limits.

Expected shape: a data or risk plugin, a reproducible example, and a compact
result artifact under `outputs/examples/`.

## Route B2: Broker / Trading Operations

These contributions move TreLLM from offline audit research toward human-gated,
live-ready trading infrastructure.

- Harden broker-review exports with approval fields and reconciliation IDs.
- Add dry-run broker adapters that validate request shape without network
  calls.
- Add paper-sandbox broker adapters behind optional dependencies.
- Add broker response artifacts for rejects, partial fills, cancels, and fees.
- Add kill-switch, notional-limit, and allowed-symbol tests for broker paths.

Expected shape: an adapter or contract test, no default live submission, a
reviewable demo artifact, and compliance with
[`broker_adapter_contract.md`](broker_adapter_contract.md). The PR should also
match one of the external contribution tracks in
[`live_trading_readiness.md`](live_trading_readiness.md#external-contribution-tracks).

## Route C: ML / LLM Evaluation

These contributions strengthen the TradeArena leaderboard module and benchmark-card layer.

- Redacted TradeArena leaderboard submissions using `schemas/benchmark_submission.schema.json`.
- Reasoning-mode ablations, including rationale-free and tool-restricted modes.
- False-audit and placebo-feedback trust-calibration probes.
- Additional representation diagnostics that do not require raw provider text.

Expected shape: a benchmark scenario, metrics that can be compared across
agents, and redaction rules for provider-sensitive content.

## Route D: Infra / Ecosystem

These contributions reduce friction for external users.

- Colab and Codespaces improvements.
- PyPI packaging hardening.
- Static result gallery and benchmark registry pages.
- CI checks for generated docs, schemas, and demo artifacts.

Expected shape: a repeatable command, documentation, and no hidden service
dependency in the first-run path.

## What A Strong PR Looks Like

- It keeps raw LLM prompt/response caches out of Git.
- It adds or updates a hands-on example.
- It names the exact command used for validation.
- It preserves the audit lifecycle: observation, decision, risk, execution,
  portfolio state, memory, and evaluation.
- It is clear whether live APIs are optional or required.
- Broker-facing work states its mode: offline export, dry run, paper sandbox,
  or human-approved live.
- It states whether the contribution supports the academic report, external
  validation, or community participation maturity track.
