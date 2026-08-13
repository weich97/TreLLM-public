from __future__ import annotations

from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

import tradearena.execution as execution
import tradearena.tools.simulator as simulator_compat
from tradearena.agents import MaxPositionRiskManager
from tradearena.core.domain import Bar, Decision, Fill, MarketSnapshot, Order, PortfolioState, Side
from tradearena.tools import (
    FillReplayOrderSimulator,
    MarketRuleState,
    RealisticOrderSimulator,
    ashare_rule_package,
    crypto_rule_package,
    futures_rule_package,
    liquidity_halt_rule_package,
    market_rule_from_package,
)


def _snapshot(volume: float = 1_000.0) -> MarketSnapshot:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return MarketSnapshot(
        timestamp=timestamp,
        bars={
            "SYN": Bar(
                symbol="SYN",
                timestamp=timestamp,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=volume,
            )
        },
    )


def test_execution_package_and_tools_simulator_share_public_classes():
    assert execution.RealisticOrderSimulator is simulator_compat.RealisticOrderSimulator
    assert execution.FillReplayOrderSimulator is simulator_compat.FillReplayOrderSimulator
    assert execution.SimpleOrderSimulator is simulator_compat.SimpleOrderSimulator
    assert execution.EXECUTION_STRESS == "stress"
    assert execution.EXECUTION_FILL_REPLAY == "fill_replay"


