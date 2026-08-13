from datetime import datetime

from tradearena.core.trajectory import StepRecord, Trajectory
from tradearena.evaluation.metrics import IntentExecutionGapEvaluator


def _step(decisions, approved, positions, equity=100_000.0, prices=None):
    prices = prices or {"SYN": 100.0}
    return StepRecord(
        timestamp=datetime(2026, 1, 1),
        observation={},
        signals=[],
        decisions=decisions,
        approved_decisions=approved,
        orders=[],
        fills=[],
        portfolio={"cash": 0.0, "positions": positions, "last_prices": prices, "equity": equity},
    )


def test_gap_is_zero_when_intent_matches_execution():
    trajectory = Trajectory(experiment_name="t", seed=1)
    trajectory.append(
        _step(
            decisions=[{"symbol": "SYN", "target_weight": 0.5}],
            approved=[{"symbol": "SYN", "target_weight": 0.5}],
            positions={"SYN": 500.0},  # 500 * 100 / 100000 = 0.5
        )
    )

    metrics = IntentExecutionGapEvaluator().evaluate(trajectory)

    assert metrics["intent_gap_steps"] == 1
    assert metrics["intent_risk_gap_l1"] == 0.0
    assert metrics["risk_execution_gap_l1"] == 0.0
    assert metrics["intent_execution_gap_l1"] == 0.0


def test_gap_decomposes_risk_and_execution_contributions():
    trajectory = Trajectory(experiment_name="t", seed=1)
    trajectory.append(
        _step(
            decisions=[{"symbol": "SYN", "target_weight": 0.8}],
            approved=[{"symbol": "SYN", "target_weight": 0.35}],  # risk clip
            positions={"SYN": 200.0},  # realized 0.2: execution shortfall
        )
    )

    metrics = IntentExecutionGapEvaluator().evaluate(trajectory)

    assert round(float(metrics["intent_risk_gap_l1"]), 6) == 0.45
    assert round(float(metrics["risk_execution_gap_l1"]), 6) == 0.15
    assert round(float(metrics["intent_execution_gap_l1"]), 6) == 0.6
    assert round(float(metrics["max_intent_execution_gap_l1"]), 6) == 0.6


def test_symbols_missing_on_either_side_count_fully():
    trajectory = Trajectory(experiment_name="t", seed=1)
    trajectory.append(
        _step(
            decisions=[{"symbol": "SYN", "target_weight": 0.4}],
            approved=[{"symbol": "SYN", "target_weight": 0.4}],
            positions={"ALT": 100.0},  # realized weight on an unintended symbol
            prices={"SYN": 100.0, "ALT": 100.0},
        )
    )

    metrics = IntentExecutionGapEvaluator().evaluate(trajectory)

    # intent SYN 0.4 vs realized ALT 0.1: distance 0.4 + 0.1
    assert round(float(metrics["intent_execution_gap_l1"]), 6) == 0.5


def test_steps_without_decisions_are_skipped():
    trajectory = Trajectory(experiment_name="t", seed=1)
    trajectory.append(_step(decisions=[], approved=[], positions={}))

    metrics = IntentExecutionGapEvaluator().evaluate(trajectory)

    assert metrics["intent_gap_steps"] == 0
    assert metrics["intent_execution_gap_l1"] == 0.0


def test_zero_equity_yields_no_realized_weights():
    trajectory = Trajectory(experiment_name="t", seed=1)
    trajectory.append(
        _step(
            decisions=[{"symbol": "SYN", "target_weight": 0.4}],
            approved=[{"symbol": "SYN", "target_weight": 0.4}],
            positions={"SYN": 100.0},
            equity=0.0,
        )
    )

    metrics = IntentExecutionGapEvaluator().evaluate(trajectory)

    assert round(float(metrics["intent_execution_gap_l1"]), 6) == 0.4
