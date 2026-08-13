from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tradearena.agents.llm import _get_secret
from tradearena.core.serialization import to_jsonable, write_json
from tradearena.core.trajectory import Trajectory
from tradearena.experiments.reporting import (
    KEY_METRICS,
    write_artifacts,
    write_bar_chart,
    write_csv,
    write_line_chart,
    write_markdown_table,
)
from tradearena.factory import build_default_system


@dataclass(frozen=True)
class PaperExperimentConfig:
    output_dir: str = "outputs/tradearena_paper"
    symbols: tuple[str, ...] = ("SYN", "ALT", "DEF")
    periods: int = 120
    seeds: tuple[int, ...] = (3, 7, 11)
    include_stress: bool = True
    include_extended: bool = True
    include_real_data: bool = True
    real_data_dir: str = "data/real/yahoo_daily_2021_2026"
    real_symbols: tuple[str, ...] = ("GSPC", "BTC-USD", "ETH-USD")
    real_data_frequency: str = "weekly"
    real_data_start: str = "2021-05-01"
    real_data_end: str = "2026-05-14"
    include_llm: bool = True
    llm_model: str = "deepseek-v4-flash"
    llm_models: tuple[str, ...] = ("deepseek-v4-flash", "deepseek-v4-pro")
    include_model_matrix: bool = True
    model_matrix_models: tuple[str, ...] = ("gpt-5.5", "gemini-3.1-pro", "kimi-k2.5", "glm-5", "claude-opus-4.7")
    llm_cache_path: str = "data/llm_cache/deepseek_analyst.jsonl"
    llm_periods: int = 52
    include_statistical: bool = True
    statistical_seeds: tuple[int, ...] = tuple(range(1, 31))
    include_synthetic_market_stress: bool = True
    synthetic_stress_markets: int = 120
    include_rolling_windows: bool = True
    include_representation_analysis: bool = True
    include_hallucination_analysis: bool = True
    hallucination_annotation_path: str = "data/annotations/hallucination_gold.csv"
    include_memory_learning: bool = True
    include_intraday_complex: bool = True
    include_intraday_llm_probe: bool = False
    include_risk_feedback_ablation: bool = True
    include_cot_free_ablation: bool = True
    include_noise_injection: bool = True
    include_contrarian_audit: bool = True
    intraday_data_dir: str = "data/real/yahoo_intraday_1h_50"
    intraday_symbols: tuple[str, ...] = (
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "META",
        "GOOGL",
        "GOOG",
        "TSLA",
        "AVGO",
        "JPM",
        "V",
        "MA",
        "UNH",
        "XOM",
        "COST",
        "WMT",
        "HD",
        "PG",
        "JNJ",
        "ABBV",
        "BAC",
        "KO",
        "PEP",
        "CRM",
        "NFLX",
        "ORCL",
        "AMD",
        "CSCO",
        "MRK",
        "CVX",
        "TMO",
        "ACN",
        "LIN",
        "MCD",
        "IBM",
        "GE",
        "CAT",
        "DIS",
        "QCOM",
        "INTU",
        "AMAT",
        "TXN",
        "NOW",
        "ISRG",
        "PM",
        "NEE",
        "RTX",
        "SPGI",
        "GS",
        "HON",
        "LOW",
    )
    intraday_max_periods: int = 40
    intraday_llm_max_periods: int = 8
    intraday_llm_model: str = "deepseek-v4-pro"
    intraday_llm_models: tuple[str, ...] = ()
    intraday_llm_provider: str = "deepseek"


