from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tradearena.agents import MaxPositionRiskManager, SignalWeightedStrategy, TargetWeightExecutionAgent
from tradearena.core.domain import (
    Decision,
    ExperimentConfig,
    MarketSnapshot,
    PortfolioState,
    RiskCheck,
    RiskPhase,
    RiskReport,
    RiskViolation,
    Side,
    Signal,
)
from tradearena.core.runner import TradeArena
from tradearena.core.serialization import write_json
from tradearena.core.trajectory import Trajectory
from tradearena.data import SyntheticMarketDataProvider
from tradearena.evaluation import ExecutionRealismEvaluator, PerformanceEvaluator, RiskAuditEvaluator
from tradearena.memory import InMemoryResearchMemory
from tradearena.tools import RealisticOrderSimulator

OUTPUT_DIR = Path("outputs/examples")


@dataclass
class GapVolumeAnalyst:
    """Contributor-owned analyst plugin: turns local bar features into signals."""

    name: str = "contrib-gap-volume-analyst"
    volume_history: dict[str, list[float]] = field(default_factory=dict)

    def analyze(self, snapshot: MarketSnapshot, portfolio: PortfolioState, memory: object) -> list[Signal]:
        signals: list[Signal] = []
        for symbol, bar in snapshot.bars.items():
            history = self.volume_history.setdefault(symbol, [])
            average_volume = sum(history[-8:]) / min(len(history), 8) if history else bar.volume
            history.append(bar.volume)

            intraday_return = (bar.close / bar.open) - 1.0 if bar.open else 0.0
            volume_surge = (bar.volume / average_volume) - 1.0 if average_volume else 0.0
            score = max(-1.0, min(1.0, 6.0 * intraday_return + 0.12 * volume_surge))
            signals.append(
                Signal(
                    symbol=symbol,
                    score=score,
                    confidence=min(0.9, 0.30 + abs(score) * 0.55),
                    horizon="1d",
                    rationale=f"contributor gap-volume signal: return={intraday_return:.3f}, volume_surge={volume_surge:.2f}",
                    metadata={
                        "analyst": self.name,
                        "feature": "gap_volume_blend",
                        "contributor_owned": True,
                    },
                )
            )
        return signals


@dataclass
class VolatilityCircuitBreakerRisk(MaxPositionRiskManager):
    """Contributor-owned risk plugin: wraps the baseline risk gate with a circuit breaker."""

    range_threshold: float = 0.024
    name: str = "contrib-volatility-circuit-breaker"
    circuit_breaker_blocks: int = field(default=0, init=False)

    def approve(self, snapshot: MarketSnapshot, decisions: list[Decision], portfolio: PortfolioState, memory: object) -> list[Decision]:
        approved = super().approve(snapshot, decisions, portfolio, memory)
        base_report = self.last_report
        average_range = sum((bar.high - bar.low) / max(1e-9, bar.open) for bar in snapshot.bars.values()) / len(snapshot.bars)

        if average_range <= self.range_threshold:
            self.last_report = self._extend_report(
                base_report,
                extra_checks=(
                    RiskCheck(
                        name="volatility_circuit_breaker",
                        passed=True,
                        severity="info",
                        message=f"average intraperiod range {average_range:.3f} within threshold {self.range_threshold:.3f}",
                    ),
                ),
            )
            return approved

        revised: list[Decision] = []
        blocked = 0
        for decision in approved:
            if decision.target_weight > 0:
                blocked += 1
                revised.append(
                    Decision(
                        symbol=decision.symbol,
                        side=Side.HOLD,
                        target_weight=0.0,
                        confidence=decision.confidence,
                        rationale=f"blocked by volatility circuit breaker: {decision.rationale}",
                        metadata={
                            **decision.metadata,
                            "risk_blocked": "volatility_circuit_breaker",
                            "observed_range": average_range,
                        },
                    )
                )
            else:
                revised.append(decision)

        self.circuit_breaker_blocks += blocked
        self.last_report = self._extend_report(
            base_report,
            blocked_delta=blocked,
            extra_checks=(
                RiskCheck(
                    name="volatility_circuit_breaker",
                    passed=False,
                    severity="warning",
                    message=f"average intraperiod range {average_range:.3f} exceeded threshold {self.range_threshold:.3f}",
                    metadata={"observed": average_range, "limit": self.range_threshold},
                ),
            ),
            extra_violations=(
                RiskViolation(
                    phase=RiskPhase.PRE_TRADE,
                    constraint="volatility_circuit_breaker",
                    severity="warning",
                    observed=average_range,
                    limit=self.range_threshold,
                    message="new long exposure blocked during high intraperiod volatility",
                ),
            )
            if blocked
            else (),
        )
        return revised

    def _extend_report(
        self,
        report: RiskReport | None,
        *,
        blocked_delta: int = 0,
        extra_checks: tuple[RiskCheck, ...] = (),
        extra_violations: tuple[RiskViolation, ...] = (),
    ) -> RiskReport:
        if report is None:
            raise RuntimeError("VolatilityCircuitBreakerRisk expected the parent risk report to exist.")
        return RiskReport(
            timestamp=report.timestamp,
            checks=tuple(report.checks) + extra_checks,
            approved_count=report.approved_count,
            blocked_count=report.blocked_count + blocked_delta,
            clipped_count=report.clipped_count,
            phase=report.phase,
            budget=report.budget,
            violations=tuple(report.violations) + extra_violations,
            attribution=report.attribution,
        )


