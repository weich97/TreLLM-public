# TreLLM Hands-On Examples

These examples are designed for the first hour after cloning TreLLM. They avoid
live LLM calls by default and write local artifacts under `outputs/examples/`.
The default examples are deterministic smoke tests and visual demos, not live
model benchmarks; live or cache-backed LLM runs are opt-in.

## Recommended First Run

```bash
python scripts/run_showcase.py
```

Open:

```text
outputs/examples/showcase.html
```

The showcase links to a practical tour of auditable trajectories, execution
realism, animated visual diagnostics, A-share market-rule interventions,
portfolio baselines, paper broker exports, crypto microstructure stress,
futures roll risk, redacted LLM cache manifests, and a custom plugin extension
plus a contributor extension walkthrough and retail planning sandbox.

## 1. Core Benchmark

```bash
python examples/quickstart_core_benchmark.py
```

Shows how two leaderboard cases share the same market, risk, execution, and
evaluation stack.

Output:

- `outputs/examples/quickstart_core_metrics.json`

## 2. Animated Visual Tour

```bash
python examples/visual_tour_demo.py
```

Regenerates the README-style audit lifecycle, execution realism, and
diagnostics animations as local hands-on artifacts.

Output:

- `outputs/examples/visual_tour_index.html`
- `outputs/examples/visual_tour_summary.json`
- `outputs/examples/visual_tour_audit_lifecycle.gif`
- `outputs/examples/visual_tour_execution_realism.gif`
- `outputs/examples/visual_tour_diagnostics_loop.gif`

## 3. Audit Trajectory Walkthrough

```bash
python examples/audit_trajectory_walkthrough.py
python scripts/render_audit_report.py
```

Shows one complete observe-plan-risk-act-reflect trajectory, including risk
clipping, pending orders, rejected orders, fills, memory events, and
reproducibility metadata.

Output:

- `outputs/examples/audit_walkthrough_trajectory.json`
- `outputs/examples/audit_report.html`

## 4. Optional Data Sidecars

```bash
python examples/sidecar_data_demo.py
```

Shows how `news.csv`, `macro.csv`, `filings.csv`, and
`alternative_data.csv` can enter observations through the CSV provider without
changing the runner.

Output:

- `outputs/examples/sidecar_data/`

## 5. AkShare CSV Reuse

```bash
python examples/akshare_csv_reuse_demo.py
```

Shows the recommended A-share integration boundary: download data once,
normalize to OHLCV CSV, and reuse the standard `CsvMarketDataProvider`.

Output:

- `outputs/examples/akshare_csv_reuse_summary.json`
- `outputs/examples/akshare_csv_reuse.svg`

Live download command:

```bash
python -m pip install -e ".[ashare]"
python scripts/download_akshare_ashare_daily.py \
  --symbols 600519.SS,300750.SZ \
  --start 2021-01-01 \
  --end 2026-05-14 \
  --output-dir data/real/akshare_ashare_daily
```

## 6. A-Share Market Rules

```bash
python examples/ashare_market_rules_demo.py
```

Shows how T+1, 10% price limits, and 100-share board lots become auditable
risk-gate outcomes.

Output:

- `outputs/examples/ashare_market_rules_summary.json`
- `outputs/examples/ashare_market_rules_orders.csv`
- `outputs/examples/ashare_market_rules.svg`

Hong Kong board-lot conversion uses the same market-rule boundary:

```bash
python examples/hk_market_rules_demo.py
```

It converts target weights into raw share quantities, clips them to tradable
board lots, and records regular-session plus stamp-duty assumptions.

Output:

- `outputs/examples/hk_market_rules_summary.json`
- `outputs/examples/hk_market_rules_orders.csv`
- `outputs/examples/hk_market_rules.svg`

## 7. Execution Realism Sweep

```bash
python examples/execution_realism_sweep_demo.py
```

Shows how fees, quoted spread, slippage, latency, liquidity limits, and
rejections change agent behavior. The `high_spread` preset isolates a wide
bid-ask spread while keeping fill eligibility close to the default case, so the
artifact makes crossing cost visible rather than hiding it inside generic
slippage.

Output:

- `outputs/examples/execution_realism_sweep_summary.json`
- `outputs/examples/execution_realism_sweep.csv`
- `outputs/examples/execution_realism_sweep.svg`

## 8. Portfolio / Markowitz Baselines

```bash
python examples/portfolio_markowitz_demo.py
```

Shows passive, signal-weighted, and MVO-style allocation through the same
strategy and evaluator interfaces.

Output:

- `outputs/examples/portfolio_markowitz_summary.json`
- `outputs/examples/portfolio_markowitz.csv`
- `outputs/examples/portfolio_markowitz.svg`

## 9. Representation Diagnostics

```bash
python examples/representation_signature_demo.py
```

Shows how tracked diagnostic tables can be turned into an offline visual
artifact.