def run_paper_experiment(config: PaperExperimentConfig) -> dict[str, Any]:
    metrics_rows: list[dict[str, Any]] = []
    trajectories: dict[str, Trajectory] = {}
    raw_runs: dict[str, Any] = {
        "config": to_jsonable(config),
        "claim": "auditable risk feedback and representation trajectories reveal when LLM financial reasoning is aligning, drifting, or failing",
        "runs": {},
    }

    for seed in config.seeds:
        for group, cases in _experiment_cases(config.include_extended):
            for case in cases:
                case_name = f"{case['name']}_seed{seed}"
                trajectory, metrics = _run_case(config, seed, case_name, case)
                trajectories[case_name] = trajectory
                row = _metrics_row(case_name, group, seed, case["execution"], case["risk"], metrics)
                row.update({key: value for key, value in case.items() if key not in {"name", "strategy", "risk", "execution"}})
                metrics_rows.append(row)
                raw_runs[case_name] = {"metrics": metrics, "case": case, "metadata": trajectory.metadata}

    if config.include_stress:
        for seed in config.seeds:
            for stress in _stress_cases():
                case_name = f"{stress['name']}_seed{seed}"
                trajectory, metrics = _run_case(config, seed, case_name, stress)
                trajectories[case_name] = trajectory
                row = _metrics_row(case_name, "stress", seed, "realistic", "max-position", metrics)
                row.update({key: stress[key] for key in ("commission_bps", "slippage_bps", "participation_rate", "latency_steps", "market_impact")})
                metrics_rows.append(row)
                raw_runs[case_name] = {"metrics": metrics, "stress": stress, "metadata": trajectory.metadata}

    if config.include_real_data:
        if _real_data_available(config):
            for case in _real_market_cases():
                case_name = case["name"]
                trajectory, metrics = _run_case(config, 0, case_name, case, real_market=True)
                trajectories[case_name] = trajectory
                row = _metrics_row(case_name, "real_market", "historical", case["execution"], case["risk"], metrics)
                row.update({"data_source": "yahoo_finance", "frequency": config.real_data_frequency})
                metrics_rows.append(row)
                raw_runs[case_name] = {"metrics": metrics, "case": case, "metadata": trajectory.metadata}
        else:
            raw_runs["real_market_skipped"] = {
                "reason": "historical Yahoo Finance CSV files were not found",
                "data_dir": config.real_data_dir,
            }

    if config.include_llm:
        if _llm_available(config):
            for case in _llm_cases(config):
                case_name = case["name"]
                trajectory, metrics = _run_case(config, 0, case_name, case, real_market=True, llm_market=True)
                trajectories[case_name] = trajectory
                row = _metrics_row(case_name, "llm_real_market", "historical", case["execution"], case["risk"], metrics)
                row.update(
                    {
                        "data_source": "yahoo_finance",
                        "frequency": config.real_data_frequency,
                        "llm_model": case.get("llm_model", "deterministic"),
                    }
                )
                metrics_rows.append(row)
                raw_runs[case_name] = {"metrics": metrics, "case": case, "metadata": trajectory.metadata}
        else:
            raw_runs["llm_skipped"] = {
                "reason": "DEEPSEEK_API_KEY and cached direct-provider LLM responses were not available",
                "cache_path": config.llm_cache_path,
            }

    if config.include_model_matrix:
        if _poe_available(config):
            for case in _model_matrix_cases(config):
                case_name = case["name"]
                trajectory, metrics = _run_case(config, 0, case_name, case, real_market=True, llm_market=True)
                trajectories[case_name] = trajectory
                row = _metrics_row(case_name, "llm_model_matrix", "historical", case["execution"], case["risk"], metrics)
                row.update(
                    {
                        "data_source": "yahoo_finance",
                        "frequency": config.real_data_frequency,
                        "llm_provider": "poe",
                        "llm_model": case.get("llm_model", ""),
                    }
                )
                metrics_rows.append(row)
                raw_runs[case_name] = {"metrics": metrics, "case": case, "metadata": trajectory.metadata}
        else:
            raw_runs["model_matrix_skipped"] = {
                "reason": "cached Poe responses and POE_API_KEY were not available",
                "models": config.model_matrix_models,
                "cache_path": config.llm_cache_path,
            }

    aggregate_rows = _aggregate_rows(metrics_rows)
    metrics_rows.extend(aggregate_rows)
    raw_runs["aggregate"] = aggregate_rows

    artifact_paths = write_artifacts(config.output_dir, metrics_rows, trajectories, raw_runs)
    tables_dir = Path(config.output_dir) / "tables"
    if config.include_statistical:
        statistical_rows = _statistical_rows(config)
        write_csv(tables_dir / "statistical_significance.csv", statistical_rows)
        write_markdown_table(
            tables_dir / "statistical_significance.md",
            statistical_rows,
            [
                "case",
                "metric",
                "n",
                "mean",
                "std",
                "ci95_low",
                "ci95_high",
                "baseline",
                "paired_diff_mean",
                "paired_diff_ci95_low",
                "paired_diff_ci95_high",
            ],
        )
        raw_runs["statistical_significance"] = statistical_rows
        artifact_paths["statistical_significance_csv"] = str(tables_dir / "statistical_significance.csv")
        artifact_paths["statistical_significance_md"] = str(tables_dir / "statistical_significance.md")
    if config.include_synthetic_market_stress:
        stress = _synthetic_market_stress_rows(config)
        write_csv(tables_dir / "synthetic_market_stress.csv", stress["summary_rows"])
        write_markdown_table(
            tables_dir / "synthetic_market_stress.md",
            stress["summary_rows"],
            [
                "comparison",
                "regime",
                "metric",
                "n",
                "paired_diff_mean",
                "paired_diff_ci95_low",
                "paired_diff_ci95_high",
                "p_value",
                "win_rate",
            ],
        )
        write_csv(tables_dir / "synthetic_market_stress_pairs.csv", stress["pair_rows"])
        raw_runs["synthetic_market_stress"] = stress
        artifact_paths["synthetic_market_stress_csv"] = str(tables_dir / "synthetic_market_stress.csv")
        artifact_paths["synthetic_market_stress_md"] = str(tables_dir / "synthetic_market_stress.md")
        artifact_paths["synthetic_market_stress_pairs_csv"] = str(tables_dir / "synthetic_market_stress_pairs.csv")
    if config.include_rolling_windows and config.include_real_data and _real_data_available(config):
        rolling_rows = _rolling_window_rows(config)
        write_csv(tables_dir / "rolling_windows.csv", rolling_rows)
        write_markdown_table(
            tables_dir / "rolling_windows.md",
            rolling_rows,
            ["case", "window", "total_return", "sharpe", "max_drawdown", "execution_fill_rate", "rejected_order_count"],
        )
        raw_runs["rolling_windows"] = rolling_rows
        artifact_paths["rolling_windows_csv"] = str(tables_dir / "rolling_windows.csv")
        artifact_paths["rolling_windows_md"] = str(tables_dir / "rolling_windows.md")
    if config.include_representation_analysis:
        representation = _representation_rows(trajectories)
        if representation["shift_rows"]:
            write_csv(tables_dir / "embedding_shift.csv", representation["shift_rows"])
            write_markdown_table(
                tables_dir / "embedding_shift.md",
                representation["shift_rows"],
                [
                    "case",
                    "view",
                    "normal_n",
                    "pre_drawdown_n",
                    "drawdown_n",
                    "normal_to_pre_cosine_distance",
                    "normal_to_drawdown_cosine_distance",
                    "pre_to_drawdown_cosine_distance",
                    "early_warning_balanced_accuracy",
                ],
            )
            write_csv(tables_dir / "embedding_steps.csv", representation["step_rows"])
            write_csv(tables_dir / "embedding_manifold.csv", representation["manifold_rows"])
            write_markdown_table(
                tables_dir / "embedding_manifold.md",
                representation["manifold_rows"],
                [
                    "case",
                    "view",
                    "path_length",
                    "normal_step_distance",
                    "pre_step_distance",
                    "pre_to_normal_step_ratio",
                    "normal_effective_rank",
                    "pre_effective_rank",
                    "pre_nn_pre_rate",
                ],
            )
            if representation["robustness_rows"]:
                write_csv(tables_dir / "embedding_robustness.csv", representation["robustness_rows"])
                write_markdown_table(
                    tables_dir / "embedding_robustness.md",
                    representation["robustness_rows"],
                    [
                        "cohort",
                        "embedding",
                        "view",
                        "trajectories",
                        "anchors",
                        "pre_steps",
                        "mean_pre_shift",
                        "mean_pre_to_normal_step_ratio",
                        "mean_effective_rank_delta",
                        "rank_contraction_rate",
                        "acceleration_rate",
                    ],
                )
            if representation["language_control_rows"]:
                write_csv(tables_dir / "language_collapse_controls.csv", representation["language_control_rows"])
                write_markdown_table(
                    tables_dir / "language_collapse_controls.md",
                    representation["language_control_rows"],
                    [
                        "cohort",
                        "view",
                        "trajectories",
                        "anchors",
                        "mean_effective_rank_delta",
                        "rank_contraction_rate",
                        "mean_ttr_delta",
                        "mean_entropy_delta",
                        "rank_contraction_without_lexical_collapse",
                    ],
                )
            raw_runs["representation_analysis"] = representation
            artifact_paths["embedding_shift_csv"] = str(tables_dir / "embedding_shift.csv")
            artifact_paths["embedding_shift_md"] = str(tables_dir / "embedding_shift.md")
            artifact_paths["embedding_steps_csv"] = str(tables_dir / "embedding_steps.csv")
            artifact_paths["embedding_manifold_csv"] = str(tables_dir / "embedding_manifold.csv")
            artifact_paths["embedding_manifold_md"] = str(tables_dir / "embedding_manifold.md")
            if representation["robustness_rows"]:
                artifact_paths["embedding_robustness_csv"] = str(tables_dir / "embedding_robustness.csv")
                artifact_paths["embedding_robustness_md"] = str(tables_dir / "embedding_robustness.md")
            if representation["language_control_rows"]:
                artifact_paths["language_collapse_controls_csv"] = str(tables_dir / "language_collapse_controls.csv")
                artifact_paths["language_collapse_controls_md"] = str(tables_dir / "language_collapse_controls.md")
        adaptation = _llm_risk_adaptation_rows(trajectories)
        if adaptation["summary_rows"]:
            write_csv(tables_dir / "llm_risk_adaptation.csv", adaptation["summary_rows"])
            write_markdown_table(
                tables_dir / "llm_risk_adaptation.md",
                adaptation["summary_rows"],
                [
                    "case",
                    "model",
                    "risk_events",
                    "mean_intended_abs_before",
                    "mean_intended_abs_after",
                    "mean_abs_reduction",
                    "reduction_rate",
                    "next_clipped_or_blocked_rate",
                    "mean_next_risk_violations",
                ],
            )
            write_csv(tables_dir / "llm_risk_adaptation_events.csv", adaptation["event_rows"])
            raw_runs["llm_risk_adaptation"] = adaptation
            artifact_paths["llm_risk_adaptation_csv"] = str(tables_dir / "llm_risk_adaptation.csv")
            artifact_paths["llm_risk_adaptation_md"] = str(tables_dir / "llm_risk_adaptation.md")
            artifact_paths["llm_risk_adaptation_events_csv"] = str(tables_dir / "llm_risk_adaptation_events.csv")
    if config.include_hallucination_analysis:
        hallucination = _hallucination_risk_rows(trajectories, config.llm_cache_path, config.hallucination_annotation_path)
        if hallucination["summary_rows"]:
            write_csv(tables_dir / "hallucination_risk_correlation.csv", hallucination["summary_rows"])
            write_markdown_table(
                tables_dir / "hallucination_risk_correlation.md",
                hallucination["summary_rows"],
                [
                    "case",
                    "model",
                    "steps",
                    "mean_hallucination_proxy",
                    "high_proxy_steps",
                    "risk_gate_corr",
                    "risk_violation_corr",
                    "calibration_gap_corr",
                    "rejected_orders_corr",
                    "high_proxy_risk_gate_rate",
                    "low_proxy_risk_gate_rate",
                ],
            )
            write_csv(tables_dir / "hallucination_risk_steps.csv", hallucination["step_rows"])
            if hallucination.get("annotation_rows"):
                write_csv(tables_dir / "hallucination_annotation_sample.csv", hallucination["annotation_rows"])
                artifact_paths["hallucination_annotation_sample_csv"] = str(tables_dir / "hallucination_annotation_sample.csv")
            if hallucination.get("calibration_rows"):
                write_csv(tables_dir / "hallucination_annotation_calibration.csv", hallucination["calibration_rows"])
                write_markdown_table(
                    tables_dir / "hallucination_annotation_calibration.md",
                    hallucination["calibration_rows"],
                    ["status", "samples", "annotators", "agreement", "cohen_kappa", "iou", "notes"],
                )
                artifact_paths["hallucination_annotation_calibration_csv"] = str(
                    tables_dir / "hallucination_annotation_calibration.csv"
                )
                artifact_paths["hallucination_annotation_calibration_md"] = str(
                    tables_dir / "hallucination_annotation_calibration.md"
                )
            raw_runs["hallucination_risk_correlation"] = hallucination
            artifact_paths["hallucination_risk_correlation_csv"] = str(tables_dir / "hallucination_risk_correlation.csv")
            artifact_paths["hallucination_risk_correlation_md"] = str(tables_dir / "hallucination_risk_correlation.md")
            artifact_paths["hallucination_risk_steps_csv"] = str(tables_dir / "hallucination_risk_steps.csv")
    if config.include_model_matrix:
        matrix_metric_rows = [row for row in metrics_rows if row.get("group") == "llm_model_matrix"]
        if matrix_metric_rows:
            write_csv(tables_dir / "model_matrix_metrics.csv", matrix_metric_rows)
            write_markdown_table(
                tables_dir / "model_matrix_metrics.md",
                matrix_metric_rows,
                [
                    "case",
                    "llm_model",
                    "total_return",
                    "sharpe",
                    "max_drawdown",
                    "risk_clipped_decisions",
                    "rejected_order_count",
                ],
            )
            artifact_paths["model_matrix_metrics_csv"] = str(tables_dir / "model_matrix_metrics.csv")
            artifact_paths["model_matrix_metrics_md"] = str(tables_dir / "model_matrix_metrics.md")
        matrix_adaptation = _llm_risk_adaptation_rows(
            {name: trajectory for name, trajectory in trajectories.items() if name.startswith("llm_matrix_")}
        )
        if matrix_adaptation["summary_rows"]:
            write_csv(tables_dir / "model_matrix_risk_adaptation.csv", matrix_adaptation["summary_rows"])
            write_markdown_table(
                tables_dir / "model_matrix_risk_adaptation.md",
                matrix_adaptation["summary_rows"],
                [
                    "case",
                    "model",
                    "risk_events",
                    "mean_intended_abs_before",
                    "mean_intended_abs_after",
                    "mean_abs_reduction",
                    "reduction_rate",
                    "next_clipped_or_blocked_rate",
                    "mean_next_risk_violations",
                ],
            )
            write_csv(tables_dir / "model_matrix_risk_adaptation_events.csv", matrix_adaptation["event_rows"])
            raw_runs["model_matrix_risk_adaptation"] = matrix_adaptation
            artifact_paths["model_matrix_risk_adaptation_csv"] = str(tables_dir / "model_matrix_risk_adaptation.csv")
            artifact_paths["model_matrix_risk_adaptation_md"] = str(tables_dir / "model_matrix_risk_adaptation.md")
            artifact_paths["model_matrix_risk_adaptation_events_csv"] = str(tables_dir / "model_matrix_risk_adaptation_events.csv")
        matrix_feedback = _frontier_feedback_matrix_rows(config)
        if matrix_feedback["summary_rows"]:
            write_csv(tables_dir / "model_matrix_feedback.csv", matrix_feedback["summary_rows"])
            write_markdown_table(
                tables_dir / "model_matrix_feedback.md",
                matrix_feedback["summary_rows"],
                [
                    "model",
                    "feedback",
                    "total_return",
                    "max_drawdown",
                    "risk_clipped_decisions",
                    "mean_intended_abs",
                    "late_intended_abs",
                    "intent_drift",
                    "late_calibration_gap",
                ],
            )
            write_csv(tables_dir / "model_matrix_feedback_steps.csv", matrix_feedback["step_rows"])
            write_csv(tables_dir / "model_matrix_feedback_manifold.csv", matrix_feedback["manifold_rows"])
            write_markdown_table(
                tables_dir / "model_matrix_feedback_manifold.md",
                matrix_feedback["manifold_rows"],
                [
                    "model",
                    "feedback",
                    "view",
                    "path_length_per_step",
                    "pre_to_normal_step_ratio",
                    "effective_rank_delta",
                    "step_distance_cv",
                ],
            )
            feedback_effects = _frontier_feedback_effect_rows(matrix_feedback["summary_rows"])
            feedback_learning = _frontier_feedback_learning_rows(matrix_feedback["step_rows"])
            write_csv(tables_dir / "model_matrix_feedback_effects.csv", feedback_effects)
            write_markdown_table(
                tables_dir / "model_matrix_feedback_effects.md",
                feedback_effects,
                [
                    "model",
                    "return_delta_true_hidden",
                    "drawdown_improvement_true_hidden",
                    "late_gap_reduction_true_hidden",
                    "return_delta_true_placebo",
                    "drawdown_improvement_true_placebo",
                    "late_gap_reduction_true_placebo",
                ],
            )
            write_csv(tables_dir / "model_matrix_feedback_learning.csv", feedback_learning)
            write_markdown_table(
                tables_dir / "model_matrix_feedback_learning.md",
                feedback_learning,
                [
                    "model",
                    "feedback",
                    "early_risk_gate_rate",
                    "late_risk_gate_rate",
                    "risk_gate_delta",
                    "early_calibration_score",
                    "late_calibration_score",
                    "calibration_delta",
                    "late_calibration_gap",
                ],
            )
            _write_frontier_feedback_charts(Path(config.output_dir) / "charts", matrix_feedback["summary_rows"], feedback_learning)
            raw_runs["model_matrix_feedback"] = matrix_feedback
            raw_runs["model_matrix_feedback_effects"] = feedback_effects
            raw_runs["model_matrix_feedback_learning"] = feedback_learning
            artifact_paths["model_matrix_feedback_csv"] = str(tables_dir / "model_matrix_feedback.csv")
            artifact_paths["model_matrix_feedback_md"] = str(tables_dir / "model_matrix_feedback.md")
            artifact_paths["model_matrix_feedback_steps_csv"] = str(tables_dir / "model_matrix_feedback_steps.csv")
            artifact_paths["model_matrix_feedback_manifold_csv"] = str(tables_dir / "model_matrix_feedback_manifold.csv")
            artifact_paths["model_matrix_feedback_manifold_md"] = str(tables_dir / "model_matrix_feedback_manifold.md")
            artifact_paths["model_matrix_feedback_effects_csv"] = str(tables_dir / "model_matrix_feedback_effects.csv")
            artifact_paths["model_matrix_feedback_effects_md"] = str(tables_dir / "model_matrix_feedback_effects.md")
            artifact_paths["model_matrix_feedback_learning_csv"] = str(tables_dir / "model_matrix_feedback_learning.csv")
            artifact_paths["model_matrix_feedback_learning_md"] = str(tables_dir / "model_matrix_feedback_learning.md")
            artifact_paths["frontier_feedback_returns_svg"] = str(Path(config.output_dir) / "charts" / "frontier_feedback_returns.svg")
            artifact_paths["frontier_feedback_late_gap_svg"] = str(Path(config.output_dir) / "charts" / "frontier_feedback_late_gap.svg")
            artifact_paths["frontier_feedback_true_learning_svg"] = str(Path(config.output_dir) / "charts" / "frontier_feedback_true_learning.svg")
    if config.include_cot_free_ablation:
        if _poe_available(config, _frontier_probe_models(config)):
            cot_free = _cot_free_ablation_rows(config)
            if cot_free["summary_rows"]:
                write_csv(tables_dir / "cot_free_ablation.csv", cot_free["summary_rows"])
                write_markdown_table(
                    tables_dir / "cot_free_ablation.md",
                    cot_free["summary_rows"],
                    [
                        "model",
                        "mode",
                        "total_return",
                        "max_drawdown",
                        "language_effective_rank_delta",
                        "intent_effective_rank_delta",
                        "language_pre_to_normal_step_ratio",
                        "intent_pre_to_normal_step_ratio",
                        "language_early_warning_ba",
                        "intent_early_warning_ba",
                    ],
                )
                write_csv(tables_dir / "cot_free_ablation_steps.csv", cot_free["step_rows"])
                write_csv(tables_dir / "cot_free_ablation_manifold.csv", cot_free["manifold_rows"])
                write_markdown_table(
                    tables_dir / "cot_free_ablation_manifold.md",
                    cot_free["manifold_rows"],
                    [
                        "model",
                        "mode",
                        "view",
                        "path_length_per_step",
                        "pre_to_normal_step_ratio",
                        "normal_effective_rank",
                        "pre_effective_rank",
                        "effective_rank_delta",
                    ],
                )
                _write_cot_free_chart(Path(config.output_dir) / "charts", cot_free["summary_rows"])
                raw_runs["cot_free_ablation"] = cot_free
                artifact_paths["cot_free_ablation_csv"] = str(tables_dir / "cot_free_ablation.csv")
                artifact_paths["cot_free_ablation_md"] = str(tables_dir / "cot_free_ablation.md")
                artifact_paths["cot_free_ablation_steps_csv"] = str(tables_dir / "cot_free_ablation_steps.csv")
                artifact_paths["cot_free_ablation_manifold_csv"] = str(tables_dir / "cot_free_ablation_manifold.csv")
                artifact_paths["cot_free_ablation_manifold_md"] = str(tables_dir / "cot_free_ablation_manifold.md")
                artifact_paths["cot_free_rank_delta_svg"] = str(Path(config.output_dir) / "charts" / "cot_free_rank_delta.svg")
        else:
            raw_runs["cot_free_ablation_skipped"] = {
                "reason": "cached Poe responses and POE_API_KEY were not available",
                "models": _frontier_probe_models(config),
                "cache_path": config.llm_cache_path,
            }
    if config.include_noise_injection:
        noise = _noise_injection_robustness_rows(trajectories)
        if noise["summary_rows"]:
            write_csv(tables_dir / "noise_injection_robustness.csv", noise["summary_rows"])
            write_markdown_table(
                tables_dir / "noise_injection_robustness.md",
                noise["summary_rows"],
                [
                    "epsilon",
                    "view",
                    "trajectories",
                    "anchors",
                    "mean_pre_shift",
                    "mean_effective_rank_delta",
                    "rank_contraction_rate",
                    "mean_early_warning_ba",
                    "ba_drop_from_clean",
                    "rank_delta_retention",
                    "robust_ba_075",
                    "robust_signature",
                ],
            )
            write_csv(tables_dir / "noise_injection_events.csv", noise["event_rows"])
            _write_noise_chart(Path(config.output_dir) / "charts", noise["summary_rows"])
            raw_runs["noise_injection_robustness"] = noise
            artifact_paths["noise_injection_robustness_csv"] = str(tables_dir / "noise_injection_robustness.csv")
            artifact_paths["noise_injection_robustness_md"] = str(tables_dir / "noise_injection_robustness.md")
            artifact_paths["noise_injection_events_csv"] = str(tables_dir / "noise_injection_events.csv")
            artifact_paths["noise_injection_ba_svg"] = str(Path(config.output_dir) / "charts" / "noise_injection_ba.svg")
    if config.include_contrarian_audit:
        if _poe_available(config, _frontier_probe_models(config)):
            contrarian = _contrarian_audit_rows(config)
            if contrarian["summary_rows"]:
                write_csv(tables_dir / "contrarian_audit.csv", contrarian["summary_rows"])
                write_markdown_table(
                    tables_dir / "contrarian_audit.md",
                    contrarian["summary_rows"],
                    [
                        "model",
                        "feedback",
                        "total_return",
                        "max_drawdown",
                        "mean_intended_abs",
                        "late_intended_abs",
                        "intent_drift",
                        "mean_calibration_score",
                        "late_calibration_score",
                        "contrarian_conservative_shift",
                        "return_delta_vs_true",
                        "drawdown_delta_vs_true",
                        "over_compliance_flag",
                        "false_audit_harm_flag",
                        "trust_calibration_failure",
                    ],
                )
                write_csv(tables_dir / "contrarian_audit_steps.csv", contrarian["step_rows"])
                write_csv(tables_dir / "contrarian_audit_manifold.csv", contrarian["manifold_rows"])
                _write_contrarian_chart(Path(config.output_dir) / "charts", contrarian["summary_rows"])
                raw_runs["contrarian_audit"] = contrarian
                artifact_paths["contrarian_audit_csv"] = str(tables_dir / "contrarian_audit.csv")
                artifact_paths["contrarian_audit_md"] = str(tables_dir / "contrarian_audit.md")
                artifact_paths["contrarian_audit_steps_csv"] = str(tables_dir / "contrarian_audit_steps.csv")
                artifact_paths["contrarian_audit_manifold_csv"] = str(tables_dir / "contrarian_audit_manifold.csv")
                artifact_paths["contrarian_intent_shift_svg"] = str(Path(config.output_dir) / "charts" / "contrarian_intent_shift.svg")
        else:
            raw_runs["contrarian_audit_skipped"] = {
                "reason": "cached Poe responses and POE_API_KEY were not available",
                "models": _frontier_probe_models(config),
                "cache_path": config.llm_cache_path,
            }
    if config.include_memory_learning:
        learning = _memory_learning_rows(trajectories)
        if learning["summary_rows"]:
            write_csv(tables_dir / "memory_learning_curve.csv", learning["summary_rows"])
            write_markdown_table(
                tables_dir / "memory_learning_curve.md",
                learning["summary_rows"],
                [
                    "case",
                    "model",
                    "steps",
                    "early_risk_gate_rate",
                    "late_risk_gate_rate",
                    "risk_gate_rate_delta",
                    "early_calibration_score",
                    "late_calibration_score",
                    "calibration_score_delta",
                    "early_calibration_gap",
                    "late_calibration_gap",
                ],
            )
            write_csv(tables_dir / "memory_learning_steps.csv", learning["step_rows"])
            raw_runs["memory_learning"] = learning
            artifact_paths["memory_learning_curve_csv"] = str(tables_dir / "memory_learning_curve.csv")
            artifact_paths["memory_learning_curve_md"] = str(tables_dir / "memory_learning_curve.md")
            artifact_paths["memory_learning_steps_csv"] = str(tables_dir / "memory_learning_steps.csv")
    if config.include_intraday_complex and _intraday_data_available(config):
        intraday = _intraday_complex_rows(config)
        write_csv(tables_dir / "intraday_complex.csv", intraday["case_rows"])
        write_markdown_table(
            tables_dir / "intraday_complex.md",
            intraday["case_rows"],
            [
                "case",
                "model",
                "symbols",
                "steps",
                "total_return",
                "sharpe",
                "max_drawdown",
                "risk_clipped_decisions",
                "correlation_mean_abs",
                "effective_assets",
                "mean_herfindahl",
            ],
        )
        write_csv(tables_dir / "intraday_correlation.csv", intraday["correlation_rows"])
        if intraday.get("blind_spot_rows"):
            write_csv(tables_dir / "intraday_blind_spots.csv", intraday["blind_spot_rows"])
            write_markdown_table(
                tables_dir / "intraday_blind_spots.md",
                intraday["blind_spot_rows"],
                [
                    "case",
                    "model",
                    "step",
                    "pair",
                    "correlation",
                    "combined_intended_weight",
                    "approved_pair_weight",
                    "clipped_count",
                    "rationale_theme",
                ],
            )
        raw_runs["intraday_complex"] = intraday
        artifact_paths["intraday_complex_csv"] = str(tables_dir / "intraday_complex.csv")
        artifact_paths["intraday_complex_md"] = str(tables_dir / "intraday_complex.md")
        artifact_paths["intraday_correlation_csv"] = str(tables_dir / "intraday_correlation.csv")
        if intraday.get("blind_spot_rows"):
            artifact_paths["intraday_blind_spots_csv"] = str(tables_dir / "intraday_blind_spots.csv")
            artifact_paths["intraday_blind_spots_md"] = str(tables_dir / "intraday_blind_spots.md")
    if config.include_risk_feedback_ablation:
        ablation = _risk_feedback_ablation_rows(config)
        if ablation["summary_rows"]:
            write_csv(tables_dir / "risk_feedback_ablation.csv", ablation["summary_rows"])
            write_markdown_table(
                tables_dir / "risk_feedback_ablation.md",
                ablation["summary_rows"],
                [
                    "case",
                    "feedback",
                    "total_return",
                    "risk_clipped_decisions",
                    "mean_intended_abs",
                    "late_intended_abs",
                    "mean_calibration_gap",
                    "late_calibration_gap",
                    "intent_drift",
                ],
            )
            write_csv(tables_dir / "risk_feedback_intent_steps.csv", ablation["step_rows"])
            if ablation.get("manifold_rows"):
                write_csv(tables_dir / "risk_feedback_manifold.csv", ablation["manifold_rows"])
                write_markdown_table(
                    tables_dir / "risk_feedback_manifold.md",
                    ablation["manifold_rows"],
                    [
                        "feedback",
                        "view",
                        "path_length_per_step",
                        "pre_to_normal_step_ratio",
                        "effective_rank_delta",
                        "step_distance_cv",
                        "turn_rate",
                    ],
                )
            raw_runs["risk_feedback_ablation"] = ablation
            artifact_paths["risk_feedback_ablation_csv"] = str(tables_dir / "risk_feedback_ablation.csv")
            artifact_paths["risk_feedback_ablation_md"] = str(tables_dir / "risk_feedback_ablation.md")
            artifact_paths["risk_feedback_intent_steps_csv"] = str(tables_dir / "risk_feedback_intent_steps.csv")
            if ablation.get("manifold_rows"):
                artifact_paths["risk_feedback_manifold_csv"] = str(tables_dir / "risk_feedback_manifold.csv")
                artifact_paths["risk_feedback_manifold_md"] = str(tables_dir / "risk_feedback_manifold.md")
    if (
        config.include_statistical
        or config.include_synthetic_market_stress
        or config.include_rolling_windows
        or config.include_representation_analysis
        or config.include_hallucination_analysis
        or config.include_model_matrix
        or config.include_memory_learning
        or config.include_intraday_complex
        or config.include_risk_feedback_ablation
        or config.include_cot_free_ablation
        or config.include_noise_injection
        or config.include_contrarian_audit
    ):
        raw_runs["artifacts"] = artifact_paths
        write_json(Path(config.output_dir) / "summary.json", raw_runs)
    raw_runs["artifacts"] = artifact_paths
    return raw_runs


def _experiment_cases(include_extended: bool) -> list[tuple[str, list[dict[str, Any]]]]:
    groups = [("core", _core_cases())]
    if include_extended:
        groups.extend(
            [
                ("execution", _execution_cases()),
                ("risk_sensitivity", _risk_sensitivity_cases()),
                ("analyst_ablation", _analyst_ablation_cases()),
                ("memory_ablation", _memory_ablation_cases()),
            ]
        )
    return groups


def _core_cases() -> list[dict[str, str]]:
    return [
        {"name": "risk_aware_realistic_agent", "strategy": "signal-weighted", "risk": "max-position", "execution": "realistic"},
        {"name": "buy_and_hold_realistic", "strategy": "buy-and-hold", "risk": "max-position", "execution": "realistic"},
        {"name": "ideal_execution_ablation", "strategy": "signal-weighted", "risk": "max-position", "execution": "ideal"},
        {"name": "no_risk_ablation", "strategy": "signal-weighted", "risk": "none", "execution": "realistic"},
    ]


def _execution_cases() -> list[dict[str, Any]]:
    return [
        {"name": "execution_ideal", "strategy": "signal-weighted", "risk": "max-position", "execution": "ideal"},
        {"name": "execution_realistic_default", "strategy": "signal-weighted", "risk": "max-position", "execution": "realistic"},
        {
            "name": "execution_constrained_latency",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "slippage_bps": 6.0,
            "participation_rate": 0.02,
            "latency_steps": 2,
            "market_impact": 0.25,
        },
    ]


