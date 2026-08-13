# TreLLM Schemas

TreLLM treats a financial AI agent as an auditable reliability lifecycle,
not a black-box signal generator. A benchmark step records the following
protocol surfaces.

## Observation Schema

- `timestamp`
- `bars`: symbol to OHLCV bar
- `news`: timestamped news items
- `macro`: macro observations
- `filings`: optional timestamped filing items loaded from CSV sidecars
- `alt_data`: optional alternative data
- `portfolio_state`: cash, positions, prices, equity
- `memory_digest`: hash of recent memory state

## Action Schema

- `Decision`: symbol, side, target weight, confidence, rationale
- `Order`: symbol, side, quantity, type, limit price, reason
- `Fill`: executed quantity, requested quantity, price, commission, slippage, latency, liquidity, fill ratio, status
- execution config: commission, quoted spread, base slippage, latency,
  participation, and market impact assumptions

## Risk Schema

- `RiskBudget`: position weight, gross exposure, turnover, drawdown, participation, confidence, latency, slippage limits
- `RiskCheck`: named constraint check with pass/fail, severity, message
- `RiskViolation`: phase, constraint, observed value, limit, severity, symbol
- `RiskReport`: phase-level audit object for pre-trade, in-trade, and post-trade stages
- drawdown kill-switch metadata: rolling drawdown, lookback window, de-risk
  weight, and trigger status
- `RiskAttribution`: post-trade PnL/cost/exposure attribution

## Memory Schema

- append-only events
- trade journal entries
- thesis tracking
- failure cases
- digest for reproducibility checks
- memory-aware strategy diagnostics: configured `memory_decay_rate`, weighted
  `memory_pollution_ratio`, base and memory-adjusted target weights, and
  `memory_driven_leverage_amplification`

## Tool Schema

- `ToolCallRecord`: tool name, inputs, outputs, timestamp, status
- examples: analyst stack, feature store, risk calculator, optimizer, backtester, retrieval

## Trajectory Schema

Each step records:

- `reproducibility_state`
- `agent_trace`
- observation
- signals
- decisions
- approved decisions
- pre-trade risk report
- orders
- fills
- execution report
- in-trade risk report
- post-trade risk attribution report
- risk violations
- portfolio
- memory events

## Evaluation Schema

- performance: return, volatility, Sharpe, drawdown
- behavior: orders, fills, hold ratio, turnover events, memory-driven leverage
  amplification, and memory pollution ratios
- execution realism: fill rate, partial fill rate, rejected/pending orders, commission, slippage, latency
- risk awareness: lifecycle coverage, blocked/clipped decisions, violations, warning/error checks
- reproducibility: prompt/model/data/memory/tool/risk/portfolio/execution state coverage
- reasoning consistency: action side and target weight agreement

## Redacted Leaderboard Submission Schema

External TradeArena rows can be shared without exposing raw provider prompts or
responses. The minimal public submission contract lives at
[`../schemas/benchmark_submission.schema.json`](../schemas/benchmark_submission.schema.json).
It records the scenario, redacted agent metadata, data source, execution
configuration, risk configuration, metrics, trajectory manifest, redaction
policy, and reproducibility hash.

Validate an example submission with:

```bash
tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json
```

## Demo Artifact Contract

The demo artifact contract lives at
[`../schemas/demo_artifact_contract.schema.json`](../schemas/demo_artifact_contract.schema.json)
and is instantiated by [`demo_artifacts.yaml`](demo_artifacts.yaml). It lists
the commands and output files that should remain stable for quickstart,
execution-realism, audit-report, benchmark-card, and community-registry demos.

Validate it after building the showcase:

```bash
python scripts/validate_demo_artifacts.py
```

When a demo summary exposes `verification_commands`, the validator also checks
that the summary commands exactly match the manifest's `required_validators` so
artifact-local replay instructions cannot drift from the release contract.

## Broker Handoff, Approval, And Response Artifact Schemas

