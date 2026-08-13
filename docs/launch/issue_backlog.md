# Starter Issue Backlog

These were the first public starter issues. The corresponding examples now live
in the repository; keep this page as launch history and as a template for future
community tasks.

## Good First Issues

### Add a small Alpaca paper-trading adapter

Labels: `good first issue`, `adapter`, `paper-trading`

Status: implemented in `examples/alpaca_paper_export_demo.py` and
`src/tradearena/tools/broker_export.py`.

Build an offline broker-review adapter that converts approved TreLLM orders
into a neutral export format compatible with Alpaca paper-trading review. The
first version should not submit live orders.

Acceptance criteria:

- add a small adapter under `src/tradearena/tools/` or `planning/`
- write output under `outputs/examples/`
- add one smoke test
- document the human-approval boundary

### Add a holdings CSV importer for the retail planning sandbox

Labels: `good first issue`, `retail-planning`, `data`

Status: implemented in `examples/holdings_csv_import_demo.py`,
`examples/fixtures/retail_holdings.csv`, and
`src/tradearena/planning/importers.py`.

Add a helper that loads holdings from a CSV with columns `symbol`, `market_value`,
`quantity`, and optional `cost_basis`, then feeds `examples/retail_planner_demo.py`.

### Add a new execution-stress preset

Labels: `good first issue`, `execution`, `benchmark`

Add one new preset to the execution realism sweep, such as low-volume
end-of-day conditions. The first high-spread preset landed in v0.1.1.

### Improve the visual tour accessibility text

Labels: `good first issue`, `docs`, `accessibility`

Review README GIF alt text, showcase copy, and HTML report headings for screen
reader clarity.

## Research Extensions

### Add a Deep RL policy baseline wrapper

Labels: `research extension`, `baseline`, `reinforcement-learning`

Status: implemented as a deterministic integration baseline in
`examples/rl_policy_baseline_demo.py` and `src/tradearena/agents/rl.py`.

Add an interface example showing how a trained RL allocation policy can be
wrapped as a TreLLM strategy or analyst through the `tradearena` package
interfaces. The goal is integration and audit compatibility, not
state-of-the-art RL performance.

### Add a multi-window intraday benchmark registry

Labels: `research extension`, `benchmark`, `intraday`

Extend the 51-stock intraday probe to support temporally detached windows and
redacted manifest submission for community comparisons.

## Benchmark Requests

### Add a crypto market microstructure demo

Labels: `benchmark request`, `crypto`, `execution`

Status: implemented in `examples/crypto_microstructure_stress_demo.py`.

Create an offline-friendly crypto-style synthetic scenario with high volatility,
continuous trading, and liquidity-sensitive fills.

### Add a futures roll and expiry risk demo

Labels: `benchmark request`, `futures`, `risk`

Status: implemented in `examples/futures_roll_risk_demo.py` and
`src/tradearena/tools/futures.py`.

Extend the retail planning or execution layer with futures expiry, roll windows,
and margin-call stress reporting.

## Discussion Seeds

These can become GitHub Discussions after Discussions are enabled:

- What should count as a reproducible financial-agent trajectory?
- Which execution realism assumptions matter most for LLM agents?
- How should community leaderboard submissions redact provider prompts/responses?
- What is the safest boundary between planning, paper trading, and live trading?
