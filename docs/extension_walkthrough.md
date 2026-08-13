# Extension Walkthrough

TreLLM is designed around narrow protocol surfaces. A contributor should be
able to add one module without editing the runner, schemas, execution simulator,
memory store, or evaluators owned by other modules.

Run the hands-on extension demo:

```bash
python examples/extension_walkthrough_demo.py
```

Open:

```text
outputs/examples/extension_walkthrough.svg
outputs/examples/extension_walkthrough_summary.json
```

## What The Demo Replaces

The walkthrough adds three contributor-owned modules:

| Extension point | Demo class | Protocol method |
| --- | --- | --- |
| Analyst plugin | `GapVolumeAnalyst` | `analyze(snapshot, portfolio, memory) -> list[Signal]` |
| Risk plugin | `VolatilityCircuitBreakerRisk` | `approve`, `monitor`, `attribute` |
| Evaluator plugin | `ExtensionCoverageEvaluator` | `evaluate(trajectory) -> dict[str, metric]` |

Everything else is reused unchanged:

- `SyntheticMarketDataProvider`
- `SignalWeightedStrategy`
- `TargetWeightExecutionAgent`
- `RealisticOrderSimulator`
- `InMemoryResearchMemory`
- trajectory logging and reproducibility state

## Minimal Contributor Pattern

```python
class MyAnalyst:
    name = "my-analyst"

    def analyze(self, snapshot, portfolio, memory):
        return [
            Signal(
                symbol=symbol,
                score=0.2,
                confidence=0.6,
                horizon="1d",
                rationale="my local feature fired",
                metadata={"analyst": self.name},
            )
            for symbol in snapshot.bars
        ]
```

Then wire it into the existing stack:

```python
system = TradeArena(
    config=config,
    data_provider=data_provider,
    analysts=[MyAnalyst()],
    strategy=SignalWeightedStrategy(),
    risk_manager=MaxPositionRiskManager(),
    execution_agent=TargetWeightExecutionAgent(),
    order_simulator=RealisticOrderSimulator(),
    memory=InMemoryResearchMemory(),
    evaluators=[PerformanceEvaluator(), RiskAuditEvaluator()],
)
trajectory, metrics = system.run()
```

The custom module automatically appears in:

- `trajectory.metadata`
- step-level `signals`, `decisions`, and `approved_decisions`
- `risk_report`, `in_trade_report`, and `post_trade_report`
- reproducibility state
- downstream evaluator output

## Contribution Checklist

Good extension examples should be small, deterministic, and inspectable.

- Implement one protocol surface at a time.
- Put demo code under `examples/`.
- Write outputs under `outputs/examples/`.
- Produce at least one human-readable artifact such as SVG, HTML, CSV, or JSON.
- Add the example to `examples/README.md` and `docs/demo_matrix.md`.
- Add a smoke test when the example supports a public claim.
