import pytest

from tradearena.agents import MaxDrawdownRiskPreset, max_drawdown_risk_preset
from tradearena.core.domain import Decision, PortfolioState, RiskReport, Side
from tradearena.data import SyntheticMarketDataProvider
from tradearena.memory import InMemoryResearchMemory


def _snapshot_and_drawdown_memory():
    snapshot = SyntheticMarketDataProvider(symbols=("SYN",), periods=1, seed=28).stream()[0]
    memory = InMemoryResearchMemory()
    memory.record("step", {"equity": 100_000.0})
    memory.record("step", {"equity": 98_000.0})
    portfolio = PortfolioState(cash=94_000.0)
    portfolio.last_prices.update({symbol: bar.close for symbol, bar in snapshot.bars.items()})
    return snapshot, memory, portfolio


def _buy_decision(target_weight: float = 0.40) -> Decision:
    return Decision(
        symbol="SYN",
        side=Side.BUY,
        target_weight=target_weight,
        confidence=0.90,
        rationale="LLM attempts to add after a drawdown",
    )


def test_max_drawdown_preset_blocks_decisions_and_emits_risk_report():
    snapshot, memory, portfolio = _snapshot_and_drawdown_memory()
    risk = max_drawdown_risk_preset(max_drawdown=0.05, de_risk_weight=0.0, drawdown_lookback=3)

    approved = risk.approve(snapshot, [_buy_decision()], portfolio, memory)

    assert isinstance(risk, MaxDrawdownRiskPreset)
    assert approved[0].side == Side.HOLD
    assert approved[0].target_weight == 0.0
    assert approved[0].metadata["risk_blocked"] == "max_drawdown"
    assert approved[0].metadata["drawdown_kill_switch"] is True
    assert isinstance(risk.last_report, RiskReport)
    assert risk.last_report.passed is False
    assert risk.last_report.blocked_count == 1
    assert risk.last_report.clipped_count == 0
    assert risk.last_report.violations[0].constraint == "drawdown_kill_switch"
    assert risk.last_report.budget is not None
    assert risk.last_report.budget.metadata["preset"] == "max_drawdown"


def test_max_drawdown_preset_clips_to_configured_derisk_weight():
    snapshot, memory, portfolio = _snapshot_and_drawdown_memory()
    risk = max_drawdown_risk_preset(max_drawdown=0.05, de_risk_weight=0.10, drawdown_lookback=3)

    approved = risk.approve(snapshot, [_buy_decision()], portfolio, memory)

    assert approved[0].side == Side.BUY
    assert approved[0].target_weight == 0.10
    assert approved[0].metadata["risk_clipped"] == "max_drawdown"
    assert approved[0].metadata["rolling_drawdown"] == pytest.approx(-0.06)
    assert isinstance(risk.last_report, RiskReport)
    assert risk.last_report.blocked_count == 0
    assert risk.last_report.clipped_count == 1
    assert risk.last_report.checks[0].name == "drawdown_kill_switch"