Broker handoff request artifacts can be validated against
[`../schemas/broker_handoff_artifact.schema.json`](../schemas/broker_handoff_artifact.schema.json).
The schema fixes the public `tradearena_broker_handoff_artifact_v0.1`
contract for adapter identity, adapter mode, account mode, safety flags, and
broker-review order rows. Top-level adapter names must be non-empty strings
without whitespace so handoff, response, capability, and runbook artifacts can
be compared without hidden padding.

Validate a broker handoff artifact with:

```bash
tradearena validate-broker-handoff outputs/examples/alpaca_paper_export/alpaca_paper_orders.json
```

Broker handoff order symbols must be non-empty strings without whitespace, so
reviewed broker-facing rows and later approval scopes cannot diverge through
hidden padding.

Broker adapter capability manifests can be validated against
[`../schemas/broker_adapter_capability.schema.json`](../schemas/broker_adapter_capability.schema.json).
The schema fixes the public `trellm_broker_adapter_capability_v0.1`
contract for adapter identity, adapter mode, account mode, credential policy,
network access, default-live prohibition, and live-safety controls. The
`adapter_id` must be a non-empty string without whitespace because
live-readiness compares it against handoff and response `adapter` values. A
future paper or live adapter should publish this manifest before its handoff,
approval, response, or runbook artifacts are reviewed. Credential environment
variable names in `credential_policy.env_vars` must also be non-empty strings
without whitespace. Schema and runtime validation require
live-capable adapters to use `adapter_kind: live_capable`, declare
`network_access` as `required_for_live`, list `live_human_approved` and `live`
mode support, require credentials with named environment variables, and enable
every live safety control before live submission can be advertised.
Runtime fallback validation also rejects unsupported `supported_modes`,
`account_modes`, `supported_order_types`, and `supported_time_in_force` entries
so lightweight installs keep the same live-readiness scope boundaries as the
JSON Schema path.

Validate the offline demo capability manifest with:

```bash
tradearena validate-broker-capability outputs/examples/broker_capability_manifest/capability_manifest.json
```

Compute the canonical hash to place in a reviewed approval artifact with:

```bash
tradearena hash-broker-handoff path/to/broker_handoff.json
```

Broker approval artifacts can be validated against
[`../schemas/broker_approval_artifact.schema.json`](../schemas/broker_approval_artifact.schema.json).
The schema fixes the public `tradearena_broker_approval_artifact_v0.1`
contract for redacted operator approval, account mode, max notional, max
quantity, allowed symbols, allowed order types, required expiry, and required
request-artifact hash binding. Approval IDs and redacted operator IDs must be
non-empty strings without whitespace. Approval timestamps must be ISO timestamps
with timezone information; runtime validation also requires `expires_at` to be
later than `approved_at`. Allowed symbols must be non-empty strings without
whitespace so hidden padding cannot change approval-scope matching.
Runtime code can consume this contract with
`broker_safety_from_approval_artifact(...)` to build a live human-approved
`BrokerSafetyConfig`; pass `now=` to reject expired approval artifacts during
validation or conversion. The `now` timestamp must include timezone information
so expiry checks do not depend on local-clock assumptions. Use
`broker_handoff_artifact_hash(...)` to populate
the required `request_artifact_hash` with a `sha256:` plus 64 lowercase hex value, and pass
`request_artifact=` to
`broker_safety_from_approval_artifact(...)` so live safety creation is bound to
the exact reviewed broker handoff artifact.

Validate a broker approval artifact with:

```bash
tradearena validate-broker-approval path/to/broker_approval.json --now 2026-05-31T12:30:00Z
```

Validate that the approval authorizes the exact reviewed handoff request with:

```bash
tradearena validate-broker-approval-binding path/to/broker_approval.json path/to/broker_handoff.json --now 2026-05-31T12:30:00Z
```

This binding check also verifies that request orders stay within the approval's
symbol, order-type, quantity, and notional limits. Each bound request order
must include a positive `limit_price` so notional can be checked before live
safety creation.

Broker response artifacts can be validated against
[`../schemas/broker_response_artifact.schema.json`](../schemas/broker_response_artifact.schema.json).
The schema fixes the public `tradearena_broker_response_artifact_v0.1`
contract for adapter identity, adapter mode, account mode, optional handoff
`request_artifact_hash`, normalized broker statuses, reconciliation counts, and
redacted response rows. Top-level adapter names must be non-empty strings
without whitespace.