@dataclass
class ExtensionCoverageEvaluator:
    """Contributor-owned evaluator: reports whether custom modules reached the trajectory."""

    name: str = "contrib-extension-coverage-evaluator"

    def evaluate(self, trajectory: Trajectory) -> dict[str, float | int | str]:
        custom_signals = 0
        circuit_breaker_blocks = 0
        for step in trajectory.steps:
            for signal in step.signals:
                if signal.get("metadata", {}).get("contributor_owned"):
                    custom_signals += 1
            for decision in step.approved_decisions:
                if decision.get("metadata", {}).get("risk_blocked") == "volatility_circuit_breaker":
                    circuit_breaker_blocks += 1
        return {
            "extension_custom_signal_count": custom_signals,
            "extension_circuit_breaker_blocks": circuit_breaker_blocks,
            "extension_components": "analyst,risk_manager,evaluator",
        }


def main() -> int:
    system = TradeArena(
        config=ExperimentConfig(name="extension_walkthrough_demo", symbols=("SYN", "ALT", "DEF"), seed=77),
        data_provider=SyntheticMarketDataProvider(
            symbols=("SYN", "ALT", "DEF"),
            periods=42,
            seed=77,
            volatility_scale=1.55,
            jump_probability=0.10,
            jump_scale=0.035,
        ),
        analysts=[GapVolumeAnalyst()],
        strategy=SignalWeightedStrategy(max_long_weight=0.34),
        risk_manager=VolatilityCircuitBreakerRisk(max_abs_weight=0.28, max_gross_exposure=0.80, max_single_step_turnover=0.50),
        execution_agent=TargetWeightExecutionAgent(),
        order_simulator=RealisticOrderSimulator(participation_rate=0.04, latency_steps=1, market_impact=0.16),
        memory=InMemoryResearchMemory(),
        evaluators=[
            PerformanceEvaluator(),
            ExecutionRealismEvaluator(),
            RiskAuditEvaluator(),
            ExtensionCoverageEvaluator(),
        ],
    )
    trajectory, metrics = system.run()
    summary = _summary(system, trajectory, metrics)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "extension_walkthrough_summary.json", summary)
    _write_svg(OUTPUT_DIR / "extension_walkthrough.svg", summary)
    _write_markdown(OUTPUT_DIR / "extension_walkthrough_notes.md", summary)

    print("Extension walkthrough demo")
    print("  contributor modules=analyst, risk_manager, evaluator")
    print("  reused modules=data_provider, strategy, execution_agent, order_simulator, memory")
    print(
        "  "
        f"custom_signals={summary['metrics']['extension_custom_signal_count']} "
        f"circuit_breaker_blocks={summary['metrics']['extension_circuit_breaker_blocks']} "
        f"return={summary['metrics']['total_return']:.4f}"
    )
    print(f"\nWrote {OUTPUT_DIR / 'extension_walkthrough.svg'}")
    return 0


def _summary(system: TradeArena, trajectory: Trajectory, metrics: dict[str, float | int | str]) -> dict[str, object]:
    first_trace = trajectory.steps[0].agent_trace
    return {
        "purpose": "show how a contributor can add modules without modifying the runner",
        "custom_modules": {
            "analyst": "GapVolumeAnalyst",
            "risk_manager": "VolatilityCircuitBreakerRisk",
            "evaluator": "ExtensionCoverageEvaluator",
        },
        "reused_core_modules": {
            "data_provider": system.data_provider.name,
            "strategy": system.strategy.name,
            "execution_agent": system.execution_agent.name,
            "order_simulator": system.order_simulator.name,
            "memory": system.memory.name,
        },
        "protocol_surfaces": [
            "AnalystAgent.analyze(snapshot, portfolio, memory) -> list[Signal]",
            "RiskManagerAgent.approve/monitor/attribute(...) -> decisions + reports",
            "Evaluator.evaluate(trajectory) -> dict[str, metric]",
        ],
        "trajectory_fields_visible_to_plugin": sorted(first_trace.keys()) if isinstance(first_trace, dict) else [],
        "metrics": metrics,
        "artifacts": {
            "summary": "outputs/examples/extension_walkthrough_summary.json",
            "figure": "outputs/examples/extension_walkthrough.svg",
            "notes": "outputs/examples/extension_walkthrough_notes.md",
        },
    }


