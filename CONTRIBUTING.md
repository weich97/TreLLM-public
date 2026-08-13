# Contributing to TreLLM

TreLLM is designed around narrow interfaces. A useful contribution usually
adds one small component, one clear demo, and one smoke test. TradeArena
leaderboard or benchmark artifacts should remain comparable, redacted, and
reproducible.

## Local Setup

```bash
python -m pip install -e ".[dev]"
python -m pytest tests -q
python scripts/run_showcase.py --reuse-existing
```

Run the full offline-friendly showcase before a larger pull request:

```bash
python scripts/run_showcase.py
python scripts/check_release_readiness.py
```

## Good First Contributions

- Add a new analyst example under `examples/`.
- Add a CSV sidecar example for a new data field.
- Add a risk metric to `RiskAuditEvaluator`.
- Add a small visualization for an existing JSON or CSV output.
- Improve the HTML audit report navigation.
- Add documentation that maps a paper claim to a runnable script.
- Reproduce a documented command and file an external validation report.

## Research Extensions

- A PPO or FinRL baseline on the 51-stock intraday panel.
- A direct provider adapter for a non-Poe frontier model endpoint.
- A limit-order-book execution simulator.
- A new dense embedding or hidden-state probe.
- A human annotation workflow for hallucination and audit-proxy calibration.
- An A-share sector panel and cross-market model comparison.

See `docs/benchmark_maturity.md` for the current academic-report,
external-validation, and community-participation gaps.

## Interface Pointers

Core protocols live in `src/tradearena/core/interfaces.py`.

Common extension points:

- `MarketDataProvider`
- `AnalystAgent`
- `StrategyAgent`
- `RiskManagerAgent`
- `ExecutionAgent`
- `OrderSimulator`
- `MemoryStore`
- `Evaluator`

The fastest pattern is `examples/custom_plugin_demo.py`: it adds one analyst and
leaves the rest of the framework unchanged.

## Demo Standards

Every public demo should:

- Run without API keys unless the filename or docs clearly say otherwise.
- Write artifacts under `outputs/examples/`.
- Keep generated raw outputs out of Git unless they are small, stable paper
  artifacts.
- Avoid storing credentials, private data, or live trading endpoints.
- Include a short explanation in `examples/README.md`.

## Testing

Before opening a pull request:

```bash
python -m compileall src scripts examples tests -q
python -m ruff check src scripts examples tests
python -m mypy
python -m pytest tests -q
python scripts/validate_demo_artifacts.py
python scripts/check_release_readiness.py
```

If your change affects a demo, run that demo directly and include the output path
in the pull request description.

## Broker-Facing Contributions

Broker-review exports, dry-run adapters, paper-sandbox adapters, and any future
live-capable path must follow `docs/broker_adapter_contract.md`.

Before opening this kind of pull request:

- State the adapter mode: `offline_export`, `dry_run`, `paper_sandbox`, or
  `live_human_approved`.
- Confirm that default construction cannot submit live orders.
- Include a redacted broker handoff, approval, or response artifact when the PR
  changes those surfaces.
- Run the matching validator, such as `tradearena validate-broker-handoff`,
  `tradearena validate-broker-approval`, or
  `tradearena validate-broker-response`.
- Add tests for notional limits, quantity limits, allowed symbols, kill-switches,
  and response reconciliation when the PR touches broker execution paths.
- Keep credentials, account identifiers, private holdings, and raw broker
  payloads out of committed files and public issue bodies.

## Data And Model Artifacts

Small reproducibility inputs can be tracked. Large generated trajectories, model
weights, and fresh raw outputs should stay outside Git. See
`docs/artifact_portability.md` for the current policy.

LLM responses are cacheable under `data/llm_cache/`, but API keys must never be
committed.