def _risk_sensitivity_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "risk_strict_20pct",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "max_position_weight": 0.20,
            "max_turnover": 0.45,
        },
        {
            "name": "risk_default_35pct",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "max_position_weight": 0.35,
            "max_turnover": 0.75,
        },
        {
            "name": "risk_loose_50pct",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "max_position_weight": 0.50,
            "max_turnover": 1.20,
        },
    ]


def _analyst_ablation_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "analyst_momentum_only",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum",),
        },
        {
            "name": "analyst_macro_news_only",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("macro-news",),
        },
        {
            "name": "analyst_full_stack",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum", "macro-news"),
        },
    ]


def _memory_ablation_cases() -> list[dict[str, Any]]:
    return [
        {"name": "memory_blind_signal_agent", "strategy": "signal-weighted", "risk": "max-position", "execution": "realistic"},
        {"name": "memory_aware_signal_agent", "strategy": "memory-aware", "risk": "max-position", "execution": "realistic"},
    ]


def _stress_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "stress_high_cost",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "commission_bps": 8.0,
            "slippage_bps": 12.0,
            "participation_rate": 0.05,
            "latency_steps": 1,
            "market_impact": 0.2,
        },
        {
            "name": "stress_low_liquidity",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "commission_bps": 1.0,
            "slippage_bps": 4.0,
            "participation_rate": 0.005,
            "latency_steps": 1,
            "market_impact": 0.35,
        },
        {
            "name": "stress_latency",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "commission_bps": 1.0,
            "slippage_bps": 5.0,
            "participation_rate": 0.03,
            "latency_steps": 3,
            "market_impact": 0.2,
        },
        {
            "name": "stress_fragile_microstructure",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "commission_bps": 4.0,
            "slippage_bps": 10.0,
            "participation_rate": 0.01,
            "latency_steps": 2,
            "market_impact": 0.5,
        },
    ]


def _real_market_cases() -> list[dict[str, Any]]:
    return [
        {"name": "real_market_risk_aware", "strategy": "signal-weighted", "risk": "max-position", "execution": "realistic"},
        {"name": "real_market_buy_and_hold", "strategy": "buy-and-hold", "risk": "max-position", "execution": "realistic"},
        {"name": "real_market_ideal_execution", "strategy": "signal-weighted", "risk": "max-position", "execution": "ideal"},
        {"name": "real_market_no_risk", "strategy": "signal-weighted", "risk": "none", "execution": "realistic"},
    ]


def _llm_cases(config: PaperExperimentConfig) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = [
        {
            "name": "deterministic_recent_real_market",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum", "macro-news"),
        }
    ]
    for model in config.llm_models or (config.llm_model,):
        slug = _model_slug(model)
        cases.extend(
            [
                {
                    "name": f"llm_{slug}_risk_aware",
                    "strategy": "signal-weighted",
                    "risk": "max-position",
                    "execution": "realistic",
                    "analyst_names": ("deepseek-llm",),
                    "llm_model": model,
                },
                {
                    "name": f"llm_{slug}_no_risk",
                    "strategy": "signal-weighted",
                    "risk": "none",
                    "execution": "realistic",
                    "analyst_names": ("deepseek-llm",),
                    "llm_model": model,
                },
            ]
        )
    return cases


def _model_matrix_cases(config: PaperExperimentConfig) -> list[dict[str, Any]]:
    cases = []
    for model in config.model_matrix_models:
        cases.append(
            {
                "name": f"llm_matrix_{_model_slug(model)}_risk_aware",
                "strategy": "signal-weighted",
                "risk": "max-position",
                "execution": "realistic",
                "analyst_names": ("poe-llm",),
                "llm_model": model,
            }
        )
    return cases


def _model_slug(model: str) -> str:
    return model.replace("deepseek-", "").replace("-", "_").replace(".", "_")


def _real_data_available(config: PaperExperimentConfig) -> bool:
    data_dir = Path(config.real_data_dir)
    return all((data_dir / f"{_safe_symbol(symbol)}_Daily_2021_2026.csv").exists() for symbol in config.real_symbols)


def _intraday_data_available(config: PaperExperimentConfig) -> bool:
    data_dir = Path(config.intraday_data_dir)
    return all((data_dir / f"{_safe_symbol(symbol)}_Hourly_1h.csv").exists() for symbol in config.intraday_symbols)


def _llm_available(config: PaperExperimentConfig) -> bool:
    return bool(_get_secret("DEEPSEEK_API_KEY")) or Path(config.llm_cache_path).exists()


def _poe_available(config: PaperExperimentConfig, models: tuple[str, ...] | None = None) -> bool:
    if _get_secret("POE_API_KEY"):
        return True
    if not Path(config.llm_cache_path).exists():
        return False
    cache_text = Path(config.llm_cache_path).read_text(encoding="utf-8", errors="ignore")
    required_models = models or config.model_matrix_models
    return all(f"poe:{model}:" in cache_text for model in required_models)


def _statistical_rows(config: PaperExperimentConfig) -> list[dict[str, Any]]:
    cases = [
        {"name": "risk_aware_realistic_agent", "strategy": "signal-weighted", "risk": "max-position", "execution": "realistic"},
        {"name": "buy_and_hold_realistic", "strategy": "buy-and-hold", "risk": "max-position", "execution": "realistic"},
        {"name": "ideal_execution_ablation", "strategy": "signal-weighted", "risk": "max-position", "execution": "ideal"},
        {"name": "no_risk_ablation", "strategy": "signal-weighted", "risk": "none", "execution": "realistic"},
        {
            "name": "stress_latency",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "slippage_bps": 5.0,
            "participation_rate": 0.03,
            "latency_steps": 3,
            "market_impact": 0.2,
        },
    ]
    per_case: dict[str, list[dict[str, Any]]] = {case["name"]: [] for case in cases}
    for seed in config.statistical_seeds:
        for case in cases:
            _, metrics = _run_case(config, seed, f"{case['name']}_stat_seed{seed}", case)
            per_case[case["name"]].append(metrics)

    rows: list[dict[str, Any]] = []
    baseline = "buy_and_hold_realistic"
    metrics_to_report = ("total_return", "sharpe", "max_drawdown", "execution_fill_rate", "total_slippage_cost")
    for case in cases:
        case_name = case["name"]
        for metric in metrics_to_report:
            values = [float(item[metric]) for item in per_case[case_name] if metric in item]
            summary = _sample_summary(values)
            row = {
                "case": case_name,
                "metric": metric,
                **summary,
                "baseline": "",
                "paired_diff_mean": "",
                "paired_diff_ci95_low": "",
                "paired_diff_ci95_high": "",
            }
            if case_name != baseline and len(per_case[case_name]) == len(per_case[baseline]):
                diffs = [
                    float(item[metric]) - float(base[metric])
                    for item, base in zip(per_case[case_name], per_case[baseline], strict=True)
                    if metric in item and metric in base
                ]
                diff_summary = _sample_summary(diffs)
                row.update(
                    {
                        "baseline": baseline,
                        "paired_diff_mean": diff_summary["mean"],
                        "paired_diff_ci95_low": diff_summary["ci95_low"],
                        "paired_diff_ci95_high": diff_summary["ci95_high"],
                    }
                )
            rows.append(row)
    return rows


def _synthetic_market_stress_rows(config: PaperExperimentConfig) -> dict[str, list[dict[str, Any]]]:
    cases = [
        {"name": "risk_aware", "strategy": "signal-weighted", "risk": "max-position", "execution": "realistic"},
        {"name": "buy_and_hold", "strategy": "buy-and-hold", "risk": "max-position", "execution": "realistic"},
        {"name": "no_risk", "strategy": "signal-weighted", "risk": "none", "execution": "realistic"},
    ]
    pair_rows: list[dict[str, Any]] = []
    per_market: dict[tuple[int, str], dict[str, Any]] = {}
    market_count = max(1, int(config.synthetic_stress_markets))
    for market_id in range(1, market_count + 1):
        regime = _synthetic_regime(market_id)
        seed = 10_000 + market_id
        for case in cases:
            _, metrics = _run_case(
                config,
                seed,
                f"synthetic_stress_{case['name']}_{market_id}",
                {**case, **regime},
            )
            per_market[(market_id, case["name"])] = metrics
        for comparison, left, right in (
            ("risk_aware_vs_buy_and_hold", "risk_aware", "buy_and_hold"),
            ("risk_aware_vs_no_risk", "risk_aware", "no_risk"),
        ):
            left_metrics = per_market[(market_id, left)]
            right_metrics = per_market[(market_id, right)]
            pair_rows.append(
                {
                    "market_id": market_id,
                    "comparison": comparison,
                    "regime": regime["synthetic_regime"],
                    "volatility_state": regime["volatility_state"],
                    "tail_state": regime["tail_state"],
                    "seed": seed,
                    "left": left,
                    "right": right,
                    "left_total_return": left_metrics.get("total_return", 0.0),
                    "right_total_return": right_metrics.get("total_return", 0.0),
                    "diff_total_return": float(left_metrics.get("total_return", 0.0)) - float(right_metrics.get("total_return", 0.0)),
                    "left_max_drawdown": left_metrics.get("max_drawdown", 0.0),
                    "right_max_drawdown": right_metrics.get("max_drawdown", 0.0),
                    "diff_max_drawdown": float(left_metrics.get("max_drawdown", 0.0)) - float(right_metrics.get("max_drawdown", 0.0)),
                    "left_fill_rate": left_metrics.get("execution_fill_rate", 0.0),
                    "right_fill_rate": right_metrics.get("execution_fill_rate", 0.0),
                    "diff_execution_fill_rate": float(left_metrics.get("execution_fill_rate", 0.0)) - float(right_metrics.get("execution_fill_rate", 0.0)),
                    "left_rejected_orders": left_metrics.get("rejected_order_count", 0.0),
                    "right_rejected_orders": right_metrics.get("rejected_order_count", 0.0),
                    "diff_rejected_order_count": float(left_metrics.get("rejected_order_count", 0.0)) - float(right_metrics.get("rejected_order_count", 0.0)),
                }
            )

    summary_rows: list[dict[str, Any]] = []
    for comparison in ("risk_aware_vs_buy_and_hold", "risk_aware_vs_no_risk"):
        comparison_rows = [row for row in pair_rows if row["comparison"] == comparison]
        groups: list[tuple[str, list[dict[str, Any]]]] = [("all", comparison_rows)]
        groups.extend(
            (f"volatility:{state}", [row for row in comparison_rows if row["volatility_state"] == state])
            for state in _ordered_unique(row["volatility_state"] for row in comparison_rows)
        )
        groups.extend(
            (f"tail:{state}", [row for row in comparison_rows if row["tail_state"] == state])
            for state in _ordered_unique(row["tail_state"] for row in comparison_rows)
        )
        for regime, subset in groups:
            for metric in ("total_return", "max_drawdown", "execution_fill_rate", "rejected_order_count"):
                diffs = [float(row[f"diff_{metric}"]) for row in subset]
                stats = _paired_test_summary(diffs)
                summary_rows.append(
                    {
                        "comparison": comparison,
                        "regime": regime,
                        "metric": metric,
                        **stats,
                    }
                )
    return {"summary_rows": summary_rows, "pair_rows": pair_rows}


