from tradearena.agents import MaxPositionRiskManager
from tradearena.core.domain import Decision, PortfolioState, RiskReport, Side
from tradearena.data import SyntheticMarketDataProvider
from tradearena.memory import InMemoryResearchMemory


def test_default_risk_manager_records_drawdown_kill_switch_report():
    snapshot = SyntheticMarketDataProvider(symbols=("SYN",), periods=1, seed=7).stream()[0]
    memory = InMemoryResearchMemory()
    memory.record("step", {"equity": 100_000.0})
    memory.record("step", {"equity": 96_000.0})
    portfolio = PortfolioState(cash=94_000.0)
    portfolio.last_prices.update({symbol: bar.close for symbol, bar in snapshot.bars.items()})
    decision = Decision(
        symbol="SYN",
        side=Side.BUY,
        target_weight=0.25,
        confidence=0.80,
        rationale="attempted risk-on rebalance",
    )
    risk = MaxPositionRiskManager(max_drawdown=0.05, drawdown_lookback=3)

    approved = risk.approve(snapshot, [decision], portfolio, memory)

    assert approved[0].metadata["drawdown_kill_switch"] is True
    assert isinstance(risk.last_report, RiskReport)
    assert risk.last_report.passed is False
    assert risk.last_report.violations[0].constraint == "drawdown_kill_switch"
