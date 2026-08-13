# Broker Adapter Contract

This contract defines the minimum bar for any TreLLM adapter that touches a
broker, exchange, paper account, or order-management workflow. It applies to
offline exports, paper trading sandboxes, and future human-approved live
adapters.

The contract is intentionally stricter than the current public examples. A
small adapter that cannot satisfy these rules should stay as an offline export.

## Modes

Every broker adapter must declare exactly one mode at runtime:

| Mode | Broker API call allowed? | Live order allowed? | Typical use |
| --- | --- | --- | --- |
| `offline_export` | No | No | Write CSV/JSON orders for review. |
| `dry_run` | No | No | Validate request shape without network calls. |
| `paper_sandbox` | Yes, paper account only | No | Submit to a broker simulator or paper account. |
| `live_human_approved` | Yes | Only after explicit approval | Submit constrained live orders after operator review. |

The default mode must be `offline_export` or `dry_run`. `live_human_approved`
must never be the default.

Before a broker-facing adapter is reviewed, it should publish a capability
manifest that names its supported modes, account modes, network access,
credential policy, and live-safety controls. The manifest `adapter_id` must be
a non-empty string without whitespace because live-readiness compares it against
handoff and response `adapter` values. Credential environment variable names in
`credential_policy.env_vars` must also be non-empty strings without whitespace.
Validate that manifest with:

```bash
tradearena validate-broker-capability outputs/examples/broker_capability_manifest/capability_manifest.json
```

Once capability, handoff, approval, response, and runbook artifacts exist,
validate the cross-artifact packet with:

```bash
tradearena validate-live-readiness outputs/examples/live_readiness_preflight/preflight_bundle.json --now 2026-05-31T12:30:00Z
```

The preflight validator rejects safety packets whose handoff and response
artifacts disagree about `adapter`, `adapter_mode`, `account_mode`, or
`live_submission`, whose capability manifest does not satisfy the operator
runbook's required manual-approval, approval-expiry, kill-switch, and
artifact-retention controls, whose response artifact does not name the reviewed
handoff `request_artifact_hash`, or whose response rows reference
`client_order_id` values that are absent from the reviewed handoff artifact.
Top-level `adapter` values in handoff and response artifacts must be non-empty
strings without whitespace so cross-artifact equality checks are unambiguous.
Publish separate packets rather than mixing paper, live, non-submission, or
unrelated response evidence.

The current code-level primitives live in `tradearena.tools.broker_export`:

- `validate_broker_adapter_capability`;
- `validate_broker_adapter_capability_file`;
- `BrokerAdapter`, the minimal interface future broker adapters should satisfy;
- `BrokerAdapterMode`;
- `BrokerSafetyConfig`;
- `BrokerApproval`;
- `BrokerAdapterContractError`;
- `BrokerOrderStatus`;
- `BrokerResponse`;
- `BrokerReconciliationSummary`;
- `build_broker_approval_artifact`;
- `broker_approval_from_artifact`;
- `broker_handoff_artifact_hash`;
- `broker_safety_from_approval_artifact`;
- `reconcile_broker_responses`;
- `validate_broker_approval_artifact`;
- `validate_broker_approval_artifact_file`;
- `validate_broker_approval_request_binding`;
- `validate_broker_handoff_artifact`;
- `validate_broker_handoff_artifact_file`;
- `validate_broker_response_artifact`;
- `validate_broker_response_artifact_file`;
- `write_broker_response_artifact`;
- `DryRunBrokerAdapter`, the no-network reference adapter for request-shape
  validation;
- `PaperSandboxAdapterSkeleton`, a no-default-network paper adapter scaffold
  whose broker-specific client must be injected from an optional dependency;
- `AlpacaPaperExportAdapter`, the export-only reference implementation.

## Required Order Fields

Each broker handoff row should include:

- `client_order_id`;
- `symbol`;
- `side`;
- `order_type`;
- `quantity`;
- `time_in_force`;
- `limit_price` when relevant;
- `risk_report_id` or risk report hash;
- `trajectory_id` or run hash;
- `approval_status`;
- `approved_by` when live submission is allowed;
- `approved_at` when live submission is allowed;
- `submit_live`;
- `reason`;
- `max_notional`;
- `account_mode`.

Current export-only examples may use a subset, but new broker-facing adapters
should move toward this complete shape.
Public handoff artifacts should validate against
[`../schemas/broker_handoff_artifact.schema.json`](../schemas/broker_handoff_artifact.schema.json).
Handoff `client_order_id` values must be unique non-empty strings without
whitespace because approval and response artifacts use them as audit keys.
Use `tradearena validate-broker-handoff <artifact.json>` before sharing a
broker-review or paper-sandbox request artifact.

## Safety Invariants

Adapter implementations must satisfy these invariants:

