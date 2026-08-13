from datetime import datetime, timedelta
from pathlib import Path

from tradearena.core.trajectory import StepRecord, Trajectory
from tradearena.experiments import PaperExperimentConfig, run_paper_experiment
from tradearena.experiments.paper import (
    _annotate_contrarian_effects,
    _hallucination_calibration_rows,
    _language_collapse_control_rows,
    _noise_injection_robustness_rows,
)


def test_paper_experiment_writes_tables_and_charts(tmp_path: Path):
    result = run_paper_experiment(
        PaperExperimentConfig(
            output_dir=str(tmp_path / "paper"),
            symbols=("SYN", "ALT"),
            periods=12,
            seeds=(5,),
            include_stress=True,
            include_real_data=False,
            include_llm=False,
            include_model_matrix=False,
            include_statistical=False,
            include_synthetic_market_stress=False,
            include_rolling_windows=False,
            include_intraday_complex=False,
            include_intraday_llm_probe=False,
            include_risk_feedback_ablation=False,
            include_cot_free_ablation=False,
            include_noise_injection=False,
            include_contrarian_audit=False,
            include_hallucination_analysis=False,
        )
    )

    artifacts = result["artifacts"]
    required = [
        "metrics_csv",
        "metrics_md",
        "equity_csv",
        "execution_csv",
        "risk_csv",
        "summary_json",
    ]
    for key in required:
        path = Path(artifacts[key])
        assert path.exists()
        assert path.stat().st_size > 0

    charts_dir = Path(artifacts["charts_dir"])
    assert (charts_dir / "equity_curves.svg").exists()
    assert (charts_dir / "returns.svg").exists()
    assert (charts_dir / "execution_costs.svg").exists()
    assert (charts_dir / "risk_audit.svg").exists()
    assert (charts_dir / "aggregate_returns.svg").exists()
    assert (charts_dir / "aggregate_fill_rates.svg").exists()

    metrics = Path(artifacts["metrics_csv"]).read_text(encoding="utf-8")
    assert "analyst_ablation" in metrics
    assert "memory_ablation" in metrics
    assert "risk_sensitivity" in metrics
    assert "execution" in metrics


def test_noise_injection_rows_include_robustness_diagnostics():
    trajectory = _toy_llm_failure_trajectory()

    result = _noise_injection_robustness_rows({"llm_matrix_test_model_risk_aware": trajectory})

    assert result["event_rows"]
    assert result["summary_rows"]
    market_rows = [row for row in result["summary_rows"] if row["view"] == "market_fused"]
    assert {float(row["epsilon"]) for row in market_rows} == {0.0, 0.05, 0.10, 0.20}
    for row in market_rows:
        assert "ba_drop_from_clean" in row
        assert "rank_delta_retention" in row
        assert "robust_ba_075" in row
        assert "robust_signature" in row


def test_contrarian_effect_annotation_flags_false_audit_drift():
    rows = [
        {
            "model": "test-model",
            "feedback": "true",
            "late_intended_abs": 1.0,
            "total_return": 0.05,
            "max_drawdown": -0.10,
        },
        {
            "model": "test-model",
            "feedback": "contrarian",
            "late_intended_abs": 0.7,
            "total_return": 0.01,
            "max_drawdown": -0.16,
            "contrarian_conservative_shift": "",
        },
    ]

    annotated = _annotate_contrarian_effects(rows)
    contrarian = next(row for row in annotated if row["feedback"] == "contrarian")

    assert contrarian["contrarian_conservative_shift"] == 0.30000000000000004
    assert contrarian["return_delta_vs_true"] == -0.04
    assert contrarian["drawdown_delta_vs_true"] == -0.06
    assert contrarian["over_compliance_flag"] == 1
    assert contrarian["false_audit_harm_flag"] == 1
    assert contrarian["trust_calibration_failure"] == 1


def test_language_collapse_controls_separate_rank_from_lexical_repetition():
    trajectory = _toy_llm_failure_trajectory()

    rows = _language_collapse_control_rows({"llm_matrix_test_model_risk_aware": trajectory})

    assert rows
    plan_rows = [row for row in rows if row["view"] == "plan"]
    assert plan_rows
    assert "mean_ttr_delta" in plan_rows[0]
    assert "mean_entropy_delta" in plan_rows[0]
    assert "rank_contraction_without_lexical_collapse" in plan_rows[0]


def test_hallucination_calibration_computes_kappa_when_labels_exist(tmp_path: Path):
    annotation_path = tmp_path / "gold.csv"
    annotation_path.write_text(
        "case,step,proxy_label,annotator_a_label,annotator_b_label,adjudicated_label\n"
        "a,0,1,1,1,1\n"
        "a,1,0,0,0,0\n"
        "a,2,1,1,0,1\n",
        encoding="utf-8",
    )

    rows = _hallucination_calibration_rows([], str(annotation_path))

    assert rows[0]["status"] == "manual_labels_loaded"
    assert rows[0]["samples"] == 3
    assert rows[0]["cohen_kappa"] != ""
    assert rows[0]["iou"] == 1.0


def test_hallucination_calibration_omits_placeholder_without_labels(tmp_path: Path):
    annotation_path = tmp_path / "missing.csv"

    rows = _hallucination_calibration_rows([{"case": "a", "step": 0}], str(annotation_path))

    assert rows == []


def _toy_llm_failure_trajectory() -> Trajectory:
    trajectory = Trajectory(experiment_name="llm_matrix_test_model_risk_aware", seed=1)
    start = datetime(2024, 1, 1)
    equities = [
        100.0,
        103.0,
        106.0,
        108.0,
        107.0,
        106.0,
        104.0,
        99.0,
        96.0,
        98.0,
        101.0,
        103.0,
        102.0,
        100.0,
        97.0,
        94.0,
        95.0,
        97.0,
        99.0,
        100.0,
    ]
    for idx, equity in enumerate(equities):
        phase_text = "calm diversified normal regime"
        if idx in {4, 5, 6, 12, 13, 14}:
            phase_text = "fragile crowded pre failure risk narrowing"
        elif idx in {7, 8, 15}:
            phase_text = "drawdown loss defensive deleveraging"
        trajectory.append(
            StepRecord(
                timestamp=start + timedelta(days=idx),
                observation={"prices": {"SYN": 100.0 + idx, "ALT": 80.0 + idx * 0.5}},
                signals=[
                    {
                        "symbol": "SYN",
                        "score": 0.2,
                        "confidence": 0.8,
                        "rationale": phase_text,
                        "metadata": {"model": "test-model", "risk_notes": phase_text},
                    }
                ],
                decisions=[
                    {
                        "symbol": "SYN",
                        "side": "buy",
                        "target_weight": 0.2 if idx % 2 else 0.35,
                        "confidence": 0.8,
                        "rationale": phase_text,
                    }
                ],
                approved_decisions=[
                    {
                        "symbol": "SYN",
                        "side": "buy",
                        "target_weight": 0.2,
                        "confidence": 0.8,
                        "rationale": phase_text,
                    }
                ],
                orders=[],
                fills=[],
                portfolio={"cash": equity, "positions": {}, "last_prices": {"SYN": 100.0 + idx}, "equity": equity},
                execution_report={"total_slippage": 0.0, "rejected_orders": 0, "pending_orders": 0},
                risk_report={"clipped_count": 0, "blocked_count": 0},
                agent_trace={"reflect": {"note": phase_text}},
            )
        )
    return trajectory
