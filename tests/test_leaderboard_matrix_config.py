from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_model_matrix_module():
    path = ROOT / "scripts" / "run_leaderboard_model_matrix.py"
    spec = importlib.util.spec_from_file_location("run_leaderboard_model_matrix", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_classical_matrix_module():
    path = ROOT / "scripts" / "run_classical_baseline_matrix.py"
    spec = importlib.util.spec_from_file_location("run_classical_baseline_matrix", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_real_matrix_module():
    path = ROOT / "scripts" / "run_real_market_leaderboard.py"
    spec = importlib.util.spec_from_file_location("run_real_market_leaderboard", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_quality_decomposition_module():
    path = ROOT / "scripts" / "build_quality_decomposition.py"
    spec = importlib.util.spec_from_file_location("build_quality_decomposition", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_model_matrix_includes_execution_shock_scenarios():
    module = _load_model_matrix_module()

    assert len(module.DEFAULT_SEEDS) >= 5
    assert "baseline:random" in module.DEFAULT_MODELS
    assert "baseline:always-hold" in module.DEFAULT_MODELS
    assert module.DEFAULT_SCENARIOS == (
        "calm_trend",
        "high_vol",
        "jump_tail",
        "liquidity_collapse",
        "spread_explosion",
        "latency_spike",
    )

    liquidity = module._scenario_execution_config(module._scenario("liquidity_collapse"))
    spread = module._scenario_execution_config(module._scenario("spread_explosion"))
    latency = module._scenario_execution_config(module._scenario("latency_spike"))

    assert liquidity["participation_rate"] < 0.01
    assert spread["spread_bps"] >= 100.0
    assert latency["latency_steps"] >= 4


def test_leaderboard_evidence_labels_bound_claim_scope():
    model_module = _load_model_matrix_module()
    real_module = _load_real_matrix_module()

    provider_evidence = model_module.evidence_payload_for_row(provider="poe", execution_mode="realistic-stress")
    baseline_evidence = real_module.evidence_payload_for_row(provider="baseline", execution_mode="realistic-stress")

    assert provider_evidence["tags"] == ["stress-only", "cached-provider", "redacted-prompt"]
    assert baseline_evidence["tags"] == ["stress-only", "deterministic-baseline"]
    assert model_module._format_evidence("stress-only;cached-provider") == "`stress-only`<br>`cached-provider`"
    assert real_module._format_evidence("stress-only;deterministic-baseline")


def test_model_matrix_aggregate_reports_uncertainty_and_baseline_tests():
    module = _load_model_matrix_module()
    rows = [
        {"scenario_key": "calm", "seed": 1, "provider": "baseline", "model": "always-hold", "total_return": 0.0, "max_drawdown": 0.0, "sharpe": 0.0, "execution_fill_rate": 0.0, "rejected_order_count": 0, "risk_clipped_decisions": 0, "parse_coverage": 1.0, "alpha_quality_score": 0.0, "risk_discipline_score": 1.0, "execution_robustness_score": 1.0},
        {"scenario_key": "calm", "seed": 2, "provider": "baseline", "model": "always-hold", "total_return": 0.0, "max_drawdown": 0.0, "sharpe": 0.0, "execution_fill_rate": 0.0, "rejected_order_count": 0, "risk_clipped_decisions": 0, "parse_coverage": 1.0, "alpha_quality_score": 0.0, "risk_discipline_score": 1.0, "execution_robustness_score": 1.0},
        {"scenario_key": "calm", "seed": 1, "provider": "baseline", "model": "random", "total_return": -0.01, "max_drawdown": -0.01, "sharpe": -1.0, "execution_fill_rate": 0.5, "rejected_order_count": 0, "risk_clipped_decisions": 1, "parse_coverage": 1.0, "alpha_quality_score": 0.1, "risk_discipline_score": 0.8, "execution_robustness_score": 0.7},
        {"scenario_key": "calm", "seed": 2, "provider": "baseline", "model": "random", "total_return": 0.01, "max_drawdown": 0.0, "sharpe": 1.0, "execution_fill_rate": 0.5, "rejected_order_count": 0, "risk_clipped_decisions": 1, "parse_coverage": 1.0, "alpha_quality_score": 0.1, "risk_discipline_score": 0.8, "execution_robustness_score": 0.7},
        {"scenario_key": "calm", "seed": 1, "provider": "poe", "model": "gpt-test", "total_return": 0.02, "max_drawdown": -0.01, "sharpe": 2.0, "execution_fill_rate": 1.0, "rejected_order_count": 0, "risk_clipped_decisions": 0, "parse_coverage": 1.0, "alpha_quality_score": 0.5, "risk_discipline_score": 1.0, "execution_robustness_score": 1.0},
        {"scenario_key": "calm", "seed": 2, "provider": "poe", "model": "gpt-test", "total_return": 0.03, "max_drawdown": -0.02, "sharpe": 3.0, "execution_fill_rate": 1.0, "rejected_order_count": 0, "risk_clipped_decisions": 0, "parse_coverage": 1.0, "alpha_quality_score": 0.6, "risk_discipline_score": 1.0, "execution_robustness_score": 1.0},
    ]

    aggregate = module._aggregate_rows(rows)
    model_row = next(row for row in aggregate if row["provider"] == "poe")

    assert model_row["run_count"] == 2
    assert model_row["std_return"] > 0
    assert model_row["return_ci_low"] is not None
    assert model_row["paired_n_vs_hold"] == 2
    assert model_row["p_value_vs_hold"] is not None
    assert model_row["bootstrap_p_value_vs_hold"] == model_row["p_value_vs_hold"]
    assert model_row["permutation_p_value_vs_hold"] is not None


def test_real_market_matrix_defaults_to_rolling_seed_protocol():
    module = _load_real_matrix_module()

    assert len(module.DEFAULT_SEEDS) >= 5
    assert "baseline:random" in module.DEFAULT_MODELS
    assert "baseline:always-hold" in module.DEFAULT_MODELS
    assert module._parse_model_spec("baseline:random") == ("baseline", "random")

    rows = [
        {
            "scenario_key": "recent_cross_asset",
            "scenario_label": "Recent",
            "provider": "poe",
            "model": "gpt-test",
            "seed": 7,
            "window_offset": 0,
            "frequency": "weekly",
            "start": "2025-05-01",
            "end": "2026-05-14",
            "max_periods": 12,
            "total_return": 0.01,
            "cache_policy": "live_or_cache_backed_raw_cache_ignored",
            "provider_call_policy": "provider_api_or_frozen_cache",
            "timestamp_policy": "relative_masked",
        },
        {
            "scenario_key": "recent_cross_asset",
            "scenario_label": "Recent",
            "provider": "poe",
            "model": "gpt-test",
            "seed": 11,
            "window_offset": 1,
            "frequency": "weekly",
            "start": "2025-05-01",
            "end": "2026-05-14",
            "max_periods": 12,
            "total_return": 0.02,
            "cache_policy": "live_or_cache_backed_raw_cache_ignored",
            "provider_call_policy": "provider_api_or_frozen_cache",
            "timestamp_policy": "relative_masked",
        },
    ]
    walk_rows = module._walk_forward_rows(rows)

    assert walk_rows[0]["seed_count"] == 2
    assert walk_rows[0]["window_offsets"] == "0,1"
    assert walk_rows[0]["return_std"] > 0
    assert walk_rows[0]["provider_call_policy"] == "provider_api_or_frozen_cache"


def test_classical_matrix_includes_non_llm_strong_baselines():
    module = _load_classical_matrix_module()

    assert set(module.CLASSICAL_BASELINES) == {
        "always_hold",
        "random",
        "buy_and_hold",
        "equal_weight",
        "naive_momentum",
        "mean_reversion",
        "risk_parity",
        "min_var",
        "markowitz_mvo",
    }
    assert module.CLASSICAL_BASELINES["buy_and_hold"]["strategy"] == "buy-and-hold"
    assert module.CLASSICAL_BASELINES["equal_weight"]["strategy"] == "equal-weight"
    assert module.CLASSICAL_BASELINES["risk_parity"]["strategy"] == "risk-parity"
    assert module.CLASSICAL_BASELINES["min_var"]["strategy"] == "min-var"
    assert module.CLASSICAL_BASELINES["markowitz_mvo"]["strategy"] == "markowitz-mvo"


def test_quality_decomposition_uses_three_benchmark_axes():
    module = _load_quality_decomposition_module()

    assert module.DIMENSIONS == (
        ("alpha_quality_score", "Alpha quality"),
        ("risk_discipline_score", "Risk discipline"),
        ("execution_robustness_score", "Execution robustness"),
    )
    assert len(module.INPUTS) == 4