Output:

- `outputs/examples/representation_signature_summary.json`
- `outputs/examples/representation_signature.svg`

## 10. Custom Plugin Extension

```bash
python examples/custom_plugin_demo.py
```

Shows a local analyst plugin running through the existing strategy, risk,
execution, memory, and evaluator stack.

Output:

- `outputs/examples/custom_plugin_summary.json`
- `outputs/examples/custom_plugin.svg`

## 11. Contributor Extension Walkthrough

```bash
python examples/extension_walkthrough_demo.py
```

Shows how to add a custom analyst, risk manager, and evaluator without editing
the core runner.

Output:

- `outputs/examples/extension_walkthrough_summary.json`
- `outputs/examples/extension_walkthrough.svg`
- `outputs/examples/extension_walkthrough_notes.md`

## 12. Retail Planning Sandbox

```bash
python examples/retail_planner_demo.py
```

Shows how investor profiles and goals become suitability-audited allocations,
paper rebalance instructions, and futures margin estimates.

Output:

- `outputs/examples/retail_planning_report.html`
- `outputs/examples/retail_planning_summary.json`
- `outputs/examples/retail_planning_audit.json`
- `outputs/examples/retail_planning_allocation.svg`

## 13. Redacted LLM Cache Manifest

```bash
python examples/llm_cache_replay_demo.py
```

Shows portable model-experiment metadata without shipping raw prompt/response
text. This is not a live LLM run and does not replay raw model decisions; it is
a public manifest of model coverage, parse rates, and cache portability.

Output:

- `outputs/examples/llm_cache_replay_summary.json`

## 14. Live LLM Smoke Test

Use the CLI when you want the first run to actually call an LLM analyst:

```powershell
$env:POE_API_KEY="..."
tradearena --benchmark llm-smoke `
  --analysts poe-llm `
  --llm-model gpt-5.5 `
  --periods 3 `
  --symbols SYN,ALT `
  --llm-cache outputs/examples/poe_llm_smoke_cache.jsonl