def _write_markdown(path: Path, summary: dict[str, object]) -> None:
    metrics = summary["metrics"]
    text = f"""# Extension Walkthrough Output

This run demonstrates the TreLLM contribution path:

1. Add a custom analyst that emits `Signal` objects.
2. Add a custom risk manager that emits auditable `RiskReport` records.
3. Add a custom evaluator that reads the final `Trajectory`.

Core modules reused unchanged:

- data provider
- strategy
- execution agent
- realistic order simulator
- memory store
- trajectory writer

Key metrics:

- custom signals: `{metrics['extension_custom_signal_count']}`
- circuit-breaker blocks: `{metrics['extension_circuit_breaker_blocks']}`
- total return: `{metrics['total_return']:.4f}`
- execution fill rate: `{metrics['execution_fill_rate']:.3f}`
- risk lifecycle coverage: `{metrics['risk_lifecycle_coverage']:.3f}`
"""
    path.write_text(text, encoding="utf-8")


def _write_svg(path: Path, summary: dict[str, object]) -> None:
    width, height = 1040, 520
    metrics = summary["metrics"]
    custom = summary["custom_modules"]
    reused = summary["reused_core_modules"]
    cards = [
        ("1. You add", "Analyst plugin", custom["analyst"], "#2563eb"),
        ("2. Core reuses", "Strategy", reused["strategy"], "#0f766e"),
        ("3. You add", "Risk plugin", custom["risk_manager"], "#dc2626"),
        ("4. Core reuses", "Execution simulator", reused["order_simulator"], "#7c3aed"),
        ("5. You add", "Evaluator plugin", custom["evaluator"], "#ea580c"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="TreLLM extension walkthrough">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(42, 52, "Bring your own module: plug into the protocol, not the core", 24, "#0f172a", 800),
        _text(42, 82, "This hands-on demo swaps in a custom analyst, risk manager, and evaluator while reusing the runner, strategy, simulator, memory, and trajectory logger.", 13, "#64748b", 500),
    ]
    for idx, (eyebrow, title, body, color) in enumerate(cards):
        x = 42 + idx * 194
        parts.append(f'<rect x="{x}" y="132" width="166" height="124" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
        parts.append(f'<rect x="{x}" y="132" width="166" height="8" rx="4" fill="{color}"/>')
        parts.append(_text(x + 14, 164, eyebrow, 11, color, 800))
        parts.append(_text(x + 14, 190, title, 15, "#0f172a", 800))
        parts.append(_text(x + 14, 216, _clip(str(body), 24), 11, "#475569", 500))
        if idx < len(cards) - 1:
            parts.append(f'<path d="M{x + 171} 194 L{x + 190} 194" stroke="#334155" stroke-width="2"/>')
            parts.append(f'<path d="M{x + 190} 194 L{x + 184} 189 M{x + 190} 194 L{x + 184} 199" stroke="#334155" stroke-width="2" fill="none"/>')

    metric_cards = [
        ("Custom signals", int(metrics["extension_custom_signal_count"]), "#2563eb"),
        ("Circuit blocks", int(metrics["extension_circuit_breaker_blocks"]), "#dc2626"),
        ("Fill rate", f"{float(metrics['execution_fill_rate']):.3f}", "#7c3aed"),
        ("Audit coverage", f"{float(metrics['risk_lifecycle_coverage']):.3f}", "#0f766e"),
    ]
    parts.append(_text(42, 320, "What the contributor gets automatically", 18, "#0f172a", 800))
    parts.append(_text(42, 346, "Metrics, risk reports, execution realism, memory events, and reproducible trajectory fields are produced without modifying the core runner.", 13, "#64748b", 500))
    for idx, (label, value, color) in enumerate(metric_cards):
        x = 42 + idx * 240
        parts.append(f'<rect x="{x}" y="376" width="210" height="86" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
        parts.append(_text(x + 16, 408, label, 12, "#64748b", 800))
        parts.append(_text(x + 16, 446, str(value), 26, color, 800))

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{value}</text>'


def _clip(value: str, max_chars: int) -> str:
    return value if len(value) <= max_chars else value[: max_chars - 1] + "."


if __name__ == "__main__":
    raise SystemExit(main())
