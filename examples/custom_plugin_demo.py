from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tradearena.agents import MaxPositionRiskManager, SignalWeightedStrategy, TargetWeightExecutionAgent
from tradearena.core.domain import ExperimentConfig, MarketSnapshot, PortfolioState, Signal
from tradearena.core.runner import TradeArena
from tradearena.core.serialization import write_json
from tradearena.data import SyntheticMarketDataProvider
from tradearena.evaluation import (
    BehavioralEvaluator,
    ExecutionRealismEvaluator,
    PerformanceEvaluator,
    ReasoningConsistencyEvaluator,
    RiskAuditEvaluator,
)
from tradearena.memory import InMemoryResearchMemory
from tradearena.tools import RealisticOrderSimulator

OUTPUT_DIR = Path("outputs/examples")


@dataclass
class IntraperiodReversalAnalyst:
    """Tiny local analyst plugin used only for the hands-on extensibility demo."""

    name: str = "intraperiod-reversal-analyst"

    def analyze(self, snapshot: MarketSnapshot, portfolio: PortfolioState, memory: object) -> list[Signal]:
        signals = []
        for symbol, bar in snapshot.bars.items():
            intraperiod_return = (bar.close / bar.open) - 1.0 if bar.open else 0.0
            score = max(-1.0, min(1.0, -8.0 * intraperiod_return))
            if abs(intraperiod_return) < 0.004:
                score *= 0.25
            signals.append(
                Signal(
                    symbol=symbol,
                    score=score,
                    confidence=min(0.85, 0.35 + abs(intraperiod_return) * 12.0),
                    horizon="1d",
                    rationale=f"local plugin mean-reversion score from intraperiod_return={intraperiod_return:.4f}",
                    metadata={"analyst": self.name, "feature": "custom_intraperiod_reversal"},
                )
            )
        return signals


def main() -> int:
    system = TradeArena(
        config=ExperimentConfig(name="custom_plugin_demo", symbols=("SYN", "ALT", "DEF"), seed=41),
        data_provider=SyntheticMarketDataProvider(symbols=("SYN", "ALT", "DEF"), periods=36, seed=41, volatility_scale=1.15),
        analysts=[IntraperiodReversalAnalyst()],
        strategy=SignalWeightedStrategy(max_long_weight=0.32),
        risk_manager=MaxPositionRiskManager(max_abs_weight=0.24, max_gross_exposure=0.75, max_single_step_turnover=0.45),
        execution_agent=TargetWeightExecutionAgent(),
        order_simulator=RealisticOrderSimulator(participation_rate=0.035, latency_steps=1, market_impact=0.18),
        memory=InMemoryResearchMemory(),
        evaluators=[
            PerformanceEvaluator(),
            BehavioralEvaluator(),
            ReasoningConsistencyEvaluator(),
            ExecutionRealismEvaluator(),
            RiskAuditEvaluator(),
        ],
    )
    trajectory, metrics = system.run()
    first_signal = trajectory.steps[0].signals[0]
    summary = {
        "plugin": IntraperiodReversalAnalyst.name,
        "steps": len(trajectory.steps),
        "total_return": metrics["total_return"],
        "max_drawdown": metrics["max_drawdown"],
        "risk_clipped_decisions": metrics["risk_clipped_decisions"],
        "execution_fill_rate": metrics["execution_fill_rate"],
        "first_signal_feature": first_signal["metadata"]["feature"],
        "runner_metadata": trajectory.metadata,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "custom_plugin_summary.json", summary)
    _write_svg(OUTPUT_DIR / "custom_plugin.svg", summary)

    print("Custom plugin demo")
    print(f"  plugin={summary['plugin']} feature={summary['first_signal_feature']}")
    print(f"  return={summary['total_return']:.4f} clipped={summary['risk_clipped_decisions']} fill={summary['execution_fill_rate']:.3f}")
    print(f"\nWrote {OUTPUT_DIR / 'custom_plugin.svg'}")
    return 0


def _write_svg(path: Path, summary: dict[str, object]) -> None:
    width, height = 900, 300
    steps = [
        ("Custom analyst", "IntraperiodReversalAnalyst"),
        ("Existing strategy", "SignalWeightedStrategy"),
        ("Existing risk gate", "MaxPositionRiskManager"),
        ("Existing simulator", "RealisticOrderSimulator"),
        ("Same trajectory", "audit + metrics"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Custom plugin demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 44, "One new plugin, the rest of TreLLM stays fixed", 22, "#0f172a", 800),
        _text(36, 72, "This demo drops in a local analyst class and reuses strategy, risk, execution, memory, and evaluators.", 13, "#64748b", 400),
    ]
    for idx, (title, body) in enumerate(steps):
        x = 36 + idx * 170
        parts.append(f'<rect x="{x}" y="118" width="140" height="76" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
        parts.append(_text(x + 12, 146, title, 13, "#0f172a", 800))
        parts.append(_text(x + 12, 170, body[:23], 10, "#475569", 500))
        if idx < len(steps) - 1:
            parts.append(f'<path d="M{x + 144} 156 L{x + 162} 156" stroke="#2563eb" stroke-width="2"/>')
            parts.append(f'<path d="M{x + 162} 156 L{x + 156} 151 M{x + 162} 156 L{x + 156} 161" stroke="#2563eb" stroke-width="2" fill="none"/>')
    parts.append(
        _text(
            36,
            250,
            f"Output: return {float(summary['total_return']):.4f}, clipped {int(summary['risk_clipped_decisions'])}, fill {float(summary['execution_fill_rate']):.3f}",
            13,
            "#64748b",
            500,
        )
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{value}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
