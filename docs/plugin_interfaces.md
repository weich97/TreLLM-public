# TreLLM Plugin Interfaces

The core interfaces live in `src/tradearena/core/interfaces.py`.

Recommended extension categories:

- `MarketDataProvider`: streams `MarketSnapshot` objects.
- `AnalystAgent`: converts observations into `Signal` objects.
- `StrategyAgent`: converts signals into target-weight `Decision` objects.
- `RiskManagerAgent`: clips, blocks, or annotates strategy decisions.
- `ExecutionAgent`: converts approved decisions into `Order` objects.
- `OrderSimulator`: fills orders, mutates `PortfolioState`, and may expose an `ExecutionReport`.
- `MemoryStore`: records events, theses, journals, and failure cases.
- `Evaluator`: computes metrics from a `Trajectory`.

Risk managers are encouraged to expose `last_report: RiskReport | None`. Execution simulators are encouraged to expose `last_report: ExecutionReport | None`. The runner automatically serializes these reports into trajectories when present.

The TreLLM system intentionally keeps interfaces narrow. A new LLM agent,
FinRL policy, broker adapter, or risk model should be able to enter by
implementing only the protocol it owns.

## Hands-On Extension Path

Run:

```bash
python examples/extension_walkthrough_demo.py
```

This demo replaces only three modules:

- `GapVolumeAnalyst` implements `AnalystAgent`.
- `VolatilityCircuitBreakerRisk` implements the risk lifecycle by extending the
  baseline risk manager with a pre-trade circuit breaker.
- `ExtensionCoverageEvaluator` implements `Evaluator`.

The same run reuses the existing data provider, strategy, execution agent,
realistic order simulator, memory store, trajectory logger, and baseline
evaluators. Open `outputs/examples/extension_walkthrough.svg` to see the module
boundary visually.

For a contributor-oriented checklist and scaffold command, see
[`docs/extension_walkthrough.md`](extension_walkthrough.md) and
[`docs/plugin_development.md`](plugin_development.md).