```

The command runs one LLM-backed analyst case through the normal
observe-plan-risk-act-reflect loop. If a matching cache row exists, the analyst
replays it; otherwise it calls the configured provider and appends a local cache
entry ignored by Git.

## 15. Broker-Review Alpaca Export

```bash
python examples/alpaca_paper_export_demo.py
```

Converts approved TreLLM orders into neutral JSON/CSV rows for Alpaca-style
broker review. It marks the adapter mode as `offline_export` and does not
submit orders.

Output:

- `outputs/examples/alpaca_paper_export/summary.json`
- `outputs/examples/alpaca_paper_export/alpaca_paper_orders.json`
- `outputs/examples/alpaca_paper_export/alpaca_paper_orders.csv`

## 16. Dry-Run Broker Adapter

```bash
python examples/dry_run_broker_adapter_demo.py
```

Validates broker request shape through the generic dry-run adapter. It writes
reviewable JSON/CSV handoff rows, runs the broker handoff validator, and makes
no broker API calls.

Output:

- `outputs/examples/dry_run_broker_adapter/summary.json`
- `outputs/examples/dry_run_broker_adapter/dry_run_orders.json`
- `outputs/examples/dry_run_broker_adapter/dry_run_orders.csv`

## 17. Broker Capability Manifest

```bash
python examples/broker_capability_manifest_demo.py
```

Writes the adapter capability declaration reviewers should inspect before a
broker-facing adapter is accepted. It names supported modes, account modes,
credential policy, network access, and live-safety controls without reading
credentials or submitting orders.

Output:

- `outputs/examples/broker_capability_manifest/capability_manifest.json`
- `outputs/examples/broker_capability_manifest/capability_manifest.md`

## 18. Broker Approval Safety

```bash
python examples/broker_approval_safety_demo.py
```

Builds a redacted broker approval artifact, validates it, converts it into a
`live_human_approved` safety config, and proves that a bounded order passes
while an oversized order is blocked. It does not read broker credentials or
submit orders.

Output:

- `outputs/examples/broker_approval_safety/summary.json`
- `outputs/examples/broker_approval_safety/broker_approval_artifact.json`

## 19. Broker Response Reconciliation

```bash
python examples/broker_response_reconciliation_demo.py
```

Matches synthetic paper broker responses back to submitted client order IDs and
writes a reconciliation artifact. It uses paper-mode sample responses only:
no credentials are read and no live orders are submitted.

Output:

- `outputs/examples/broker_response_reconciliation/summary.json`
- `outputs/examples/broker_response_reconciliation/broker_response_artifact.json`
- `outputs/examples/broker_response_reconciliation/alpaca_paper_orders.json`

## 20. Broker Response Status-Mapping Fixture

```bash
python examples/broker_response_status_mapping_fixture_demo.py
```

Writes a schema-valid paper response artifact with accepted, rejected,
partially filled, canceled, and unknown statuses plus recomputed reconciliation
counts. The fixture is synthetic: no credentials are read and no live orders are
submitted.

Output:

- `outputs/examples/broker_response_artifact/summary.json`
- `outputs/examples/broker_response_artifact/response_artifact.json`
- `outputs/examples/broker_response_artifact/alpaca_paper_orders.json`

## 21. Mock Paper Sandbox Client

```bash
python examples/mock_paper_sandbox_client_demo.py
```

Shows a broker-specific paper sandbox contribution pattern with an injected
mock client. The fixture proves no default network call is made, writes a
paper-mode handoff artifact, and records a broker response artifact through the
generic paper sandbox skeleton.

Output:

- `outputs/examples/mock_paper_sandbox_client/summary.json`
- `outputs/examples/mock_paper_sandbox_client/alpaca_paper_orders.json`
- `outputs/examples/mock_paper_sandbox_client/paper_sandbox_response_artifact.json`

## 22. Operator Runbook Checklist

```bash
python examples/operator_runbook_demo.py
```

Writes an offline operator checklist for live-capable paths. The artifact names
the default mode, approval expiry, kill switch, reconciliation, rollback, and
artifact-retention evidence, plus the incident owner and final live-readiness
preflight validation command, without reading credentials or submitting orders.

Output:

- `outputs/examples/operator_runbook/summary.json`
- `outputs/examples/operator_runbook/operator_runbook.md`

## 23. Live-Readiness Preflight Bundle

```bash
python examples/live_readiness_preflight_demo.py
```

Links the capability manifest, handoff artifact, approval binding, a response
artifact bound to the reviewed handoff hash and `client_order_id`, and operator
runbook into one review packet. It validates the chain locally and does not
authorize live submission.

Output:

- `outputs/examples/live_readiness_preflight/preflight_bundle.json`
- `outputs/examples/live_readiness_preflight/preflight_response_artifact.json`
- `outputs/examples/live_readiness_preflight/preflight_summary.json`

## 24. Holdings CSV Import

```bash
python examples/holdings_csv_import_demo.py
```

Loads `examples/fixtures/retail_holdings.csv` into the retail planning sandbox
and produces paper rebalance diagnostics.

Output:

- `outputs/examples/holdings_csv_import/summary.json`

## 25. Futures Roll Risk

```bash
python examples/futures_roll_risk_demo.py
```

Uses contract metadata and a paper roll schedule to flag futures expiry or roll
risk in a normal `RiskReport`.

Output:

- `outputs/examples/futures_roll_risk/summary.json`
- `outputs/examples/futures_roll_risk/futures_roll_risk.svg`

## 26. Crypto Microstructure Stress

```bash
python examples/crypto_microstructure_stress_demo.py
```

Runs a no-key synthetic crypto scenario with matching baseline and
fee-tier/spread-shock execution presets. The artifact exposes fill rate,
slippage cost, commission, rejected orders, partial fills, and pending orders
while marking the settings as stress assumptions rather than venue calibration.

Output:

- `outputs/examples/crypto_microstructure_stress/summary.json`
- `outputs/examples/crypto_microstructure_stress/crypto_microstructure_stress.svg`

## 27. Almgren-Chriss Impact Stress

```bash
python examples/almgren_chriss_stress_demo.py
```

Compares the default execution-stress baseline with opt-in linear and concave
market-impact proxies. The fixture reports modeled shortfall and calibration
boundaries without claiming broker-grade transaction-cost calibration.

Output:

- `outputs/examples/almgren_chriss_stress/summary.json`
- `outputs/examples/almgren_chriss_stress/summary.md`
- `outputs/examples/almgren_chriss_stress/almgren_chriss_stress.svg`

## 28. Liquidity Halt Stress

```bash
python examples/liquidity_halt_demo.py
```

Builds a deterministic paper-only trajectory where a delayed order is pending
when a circuit halt begins. The artifact includes risk and execution reports
for pending, partial, rejected, and blocked order outcomes.

Output:

- `outputs/examples/liquidity_halt/summary.json`
- `outputs/examples/liquidity_halt/trajectory.json`
- `outputs/examples/liquidity_halt/summary.md`
- `outputs/examples/liquidity_halt/liquidity_halt.svg`

## 29. Mock Deep-RL Policy Baseline

```bash
python examples/rl_policy_baseline_demo.py
```

Wraps a deterministic mock RL allocation policy as a `StrategyAgent` so a real
FinRL/Qlib policy can later replace the scoring function while reusing the risk,
execution, trajectory, and evaluator stack.

Output:

- `outputs/examples/rl_policy_baseline/summary.json`
- `outputs/examples/rl_policy_baseline/rl_policy_baseline.svg`

## Full Local Check

```bash
python -m pytest tests -q
python scripts/run_showcase.py --reuse-existing
```