Validate a broker response artifact with:

```bash
tradearena validate-broker-response outputs/examples/broker_response_reconciliation/broker_response_artifact.json
```

## Operator Runbook Artifact Schema

Operator runbook artifacts can be validated against
[`../schemas/operator_runbook_artifact.schema.json`](../schemas/operator_runbook_artifact.schema.json).
The schema fixes the public `trellm_operator_runbook_v0.1` contract for
human-gated live-readiness evidence: default mode, live-submission boundary,
manual approval, approval expiry, kill switch, reconciliation, rollback, and
artifact-retention checks. It also requires a structured
`incident_response_drill` naming the kill-switch action, rollback owner,
affected account mode and symbols, retention path, and re-enable approval gate.
Rollback owners and checklist owners must be non-empty strings without
whitespace so incident ownership and per-control responsibility cannot drift
through hidden padding. Affected symbols must also be non-empty strings
without whitespace because live-readiness compares them against handoff order
symbols.
The retention path must stay under `outputs/examples/operator_runbook/` without
parent traversal, drive qualifiers, backslashes, whitespace, or absolute paths.
The checklist must include each critical control id exactly once: `mode-boundary`,
`approval-expiry`, `kill-switch`, `reconciliation`, `rollback`,
`artifact-retention`, and `incident-owner`.
Runtime validation also requires exactly one supported, runnable
`validate-live-readiness` command with no shell chaining (`;`, `&`, `&&`, `||`,
or `|`), a portable relative preflight bundle path, `--now`, and an ISO timezone
timestamp, with no absolute paths, drive-qualified paths, parent traversal,
backslashes, extra arguments, or unsupported extra
`validate-live-readiness` mentions. When the runbook is linked from a
live-readiness preflight bundle, the command path must name the current
preflight bundle being validated and the command timestamp must match that
bundle's `approval_checked_at`, so the runbook names one final packet-level
gate instead of a placeholder note or competing commands.

Validate the offline demo runbook with:

```bash
tradearena validate-operator-runbook outputs/examples/operator_runbook/summary.json
```

## Live-Readiness Preflight Bundle Schema

Live-readiness preflight bundles can be validated against
[`../schemas/live_readiness_preflight.schema.json`](../schemas/live_readiness_preflight.schema.json).
The schema fixes the public `trellm_live_readiness_preflight_v0.1` contract for
linking a broker capability manifest, handoff artifact, approval artifact,
response artifact, and operator runbook into one reviewable safety packet.
The schema encodes portable relative component paths: no absolute paths, drive
qualifiers, parent traversal (`..`), backslashes, or whitespace. Runtime
validation then calls the component validators and checks approval binding,
capability adapter-id and mode consistency, runbook/capability default-mode
consistency, runbook safety controls including reconciliation checklist
coverage, and handoff/response adapter, adapter-mode, account-mode, and
live-submission consistency. Handoff orders must also use order types and
time-in-force values declared in the capability manifest. The linked runbook's
incident drill must cover the current handoff account mode and order symbols.
`approval_checked_at` must match the timestamp passed to
`validate-live-readiness --now` so approval-expiry checks and the recorded
review time cannot drift. Response artifacts in a preflight packet must name
the reviewed handoff `request_artifact_hash`, and response rows must use
`client_order_id` values from that handoff artifact. Every handoff order must
also have a matching response row before the packet is considered live-ready,
and the response artifact's reconciliation `missing_response_count` and
`unmatched_response_count` must match the handoff/response linkage result.

Validate the offline demo preflight bundle with:

```bash
tradearena validate-live-readiness outputs/examples/live_readiness_preflight/preflight_bundle.json --now 2026-05-31T12:30:00Z
```

## Reproduction Report Schema

The external reproduction report schema lives at
[`../schemas/reproduction_report.schema.json`](../schemas/reproduction_report.schema.json).
It records commit/tag, Python environment, commands, output hashes, trajectory
hash, and whether live APIs, downloaded market data, or private fills were used.
Generate a no-key report with:

```bash
python scripts/run_external_reproduction_pack.py
```