- default construction cannot submit a live order;
- `submit_live=true` is rejected unless mode is `live_human_approved`;
- `live_human_approved` handoff artifacts must use `account_mode: "live"`;
- live mode requires an explicit approval record;
- live mode requires max notional and max quantity limits;
- any configured max-notional or max-quantity limit must be positive and
  finite;
- live mode must have a reference price whenever max-notional checks are
  enforced;
- live orders must satisfy both the adapter max-notional limit and the human
  approval max-notional limit;
- live-mode handoff writers must validate live limits, account mode, and human
  approval before writing an artifact, even when the filtered order list is
  empty;
- `live_human_approved` handoff artifacts must not set `kill_switch: true`; a
  tripped kill-switch stops the live path before any live-submission artifact is
  written;
- allowed symbols and allowed order types are enforced before broker handoff;
- broker credentials are read from environment variables or an OS secret
  manager, never from committed files or command-line arguments;
- logs and exceptions redact credentials, account numbers, and private holdings;
- all generated artifacts state whether they are offline, paper, or live;
- tests prove that offline and dry-run modes perform no broker API calls.

## Broker Response Artifact

Any adapter that calls a broker API should write a response artifact with:

- request client order ID;
- broker order ID when available;
- submitted quantity and accepted quantity;
- status: accepted, rejected, partially filled, filled, canceled, expired, or
  unknown;
- rejection reason or error class with sensitive fields redacted;
- submitted timestamp and broker timestamp;
- fill price, fill quantity, fees, and liquidity flags when available;
- account mode: paper or live;
- reconciliation status against the original TreLLM order.

This artifact is part of the audit trail, not a throwaway log.
`write_broker_response_artifact(...)` writes the repository's first version of
this artifact. It records `tradearena_broker_response_artifact_v0.1`, the
adapter mode, account mode, optional handoff `request_artifact_hash`, response
rows, and a reconciliation summary with missing and unmatched response counts.
Response validation also rejects impossible quantity relationships, including
`accepted_quantity` or `fill_quantity` values greater than `submitted_quantity`,
or `fill_quantity` values greater than `accepted_quantity`.
All numeric response fields (`submitted_quantity`, `accepted_quantity`,
`fill_quantity`, `fill_price`, and `fees`) must be non-negative finite numbers
or `null`; use `null` or zero for fields that do not apply to a terminal
non-execution status.
Every response row must report a positive `submitted_quantity`.
Every response row must include `submitted_at` and `broker_timestamp` as ISO
timestamps with explicit timezone offsets so reconciliation can sort events and
measure broker latency without locale-dependent parsing. `broker_timestamp`
must be at or after `submitted_at`.
Every response row's `account_mode` must match the artifact-level
`account_mode`; publish separate artifacts for paper and live accounts.
Each response row must use a unique non-empty `client_order_id` without
whitespace; duplicate broker responses for the same client order must be
consolidated before publishing the artifact.
Accepted, partially filled, filled, canceled, and expired rows must include a
non-empty `broker_order_id`; rejected rows may omit it when the broker never
created an order. Non-empty `broker_order_id` values must not contain
whitespace and must also be unique within the artifact.
Rejected response rows must include a non-empty, redacted `rejection_reason`
so reconciliation artifacts explain why an order did not proceed. `unknown`
rows must also include a non-empty, redacted `rejection_reason` that explains
which broker status, parser failure, or adapter error prevented classification.
`rejected` rows must not report positive `accepted_quantity`, `fill_quantity`,
`fill_price`, or `fees`.
`unknown` rows must not report positive `accepted_quantity`, `fill_quantity`,
`fill_price`, or `fees`; classify the order before publishing execution or cost
fields.
`accepted`, `partially_filled`, and `filled` rows must report a positive
`accepted_quantity`.
`accepted` rows must not report `fill_quantity` or `fill_price`; use
`partially_filled` or `filled` once execution occurs.
`partially_filled` rows must report a positive `fill_quantity` that remains
below `submitted_quantity`; a full fill should use the `filled` status instead.
`filled` rows must also report a positive `fill_quantity` equal to
`submitted_quantity`. Any `partially_filled` or `filled` row must also report a
positive `fill_price` so audit tools can attribute execution costs.
`canceled` and `expired` rows must not report positive `fill_quantity` or
`fill_price`; use `partially_filled` if a cancel/expiry follows a broker-visible
partial execution that the artifact needs to represent.
The reconciliation summary is not free-form. Validators recompute
`response_count`, each status count, `fill_ratio_mean`, and the
`unmatched_response_count <= response_count` invariant from the response rows,
then reject artifacts whose summary does not match those rows.
For `live_human_approved` response artifacts, `account_mode` must be `live`;
response rows must also use `client_order_id` values from the reviewed live
request set. Paper or sandbox broker responses should use `paper_sandbox` or
another non-live adapter mode.
Public response artifacts should validate against
[`../schemas/broker_response_artifact.schema.json`](../schemas/broker_response_artifact.schema.json).
Use `tradearena validate-broker-response <artifact.json>` before submitting a
broker-facing PR or paper-sandbox run report.

