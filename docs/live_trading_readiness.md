# Live Trading Readiness

TreLLM should grow beyond offline and paper-only research paths, but it should
not jump straight from TradeArena leaderboard rows to unattended live orders.
TradeArena remains the public leaderboard module for comparable rows. The
intended direction for TreLLM is **live-ready, human-gated trading
infrastructure**: every order candidate is observable, risk-checked,
calibrated, exported, approved, reconciled, and auditable before any
broker-facing adapter can submit it.

The default repository path remains safe: first-run commands do not place live
orders or require broker credentials. The long-term value is that the same
audit stack can become the control plane around real trading systems.

## Maturity Ladder

| Stage | Name | What TreLLM can do | Required evidence before moving on |
| --- | --- | --- | --- |
| 0 | Offline benchmark | Run deterministic agents, risk gates, and stress execution without network calls. | Reproducible trajectory, schema validation, release-readiness checks. |
| 1 | Calibrated paper research | Fit or replay execution assumptions from quote, order-book, or fill evidence. | Calibration report with source, venue, date range, residuals, and hashes. |
| 2 | Broker-review export | Convert approved paper orders into broker-compatible review files. | Capability manifest, `submit_live=false`, human approval fields, redacted artifacts, no broker API call. |
| 3 | Paper trading sandbox | Submit to a broker sandbox or paper account only. | Capability manifest, sandbox credentials, account isolation, order limits, dry-run test, audit manifest. |
| 4 | Human-approved live adapter | Submit live orders only after explicit operator approval. | Broker adapter contract, manual approval record, kill switch, reconciliation, incident runbook. |
| 5 | Supervised automation | Allow tightly scoped automation after repeated paper/live shadow validation. | External review, capital limits, monitoring, rollback, compliance and jurisdiction review. |

Stages 4 and 5 are not part of the public TradeArena leaderboard claim. They
are future TreLLM integration tracks for users who accept the regulatory,
operational, and financial risk of real trading.

## Live-Ready Architecture

The system should keep these boundaries separate:

| Layer | Responsibility | Current surface |
| --- | --- | --- |
| Decision | Agents, strategies, and planners propose intent. | `tradearena.agents`, `tradearena.planning` |
| Risk gate | Risk managers clip, block, or annotate intent. | `MaxPositionRiskManager`, market-rule helpers |
| Execution model | Simulators, quote replay, fill replay, and calibration estimate feasibility. | `tradearena.execution` |
| Broker handoff | Broker adapters export or submit only approved orders. | `BrokerAdapter`, `DryRunBrokerAdapter`, `AlpacaPaperExportAdapter` |
| Reconciliation | Fills, rejects, partial fills, and broker state are compared against intent. | future broker adapter reports |
| Audit trail | Trajectory, risk report, order review, broker response, and hashes stay linked. | trajectory records, manifests, registry |

A broker-facing adapter should never bypass the decision/risk/execution trail.
It consumes approved orders and produces a broker handoff artifact or a broker
response artifact.

## Stage Gate Checklist

Before a broker-facing contribution is accepted, it should prove:

- default mode is `offline_export`, `dry_run`, or `paper_sandbox`;
- a schema-valid broker adapter capability manifest declares supported modes,
  account modes, network access, credential policy, and safety controls;
- a live-readiness preflight bundle validates the capability manifest, handoff,
  approval binding, response artifact, and operator runbook together, including
  portable relative component references without drive qualifiers, backslashes,
  whitespace, or parent traversal, matching capability/runbook default modes,
  matching capability/runbook safety-control declarations for manual approval,
  approval expiry, kill switch, and artifact retention, handoff/response
  account modes, live-submission boundaries, and reviewed handoff hash plus
  `client_order_id` values, with one response row for every reviewed handoff
  order and matching response reconciliation missing/unmatched counts;
- the operator runbook names exactly one supported, runnable final
  `validate-live-readiness` command with no shell chaining (`;`, `&`, `&&`,
  `||`, or `|`), exactly the preflight bundle path, `--now`, and an ISO
  timezone timestamp, with no extra arguments, unsupported duplicate mentions,
  or competing final gates before broker-facing review;
- live submission is impossible without an explicit mode switch;
- credentials are read from environment variables or an OS secret manager;
- no credentials, account IDs, private holdings, raw fills, or raw provider
  responses are committed;
- every order carries a risk report reference, approval status, and client
  order ID;
- live approvals are recorded as schema-valid, redacted broker approval
  artifacts before any live handoff;
- every live approval binds to the reviewed broker handoff artifact via
  `request_artifact_hash`, and the binding is checked before live-mode safety is
  created;
- max notional, max quantity, allowed symbols, and allowed order types are
  enforced before broker handoff;
- cancellation, partial-fill, rejection, and reconciliation states are
  represented in artifacts;
- a kill-switch or disable flag can block all broker submission paths;
- tests prove that the default path cannot submit live orders;
- docs name the account type: offline, paper sandbox, or live human-approved.

## Recommended Contribution Sequence

1. Harden export-only broker capability, handoff, preflight, and review manifests.
2. Add one broker-specific sandbox adapter behind an optional dependency.
3. Add reconciliation reports that compare submitted orders, broker acks, fills,
   cancels, rejects, and portfolio state.
4. Add human approval records and operator runbooks.
5. Only then discuss constrained live submission, and keep it out of first-run
   examples.

The current engineering step is to keep hardening the generic broker adapter
contract in [`broker_adapter_contract.md`](broker_adapter_contract.md) and the
capability manifest in
[`schemas/broker_adapter_capability.schema.json`](../schemas/broker_adapter_capability.schema.json)
before adding any broker-specific sandbox dependency.

## External Contribution Tracks

The safest way to move TreLLM toward real trading is to land small,
evidence-backed PRs that make one stage more auditable. A contributor does not
need to build a full broker integration to help.

| Track | Good first PR | Evidence that makes it reviewable |
| --- | --- | --- |
| Broker capability manifest | Add or tighten one supported-mode, credential, network-access, or safety-control field. | Schema-valid capability manifest, command transcript, no default live path. |
| Broker review export | Add or tighten one handoff field, validator error, or example summary. | Schema-valid handoff artifact, command transcript, no credential or live API path. |
| Approval binding | Add one edge-case test for stale approvals, mismatched request hashes, symbols, quantities, or order types. | Failing-then-passing test and a redacted approval artifact tied to a reviewed request hash. |
| Paper-sandbox adapter | Add a broker-specific paper adapter behind an optional dependency. | Paper-only account mode, no default network call, response artifact, reconciliation summary, and mocked CI tests. |
| Reconciliation | Improve status mapping for rejects, cancels, partial fills, duplicate IDs, or unknown broker states. | Response artifact that validates, recomputed reconciliation counts, and redacted failure reasons. |
| Operator runbook | Document a human approval or incident-response step for a live-capable path. | Checklist with kill switch, rollback, account mode, approval expiry, artifact retention rules, and an incident owner. |
| Live-readiness preflight | Add one cross-artifact consistency check across capability, handoff, approval, response, or runbook artifacts. | `tradearena validate-live-readiness ...` passes and fails on a targeted broken bundle. |

Paper-sandbox adapters must stay behind optional dependencies and must publish
response artifacts with account mode, status, and reconciliation counts. Live
submission remains out of first-run examples and requires the Stage 4 evidence
in the maturity ladder.