@settings(max_examples=40, deadline=None)
@given(
    side=st.sampled_from([Side.BUY, Side.SELL]),
    quantity=st.floats(min_value=0.0, max_value=2_000.0, allow_nan=False, allow_infinity=False),
    initial_cash=st.floats(min_value=0.0, max_value=200_000.0, allow_nan=False, allow_infinity=False),
    initial_position=st.floats(min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False),
    participation_rate=st.floats(min_value=0.0001, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_realistic_simulator_accounting_invariants(
    side: Side,
    quantity: float,
    initial_cash: float,
    initial_position: float,
    participation_rate: float,
):
    snapshot = _snapshot()
    portfolio = PortfolioState(cash=initial_cash, positions={"SYN": initial_position})
    simulator = RealisticOrderSimulator(
        commission_bps=5.0,
        base_slippage_bps=2.0,
        spread_bps=10.0,
        participation_rate=participation_rate,
        latency_steps=0,
        market_impact=0.15,
        allow_short=False,
    )

    fills = simulator.execute(snapshot, [Order(symbol="SYN", side=side, quantity=quantity)], portfolio)

    assert simulator.last_report is not None
    assert simulator.last_report.filled_orders == len(fills)
    assert simulator.last_report.partial_fills == sum(1 for fill in fills if fill.status == "partial")
    assert simulator.last_report.pending_orders == 0
    assert simulator.last_report.filled_orders + simulator.last_report.rejected_orders == simulator.last_report.eligible_orders
    assert portfolio.cash >= -1e-6
    assert portfolio.positions.get("SYN", 0.0) >= -1e-6
    for fill in fills:
        assert 0.0 <= fill.fill_ratio <= 1.0 + 1e-12
        assert fill.quantity <= max(fill.requested_quantity or 0.0, 0.0) + 1e-9
        expected_status = "partial" if fill.fill_ratio < 0.999999 else "filled"
        assert fill.status == expected_status


@settings(max_examples=50, deadline=None)
@given(
    package_name=st.sampled_from(["ashare", "crypto", "futures", "liquidity_halt"]),
    side=st.sampled_from([Side.BUY, Side.SELL]),
    quantity=st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    price=st.floats(min_value=0.01, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    volume=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
    settled_position=st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    same_day_buy_quantity=st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    available_cash=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
)
def test_market_rule_plugins_preserve_order_feasibility_invariants(
    package_name: str,
    side: Side,
    quantity: float,
    price: float,
    volume: float,
    settled_position: float,
    same_day_buy_quantity: float,
    available_cash: float,
):
    packages = {
        "ashare": ashare_rule_package(),
        "crypto": crypto_rule_package(),
        "futures": futures_rule_package(initial_margin_rate=0.10, contract_multiplier=10.0),
        "liquidity_halt": liquidity_halt_rule_package(participation_rate=0.02, eta=0.25),
    }
    rule = market_rule_from_package(packages[package_name])
    state = MarketRuleState(
        price=price,
        previous_close=price,
        volume=volume,
        settled_position=settled_position,
        same_day_buy_quantity=same_day_buy_quantity,
        available_cash=available_cash,
    )

    decision = rule.validate_order(symbol="SYN", side=side, quantity=quantity, state=state)

    assert decision.status in {"approved", "clipped", "blocked"}
    assert 0.0 <= decision.approved_quantity <= max(0.0, quantity) + 1e-9
    assert decision.estimated_fee >= 0.0
    assert decision.estimated_funding >= 0.0
    assert decision.estimated_market_impact >= 0.0
    assert decision.estimated_margin_required >= 0.0
    assert decision.metadata["package"] == rule.name
    if decision.blocked:
        assert decision.approved_quantity == 0.0
        assert decision.reasons
    if decision.clipped:
        assert decision.approved_quantity <= decision.requested_quantity


def test_realistic_limit_rejection_does_not_consume_liquidity_or_partial_count():
    snapshot = _snapshot(volume=1_000.0)
    portfolio = PortfolioState(cash=1_000_000.0)
    simulator = RealisticOrderSimulator(participation_rate=0.05, latency_steps=0)
    rejected_limit = Order(symbol="SYN", side=Side.BUY, quantity=50.0, limit_price=1.0)
    accepted_market = Order(symbol="SYN", side=Side.BUY, quantity=50.0)

    fills = simulator.execute(snapshot, [rejected_limit, accepted_market], portfolio)

    assert len(fills) == 1
    assert fills[0].quantity == 50.0
    assert fills[0].status == "filled"
    assert simulator.last_report is not None
    assert simulator.last_report.rejected_orders == 1
    assert simulator.last_report.partial_fills == 0


def test_realistic_pending_order_counts_follow_latency_queue():
    snapshot = _snapshot()
    portfolio = PortfolioState(cash=1_000_000.0)
    simulator = RealisticOrderSimulator(participation_rate=1.0, latency_steps=2)
    order = Order(symbol="SYN", side=Side.BUY, quantity=10.0)

    first = simulator.execute(snapshot, [order], portfolio)
    assert first == []
    assert simulator.last_report is not None
    assert simulator.last_report.eligible_orders == 0
    assert simulator.last_report.pending_orders == 1

    second = simulator.execute(snapshot, [], portfolio)
    assert second == []
    assert simulator.last_report is not None
    assert simulator.last_report.eligible_orders == 0
    assert simulator.last_report.pending_orders == 1

    third = simulator.execute(snapshot, [], portfolio)
    assert len(third) == 1
    assert simulator.last_report is not None
    assert simulator.last_report.eligible_orders == 1
    assert simulator.last_report.pending_orders == 0


def test_fill_replay_rejects_order_without_matching_realized_fill():
    snapshot = _snapshot()
    portfolio = PortfolioState(cash=1_000.0)
    simulator = FillReplayOrderSimulator(replay_fills=[])

    fills = simulator.execute(snapshot, [Order(symbol="SYN", side=Side.BUY, quantity=1.0)], portfolio)

    assert fills == []
    assert simulator.last_report is not None
    assert simulator.last_report.filled_orders == 0
    assert simulator.last_report.pending_orders == 0
    assert simulator.last_report.rejected_orders == 1


def test_fill_replay_long_only_sell_cannot_create_negative_position():
    snapshot = _snapshot()
    replay_fill = Fill(
        symbol="SYN",
        side=Side.SELL,
        quantity=10.0,
        price=100.0,
        commission=0.0,
        timestamp=snapshot.timestamp,
    )
    portfolio = PortfolioState(cash=0.0, positions={"SYN": 3.0})
    simulator = FillReplayOrderSimulator(replay_fills=[replay_fill], allow_short=False)

    fills = simulator.execute(snapshot, [Order(symbol="SYN", side=Side.SELL, quantity=10.0)], portfolio)

    assert len(fills) == 1
    assert fills[0].quantity == 3.0
    assert fills[0].fill_ratio == 0.3
    assert portfolio.positions["SYN"] == 0.0
    assert simulator.last_report is not None
    assert simulator.last_report.partial_fills == 1


@settings(max_examples=30, deadline=None)
@given(
    decision_rows=st.lists(
        st.tuples(
            st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=6,
    )
)
def test_risk_manager_weight_bounds_and_gross_exposure_invariants(decision_rows: list[tuple[float, float]]):
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = {
        f"S{idx}": Bar(
            symbol=f"S{idx}",
            timestamp=timestamp,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1_000.0,
        )
        for idx in range(len(decision_rows))
    }
    snapshot = MarketSnapshot(timestamp=timestamp, bars=bars)
    portfolio = PortfolioState(cash=100_000.0)
    risk = MaxPositionRiskManager(max_abs_weight=0.35, max_gross_exposure=1.0, min_confidence=0.10)
    decisions = [
        Decision(
            symbol=f"S{idx}",
            side=Side.BUY if target >= 0 else Side.SELL,
            target_weight=target,
            confidence=confidence,
            rationale="property test",
        )
        for idx, (target, confidence) in enumerate(decision_rows)
    ]

    approved = risk.approve(snapshot, decisions, portfolio, memory=None)

    assert len(approved) == len(decisions)
    assert all(abs(decision.target_weight) <= 0.35 + 1e-12 for decision in approved)
    assert sum(abs(decision.target_weight) for decision in approved) <= 1.0 + 1e-12
    for source, revised in zip(decisions, approved, strict=True):
        if source.confidence < 0.10:
            assert revised.side == Side.HOLD
            assert revised.target_weight == 0.0
    assert risk.last_report is not None
    assert risk.last_report.approved_count == len(decisions)