## Human Approval Gate

`live_human_approved` mode requires a durable approval record:
`approval_id` must be a non-empty string without whitespace so reviewers and
adapters can use it as a stable audit key. `approved_by` must also be a
redacted operator ID without whitespace, not an email address.

```json
{
  "schema": "tradearena_broker_approval_artifact_v0.1",
  "approval_id": "approval-20260531-001",
  "approval_status": "approved",
  "approved_by": "operator-id",
  "approved_at": "2026-05-31T12:00:00Z",
  "expires_at": "2026-05-31T13:00:00Z",
  "account_mode": "live",
  "max_notional": 1000.0,
  "max_quantity": 10.0,
  "allowed_symbols": ["AAPL", "MSFT"],
  "allowed_order_types": ["market", "limit"],
  "approval_reason": "paper/live shadow checks passed for this rebalance",
  "request_artifact_hash": "sha256:..."
}
```

The adapter should reject stale, missing, or over-broad approvals. Approval
artifacts are only valid for `account_mode: "live"`; paper and sandbox reviews
should use handoff or response artifacts instead. Approval records should use
redacted operator IDs in public artifacts, and both `approved_at`
and `expires_at` must be ISO timestamps with timezone information, such as
`2026-05-31T12:00:00Z`. `expires_at` is required and must be later than
`approved_at`, so every approval is time-boxed. Approval artifacts can be checked with
`tradearena validate-broker-approval <artifact.json> --now <ISO_TIMESTAMP>`.
The approval should also bind to the exact request artifact that was reviewed:
compute `broker_handoff_artifact_hash(request_artifact)` and store it in
`request_artifact_hash` as `sha256:` followed by 64 lowercase hex characters,
then run
`validate_broker_approval_request_binding(approval, request_artifact)` before
building any live-mode safety config. This prevents an operator approval for one
handoff file from being reused against a different order request. The reviewed
request artifact must be a pre-live broker-review handoff with
`live_submission=false` and `manual_approval_required=true`; approval binding
rejects handoff artifacts that are already in `live_human_approved` mode.
Reviewers can compute the reviewed request hash with
`tradearena hash-broker-handoff <request.json>` or
`python scripts/hash_broker_handoff_artifact.py <request.json>`; both commands
validate the handoff artifact before printing the hash.
Command-line reviewers can check the same invariant with
`tradearena validate-broker-approval-binding <approval.json> <request.json> --now <ISO_TIMESTAMP>` or
`python scripts/validate_broker_approval_binding.py <approval.json> <request.json> --now <ISO_TIMESTAMP>`.
The binding validator also checks that every request order stays inside the
approval's allowed symbols, allowed order types, max quantity, and max notional
limits. The reviewed request must contain at least one order; empty handoff
artifacts cannot be used to mint a broad live-safety gate. Request orders must
include a positive `limit_price` so approval-time notional can be calculated;
unpriced market requests should stay out of live approval binding until a
reviewed reference-price field is added.
Adapter implementations can turn a validated approval artifact into the
runtime safety gate with `broker_safety_from_approval_artifact(...)`; the
result is a `BrokerSafetyConfig` in `live_human_approved` mode with the same
symbol, order-type, quantity, and notional limits as the approval.
`request_artifact=` is required when calling
`broker_safety_from_approval_artifact(...)`; the approval/request binding is
enforced inside the live-safety creation path, and the resulting safety gate
only accepts orders that match the reviewed handoff orders. Batch conversion
also enforces the reviewed order counts, so one approved handoff row cannot be
reused multiple times in the same live write. Broker execution instructions
captured in the handoff row, including `time_in_force`, must also match the
reviewed request before live conversion is allowed.
Pass `now=` when validating or consuming approval artifacts so stale approvals
are rejected before any live-mode safety config is created.

## Testing Requirements

At minimum, a broker adapter PR should include tests that prove:

- default mode writes an offline artifact and makes no network call;
- dry-run mode validates request shape and writes a broker handoff artifact
  without broker credentials or API calls;
- live submission is rejected without approval;
- order-size and symbol allow-list checks run before broker handoff;
- credentials are not printed in errors;
- response artifacts can represent rejected and partially filled orders;
- a kill-switch setting blocks all broker submission paths.

The current Alpaca example is intentionally below live-adapter scope: it writes
broker-review JSON/CSV files by default, declares `adapter_mode=offline_export`,
and sets `submit_live=false`.