def _synthetic_regime(market_id: int) -> dict[str, Any]:
    volatility_states = (
        ("calm", 0.65),
        ("baseline", 1.0),
        ("volatile", 1.8),
        ("crisis", 2.7),
    )
    tail_states = (
        ("gaussian", None, 0.0, 0.0),
        ("student_t", 4, 0.0, 0.0),
        ("jump", None, 0.045, 0.045),
        ("student_t_jump", 5, 0.035, 0.035),
    )
    trend_states = (
        ("positive", 1.0),
        ("flat", 0.15),
        ("negative", -0.35),
    )
    vol_name, vol_scale = volatility_states[(market_id - 1) % len(volatility_states)]
    tail_name, tail_df, jump_probability, jump_scale = tail_states[((market_id - 1) // len(volatility_states)) % len(tail_states)]
    trend_name, trend_scale = trend_states[((market_id - 1) // (len(volatility_states) * len(tail_states))) % len(trend_states)]
    return {
        "synthetic_regime": f"{vol_name}_{tail_name}_{trend_name}",
        "volatility_state": vol_name,
        "tail_state": tail_name,
        "trend_state": trend_name,
        "synthetic_volatility_scale": vol_scale,
        "synthetic_trend_scale": trend_scale,
        "synthetic_tail_df": tail_df,
        "synthetic_jump_probability": jump_probability,
        "synthetic_jump_scale": jump_scale,
        "synthetic_seasonal_scale": 1.0 + 0.1 * ((market_id % 5) - 2),
        "synthetic_macro_scale": 1.0 + 0.08 * ((market_id % 7) - 3),
    }


def _paired_test_summary(diffs: list[float]) -> dict[str, Any]:
    summary = _sample_summary(diffs)
    n = int(summary["n"])
    if n < 2:
        p_value = 1.0
    else:
        std = float(summary["std"])
        t_stat = 0.0 if std == 0.0 else float(summary["mean"]) / (std / math.sqrt(n))
        p_value = 2.0 * (1.0 - _normal_cdf(abs(t_stat)))
    wins = sum(1 for value in diffs if value > 0.0)
    summary.update(
        {
            "paired_diff_mean": summary.pop("mean"),
            "paired_diff_std": summary.pop("std"),
            "paired_diff_ci95_low": summary.pop("ci95_low"),
            "paired_diff_ci95_high": summary.pop("ci95_high"),
            "p_value": max(0.0, min(1.0, p_value)),
            "win_rate": wins / n if n else "",
        }
    )
    return summary


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _ordered_unique(values: Any) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _rolling_window_rows(config: PaperExperimentConfig) -> list[dict[str, Any]]:
    windows = (
        ("2021-05-01", "2023-05-01"),
        ("2022-05-01", "2024-05-01"),
        ("2023-05-01", "2025-05-01"),
        ("2024-05-01", "2026-05-14"),
    )
    cases = [
        {"name": "rolling_risk_aware", "strategy": "signal-weighted", "risk": "max-position", "execution": "realistic"},
        {"name": "rolling_buy_and_hold", "strategy": "buy-and-hold", "risk": "max-position", "execution": "realistic"},
        {"name": "rolling_no_risk", "strategy": "signal-weighted", "risk": "none", "execution": "realistic"},
    ]
    rows = []
    for start, end in windows:
        for case in cases:
            window_case = {**case, "real_data_start": start, "real_data_end": end}
            _, metrics = _run_case(
                config,
                0,
                f"{case['name']}_{start}_{end}",
                window_case,
                real_market=True,
            )
            row = _metrics_row(case["name"], "rolling_window", f"{start}_to_{end}", case["execution"], case["risk"], metrics)
            row.update({"window": f"{start} to {end}", "data_source": "yahoo_finance", "frequency": config.real_data_frequency})
            rows.append(row)
    return rows


def _sample_summary(values: list[float]) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": "", "std": "", "ci95_low": "", "ci95_high": ""}
    mean = sum(values) / n
    if n == 1:
        return {"n": n, "mean": mean, "std": 0.0, "ci95_low": mean, "ci95_high": mean}
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    std = math.sqrt(variance)
    half_width = _t_critical_95(n - 1) * std / math.sqrt(n)
    return {"n": n, "mean": mean, "std": std, "ci95_low": mean - half_width, "ci95_high": mean + half_width}


def _t_critical_95(df: int) -> float:
    table = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        15: 2.131,
        20: 2.086,
        25: 2.060,
        30: 2.042,
        40: 2.021,
        60: 2.000,
    }
    if df in table:
        return table[df]
    larger = [key for key in table if key >= df]
    return table[min(larger)] if larger else 1.960


def _representation_rows(trajectories: dict[str, Trajectory]) -> dict[str, list[dict[str, Any]]]:
    shift_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    manifold_rows: list[dict[str, Any]] = []
    for case_name, trajectory in trajectories.items():
        if "llm" not in case_name:
            continue
        if not trajectory.steps:
            continue
        equities = [float(step.portfolio.get("equity", 0.0)) for step in trajectory.steps]
        peaks: list[float] = []
        peak = equities[0]
        for equity in equities:
            peak = max(peak, equity)
            peaks.append(peak)
        drawdowns = [(equity / peak_value) - 1.0 if peak_value else 0.0 for equity, peak_value in zip(equities, peaks, strict=True)]
        trough_idx = min(range(len(drawdowns)), key=lambda idx: drawdowns[idx])
        pre_window = set(range(max(0, trough_idx - 4), trough_idx))
        drawdown_window = set(range(trough_idx, min(len(drawdowns), trough_idx + 4)))

        embeddings_by_view: dict[str, dict[str, list[list[float]]]] = {
            "plan": {"normal": [], "pre_drawdown": [], "drawdown": []},
            "reflect": {"normal": [], "pre_drawdown": [], "drawdown": []},
            "fused": {"normal": [], "pre_drawdown": [], "drawdown": []},
        }
        sequence_by_view: dict[str, list[dict[str, Any]]] = {"plan": [], "reflect": [], "fused": []}
        step_vectors: list[dict[str, Any]] = []
        for idx, step in enumerate(trajectory.steps):
            if idx in pre_window:
                phase = "pre_drawdown"
            elif idx in drawdown_window:
                phase = "drawdown"
            else:
                phase = "normal"
            plan_text = _plan_text(step)
            reflect_text = _reflect_text(step)
            structured = _structured_features(step, drawdowns[idx])
            plan_vec = _embed_text(plan_text)
            reflect_vec = _embed_text(reflect_text)
            fused_vec = _normalize([*plan_vec, *reflect_vec, *structured])
            embeddings_by_view["plan"][phase].append(plan_vec)
            embeddings_by_view["reflect"][phase].append(reflect_vec)
            embeddings_by_view["fused"][phase].append(fused_vec)
            sequence_by_view["plan"].append({"step": idx, "phase": phase, "vector": plan_vec, "drawdown": drawdowns[idx]})
            sequence_by_view["reflect"].append({"step": idx, "phase": phase, "vector": reflect_vec, "drawdown": drawdowns[idx]})
            sequence_by_view["fused"].append({"step": idx, "phase": phase, "vector": fused_vec, "drawdown": drawdowns[idx]})
            step_vectors.append(
                {
                    "case": case_name,
                    "step": idx,
                    "timestamp": step.timestamp.isoformat(),
                    "phase": phase,
                    "equity": equities[idx],
                    "drawdown": drawdowns[idx],
                    "plan_token_count": len(_tokens(plan_text)),
                    "reflect_token_count": len(_tokens(reflect_text)),
                    "mean_signal_score": structured[0],
                    "mean_signal_confidence": structured[1],
                    "risk_violation_count": structured[2],
                    "fill_rate": structured[3],
                }
            )
        step_rows.extend(step_vectors)

        for view, phase_vectors in embeddings_by_view.items():
            normal = _centroid(phase_vectors["normal"])
            pre = _centroid(phase_vectors["pre_drawdown"])
            drawdown = _centroid(phase_vectors["drawdown"])
            shift_rows.append(
                {
                    "case": case_name,
                    "view": view,
                    "trough_step": trough_idx,
                    "trough_drawdown": drawdowns[trough_idx],
                    "normal_n": len(phase_vectors["normal"]),
                    "pre_drawdown_n": len(phase_vectors["pre_drawdown"]),
                    "drawdown_n": len(phase_vectors["drawdown"]),
                    "normal_to_pre_cosine_distance": _cosine_distance(normal, pre),
                    "normal_to_drawdown_cosine_distance": _cosine_distance(normal, drawdown),
                    "pre_to_drawdown_cosine_distance": _cosine_distance(pre, drawdown),
                    "pre_shift_norm": _euclidean_distance(normal, pre),
                    "drawdown_shift_norm": _euclidean_distance(normal, drawdown),
                    "early_warning_balanced_accuracy": _early_warning_balanced_accuracy(
                        phase_vectors["normal"], phase_vectors["pre_drawdown"]
                    ),
                    "embedding": "deterministic_hash_64_plus_structured_features" if view == "fused" else "deterministic_hash_64",
                }
            )
            manifold_rows.append(_manifold_row(case_name, view, sequence_by_view[view]))
    robustness_rows = _representation_robustness_rows(trajectories)
    language_control_rows = _language_collapse_control_rows(trajectories)
    return {
        "shift_rows": shift_rows,
        "step_rows": step_rows,
        "manifold_rows": manifold_rows,
        "robustness_rows": robustness_rows,
        "language_control_rows": language_control_rows,
    }


def _representation_robustness_rows(trajectories: dict[str, Trajectory]) -> list[dict[str, Any]]:
    eligible = {name: trajectory for name, trajectory in trajectories.items() if "llm" in name and trajectory.steps}
    if not eligible:
        return []
    plan_docs: list[str] = []
    fused_docs: list[str] = []
    doc_keys: list[tuple[str, int]] = []
    for case_name, trajectory in eligible.items():
        for idx, step in enumerate(trajectory.steps):
            plan = _plan_text(step)
            fused = " ".join([plan, _reflect_text(step), _structured_text(step)])
            plan_docs.append(plan)
            fused_docs.append(fused)
            doc_keys.append((case_name, idx))
    lsa_plan = _lsa_doc_embeddings(plan_docs, dims=32)
    lsa_fused = _lsa_doc_embeddings(fused_docs, dims=32)

    vector_sets: dict[tuple[str, str], dict[str, list[list[float]]]] = {
        ("hash64", "plan"): {},
        ("hash64", "fused"): {},
    }
    if lsa_plan and lsa_fused:
        vector_sets[("lsa32", "plan")] = {}
        vector_sets[("lsa32", "fused")] = {}

    for doc_idx, (case_name, step_idx) in enumerate(doc_keys):
        trajectory = eligible[case_name]
        step = trajectory.steps[step_idx]
        plan = _plan_text(step)
        fused = " ".join([plan, _reflect_text(step), _structured_text(step)])
        drawdowns = _drawdowns(trajectory)
        hash_plan = _embed_text(plan)
        hash_fused = _normalize([*hash_plan, *_embed_text(_reflect_text(step)), *_structured_features(step, drawdowns[step_idx])])
        vector_sets[("hash64", "plan")].setdefault(case_name, []).append(hash_plan)
        vector_sets[("hash64", "fused")].setdefault(case_name, []).append(hash_fused)
        if lsa_plan and lsa_fused:
            vector_sets[("lsa32", "plan")].setdefault(case_name, []).append(lsa_plan[doc_idx])
            vector_sets[("lsa32", "fused")].setdefault(case_name, []).append(lsa_fused[doc_idx])

    rows = []
    cohorts = {
        "all_llm": list(eligible),
        "deepseek": [name for name in eligible if "llm_v4" in name],
        "frontier_matrix": [name for name in eligible if name.startswith("llm_matrix_")],
    }
    for (embedding, view), vectors_by_case in vector_sets.items():
        for cohort, case_names in cohorts.items():
            event_rows = []
            for case_name in case_names:
                if case_name not in vectors_by_case:
                    continue
                event_rows.extend(_rolling_failure_events(case_name, eligible[case_name], vectors_by_case[case_name]))
            if not event_rows:
                continue
            rows.append(
                {
                    "cohort": cohort,
                    "embedding": embedding,
                    "view": view,
                    "trajectories": len({row["case"] for row in event_rows}),
                    "anchors": len(event_rows),
                    "pre_steps": sum(int(row["pre_steps"]) for row in event_rows),
                    "mean_pre_shift": _mean([float(row["pre_shift"]) for row in event_rows]),
                    "mean_pre_to_normal_step_ratio": _mean(
                        [float(row["pre_to_normal_step_ratio"]) for row in event_rows if row["pre_to_normal_step_ratio"] != ""]
                    ),
                    "mean_effective_rank_delta": _mean(
                        [float(row["effective_rank_delta"]) for row in event_rows if row["effective_rank_delta"] != ""]
                    ),
                    "rank_contraction_rate": _mean(
                        [1.0 if float(row["effective_rank_delta"]) > 0 else 0.0 for row in event_rows if row["effective_rank_delta"] != ""]
                    ),
                    "acceleration_rate": _mean(
                        [
                            1.0 if float(row["pre_to_normal_step_ratio"]) > 1.0 else 0.0
                            for row in event_rows
                            if row["pre_to_normal_step_ratio"] != ""
                        ]
                    ),
                }
            )
    return rows


def _language_collapse_control_rows(trajectories: dict[str, Trajectory]) -> list[dict[str, Any]]:
    eligible = {name: trajectory for name, trajectory in trajectories.items() if "llm" in name and trajectory.steps}
    if not eligible:
        return []
    vector_sets: dict[str, dict[str, list[list[float]]]] = {"plan": {}, "fused": {}}
    texts_by_case: dict[str, list[str]] = {}
    for case_name, trajectory in eligible.items():
        drawdowns = _drawdowns(trajectory)
        texts = []
        for idx, step in enumerate(trajectory.steps):
            plan = _plan_text(step)
            texts.append(plan)
            plan_vec = _embed_text(plan)
            fused_vec = _normalize([*plan_vec, *_embed_text(_reflect_text(step)), *_structured_features(step, drawdowns[idx])])
            vector_sets["plan"].setdefault(case_name, []).append(plan_vec)
            vector_sets["fused"].setdefault(case_name, []).append(fused_vec)
        texts_by_case[case_name] = texts

    rows: list[dict[str, Any]] = []
    cohorts = {
        "all_llm": list(eligible),
        "deepseek": [name for name in eligible if "llm_v4" in name],
        "frontier_matrix": [name for name in eligible if name.startswith("llm_matrix_")],
    }
    for view, vectors_by_case in vector_sets.items():
        for cohort, case_names in cohorts.items():
            event_rows: list[dict[str, Any]] = []
            for case_name in case_names:
                if case_name not in vectors_by_case:
                    continue
                events = _rolling_failure_events(case_name, eligible[case_name], vectors_by_case[case_name])
                for event in events:
                    anchor = int(event["anchor"])
                    pre_indices = list(range(max(0, anchor - 4), anchor))
                    drawdowns = _drawdowns(eligible[case_name])
                    median_drawdown = sorted(drawdowns)[len(drawdowns) // 2]
                    event_zone = set(range(max(0, anchor - 4), min(len(drawdowns), anchor + 4)))
                    normal_indices = [idx for idx in range(len(drawdowns)) if idx not in event_zone and drawdowns[idx] >= median_drawdown]
                    if len(normal_indices) < 2:
                        normal_indices = [idx for idx in range(len(drawdowns)) if idx not in event_zone]
                    if len(pre_indices) < 2 or len(normal_indices) < 2:
                        continue
                    pre_texts = [texts_by_case[case_name][idx] for idx in pre_indices]
                    normal_texts = [texts_by_case[case_name][idx] for idx in normal_indices]
                    event["pre_ttr"] = _mean([_type_token_ratio(text) for text in pre_texts])
                    event["normal_ttr"] = _mean([_type_token_ratio(text) for text in normal_texts])
                    event["pre_entropy"] = _mean([_token_entropy(text) for text in pre_texts])
                    event["normal_entropy"] = _mean([_token_entropy(text) for text in normal_texts])
                    event_rows.append(event)
            if not event_rows:
                continue
            ttr_delta = [float(row["pre_ttr"]) - float(row["normal_ttr"]) for row in event_rows]
            entropy_delta = [float(row["pre_entropy"]) - float(row["normal_entropy"]) for row in event_rows]
            rank_delta = [float(row["effective_rank_delta"]) for row in event_rows if row["effective_rank_delta"] != ""]
            lexical_collapse_flags = [
                1.0 if (float(row["pre_ttr"]) - float(row["normal_ttr"]) < -0.05 or float(row["pre_entropy"]) - float(row["normal_entropy"]) < -0.05) else 0.0
                for row in event_rows
            ]
            rank_without_lexical = [
                1.0
                if row["effective_rank_delta"] != ""
                and float(row["effective_rank_delta"]) > 0.0
                and not (float(row["pre_ttr"]) - float(row["normal_ttr"]) < -0.05 or float(row["pre_entropy"]) - float(row["normal_entropy"]) < -0.05)
                else 0.0
                for row in event_rows
            ]
            rows.append(
                {
                    "cohort": cohort,
                    "view": view,
                    "trajectories": len({row["case"] for row in event_rows}),
                    "anchors": len(event_rows),
                    "mean_effective_rank_delta": _mean(rank_delta),
                    "rank_contraction_rate": _mean([1.0 if value > 0.0 else 0.0 for value in rank_delta]),
                    "mean_ttr_delta": _mean(ttr_delta),
                    "mean_entropy_delta": _mean(entropy_delta),
                    "lexical_collapse_rate": _mean(lexical_collapse_flags),
                    "rank_contraction_without_lexical_collapse": _mean(rank_without_lexical),
                }
            )
    return rows


def _type_token_ratio(text: str) -> float:
    tokens = _tokens(text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _token_entropy(text: str) -> float:
    tokens = _tokens(text)
    if not tokens:
        return 0.0
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    total = len(tokens)
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log(probability, 2)
    return entropy


def _rolling_failure_events(case_name: str, trajectory: Trajectory, vectors: list[list[float]], pre_width: int = 4) -> list[dict[str, Any]]:
    drawdowns = _drawdowns(trajectory)
    if len(vectors) < pre_width + 8:
        return []
    candidates = [idx for idx in range(pre_width, len(vectors)) if drawdowns[idx] < 0.0]
    if not candidates:
        candidates = list(range(pre_width, len(vectors)))
    anchor_count = min(12, max(4, len(vectors) // 5), len(candidates))
    anchors = sorted(candidates, key=lambda idx: drawdowns[idx])[:anchor_count]
    median_drawdown = sorted(drawdowns)[len(drawdowns) // 2]
    rows = []
    for anchor in anchors:
        pre_indices = list(range(max(0, anchor - pre_width), anchor))
        event_zone = set(range(max(0, anchor - pre_width), min(len(vectors), anchor + pre_width)))
        normal_indices = [idx for idx in range(len(vectors)) if idx not in event_zone and drawdowns[idx] >= median_drawdown]
        if len(normal_indices) < 2:
            normal_indices = [idx for idx in range(len(vectors)) if idx not in event_zone]
        if len(pre_indices) < 2 or len(normal_indices) < 2:
            continue
        pre_vectors = [vectors[idx] for idx in pre_indices]
        normal_vectors = [vectors[idx] for idx in normal_indices]
        normal_step = _mean(_adjacent_distances(normal_vectors))
        pre_step = _mean(_adjacent_distances(pre_vectors))
        normal_rank = _effective_rank(normal_vectors)
        pre_rank = _effective_rank(pre_vectors)
        rows.append(
            {
                "case": case_name,
                "anchor": anchor,
                "anchor_drawdown": drawdowns[anchor],
                "pre_steps": len(pre_indices),
                "normal_steps": len(normal_indices),
                "pre_shift": _cosine_distance(_centroid(normal_vectors), _centroid(pre_vectors)),
                "pre_to_normal_step_ratio": pre_step / normal_step if normal_step else "",
                "effective_rank_delta": (float(normal_rank) - float(pre_rank)) if normal_rank != "" and pre_rank != "" else "",
                "early_warning_ba": _early_warning_balanced_accuracy(normal_vectors, pre_vectors),
            }
        )
    return rows


def _lsa_doc_embeddings(documents: list[str], dims: int = 32) -> list[list[float]]:
    try:
        import numpy as np
    except ImportError:
        return []
    tokenized = [_tokens(document) for document in documents]
    doc_freq: dict[str, int] = {}
    for tokens in tokenized:
        for token in set(tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1
    vocab = [
        token
        for token, freq in sorted(doc_freq.items(), key=lambda item: (-item[1], item[0]))
        if freq >= 2 and len(token) > 2
    ][:768]
    if len(vocab) < 2 or len(documents) < 3:
        return []
    vocab_index = {token: idx for idx, token in enumerate(vocab)}
    matrix = np.zeros((len(documents), len(vocab)), dtype=float)
    total_docs = len(documents)
    for row_idx, tokens in enumerate(tokenized):
        counts: dict[str, int] = {}
        for token in tokens:
            if token in vocab_index:
                counts[token] = counts.get(token, 0) + 1
        if not counts:
            continue
        total = sum(counts.values())
        for token, count in counts.items():
            col_idx = vocab_index[token]
            tf = count / total
            idf = math.log((1 + total_docs) / (1 + doc_freq[token])) + 1.0
            matrix[row_idx, col_idx] = tf * idf
    if not np.any(matrix):
        return []
    try:
        u, s, _ = np.linalg.svd(matrix, full_matrices=False)
    except Exception:
        return []
    rank = min(dims, len(s))
    embedded = u[:, :rank] * s[:rank]
    return [_normalize([float(value) for value in embedded[row_idx]]) for row_idx in range(embedded.shape[0])]


def _llm_risk_adaptation_rows(trajectories: dict[str, Trajectory]) -> dict[str, list[dict[str, Any]]]:
    event_rows: list[dict[str, Any]] = []
    for case_name, trajectory in trajectories.items():
        if "llm_" not in case_name or "risk_aware" not in case_name:
            continue
        model = _trajectory_model(trajectory)
        for idx, step in enumerate(trajectory.steps[:-1]):
            risk_report = step.risk_report if isinstance(step.risk_report, dict) else {}
            clipped = int(risk_report.get("clipped_count", 0) or 0)
            blocked = int(risk_report.get("blocked_count", 0) or 0)
            if clipped + blocked <= 0:
                continue
            next_step = trajectory.steps[idx + 1]
            intended_before = _intended_abs_exposure(step.decisions)
            approved_before = _intended_abs_exposure(step.approved_decisions)
            intended_after = _intended_abs_exposure(next_step.decisions)
            approved_after = _intended_abs_exposure(next_step.approved_decisions)
            next_risk = next_step.risk_report if isinstance(next_step.risk_report, dict) else {}
            event_rows.append(
                {
                    "case": case_name,
                    "model": model,
                    "event_step": idx,
                    "next_step": idx + 1,
                    "timestamp": step.timestamp.isoformat(),
                    "next_timestamp": next_step.timestamp.isoformat(),
                    "clipped_count": clipped,
                    "blocked_count": blocked,
                    "intended_abs_before": intended_before,
                    "approved_abs_before": approved_before,
                    "intended_abs_after": intended_after,
                    "approved_abs_after": approved_after,
                    "abs_reduction": intended_before - intended_after,
                    "reduced_next_intent": intended_after < intended_before,
                    "next_clipped_count": int(next_risk.get("clipped_count", 0) or 0),
                    "next_blocked_count": int(next_risk.get("blocked_count", 0) or 0),
                    "next_risk_violations": len(next_step.risk_violations),
                    "mean_signal_score_before": _mean_abs_signal_score(step.signals),
                    "mean_signal_score_after": _mean_abs_signal_score(next_step.signals),
                }
            )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in event_rows:
        grouped.setdefault(str(row["case"]), []).append(row)
    summary_rows = []
    for case_name, rows in grouped.items():
        summary_rows.append(
            {
                "case": case_name,
                "model": rows[0]["model"],
                "risk_events": len(rows),
                "mean_intended_abs_before": _mean([float(row["intended_abs_before"]) for row in rows]),
                "mean_intended_abs_after": _mean([float(row["intended_abs_after"]) for row in rows]),
                "mean_abs_reduction": _mean([float(row["abs_reduction"]) for row in rows]),
                "reduction_rate": _mean([1.0 if row["reduced_next_intent"] == "True" or row["reduced_next_intent"] is True else 0.0 for row in rows]),
                "next_clipped_or_blocked_rate": _mean(
                    [1.0 if int(row["next_clipped_count"]) + int(row["next_blocked_count"]) > 0 else 0.0 for row in rows]
                ),
                "mean_next_risk_violations": _mean([float(row["next_risk_violations"]) for row in rows]),
                "mean_signal_score_before": _mean([float(row["mean_signal_score_before"]) for row in rows]),
                "mean_signal_score_after": _mean([float(row["mean_signal_score_after"]) for row in rows]),
            }
        )
    return {"summary_rows": summary_rows, "event_rows": event_rows}


def _hallucination_risk_rows(
    trajectories: dict[str, Trajectory], cache_path: str, annotation_path: str = "data/annotations/hallucination_gold.csv"
) -> dict[str, list[dict[str, Any]]]:
    prompt_cache = _prompt_cache_by_hash(cache_path)
    step_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for case_name, trajectory in trajectories.items():
        if "llm_" not in case_name:
            continue
        model = _trajectory_model(trajectory)
        rows = []
        prior_risk_events = 0
        for idx, step in enumerate(trajectory.steps):
            risk_report = step.risk_report if isinstance(step.risk_report, dict) else {}
            execution_report = step.execution_report if isinstance(step.execution_report, dict) else {}
            prompt = _step_prompt(step, prompt_cache)
            proxy = _hallucination_proxy(step, prompt, prior_risk_events)
            clipped = int(risk_report.get("clipped_count", 0) or 0)
            blocked = int(risk_report.get("blocked_count", 0) or 0)
            risk_violations = len(step.risk_violations)
            rejected_orders = int(execution_report.get("rejected_orders", 0) or 0)
            calibration_gap = _calibration_gap(step.decisions, step.approved_decisions)
            risk_gate = 1.0 if clipped + blocked + risk_violations > 0 else 0.0
            row = {
                "case": case_name,
                "model": model,
                "step": idx,
                "timestamp": step.timestamp.isoformat(),
                "hallucination_proxy": proxy["score"],
                "unsupported_context_claims": proxy["unsupported_context_claims"],
                "directional_contradictions": proxy["directional_contradictions"],
                "overconfident_weak_evidence": proxy["overconfident_weak_evidence"],
                "stale_no_risk_claims": proxy["stale_no_risk_claims"],
                "signals": proxy["signals"],
                "risk_gate_triggered": risk_gate,
                "clipped_count": clipped,
                "blocked_count": blocked,
                "risk_violations": risk_violations,
                "calibration_gap": calibration_gap,
                "rejected_orders": rejected_orders,
            }
            rows.append(row)
            prior_risk_events += clipped + blocked + risk_violations + rejected_orders
        step_rows.extend(rows)
        if rows:
            threshold = _percentile([float(row["hallucination_proxy"]) for row in rows], 0.75)
            high = [row for row in rows if float(row["hallucination_proxy"]) >= threshold and float(row["hallucination_proxy"]) > 0.0]
            low = [row for row in rows if row not in high]
            summary_rows.append(
                {
                    "case": case_name,
                    "model": model,
                    "steps": len(rows),
                    "mean_hallucination_proxy": _mean([float(row["hallucination_proxy"]) for row in rows]),
                    "high_proxy_threshold": threshold,
                    "high_proxy_steps": len(high),
                    "risk_gate_corr": _pearson(
                        [float(row["hallucination_proxy"]) for row in rows],
                        [float(row["risk_gate_triggered"]) for row in rows],
                    ),
                    "risk_violation_corr": _pearson(
                        [float(row["hallucination_proxy"]) for row in rows],
                        [float(row["risk_violations"]) for row in rows],
                    ),
                    "calibration_gap_corr": _pearson(
                        [float(row["hallucination_proxy"]) for row in rows],
                        [float(row["calibration_gap"]) for row in rows],
                    ),
                    "rejected_orders_corr": _pearson(
                        [float(row["hallucination_proxy"]) for row in rows],
                        [float(row["rejected_orders"]) for row in rows],
                    ),
                    "high_proxy_risk_gate_rate": _mean([float(row["risk_gate_triggered"]) for row in high]),
                    "low_proxy_risk_gate_rate": _mean([float(row["risk_gate_triggered"]) for row in low]),
                    "high_proxy_mean_calibration_gap": _mean([float(row["calibration_gap"]) for row in high]),
                    "low_proxy_mean_calibration_gap": _mean([float(row["calibration_gap"]) for row in low]),
                    "high_proxy_mean_rejected_orders": _mean([float(row["rejected_orders"]) for row in high]),
                    "low_proxy_mean_rejected_orders": _mean([float(row["rejected_orders"]) for row in low]),
                }
            )
    annotation_rows = _hallucination_annotation_sample(step_rows, trajectories)
    calibration_rows = _hallucination_calibration_rows(annotation_rows, annotation_path)
    return {
        "summary_rows": summary_rows,
        "step_rows": step_rows,
        "annotation_rows": annotation_rows,
        "calibration_rows": calibration_rows,
    }


def _hallucination_annotation_sample(
    step_rows: list[dict[str, Any]], trajectories: dict[str, Trajectory], sample_size: int = 50
) -> list[dict[str, Any]]:
    if not step_rows:
        return []
    indexed_steps: dict[tuple[str, int], Any] = {}
    for case_name, trajectory in trajectories.items():
        for idx, step in enumerate(trajectory.steps):
            indexed_steps[(case_name, idx)] = step
    ranked = sorted(
        step_rows,
        key=lambda row: (
            hashlib.sha256(f"{row['case']}:{row['step']}".encode()).hexdigest(),
            str(row["case"]),
            int(row["step"]),
        ),
    )[:sample_size]
    sample = []
    for row in ranked:
        case = str(row["case"])
        step_idx = int(row["step"])
        step = indexed_steps.get((case, step_idx))
        text = _plan_text(step) if step is not None else ""
        threshold = _percentile(
            [float(candidate["hallucination_proxy"]) for candidate in step_rows if candidate["case"] == case],
            0.75,
        )
        proxy_label = 1 if float(row["hallucination_proxy"]) >= threshold and float(row["hallucination_proxy"]) > 0.0 else 0
        sample.append(
            {
                "case": case,
                "model": row["model"],
                "step": step_idx,
                "timestamp": row["timestamp"],
                "proxy_score": row["hallucination_proxy"],
                "proxy_label": proxy_label,
                "audit_signals": row["signals"],
                "rationale_excerpt": text[:800].replace("\n", " "),
                "annotator_a_label": "",
                "annotator_b_label": "",
                "adjudicated_label": "",
                "annotation_guideline": "1 if the rationale makes unsupported external-context, causal, or directional claims not justified by the recorded prompt; else 0.",
            }
        )
    return sample


def _hallucination_calibration_rows(annotation_rows: list[dict[str, Any]], annotation_path: str) -> list[dict[str, Any]]:
    rows = _load_annotation_rows(annotation_path) or annotation_rows
    labeled = [
        row
        for row in rows
        if str(row.get("annotator_a_label", "")).strip() in {"0", "1"}
        and str(row.get("annotator_b_label", "")).strip() in {"0", "1"}
    ]
    if not labeled:
        return []
    a = [int(str(row["annotator_a_label"]).strip()) for row in labeled]
    b = [int(str(row["annotator_b_label"]).strip()) for row in labeled]
    proxy = [int(row.get("proxy_label", 0)) for row in labeled]
    gold = [int(str(row.get("adjudicated_label", "")).strip()) if str(row.get("adjudicated_label", "")).strip() in {"0", "1"} else round((x + y) / 2) for x, y, row in zip(a, b, labeled)]
    return [
        {
            "status": "manual_labels_loaded",
            "samples": len(labeled),
            "annotators": 2,
            "agreement": _mean([1.0 if x == y else 0.0 for x, y in zip(a, b)]),
            "cohen_kappa": _cohen_kappa(a, b),
            "iou": _binary_iou(proxy, gold),
            "notes": "Cohen's kappa is inter-annotator agreement; IoU compares deterministic proxy labels with adjudicated/majority human labels.",
        }
    ]


def _load_annotation_rows(annotation_path: str) -> list[dict[str, Any]]:
    path = Path(annotation_path)
    if not path.exists():
        return []
    import csv

    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _cohen_kappa(left: list[int], right: list[int]) -> float | str:
    if not left or len(left) != len(right):
        return ""
    observed = _mean([1.0 if a == b else 0.0 for a, b in zip(left, right)])
    left_pos = _mean([float(value) for value in left])
    right_pos = _mean([float(value) for value in right])
    expected = left_pos * right_pos + (1.0 - left_pos) * (1.0 - right_pos)
    if abs(1.0 - expected) < 1e-12:
        return ""
    return (observed - expected) / (1.0 - expected)


def _binary_iou(predicted: list[int], gold: list[int]) -> float | str:
    if not predicted or len(predicted) != len(gold):
        return ""
    intersection = sum(1 for pred, actual in zip(predicted, gold) if pred == 1 and actual == 1)
    union = sum(1 for pred, actual in zip(predicted, gold) if pred == 1 or actual == 1)
    return intersection / union if union else 1.0


def _prompt_cache_by_hash(cache_path: str) -> dict[str, dict[str, Any]]:
    path = Path(cache_path)
    if not path.exists():
        return {}
    prompts: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            prompt_hash = str(item.get("prompt_hash", ""))
            prompt_text = str(item.get("prompt", "{}"))
            try:
                prompts[prompt_hash] = json.loads(prompt_text)
            except json.JSONDecodeError:
                prompts[prompt_hash] = {}
    return prompts


def _step_prompt(step: Any, prompt_cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for signal in step.signals:
        metadata = signal.get("metadata", {}) if isinstance(signal, dict) else {}
        prompt_hash = str(metadata.get("prompt_hash", ""))
        if prompt_hash in prompt_cache:
            return prompt_cache[prompt_hash]
    return {}


def _hallucination_proxy(step: Any, prompt: dict[str, Any], prior_risk_events: int) -> dict[str, Any]:
    bars_by_symbol = {str(item.get("symbol", "")): item for item in prompt.get("bars", []) if isinstance(item, dict)}
    unsupported_terms = (
        "news",
        "headline",
        "earnings",
        "fundamental",
        "regulation",
        "regulatory",
        "fed",
        "macro",
        "institutional",
        "on-chain",
        "support",
        "resistance",
        "breakout",
        "oversold",
        "overbought",
    )
    no_risk_terms = ("no risk", "no prior risk", "no risk feedback", "no prior violations", "no violations")
    unsupported = 0
    contradictions = 0
    overconfident = 0
    stale_no_risk = 0
    signal_count = 0
    for signal in step.signals:
        if not isinstance(signal, dict):
            continue
        signal_count += 1
        text = f"{signal.get('rationale', '')} {signal.get('metadata', {}).get('risk_notes', '')}".lower()
        if any(term in text for term in unsupported_terms):
            unsupported += 1
        score = float(signal.get("score", 0.0) or 0.0)
        confidence = float(signal.get("confidence", 0.0) or 0.0)
        bar = bars_by_symbol.get(str(signal.get("symbol", "")), {})
        intraperiod = float(bar.get("intraperiod_return", 0.0) or 0.0)
        if abs(intraperiod) >= 0.006 and abs(score) >= 0.25 and score * intraperiod < 0.0:
            contradictions += 1
        if confidence >= 0.6 and abs(intraperiod) < 0.004:
            overconfident += 1
        if prior_risk_events > 0 and any(term in text for term in no_risk_terms):
            stale_no_risk += 1
    denominator = max(1, signal_count)
    score = (unsupported + contradictions + overconfident + stale_no_risk) / denominator
    return {
        "score": score,
        "unsupported_context_claims": unsupported,
        "directional_contradictions": contradictions,
        "overconfident_weak_evidence": overconfident,
        "stale_no_risk_claims": stale_no_risk,
        "signals": signal_count,
    }


def _memory_learning_rows(trajectories: dict[str, Trajectory], rolling_window: int = 8) -> dict[str, list[dict[str, Any]]]:
    step_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for case_name, trajectory in trajectories.items():
        if "llm_" not in case_name or "risk_aware" not in case_name:
            continue
        model = _trajectory_model(trajectory)
        rows = []
        for idx, step in enumerate(trajectory.steps):
            risk_report = step.risk_report if isinstance(step.risk_report, dict) else {}
            clipped = int(risk_report.get("clipped_count", 0) or 0)
            blocked = int(risk_report.get("blocked_count", 0) or 0)
            risk_violations = len(step.risk_violations)
            risk_gate_triggered = clipped + blocked + risk_violations > 0
            intended_abs = _intended_abs_exposure(step.decisions)
            approved_abs = _intended_abs_exposure(step.approved_decisions)
            gap = _calibration_gap(step.decisions, step.approved_decisions)
            score = 1.0 - min(1.0, gap / max(1.0, intended_abs))
            row = {
                "case": case_name,
                "model": model,
                "step": idx,
                "timestamp": step.timestamp.isoformat(),
                "observed_steps": idx + 1,
                "risk_gate_triggered": risk_gate_triggered,
                "clipped_count": clipped,
                "blocked_count": blocked,
                "risk_violations": risk_violations,
                "intended_abs_exposure": intended_abs,
                "approved_abs_exposure": approved_abs,
                "calibration_gap": gap,
                "calibration_score": score,
                "mean_abs_signal_score": _mean_abs_signal_score(step.signals),
                "lookback_memory_size": min(idx, 52),
            }
            rows.append(row)
        for idx, row in enumerate(rows):
            start = max(0, idx - rolling_window + 1)
            window = rows[start : idx + 1]
            row["rolling_risk_gate_rate"] = _mean([1.0 if item["risk_gate_triggered"] else 0.0 for item in window])
            row["rolling_calibration_gap"] = _mean([float(item["calibration_gap"]) for item in window])
            row["rolling_calibration_score"] = _mean([float(item["calibration_score"]) for item in window])
            step_rows.append(row)
        if rows:
            split = max(1, len(rows) // 4)
            early = rows[:split]
            late = rows[-split:]
            early_risk = _mean([1.0 if item["risk_gate_triggered"] else 0.0 for item in early])
            late_risk = _mean([1.0 if item["risk_gate_triggered"] else 0.0 for item in late])
            early_score = _mean([float(item["calibration_score"]) for item in early])
            late_score = _mean([float(item["calibration_score"]) for item in late])
            early_gap = _mean([float(item["calibration_gap"]) for item in early])
            late_gap = _mean([float(item["calibration_gap"]) for item in late])
            summary_rows.append(
                {
                    "case": case_name,
                    "model": model,
                    "steps": len(rows),
                    "early_window": split,
                    "late_window": split,
                    "early_risk_gate_rate": early_risk,
                    "late_risk_gate_rate": late_risk,
                    "risk_gate_rate_delta": late_risk - early_risk,
                    "early_calibration_score": early_score,
                    "late_calibration_score": late_score,
                    "calibration_score_delta": late_score - early_score,
                    "early_calibration_gap": early_gap,
                    "late_calibration_gap": late_gap,
                    "calibration_gap_delta": late_gap - early_gap,
                }
            )
    return {"summary_rows": summary_rows, "step_rows": step_rows}


def _intraday_complex_rows(config: PaperExperimentConfig) -> dict[str, list[dict[str, Any]]]:
    cases = [
        {
            "name": "intraday_50_buy_and_hold",
            "strategy": "buy-and-hold",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum", "macro-news"),
            "model": "deterministic",
        },
        {
            "name": "intraday_50_deterministic_risk_aware",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum", "macro-news"),
            "model": "deterministic",
        },
        {
            "name": "intraday_50_markowitz_mvo",
            "strategy": "mean-variance",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum", "macro-news"),
            "model": "markowitz_min_variance",
        },
        {
            "name": "intraday_50_low_liquidity_stress",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum", "macro-news"),
            "model": "deterministic_low_liquidity",
            "participation_rate": 0.003,
            "slippage_bps": 8.0,
            "market_impact": 0.45,
        },
        {
            "name": "intraday_50_latency_stress",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("momentum", "macro-news"),
            "model": "deterministic_latency",
            "latency_steps": 3,
            "slippage_bps": 6.0,
            "market_impact": 0.35,
        },
    ]
    if config.include_intraday_llm_probe:
        intraday_models = config.intraday_llm_models or (config.intraday_llm_model,)
        analyst_name = "poe-llm" if config.intraday_llm_provider == "poe" else "deepseek-llm"
        for model in intraday_models:
            safe_model = _safe_case_token(model)
            cases.append(
                {
                    "name": f"intraday_50_llm_{safe_model}_risk_aware",
                    "strategy": "signal-weighted",
                    "risk": "max-position",
                    "execution": "realistic",
                    "analyst_names": (analyst_name,),
                    "llm_model": model,
                    "model": f"{model}_expensive_probe",
                    "intraday_max_periods": config.intraday_llm_max_periods,
                }
            )
    correlation = _intraday_correlation_summary(config)
    pair_correlations = _intraday_pair_correlations(config)
    raw_dir = Path(config.output_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    case_rows: list[dict[str, Any]] = []
    blind_spot_rows: list[dict[str, Any]] = []
    for case in cases:
        trajectory, metrics = _run_case(
            config,
            0,
            case["name"],
            {
                **case,
                "max_position_weight": 0.08,
                "max_gross_exposure": 1.0,
                "max_turnover": 0.5,
                "participation_rate": case.get("participation_rate", 0.01),
                "slippage_bps": case.get("slippage_bps", 3.0),
                "market_impact": case.get("market_impact", 0.25),
                "latency_steps": case.get("latency_steps", 1),
            },
            real_market=True,
            llm_market=False,
        )
        write_json(raw_dir / f"{case['name']}_trajectory.json", trajectory.to_dict())
        row = _metrics_row(case["name"], "intraday_complex", "hourly", "realistic", case["risk"], metrics)
        row.update(
            {
                "model": case["model"],
                "symbols": len(config.intraday_symbols),
                "steps": len(trajectory.steps),
                "frequency": "1h",
                "data_source": "yahoo_finance_chart_api",
                "correlation_mean_abs": correlation["correlation_mean_abs"],
                "correlation_p90_abs": correlation["correlation_p90_abs"],
                "effective_assets": correlation["effective_assets"],
                "first_principal_component_share": correlation["first_principal_component_share"],
                "mean_herfindahl": _mean_herfindahl(trajectory),
                "mean_active_positions": _mean_active_positions(trajectory),
            }
        )
        case_rows.append(row)
        if str(case["name"]).startswith("intraday_50_llm_"):
            blind_spot_rows.extend(_intraday_blind_spot_rows(trajectory, pair_correlations, case_name=str(case["name"]), model=str(case["model"])))
    return {"case_rows": case_rows, "correlation_rows": [correlation], "blind_spot_rows": blind_spot_rows}


def _risk_feedback_ablation_rows(config: PaperExperimentConfig) -> dict[str, list[dict[str, Any]]]:
    cases = [
        {
            "name": "feedback_on",
            "feedback": "true",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("deepseek-llm",),
            "llm_model": "deepseek-v4-pro",
            "llm_use_risk_feedback": True,
            "llm_risk_feedback_mode": "true",
        },
        {
            "name": "feedback_placebo",
            "feedback": "placebo",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("deepseek-llm",),
            "llm_model": "deepseek-v4-pro",
            "llm_use_risk_feedback": True,
            "llm_risk_feedback_mode": "placebo",
        },
        {
            "name": "feedback_off",
            "feedback": "hidden",
            "strategy": "signal-weighted",
            "risk": "max-position",
            "execution": "realistic",
            "analyst_names": ("deepseek-llm",),
            "llm_model": "deepseek-v4-pro",
            "llm_use_risk_feedback": False,
        },
    ]
    summary_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    manifold_rows: list[dict[str, Any]] = []
    for case in cases:
        trajectory, metrics = _run_case(
            config,
            0,
            f"risk_feedback_{case['name']}",
            case,
            real_market=True,
            llm_market=True,
        )
        feedback_label = str(case.get("feedback", "true" if case["llm_use_risk_feedback"] else "hidden"))
        rows = _intent_step_rows(f"risk_feedback_{case['name']}", trajectory, feedback_label)
        step_rows.extend(rows)
        manifold_rows.extend(_feedback_manifold_rows(f"risk_feedback_{case['name']}", feedback_label, trajectory))
        split = max(1, len(rows) // 4)
        late = rows[-split:]
        summary_rows.append(
            {
                "case": f"risk_feedback_{case['name']}",
                "feedback": feedback_label,
                "model": case["llm_model"],
                "steps": len(rows),
                "total_return": metrics.get("total_return", 0.0),
                "sharpe": metrics.get("sharpe", 0.0),
                "max_drawdown": metrics.get("max_drawdown", 0.0),
                "risk_clipped_decisions": metrics.get("risk_clipped_decisions", 0),
                "risk_violation_count": metrics.get("risk_violation_count", 0),
                "mean_intended_abs": _mean([float(row["intended_abs_exposure"]) for row in rows]),
                "late_intended_abs": _mean([float(row["intended_abs_exposure"]) for row in late]),
                "mean_calibration_gap": _mean([float(row["calibration_gap"]) for row in rows]),
                "late_calibration_gap": _mean([float(row["calibration_gap"]) for row in late]),
                "mean_calibration_score": _mean([float(row["calibration_score"]) for row in rows]),
                "late_calibration_score": _mean([float(row["calibration_score"]) for row in late]),
                "intent_drift": _intent_drift(rows),
            }
        )
    return {"summary_rows": summary_rows, "step_rows": step_rows, "manifold_rows": manifold_rows}


def _frontier_feedback_matrix_rows(config: PaperExperimentConfig) -> dict[str, list[dict[str, Any]]]:
    feedback_modes = [
        ("true", True, "true"),
        ("placebo", True, "placebo"),
        ("hidden", False, "true"),
    ]
    summary_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    manifold_rows: list[dict[str, Any]] = []
    raw_dir = Path(config.output_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for model in config.model_matrix_models:
        slug = _model_slug(model)
        for feedback, use_feedback, feedback_mode in feedback_modes:
            case = {
                "name": f"llm_matrix_feedback_{slug}_{feedback}",
                "strategy": "signal-weighted",
                "risk": "max-position",
                "execution": "realistic",
                "analyst_names": ("poe-llm",),
                "llm_model": model,
                "llm_use_risk_feedback": use_feedback,
                "llm_risk_feedback_mode": feedback_mode,
            }
            trajectory, metrics = _run_case(
                config,
                0,
                str(case["name"]),
                case,
                real_market=True,
                llm_market=True,
            )
            write_json(raw_dir / f"{case['name']}_trajectory.json", trajectory.to_dict())
            rows = _intent_step_rows(str(case["name"]), trajectory, feedback)
            for row in rows:
                row["model"] = model
            step_rows.extend(rows)
            for row in _feedback_manifold_rows(str(case["name"]), feedback, trajectory):
                row["model"] = model
                manifold_rows.append(row)
            split = max(1, len(rows) // 4)
            late = rows[-split:]
            summary_rows.append(
                {
                    "case": case["name"],
                    "model": model,
                    "feedback": feedback,
                    "steps": len(rows),
                    "total_return": metrics.get("total_return", 0.0),
                    "sharpe": metrics.get("sharpe", 0.0),
                    "max_drawdown": metrics.get("max_drawdown", 0.0),
                    "risk_clipped_decisions": metrics.get("risk_clipped_decisions", 0),
                    "risk_violation_count": metrics.get("risk_violation_count", 0),
                    "mean_intended_abs": _mean([float(row["intended_abs_exposure"]) for row in rows]),
                    "late_intended_abs": _mean([float(row["intended_abs_exposure"]) for row in late]),
                    "mean_calibration_gap": _mean([float(row["calibration_gap"]) for row in rows]),
                    "late_calibration_gap": _mean([float(row["calibration_gap"]) for row in late]),
                    "mean_calibration_score": _mean([float(row["calibration_score"]) for row in rows]),
                    "late_calibration_score": _mean([float(row["calibration_score"]) for row in late]),
                    "intent_drift": _intent_drift(rows),
                }
            )
    return {"summary_rows": summary_rows, "step_rows": step_rows, "manifold_rows": manifold_rows}


def _frontier_feedback_effect_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, dict[str, dict[str, Any]]] = {}
    for row in summary_rows:
        by_model.setdefault(str(row["model"]), {})[str(row["feedback"])] = row
    effect_rows = []
    for model, rows in sorted(by_model.items()):
        true = rows.get("true")
        hidden = rows.get("hidden")
        placebo = rows.get("placebo")
        if not true or not hidden or not placebo:
            continue
        true_return = float(true.get("total_return", 0.0))
        hidden_return = float(hidden.get("total_return", 0.0))
        placebo_return = float(placebo.get("total_return", 0.0))
        true_drawdown = float(true.get("max_drawdown", 0.0))
        hidden_drawdown = float(hidden.get("max_drawdown", 0.0))
        placebo_drawdown = float(placebo.get("max_drawdown", 0.0))
        true_late_gap = float(true.get("late_calibration_gap", 0.0))
        hidden_late_gap = float(hidden.get("late_calibration_gap", 0.0))
        placebo_late_gap = float(placebo.get("late_calibration_gap", 0.0))
        effect_rows.append(
            {
                "model": model,
                "return_delta_true_hidden": true_return - hidden_return,
                "drawdown_improvement_true_hidden": true_drawdown - hidden_drawdown,
                "late_gap_reduction_true_hidden": hidden_late_gap - true_late_gap,
                "return_delta_true_placebo": true_return - placebo_return,
                "drawdown_improvement_true_placebo": true_drawdown - placebo_drawdown,
                "late_gap_reduction_true_placebo": placebo_late_gap - true_late_gap,
            }
        )
    return effect_rows


def _frontier_feedback_learning_rows(step_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in step_rows:
        grouped.setdefault((str(row["model"]), str(row["feedback"])), []).append(row)
    learning_rows = []
    for (model, feedback), rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: int(row["step"]))
        split = max(1, len(ordered) // 4)
        early = ordered[:split]
        late = ordered[-split:]
        early_risk = _risk_gate_rate(early)
        late_risk = _risk_gate_rate(late)
        early_calibration = _mean([float(row["calibration_score"]) for row in early])
        late_calibration = _mean([float(row["calibration_score"]) for row in late])
        early_gap = _mean([float(row["calibration_gap"]) for row in early])
        late_gap = _mean([float(row["calibration_gap"]) for row in late])
        early_intent = _mean([float(row["intended_abs_exposure"]) for row in early])
        late_intent = _mean([float(row["intended_abs_exposure"]) for row in late])
        learning_rows.append(
            {
                "model": model,
                "feedback": feedback,
                "steps": len(ordered),
                "early_risk_gate_rate": early_risk,
                "late_risk_gate_rate": late_risk,
                "risk_gate_delta": late_risk - early_risk,
                "early_calibration_score": early_calibration,
                "late_calibration_score": late_calibration,
                "calibration_delta": late_calibration - early_calibration,
                "early_calibration_gap": early_gap,
                "late_calibration_gap": late_gap,
                "early_intended_abs": early_intent,
                "late_intended_abs": late_intent,
            }
        )
    return learning_rows


def _frontier_probe_models(config: PaperExperimentConfig) -> tuple[str, ...]:
    preferred = ("gpt-5.5", "gemini-3.1-pro", "claude-opus-4.7")
    selected = [model for model in preferred if model in config.model_matrix_models]
    if selected:
        return tuple(selected)
    return tuple(config.model_matrix_models[:3])


def _cot_free_ablation_rows(config: PaperExperimentConfig) -> dict[str, list[dict[str, Any]]]:
    raw_dir = Path(config.output_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    manifold_rows: list[dict[str, Any]] = []
    for model in _frontier_probe_models(config):
        slug = _model_slug(model)
        for mode_label, output_mode in (("cot", "rationale"), ("cot_free", "weights_only")):
            case = {
                "name": f"cot_free_{slug}_{mode_label}",
                "strategy": "signal-weighted",
                "risk": "max-position",
                "execution": "realistic",
                "analyst_names": ("poe-llm",),
                "llm_model": model,
                "llm_use_risk_feedback": True,
                "llm_risk_feedback_mode": "true",
                "llm_output_mode": output_mode,
            }
            trajectory, metrics = _run_case(config, 0, str(case["name"]), case, real_market=True, llm_market=True)
            write_json(raw_dir / f"{case['name']}_trajectory.json", trajectory.to_dict())
            steps = _intent_step_rows(str(case["name"]), trajectory, mode_label)
            for row in steps:
                row["model"] = model
                row["mode"] = mode_label
                row["language_token_count"] = len(_tokens(_plan_text(trajectory.steps[int(row["step"])])))
            step_rows.extend(steps)
            geometry = _cot_free_geometry_rows(str(case["name"]), model, mode_label, trajectory)
            manifold_rows.extend(geometry["manifold_rows"])
            by_view = {str(row["view"]): row for row in geometry["manifold_rows"]}
            language = by_view.get("language_plan", {})
            intent = by_view.get("intent_weights", {})
            summary_rows.append(
                {
                    "case": case["name"],
                    "model": model,
                    "mode": mode_label,
                    "steps": len(steps),
                    "total_return": metrics.get("total_return", 0.0),
                    "sharpe": metrics.get("sharpe", 0.0),
                    "max_drawdown": metrics.get("max_drawdown", 0.0),
                    "risk_clipped_decisions": metrics.get("risk_clipped_decisions", 0),
                    "mean_language_tokens": _mean([float(row["language_token_count"]) for row in steps]),
                    "language_effective_rank_delta": language.get("effective_rank_delta", ""),
                    "intent_effective_rank_delta": intent.get("effective_rank_delta", ""),
                    "language_pre_to_normal_step_ratio": language.get("pre_to_normal_step_ratio", ""),
                    "intent_pre_to_normal_step_ratio": intent.get("pre_to_normal_step_ratio", ""),
                    "language_early_warning_ba": geometry["shift_rows"].get("language_plan", ""),
                    "intent_early_warning_ba": geometry["shift_rows"].get("intent_weights", ""),
                }
            )
    return {"summary_rows": summary_rows, "step_rows": step_rows, "manifold_rows": manifold_rows}


def _cot_free_geometry_rows(case_name: str, model: str, mode: str, trajectory: Trajectory) -> dict[str, Any]:
    drawdowns = _drawdowns(trajectory)
    if not drawdowns:
        return {"manifold_rows": [], "shift_rows": {}}
    symbols = _trajectory_symbols(trajectory)
    sequences: dict[str, list[dict[str, Any]]] = {"language_plan": [], "intent_weights": []}
    phases = _drawdown_phases(drawdowns)
    for idx, step in enumerate(trajectory.steps):
        language_vec = _embed_text(_plan_text(step))
        intent_vec = _intent_weight_vector(step, symbols)
        sequences["language_plan"].append({"step": idx, "phase": phases[idx], "vector": language_vec, "drawdown": drawdowns[idx]})
        sequences["intent_weights"].append({"step": idx, "phase": phases[idx], "vector": intent_vec, "drawdown": drawdowns[idx]})
    manifold_rows: list[dict[str, Any]] = []
    ba_by_view: dict[str, Any] = {}
    for view, sequence in sequences.items():
        row = _manifold_row(case_name, view, sequence)
        row["model"] = model
        row["mode"] = mode
        manifold_rows.append(row)
        normal = [item["vector"] for item in sequence if item["phase"] == "normal"]
        pre = [item["vector"] for item in sequence if item["phase"] == "pre_drawdown"]
        ba_by_view[view] = _early_warning_balanced_accuracy(normal, pre)
    return {"manifold_rows": manifold_rows, "shift_rows": ba_by_view}


def _noise_injection_robustness_rows(trajectories: dict[str, Trajectory]) -> dict[str, list[dict[str, Any]]]:
    eligible = {
        name: trajectory
        for name, trajectory in trajectories.items()
        if trajectory.steps and (name.startswith("llm_matrix_") or name.startswith("llm_v4_") or name.startswith("llm_"))
    }
    if not eligible:
        return {"summary_rows": [], "event_rows": []}
    event_rows: list[dict[str, Any]] = []
    for epsilon in (0.0, 0.05, 0.10, 0.20):
        for case_name, trajectory in eligible.items():
            drawdowns = _drawdowns(trajectory)
            plan_vectors = [_embed_text(_plan_text(step)) for step in trajectory.steps]
            market_vectors = _noisy_market_vectors(case_name, trajectory, epsilon)
            fused_vectors = [
                _normalize([*plan_vectors[idx], *market_vectors[idx], *_structured_features(step, drawdowns[idx])])
                for idx, step in enumerate(trajectory.steps)
            ]
            for view, vectors in (("language_plan", plan_vectors), ("market_fused", fused_vectors)):
                for event in _rolling_failure_events(case_name, trajectory, vectors):
                    event_rows.append(
                        {
                            "epsilon": epsilon,
                            "view": view,
                            "case": case_name,
                            "model": _trajectory_model(trajectory),
                            **event,
                        }
                    )
    summary_rows: list[dict[str, Any]] = []
    clean_by_view: dict[str, dict[str, float]] = {}
    for epsilon in (0.0, 0.05, 0.10, 0.20):
        for view in ("language_plan", "market_fused"):
            rows = [row for row in event_rows if float(row["epsilon"]) == epsilon and row["view"] == view]
            if not rows:
                continue
            mean_ba = _mean([float(row["early_warning_ba"]) for row in rows if row.get("early_warning_ba") != ""])
            mean_rank_delta = _mean(
                [float(row["effective_rank_delta"]) for row in rows if row["effective_rank_delta"] != ""]
            )
            mean_pre_shift = _mean([float(row["pre_shift"]) for row in rows])
            contraction_rate = _mean(
                [1.0 if float(row["effective_rank_delta"]) > 0 else 0.0 for row in rows if row["effective_rank_delta"] != ""]
            )
            if epsilon == 0.0:
                clean_by_view[view] = {
                    "mean_early_warning_ba": float(mean_ba) if mean_ba != "" else 0.0,
                    "mean_effective_rank_delta": float(mean_rank_delta) if mean_rank_delta != "" else 0.0,
                    "mean_pre_shift": float(mean_pre_shift) if mean_pre_shift != "" else 0.0,
                }
            clean = clean_by_view.get(view, {})
            clean_ba = clean.get("mean_early_warning_ba", float(mean_ba) if mean_ba != "" else 0.0)
            clean_rank = clean.get("mean_effective_rank_delta", float(mean_rank_delta) if mean_rank_delta != "" else 0.0)
            clean_shift = clean.get("mean_pre_shift", float(mean_pre_shift) if mean_pre_shift != "" else 0.0)
            ba_drop = clean_ba - float(mean_ba) if mean_ba != "" else ""
            rank_retention = (
                float(mean_rank_delta) / clean_rank
                if mean_rank_delta != "" and abs(clean_rank) >= 1.0
                else ""
            )
            shift_retention = (
                float(mean_pre_shift) / clean_shift
                if mean_pre_shift != "" and abs(clean_shift) > 1e-12
                else ""
            )
            robust_ba = bool(mean_ba != "" and float(mean_ba) >= 0.75)
            robust_signature = bool(
                robust_ba
                and contraction_rate != ""
                and float(contraction_rate) >= 0.75
                and (mean_rank_delta == "" or float(mean_rank_delta) > 0)
            )
            summary_rows.append(
                {
                    "epsilon": epsilon,
                    "view": view,
                    "trajectories": len({row["case"] for row in rows}),
                    "anchors": len(rows),
                    "mean_pre_shift": mean_pre_shift,
                    "mean_effective_rank_delta": mean_rank_delta,
                    "rank_contraction_rate": contraction_rate,
                    "mean_pre_to_normal_step_ratio": _mean(
                        [float(row["pre_to_normal_step_ratio"]) for row in rows if row["pre_to_normal_step_ratio"] != ""]
                    ),
                    "mean_early_warning_ba": mean_ba,
                    "ba_drop_from_clean": ba_drop,
                    "rank_delta_retention": rank_retention,
                    "pre_shift_retention": shift_retention,
                    "robust_ba_075": int(robust_ba),
                    "robust_signature": int(robust_signature),
                }
            )
    return {"summary_rows": summary_rows, "event_rows": event_rows}


def _contrarian_audit_rows(config: PaperExperimentConfig) -> dict[str, list[dict[str, Any]]]:
    raw_dir = Path(config.output_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    manifold_rows: list[dict[str, Any]] = []
    for model in _frontier_probe_models(config):
        slug = _model_slug(model)
        for feedback, feedback_mode in (("true", "true"), ("contrarian", "contrarian")):
            case = {
                "name": f"contrarian_audit_{slug}_{feedback}",
                "strategy": "signal-weighted",
                "risk": "max-position",
                "execution": "realistic",
                "analyst_names": ("poe-llm",),
                "llm_model": model,
                "llm_use_risk_feedback": True,
                "llm_risk_feedback_mode": feedback_mode,
            }
            trajectory, metrics = _run_case(config, 0, str(case["name"]), case, real_market=True, llm_market=True)
            write_json(raw_dir / f"{case['name']}_trajectory.json", trajectory.to_dict())
            rows = _intent_step_rows(str(case["name"]), trajectory, feedback)
            for row in rows:
                row["model"] = model
            step_rows.extend(rows)
            for row in _feedback_manifold_rows(str(case["name"]), feedback, trajectory):
                row["model"] = model
                manifold_rows.append(row)
            split = max(1, len(rows) // 4)
            late = rows[-split:]
            summary_rows.append(
                {
                    "case": case["name"],
                    "model": model,
                    "feedback": feedback,
                    "steps": len(rows),
                    "total_return": metrics.get("total_return", 0.0),
                    "sharpe": metrics.get("sharpe", 0.0),
                    "max_drawdown": metrics.get("max_drawdown", 0.0),
                    "risk_clipped_decisions": metrics.get("risk_clipped_decisions", 0),
                    "risk_violation_count": metrics.get("risk_violation_count", 0),
                    "mean_intended_abs": _mean([float(row["intended_abs_exposure"]) for row in rows]),
                    "late_intended_abs": _mean([float(row["intended_abs_exposure"]) for row in late]),
                    "mean_calibration_score": _mean([float(row["calibration_score"]) for row in rows]),
                    "late_calibration_score": _mean([float(row["calibration_score"]) for row in late]),
                    "intent_drift": _intent_drift(rows),
                    "contrarian_conservative_shift": "",
                    "return_delta_vs_true": "",
                    "drawdown_delta_vs_true": "",
                    "late_intent_delta_vs_true": "",
                    "over_compliance_flag": "",
                    "false_audit_harm_flag": "",
                    "trust_calibration_failure": "",
                }
            )
    true_by_model = {
        str(row["model"]): row for row in summary_rows if row.get("feedback") == "true"
    }
    _annotate_contrarian_effects(summary_rows, true_by_model)
    return {"summary_rows": summary_rows, "step_rows": step_rows, "manifold_rows": manifold_rows}


def _annotate_contrarian_effects(
    summary_rows: list[dict[str, Any]],
    true_by_model: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    baselines = true_by_model or {str(row["model"]): row for row in summary_rows if row.get("feedback") == "true"}
    for row in summary_rows:
        row.setdefault("return_delta_vs_true", "")
        row.setdefault("drawdown_delta_vs_true", "")
        row.setdefault("late_intent_delta_vs_true", "")
        row.setdefault("over_compliance_flag", "")
        row.setdefault("false_audit_harm_flag", "")
        row.setdefault("trust_calibration_failure", "")
        baseline = baselines.get(str(row.get("model", "")))
        if not baseline or row.get("feedback") != "contrarian":
            continue
        conservative_shift = float(baseline["late_intended_abs"]) - float(row["late_intended_abs"])
        return_delta = float(row["total_return"]) - float(baseline["total_return"])
        drawdown_delta = float(row["max_drawdown"]) - float(baseline["max_drawdown"])
        row["contrarian_conservative_shift"] = conservative_shift
        row["return_delta_vs_true"] = return_delta
        row["drawdown_delta_vs_true"] = drawdown_delta
        row["late_intent_delta_vs_true"] = float(row["late_intended_abs"]) - float(baseline["late_intended_abs"])
        row["over_compliance_flag"] = int(conservative_shift > 0.05)
        row["false_audit_harm_flag"] = int(return_delta < 0.0 or drawdown_delta < 0.0)
        row["trust_calibration_failure"] = int(conservative_shift > 0.0)
    return summary_rows


def _write_cot_free_chart(charts_dir: Path, summary_rows: list[dict[str, Any]]) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    bars = []
    for row in summary_rows:
        model = str(row["model"])
        mode = str(row["mode"])
        for view, key in (("language", "language_effective_rank_delta"), ("intent", "intent_effective_rank_delta")):
            value = row.get(key, "")
            if value != "":
                bars.append((f"{model} {mode} {view}", float(value)))
    write_bar_chart(charts_dir / "cot_free_rank_delta.svg", "CoT-Free Rank Contraction", bars)


def _write_noise_chart(charts_dir: Path, summary_rows: list[dict[str, Any]]) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    series: dict[str, list[tuple[float, float]]] = {}
    for row in summary_rows:
        value = row.get("mean_early_warning_ba", "")
        if value == "":
            continue
        series.setdefault(str(row["view"]), []).append((float(row["epsilon"]), float(value)))
    write_line_chart(charts_dir / "noise_injection_ba.svg", "Noise Injection Early Warning", "epsilon", "balanced accuracy", series)


def _write_contrarian_chart(charts_dir: Path, summary_rows: list[dict[str, Any]]) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    bars = [
        (str(row["model"]), float(row["contrarian_conservative_shift"]))
        for row in summary_rows
        if row.get("feedback") == "contrarian" and row.get("contrarian_conservative_shift") != ""
    ]
    write_bar_chart(charts_dir / "contrarian_intent_shift.svg", "Contrarian Audit Conservative Shift", bars)


def _write_frontier_feedback_charts(
    charts_dir: Path,
    summary_rows: list[dict[str, Any]],
    learning_rows: list[dict[str, Any]],
) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    ordered_summary = sorted(summary_rows, key=lambda row: (str(row["model"]), str(row["feedback"])))
    write_bar_chart(
        charts_dir / "frontier_feedback_returns.svg",
        "Cached Poe Frontier Feedback: Return",
        [(f"{row['model']} {row['feedback']}", float(row.get("total_return", 0.0))) for row in ordered_summary],
    )
    write_bar_chart(
        charts_dir / "frontier_feedback_late_gap.svg",
        "Cached Poe Frontier Feedback: Late Calibration Gap",
        [(f"{row['model']} {row['feedback']}", float(row.get("late_calibration_gap", 0.0))) for row in ordered_summary],
        y_min=0.0,
    )
    true_learning = [row for row in learning_rows if row.get("feedback") == "true"]
    series = {
        str(row["model"]): [
            (0.0, float(row.get("early_calibration_score", 0.0))),
            (1.0, float(row.get("late_calibration_score", 0.0))),
        ]
        for row in true_learning
    }
    write_line_chart(
        charts_dir / "frontier_feedback_true_learning.svg",
        "True Feedback Calibration Learning",
        "early to late",
        "calibration score",
        series,
    )


def _risk_gate_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    triggered = 0
    for row in rows:
        clipped = int(float(row.get("clipped_count", 0)))
        blocked = int(float(row.get("blocked_count", 0)))
        violations = int(float(row.get("risk_violations", 0)))
        if clipped or blocked or violations:
            triggered += 1
    return triggered / len(rows)


def _feedback_manifold_rows(case_name: str, feedback: str, trajectory: Trajectory) -> list[dict[str, Any]]:
    drawdowns = _drawdowns(trajectory)
    if not drawdowns:
        return []
    trough_idx = min(range(len(drawdowns)), key=lambda idx: drawdowns[idx])
    pre_window = set(range(max(0, trough_idx - 4), trough_idx))
    drawdown_window = set(range(trough_idx, min(len(drawdowns), trough_idx + 4)))
    sequences: dict[str, list[dict[str, Any]]] = {"plan": [], "fused": []}
    for idx, step in enumerate(trajectory.steps):
        if idx in pre_window:
            phase = "pre_drawdown"
        elif idx in drawdown_window:
            phase = "drawdown"
        else:
            phase = "normal"
        plan_vec = _embed_text(_plan_text(step))
        fused_vec = _normalize([*plan_vec, *_embed_text(_reflect_text(step)), *_structured_features(step, drawdowns[idx])])
        sequences["plan"].append({"step": idx, "phase": phase, "vector": plan_vec, "drawdown": drawdowns[idx]})
        sequences["fused"].append({"step": idx, "phase": phase, "vector": fused_vec, "drawdown": drawdowns[idx]})
    rows = []
    for view, sequence in sequences.items():
        row = _manifold_row(case_name, view, sequence)
        row["feedback"] = feedback
        rows.append(row)
    return rows


def _intent_step_rows(case_name: str, trajectory: Trajectory, feedback: str) -> list[dict[str, Any]]:
    rows = []
    for idx, step in enumerate(trajectory.steps):
        risk_report = step.risk_report if isinstance(step.risk_report, dict) else {}
        intended_abs = _intended_abs_exposure(step.decisions)
        approved_abs = _intended_abs_exposure(step.approved_decisions)
        gap = _calibration_gap(step.decisions, step.approved_decisions)
        rows.append(
            {
                "case": case_name,
                "feedback": feedback,
                "step": idx,
                "timestamp": step.timestamp.isoformat(),
                "intended_abs_exposure": intended_abs,
                "approved_abs_exposure": approved_abs,
                "calibration_gap": gap,
                "calibration_score": 1.0 - min(1.0, gap / max(1.0, intended_abs)),
                "clipped_count": int(risk_report.get("clipped_count", 0) or 0),
                "blocked_count": int(risk_report.get("blocked_count", 0) or 0),
                "risk_violations": len(step.risk_violations),
                "mean_abs_signal_score": _mean_abs_signal_score(step.signals),
                "intent_vector_norm": math.sqrt(sum(float(decision.get("target_weight", 0.0)) ** 2 for decision in step.decisions)),
                "intent_vector_hash_embedding_norm": math.sqrt(sum(value * value for value in _embed_text(_plan_text(step)))),
            }
        )
    return rows


def _intent_drift(rows: list[dict[str, Any]]) -> float:
    if len(rows) < 2:
        return 0.0
    split = max(1, len(rows) // 4)
    early = _mean([float(row["intended_abs_exposure"]) for row in rows[:split]])
    late = _mean([float(row["intended_abs_exposure"]) for row in rows[-split:]])
    return late - early


def _run_case(
    config: PaperExperimentConfig,
    seed: int,
    case_name: str,
    case: dict[str, Any],
    *,
    real_market: bool = False,
    llm_market: bool = False,
) -> tuple[Trajectory, dict[str, Any]]:
    symbols = config.real_symbols if real_market else config.symbols
    data_dir = config.real_data_dir
    frequency = config.real_data_frequency
    max_periods = config.llm_periods if llm_market else None
    if str(case.get("name", "")).startswith("intraday_50"):
        symbols = config.intraday_symbols
        data_dir = config.intraday_data_dir
        frequency = "hourly"
        max_periods = config.intraday_max_periods
        max_periods = int(case.get("intraday_max_periods", max_periods))
        real_data_start = None
        real_data_end = None
    else:
        real_data_start = str(case.get("real_data_start", config.real_data_start))
        real_data_end = str(case.get("real_data_end", config.real_data_end))
    system = build_default_system(
        name=case_name,
        symbols=symbols,
        periods=config.periods,
        seed=seed,
        strategy_name=case.get("strategy", "signal-weighted"),
        risk_name=case.get("risk", "max-position"),
        execution_mode=case.get("execution", "realistic"),
        commission_bps=float(case.get("commission_bps", 1.0)),
        slippage_bps=float(case.get("slippage_bps", 2.0)),
        participation_rate=float(case.get("participation_rate", 0.05)),
        latency_steps=int(case.get("latency_steps", 1)),
        market_impact=float(case.get("market_impact", 0.15)),
        max_position_weight=float(case.get("max_position_weight", 0.35)),
        max_gross_exposure=float(case.get("max_gross_exposure", 1.0)),
        max_turnover=float(case.get("max_turnover", 0.75)),
        analyst_names=tuple(case.get("analyst_names", ("momentum", "macro-news"))),
        data_source="csv" if real_market else "synthetic",
        real_data_dir=data_dir,
        real_data_frequency=frequency,
        real_data_start=real_data_start,
        real_data_end=real_data_end,
        real_data_max_periods=max_periods,
        llm_model=str(case.get("llm_model", config.llm_model)),
        llm_cache_path=config.llm_cache_path,
        llm_use_risk_feedback=bool(case.get("llm_use_risk_feedback", True)),
        llm_risk_feedback_mode=str(case.get("llm_risk_feedback_mode", "true")),
        llm_output_mode=str(case.get("llm_output_mode", "rationale")),
        synthetic_volatility_scale=float(case.get("synthetic_volatility_scale", 1.0)),
        synthetic_trend_scale=float(case.get("synthetic_trend_scale", 1.0)),
        synthetic_seasonal_scale=float(case.get("synthetic_seasonal_scale", 1.0)),
        synthetic_macro_scale=float(case.get("synthetic_macro_scale", 1.0)),
        synthetic_tail_df=case.get("synthetic_tail_df"),
        synthetic_jump_probability=float(case.get("synthetic_jump_probability", 0.0)),
        synthetic_jump_scale=float(case.get("synthetic_jump_scale", 0.0)),
    )
    return system.run()


def _intraday_correlation_summary(config: PaperExperimentConfig) -> dict[str, Any]:
    data = _load_intraday_close_matrix(config)
    returns_by_symbol: dict[str, list[float]] = {}
    for symbol, prices in data.items():
        returns_by_symbol[symbol] = [(prices[idx] / prices[idx - 1]) - 1.0 for idx in range(1, len(prices)) if prices[idx - 1]]
    symbols = list(returns_by_symbol)
    correlations = []
    for left_idx, left in enumerate(symbols):
        for right in symbols[left_idx + 1 :]:
            corr = _correlation(returns_by_symbol[left], returns_by_symbol[right])
            if corr != "":
                correlations.append(float(corr))
    abs_corr = [abs(value) for value in correlations]
    eigen = _power_iteration_first_component(returns_by_symbol)
    return {
        "symbols": len(symbols),
        "bars": min(len(values) for values in data.values()) if data else 0,
        "frequency": "1h",
        "correlation_pairs": len(correlations),
        "correlation_mean_abs": _mean(abs_corr),
        "correlation_p90_abs": _percentile(abs_corr, 0.9),
        "effective_assets": 1.0 / _mean(abs_corr) if abs_corr and _mean(abs_corr) else "",
        "first_principal_component_share": eigen,
    }


def _intraday_pair_correlations(config: PaperExperimentConfig) -> dict[tuple[str, str], float]:
    data = _load_intraday_close_matrix(config)
    returns_by_symbol: dict[str, list[float]] = {}
    for symbol, prices in data.items():
        returns_by_symbol[symbol] = [(prices[idx] / prices[idx - 1]) - 1.0 for idx in range(1, len(prices)) if prices[idx - 1]]
    symbols = list(returns_by_symbol)
    pairs: dict[tuple[str, str], float] = {}
    for left_idx, left in enumerate(symbols):
        for right in symbols[left_idx + 1 :]:
            corr = _correlation(returns_by_symbol[left], returns_by_symbol[right])
            if corr != "":
                pairs[(left, right)] = float(corr)
    return pairs


def _intraday_blind_spot_rows(
    trajectory: Trajectory,
    pair_correlations: dict[tuple[str, str], float],
    topn: int = 8,
    case_name: str = "",
    model: str = "",
) -> list[dict[str, Any]]:
    rows = []
    for step_idx, step in enumerate(trajectory.steps):
        decisions = {str(decision.get("symbol", "")): decision for decision in step.decisions}
        approved = {str(decision.get("symbol", "")): decision for decision in step.approved_decisions}
        risk_report = step.risk_report if isinstance(step.risk_report, dict) else {}
        for (left, right), corr in pair_correlations.items():
            left_decision = decisions.get(left)
            right_decision = decisions.get(right)
            if not left_decision or not right_decision:
                continue
            left_weight = abs(float(left_decision.get("target_weight", 0.0)))
            right_weight = abs(float(right_decision.get("target_weight", 0.0)))
            combined_intended = left_weight + right_weight
            if combined_intended < 0.12:
                continue
            left_approved = abs(float(approved.get(left, {}).get("target_weight", 0.0)))
            right_approved = abs(float(approved.get(right, {}).get("target_weight", 0.0)))
            rationale = " ".join([str(left_decision.get("rationale", "")), str(right_decision.get("rationale", ""))])
            rows.append(
                {
                    "case": case_name or trajectory.experiment_name,
                    "model": model or _trajectory_model(trajectory),
                    "step": step_idx,
                    "timestamp": step.timestamp.isoformat(),
                    "pair": f"{left}/{right}",
                    "correlation": corr,
                    "abs_correlation": abs(corr),
                    "combined_intended_weight": combined_intended,
                    "approved_pair_weight": left_approved + right_approved,
                    "clipped_count": int(risk_report.get("clipped_count", 0) or 0),
                    "risk_violations": len(step.risk_violations),
                    "rationale_theme": _rationale_theme(rationale),
                    "rationale_excerpt": rationale[:220],
                    "blind_spot_score": abs(corr) * combined_intended,
                }
            )
    rows.sort(key=lambda row: (float(row["blind_spot_score"]), float(row["abs_correlation"])), reverse=True)
    return rows[:topn]


def _rationale_theme(text: str) -> str:
    lowered = text.lower()
    themes = []
    for label, keywords in {
        "single-name momentum": ("momentum", "bullish", "positive", "upward", "trend"),
        "volatility caution": ("volatility", "volatile", "caution", "risk"),
        "weak diversification": ("correlation", "covariance", "diversification", "sector", "coupling"),
        "limited evidence": ("limited", "insufficient", "single", "lack"),
    }.items():
        if any(keyword in lowered for keyword in keywords):
            themes.append(label)
    return "; ".join(themes) if themes else "name-level rationale"


def _load_intraday_close_matrix(config: PaperExperimentConfig) -> dict[str, list[float]]:
    from tradearena.data.csv_market import CsvMarketDataProvider

    provider = CsvMarketDataProvider(
        data_dir=config.intraday_data_dir,
        symbols=config.intraday_symbols,
        frequency="hourly",
    )
    snapshots = provider.stream()
    data = {symbol: [] for symbol in config.intraday_symbols}
    for snapshot in snapshots:
        for symbol in config.intraday_symbols:
            data[symbol].append(snapshot.bars[symbol].close)
    return data


def _correlation(left: list[float], right: list[float]) -> float | str:
    n = min(len(left), len(right))
    if n < 2:
        return ""
    left = left[-n:]
    right = right[-n:]
    mean_left = _mean(left)
    mean_right = _mean(right)
    cov = sum((l - mean_left) * (r - mean_right) for l, r in zip(left, right, strict=True))
    var_left = sum((l - mean_left) ** 2 for l in left)
    var_right = sum((r - mean_right) ** 2 for r in right)
    denom = math.sqrt(var_left * var_right)
    return cov / denom if denom else ""


def _pearson(left: list[float], right: list[float]) -> float:
    value = _correlation(left, right)
    return float(value) if value != "" else 0.0


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[idx]


def _power_iteration_first_component(returns_by_symbol: dict[str, list[float]], iterations: int = 40) -> float:
    symbols = list(returns_by_symbol)
    n = len(symbols)
    if n == 0:
        return 0.0
    standardized = []
    for symbol in symbols:
        values = returns_by_symbol[symbol]
        mean = _mean(values)
        std = math.sqrt(_mean([(value - mean) ** 2 for value in values]))
        standardized.append([(value - mean) / std if std else 0.0 for value in values])
    corr = [[_correlation(standardized[i], standardized[j]) or 0.0 for j in range(n)] for i in range(n)]
    vector = [1.0 / math.sqrt(n)] * n
    for _ in range(iterations):
        nxt = [sum(corr[i][j] * vector[j] for j in range(n)) for i in range(n)]
        norm = math.sqrt(sum(value * value for value in nxt))
        if not norm:
            return 0.0
        vector = [value / norm for value in nxt]
    eigenvalue = sum(vector[i] * sum(corr[i][j] * vector[j] for j in range(n)) for i in range(n))
    return eigenvalue / n if n else 0.0


def _mean_herfindahl(trajectory: Trajectory) -> float:
    values = []
    for step in trajectory.steps:
        equity = float(step.portfolio.get("equity", 0.0))
        if not equity:
            continue
        weights = [
            abs(float(qty) * float(step.portfolio.get("last_prices", {}).get(symbol, 0.0)) / equity)
            for symbol, qty in step.portfolio.get("positions", {}).items()
        ]
        values.append(sum(weight * weight for weight in weights))
    return _mean(values)


def _mean_active_positions(trajectory: Trajectory) -> float:
    counts = [
        sum(1 for qty in step.portfolio.get("positions", {}).values() if abs(float(qty)) > 1e-9)
        for step in trajectory.steps
    ]
    return _mean([float(count) for count in counts])


def _calibration_gap(decisions: list[dict[str, Any]], approved_decisions: list[dict[str, Any]]) -> float:
    approved_by_symbol = {str(decision.get("symbol", "")): decision for decision in approved_decisions}
    gap = 0.0
    for decision in decisions:
        symbol = str(decision.get("symbol", ""))
        approved = approved_by_symbol.get(symbol, {})
        gap += abs(float(decision.get("target_weight", 0.0)) - float(approved.get("target_weight", 0.0)))
    return gap


def _trajectory_model(trajectory: Trajectory) -> str:
    for step in trajectory.steps:
        for signal in step.signals:
            metadata = signal.get("metadata", {}) if isinstance(signal, dict) else {}
            if isinstance(metadata, dict) and metadata.get("model"):
                return str(metadata["model"])
    return ""


def _intended_abs_exposure(decisions: list[dict[str, Any]]) -> float:
    return sum(abs(float(decision.get("target_weight", 0.0))) for decision in decisions)


def _mean_abs_signal_score(signals: list[dict[str, Any]]) -> float:
    if not signals:
        return 0.0
    return sum(abs(float(signal.get("score", 0.0))) for signal in signals) / len(signals)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _plan_text(step) -> str:
    parts = []
    for signal in step.signals:
        parts.append(str(signal.get("rationale", "")))
        metadata = signal.get("metadata", {}) if isinstance(signal.get("metadata", {}), dict) else {}
        parts.append(str(metadata.get("risk_notes", "")))
    for decision in step.decisions:
        parts.append(str(decision.get("rationale", "")))
    return " ".join(part for part in parts if part)


def _reflect_text(step) -> str:
    parts = []
    reflect = step.agent_trace.get("reflect", {}) if isinstance(step.agent_trace, dict) else {}
    parts.append(str(reflect))
    execution = step.execution_report if isinstance(step.execution_report, dict) else {}
    parts.append(
        " ".join(
            [
                f"fills {len(step.fills)}",
                f"orders {len(step.orders)}",
                f"rejected {execution.get('rejected_orders', 0)}",
                f"pending {execution.get('pending_orders', 0)}",
                f"slippage {execution.get('total_slippage', 0.0)}",
                f"risk_violations {len(step.risk_violations)}",
            ]
        )
    )
    return " ".join(parts)


def _structured_features(step, drawdown: float) -> list[float]:
    scores = [float(signal.get("score", 0.0)) for signal in step.signals]
    confidences = [float(signal.get("confidence", 0.0)) for signal in step.signals]
    fills = step.fills
    fill_ratios = [float(fill.get("fill_ratio", 0.0)) for fill in fills]
    execution = step.execution_report if isinstance(step.execution_report, dict) else {}
    return _normalize(
        [
            sum(scores) / len(scores) if scores else 0.0,
            sum(confidences) / len(confidences) if confidences else 0.0,
            float(len(step.risk_violations)),
            sum(fill_ratios) / len(fill_ratios) if fill_ratios else 0.0,
            float(execution.get("total_slippage", 0.0)) / 10000.0,
            drawdown,
        ]
    )


def _structured_text(step) -> str:
    risk_report = step.risk_report if isinstance(step.risk_report, dict) else {}
    execution = step.execution_report if isinstance(step.execution_report, dict) else {}
    parts = [
        f"risk clipped {risk_report.get('clipped_count', 0)}",
        f"risk blocked {risk_report.get('blocked_count', 0)}",
        f"risk violations {len(step.risk_violations)}",
        f"rejected orders {execution.get('rejected_orders', 0)}",
        f"pending orders {execution.get('pending_orders', 0)}",
        f"slippage {execution.get('total_slippage', 0.0)}",
    ]
    return " ".join(parts)


def _drawdowns(trajectory: Trajectory) -> list[float]:
    equities = [float(step.portfolio.get("equity", 0.0)) for step in trajectory.steps]
    if not equities:
        return []
    peak = equities[0]
    drawdowns = []
    for equity in equities:
        peak = max(peak, equity)
        drawdowns.append((equity / peak) - 1.0 if peak else 0.0)
    return drawdowns


def _drawdown_phases(drawdowns: list[float], width: int = 4) -> list[str]:
    if not drawdowns:
        return []
    trough_idx = min(range(len(drawdowns)), key=lambda idx: drawdowns[idx])
    pre_window = set(range(max(0, trough_idx - width), trough_idx))
    drawdown_window = set(range(trough_idx, min(len(drawdowns), trough_idx + width)))
    phases = []
    for idx in range(len(drawdowns)):
        if idx in pre_window:
            phases.append("pre_drawdown")
        elif idx in drawdown_window:
            phases.append("drawdown")
        else:
            phases.append("normal")
    return phases


def _trajectory_symbols(trajectory: Trajectory) -> list[str]:
    symbols = set()
    for step in trajectory.steps:
        for decision in step.decisions:
            symbols.add(str(decision.get("symbol", "")))
        prices = step.observation.get("prices", {}) if isinstance(step.observation, dict) else {}
        if isinstance(prices, dict):
            symbols.update(str(symbol) for symbol in prices)
    return sorted(symbol for symbol in symbols if symbol)


def _intent_weight_vector(step, symbols: list[str]) -> list[float]:
    by_symbol = {str(decision.get("symbol", "")): float(decision.get("target_weight", 0.0)) for decision in step.decisions}
    weights = [by_symbol.get(symbol, 0.0) for symbol in symbols]
    return _normalize([*weights, sum(abs(weight) for weight in weights), max([abs(weight) for weight in weights] or [0.0])])


def _noisy_market_vectors(case_name: str, trajectory: Trajectory, epsilon: float) -> list[list[float]]:
    symbols = _trajectory_symbols(trajectory)
    noisy_prices: list[dict[str, float]] = []
    for idx, step in enumerate(trajectory.steps):
        prices = step.observation.get("prices", {}) if isinstance(step.observation, dict) else {}
        noised: dict[str, float] = {}
        for symbol in symbols:
            price = float(prices.get(symbol, 0.0)) if isinstance(prices, dict) else 0.0
            shock = _stable_gaussian(f"{case_name}:{epsilon}:{idx}:{symbol}")
            noised[symbol] = max(0.0001, price * (1.0 + epsilon * shock))
        noisy_prices.append(noised)
    vectors: list[list[float]] = []
    for idx, current in enumerate(noisy_prices):
        previous = noisy_prices[idx - 1] if idx else current
        returns = [
            (current[symbol] / previous[symbol]) - 1.0
            if previous.get(symbol)
            else 0.0
            for symbol in symbols
        ]
        mean_return = _mean(returns)
        centered = [value - mean_return for value in returns]
        variance = _mean([value * value for value in centered])
        vectors.append(
            _normalize(
                [
                    *returns,
                    mean_return,
                    math.sqrt(variance),
                    max([abs(value) for value in returns] or [0.0]),
                ]
            )
        )
    return vectors


def _stable_gaussian(key: str) -> float:
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return rng.gauss(0.0, 1.0)


def _embed_text(text: str, dims: int = 64) -> list[float]:
    vector = [0.0] * dims
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    return _normalize(vector)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower())


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dims = len(vectors[0])
    return _normalize([sum(vector[idx] for vector in vectors) / len(vectors) for idx in range(dims)])


def _cosine_distance(left: list[float], right: list[float]) -> float | str:
    if not left or not right:
        return ""
    return 1.0 - sum(l * r for l, r in zip(left, right, strict=True))


def _euclidean_distance(left: list[float], right: list[float]) -> float | str:
    if not left or not right:
        return ""
    return math.sqrt(sum((l - r) ** 2 for l, r in zip(left, right, strict=True)))


def _adjacent_distances(vectors: list[list[float]]) -> list[float]:
    distances = []
    for idx in range(1, len(vectors)):
        distance = _euclidean_distance(vectors[idx - 1], vectors[idx])
        if distance != "":
            distances.append(float(distance))
    return distances


def _early_warning_balanced_accuracy(normal_vectors: list[list[float]], pre_vectors: list[list[float]]) -> float | str:
    if len(normal_vectors) < 2 or len(pre_vectors) < 2:
        return ""
    normal_centroid = _centroid(normal_vectors)
    pre_centroid = _centroid(pre_vectors)
    normal_score = 0.0
    for vector in normal_vectors:
        normal_distance = _cosine_distance(vector, normal_centroid)
        pre_distance = _cosine_distance(vector, pre_centroid)
        if normal_distance == pre_distance:
            normal_score += 0.5
        else:
            normal_score += float(normal_distance < pre_distance)
    pre_score = 0.0
    for vector in pre_vectors:
        normal_distance = _cosine_distance(vector, normal_centroid)
        pre_distance = _cosine_distance(vector, pre_centroid)
        if normal_distance == pre_distance:
            pre_score += 0.5
        else:
            pre_score += float(pre_distance < normal_distance)
    return 0.5 * ((normal_score / len(normal_vectors)) + (pre_score / len(pre_vectors)))


def _manifold_row(case_name: str, view: str, sequence: list[dict[str, Any]]) -> dict[str, Any]:
    vectors = [item["vector"] for item in sequence]
    phases = [str(item["phase"]) for item in sequence]
    step_distances = [
        _euclidean_distance(vectors[idx - 1], vectors[idx])
        for idx in range(1, len(vectors))
        if vectors[idx - 1] and vectors[idx]
    ]
    phase_step_distances = {"normal": [], "pre_drawdown": [], "drawdown": []}
    for idx in range(1, len(vectors)):
        distance = _euclidean_distance(vectors[idx - 1], vectors[idx])
        if distance == "":
            continue
        phase_step_distances.setdefault(phases[idx], []).append(float(distance))
    normal_vectors = [item["vector"] for item in sequence if item["phase"] == "normal"]
    pre_vectors = [item["vector"] for item in sequence if item["phase"] == "pre_drawdown"]
    normal_step = _mean(phase_step_distances.get("normal", []))
    pre_step = _mean(phase_step_distances.get("pre_drawdown", []))
    return {
        "case": case_name,
        "view": view,
        "steps": len(sequence),
        "path_length": sum(float(value) for value in step_distances),
        "path_length_per_step": sum(float(value) for value in step_distances) / max(1, len(sequence) - 1),
        "normal_step_distance": normal_step,
        "pre_step_distance": pre_step,
        "drawdown_step_distance": _mean(phase_step_distances.get("drawdown", [])),
        "pre_to_normal_step_ratio": pre_step / normal_step if normal_step else "",
        "normal_effective_rank": _effective_rank(normal_vectors),
        "pre_effective_rank": _effective_rank(pre_vectors),
        "effective_rank_delta": (
            float(_effective_rank(normal_vectors)) - float(_effective_rank(pre_vectors))
            if _effective_rank(normal_vectors) != "" and _effective_rank(pre_vectors) != ""
            else ""
        ),
        "drawdown_effective_rank": _effective_rank([item["vector"] for item in sequence if item["phase"] == "drawdown"]),
        "pre_nn_pre_rate": _pre_nn_pre_rate(sequence),
        "step_distance_cv": _coefficient_of_variation([float(value) for value in step_distances]),
        "turn_rate": _turn_rate(vectors),
    }


def _coefficient_of_variation(values: list[float]) -> float | str:
    if len(values) < 2:
        return ""
    mean = _mean(values)
    if not mean:
        return ""
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / mean


def _turn_rate(vectors: list[list[float]]) -> float | str:
    if len(vectors) < 3:
        return ""
    turns = []
    for idx in range(2, len(vectors)):
        left = [a - b for a, b in zip(vectors[idx - 1], vectors[idx - 2], strict=True)]
        right = [a - b for a, b in zip(vectors[idx], vectors[idx - 1], strict=True)]
        left = _normalize(left)
        right = _normalize(right)
        distance = _cosine_distance(left, right)
        if distance != "":
            turns.append(float(distance))
    return _mean(turns)


def _effective_rank(vectors: list[list[float]]) -> float | str:
    if len(vectors) < 2:
        return ""
    dims = len(vectors[0])
    means = [sum(vector[idx] for vector in vectors) / len(vectors) for idx in range(dims)]
    variances = [
        sum((vector[idx] - means[idx]) ** 2 for vector in vectors) / (len(vectors) - 1)
        for idx in range(dims)
    ]
    total = sum(variances)
    denom = sum(value * value for value in variances)
    return (total * total / denom) if denom else 0.0


def _pre_nn_pre_rate(sequence: list[dict[str, Any]]) -> float | str:
    labeled = [(idx, item["phase"], item["vector"]) for idx, item in enumerate(sequence) if item["phase"] in {"normal", "pre_drawdown"}]
    pre_items = [item for item in labeled if item[1] == "pre_drawdown"]
    if len(pre_items) < 2 or len(labeled) < 3:
        return ""
    hits = 0
    for idx, _, vector in pre_items:
        nearest_phase = ""
        nearest_distance = float("inf")
        for other_idx, other_phase, other_vector in labeled:
            if other_idx == idx:
                continue
            distance = _cosine_distance(vector, other_vector)
            if distance != "" and float(distance) < nearest_distance:
                nearest_distance = float(distance)
                nearest_phase = str(other_phase)
        hits += int(nearest_phase == "pre_drawdown")
    return hits / len(pre_items)


def _safe_symbol(symbol: str) -> str:
    return symbol.replace("^", "").replace("/", "-")


def _safe_case_token(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _metrics_row(case_name: str, group: str, seed: int | str, execution_mode: str, risk_mode: str, metrics: dict[str, Any]) -> dict[str, Any]:
    row = {
        "case": case_name,
        "group": group,
        "seed": seed,
        "execution_mode": execution_mode,
        "risk_mode": risk_mode,
    }
    for key in KEY_METRICS:
        row[key] = metrics.get(key, "")
    return row


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        base = str(row["case"]).rsplit("_seed", 1)[0]
        grouped.setdefault(base, []).append(row)

    aggregate = []
    for case, group_rows in grouped.items():
        group = str(group_rows[0].get("group", "aggregate"))
        row = {
            "case": f"{case}_mean",
            "group": f"{group}_aggregate",
            "seed": "mean",
            "execution_mode": group_rows[0].get("execution_mode", ""),
            "risk_mode": group_rows[0].get("risk_mode", ""),
        }
        for metric in KEY_METRICS:
            values = [float(item[metric]) for item in group_rows if item.get(metric) not in ("", None)]
            row[metric] = sum(values) / len(values) if values else ""
        aggregate.append(row)
    return aggregate
