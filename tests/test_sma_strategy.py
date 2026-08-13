from datetime import datetime, timezone

from tradearena.agents import SMACrossoverStrategy
from tradearena.core.domain import Bar, MarketSnapshot, PortfolioState, Side
from tradearena.factory import build_default_system, default_registry


def _snapshot(price: float) -> MarketSnapshot:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return MarketSnapshot(
        timestamp=timestamp,
        bars={
            "SYN": Bar(
                symbol="SYN",
                timestamp=timestamp,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=1_000.0,
            )
        },
    )


def test_sma_crossover_holds_until_fast_average_crosses_above_slow_average():
    strategy = SMACrossoverStrategy(fast_window=2, slow_window=3, max_long_weight=0.40)
    portfolio = PortfolioState(cash=100_000.0)

    decisions = [
        strategy.decide(_snapshot(price), signals=[], portfolio=portfolio, memory=None)[0]
        for price in [10.0, 9.0, 8.0, 12.0]
    ]

    assert [decision.side for decision in decisions] == [Side.HOLD, Side.HOLD, Side.HOLD, Side.BUY]
    assert [decision.target_weight for decision in decisions] == [0.0, 0.0, 0.0, 0.40]
    assert decisions[-1].metadata["strategy"] == "sma-crossover-strategy"
    assert decisions[-1].metadata["fast_sma"] == 10.0
    assert decisions[-1].metadata["slow_sma"] == 9.666666666666666
    assert decisions[-1].metadata["price_history_length"] == 3


def test_sma_crossover_is_registered_as_a_default_strategy():
    registry = default_registry()

    assert "sma-crossover" in registry.names("strategy")
    system = build_default_system(strategy_name="sma-crossover", periods=4, max_position_weight=0.25)

    assert system.strategy.name == "sma-crossover-strategy"
    assert system.strategy.max_long_weight == 0.25
