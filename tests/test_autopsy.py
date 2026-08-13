from tradearena.evaluation.autopsy import autopsy_trajectory, classify_step_failure_modes


def test_failure_autopsy_classifies_decision_failure_modes():
    step = {
        "timestamp": "2026-01-01T00:00:00Z",
        "decisions": [
            {
                "symbol": "SYN",
                "side": "buy",
                "target_weight": 0.80,
                "confidence": 0.20,
                "rationale": "bullish momentum with strong setup",
                "metadata": {"memory_pollution_ratio": 0.40},
            },
            {
                "symbol": "ALT",
                "side": "hold",
                "target_weight": 0.0,
                "confidence": 0.80,
                "rationale": "buy because trend is strong",
            },
        ],
        "approved_decisions": [{"symbol": "SYN", "target_weight": 0.35}],
        "orders": [{"symbol": "SYN"}, {"symbol": "ALT"}, {"symbol": "DEF"}, {"symbol": "GHI"}, {"symbol": "JKL"}],
        "risk_report": {
            "clipped_count": 1,
            "blocked_count": 0,
            "violations": [{"constraint": "max_position_weight"}],
        },
        "execution_report": {
            "filled_orders": 1,
            "partial_fills": 1,
            "pending_orders": 1,
            "rejected_orders": 0,
            "total_slippage": 250.0,
        },
    }

    modes = classify_step_failure_modes(step)

    assert "overtrading" in modes
    assert "pre_risk_leverage" in modes
    assert "low_confidence_bet" in modes
    assert "slippage_insensitive" in modes
    assert "liquidity_insensitive" in modes
    assert "memory_pollution" in modes
    assert "rationale_decision_mismatch" in modes
    assert "position_limit_noncompliance" in modes


def test_autopsy_trajectory_counts_steps():
    autopsy = autopsy_trajectory(
        {
            "experiment_name": "unit",
            "steps": [
                {
                    "decisions": [{"symbol": "SYN", "side": "buy", "target_weight": 0.2, "confidence": 0.1}],
                    "approved_decisions": [{"symbol": "SYN", "target_weight": 0.2}],
                    "orders": [],
                    "risk_report": {},
                    "execution_report": {},
                }
            ],
        }
    )

    assert autopsy["schema"] == "tradearena_failure_autopsy_v1"
    assert autopsy["failure_mode_counts"]["low_confidence_bet"] == 1
    assert autopsy["flagged_step_count"] == 1
