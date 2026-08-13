from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TRACKED_FILE_BYTES = 25 * 1024 * 1024
REQUIRED_FILES = [
    "README.md",
    "docs/assets/trellm_readme_audit_system_banner_v2.svg",
    "CITATION.cff",
    "docs/getting_started.md",
    "docs/advanced_integrations_security.md",
    "docs/broker_adapter_contract.md",
    "docs/agent_skills.md",
    "docs/agent_skills_index.md",
    "docs/financial_audit_agent_benchmark.md",
    "docs/poe_skill_task_experiments.md",
    "docs/technical_report.md",
    "docs/benchmark_maturity.md",
    "docs/v0_2_credibility_audit.md",
    "docs/research_report.md",
    "docs/external_validation.md",
    "docs/claim_boundaries.md",
    "docs/evidence_labels.md",
    "docs/benchmark_v0_2_spec.md",
    "docs/benchmark_v0_3_protocol.md",
    "docs/execution_calibration_priority.md",
    "docs/execution_model_boundaries.md",
    "docs/reproduction_pack_v0_2.md",
    "docs/reproduction_pack_v0_3.md",
    "docs/community_participation.md",
    "docs/community_tasks.md",
    "docs/community_operations.md",
    "docs/narrative_positioning.md",
    "docs/plugin_development.md",
    "docs/benchmark_challenges.md",
    "docs/evaluation_rigor.md",
    "docs/market_rules.md",
    "docs/observability.md",
    "docs/artifact_portability.md",
    "docs/demo_matrix.md",
    "docs/launch/release_notes_v0.2.0.md",
    "docs/launch/release_notes_v0.2.1.md",
    "docs/launch/release_artifacts_v0.2.0.md",
    "docs/launch/release_artifacts_v0.2.0.json",
    "docs/launch/release_candidate_v0.2.1.md",
    "docs/launch/release_candidate_v0.2.1.json",
    "docs/results/benchmark_v0_2.md",
    "docs/results/llm_live_baseline.md",
    "docs/results/llm_live_baseline.json",
    "docs/results/execution_quote_fill_calibration_sample.md",
    "docs/results/execution_quote_fill_calibration_sample.json",
    "docs/results/execution_quote_fill_calibration_binance_sample.md",
    "docs/results/execution_quote_fill_calibration_binance_sample.json",
    "docs/results/execution_replay_calibration_loop.md",
    "docs/results/execution_replay_calibration_loop.json",
    "docs/results/execution_calibration_stability.md",
    "docs/results/execution_calibration_stability.json",
    "docs/results/external_validation_bundle.md",
    "docs/results/external_validation_bundle.json",
    "docs/results/market_rules_fixture.md",
    "docs/results/market_rules_fixture.json",
    "docs/results/llm_live_baseline_manifest/manifest.json",
    "docs/results/llm_live_baseline_manifest/poe_gpt55_live_smoke_2026-05-18_summary.json",
    "docs/results/community_registry.md",
    "docs/results/community_registry.html",
    "docs/results/model_matrix/leaderboard_model_matrix.md",
    "docs/results/model_matrix/leaderboard_model_matrix.csv",
    "docs/results/model_matrix/leaderboard_model_matrix_aggregate.csv",
    "docs/results/model_matrix/leaderboard_model_matrix_scenario_aggregate.csv",
    "docs/results/model_matrix/leaderboard_model_matrix_significance.csv",
    "docs/results/model_matrix/leaderboard_execution_shock_aggregate.csv",
    "docs/results/real_market_matrix/real_market_model_matrix.md",
    "docs/results/real_market_matrix/real_market_model_matrix.csv",
    "docs/results/real_market_matrix/real_market_model_matrix_aggregate.csv",
    "docs/results/real_market_matrix/real_market_model_matrix_scenario_aggregate.csv",
    "docs/results/real_market_matrix/real_market_model_matrix_significance.csv",
    "docs/results/real_market_matrix/real_market_walk_forward.csv",
    "docs/results/v0_3_direct_api_pilot/direct_api_pilot_rows.csv",
    "docs/results/v0_3_direct_api_pilot/direct_api_pilot_summary.json",
    "docs/results/v0_3_direct_api_pilot/direct_api_pilot_summary.md",
    "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_rows.csv",
    "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_coverage.csv",
    "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json",
    "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.md",
    "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv",
    "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_coverage.csv",
    "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.json",
    "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.md",
    "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.jsonl",
    "docs/results/v0_3_direct_api_call_packets/direct_api_call_packet_manifest.csv",
    "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets_summary.json",
    "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.md",
    "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist_items.csv",
    "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist_summary.json",
    "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist.md",
    "docs/results/v0_3_execution_ladder/execution_ladder_rows.csv",
    "docs/results/v0_3_execution_ladder/execution_ladder_aggregate.csv",
    "docs/results/v0_3_execution_ladder/execution_ladder_ranking_stability.csv",
    "docs/results/v0_3_execution_ladder/execution_ladder_summary.json",
    "docs/results/v0_3_execution_ladder/execution_ladder_summary.md",
    "docs/results/v0_3_execution_stress_grid/execution_stress_grid_rows.csv",
    "docs/results/v0_3_execution_stress_grid/execution_stress_grid_sensitivity.csv",
    "docs/results/v0_3_execution_stress_grid/execution_stress_grid_summary.json",
    "docs/results/v0_3_execution_stress_grid/execution_stress_grid_summary.md",
    "docs/results/v0_3_finaudit_pilot/finaudit_pilot_task_manifest.csv",
    "docs/results/v0_3_finaudit_pilot/finaudit_pilot_scores.csv",
    "docs/results/v0_3_finaudit_pilot/finaudit_pilot_difficulty_breakdown.csv",
    "docs/results/v0_3_finaudit_pilot/finaudit_pilot_summary.json",
    "docs/results/v0_3_finaudit_pilot/finaudit_pilot_summary.md",
    "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_rows.csv",
    "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_coverage.csv",
    "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_summary.json",
    "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan.md",
    "docs/results/v0_3_memory_contamination/memory_contamination_rows.csv",
    "docs/results/v0_3_memory_contamination/memory_contamination_aggregate.csv",
    "docs/results/v0_3_memory_contamination/memory_contamination_dose_response.csv",
    "docs/results/v0_3_memory_contamination/contamination_tier_controls.csv",
    "docs/results/v0_3_memory_contamination/memory_contamination_summary.json",
    "docs/results/v0_3_memory_contamination/memory_contamination_summary.md",
    "docs/results/v0_3_contamination_control_audit/contamination_control_audit.csv",
    "docs/results/v0_3_contamination_control_audit/contamination_control_audit_summary.json",
    "docs/results/v0_3_contamination_control_audit/contamination_control_audit.md",
    "docs/results/v0_3_power_note/v0_3_power_curves.csv",
    "docs/results/v0_3_power_note/v0_3_detectable_effects.csv",
    "docs/results/v0_3_power_note/v0_3_power_note_summary.json",
    "docs/results/v0_3_power_note/v0_3_power_note_summary.md",
    "docs/results/v0_3_variance_decomposition/variance_decomposition_rows.csv",
    "docs/results/v0_3_variance_decomposition/variance_decomposition_summary.json",
    "docs/results/v0_3_variance_decomposition/variance_decomposition.md",
    "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit_findings.csv",
    "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit_summary.json",
    "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit.md",
    "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_reports.csv",
    "docs/results/v0_3_external_reproduction_reports/external_reproduction_environment_coverage.csv",
    "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.json",
    "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.md",
    "docs/results/v0_3_external_reproduction_reports/reports/README.md",
    "docs/results/v0_3_evidence_index/v0_3_evidence_index.csv",
    "docs/results/v0_3_evidence_index/v0_3_claim_coverage.csv",
    "docs/results/v0_3_evidence_index/v0_3_open_gaps.csv",
    "docs/results/v0_3_evidence_index/v0_3_evidence_index.json",
    "docs/results/v0_3_evidence_index/v0_3_evidence_index.md",
    "docs/results/classical_baselines/classical_baselines.md",
    "docs/results/classical_baselines/classical_baseline_matrix.csv",
    "docs/results/classical_baselines/classical_baseline_aggregate.csv",
    "docs/results/classical_baselines/classical_vs_llm_comparison.csv",
    "docs/results/quality_decomposition/quality_decomposition.md",
    "docs/results/quality_decomposition/quality_decomposition_rows.csv",
    "docs/results/quality_decomposition/quality_decomposition_aggregate.csv",
    "docs/results/quality_decomposition/decision_execution_radar.svg",
    "docs/results/skill_task_matrix.md",
    "docs/results/poe_skill_task_matrix.md",
    "docs/results/poe_skill_task_matrix.csv",
    "docs/results/poe_skill_challenge_matrix.md",
    "docs/results/poe_skill_challenge_matrix.csv",
    "docs/results/poe_skill_challenge_followup_matrix.md",
    "docs/results/poe_skill_challenge_followup_matrix.csv",
    "docs/results/poe_skill_challenge_followup_claude_adversarial.md",
    "docs/results/poe_skill_challenge_followup_claude_adversarial.csv",
    "docs/demo_artifacts.yaml",
    "schemas/benchmark_submission.schema.json",
    "schemas/broker_approval_artifact.schema.json",
    "schemas/broker_adapter_capability.schema.json",
    "schemas/broker_handoff_artifact.schema.json",
    "schemas/broker_response_artifact.schema.json",
    "schemas/calibration_profile.schema.json",
    "schemas/demo_artifact_contract.schema.json",
    "schemas/direct_provider_manifest.schema.json",
    "schemas/live_readiness_preflight.schema.json",
    "schemas/operator_runbook_artifact.schema.json",
    "schemas/reproduction_report.schema.json",
    "schemas/skill_answer_set.schema.json",
    "schemas/skill_task_rubric.schema.json",
    "schemas/trajectory.schema.json",
    "benchmarks/v0.2/spec.json",
    "benchmarks/v0.3/protocol.json",
    "examples/benchmark_submissions/example_redacted_submission.json",
    "examples/benchmark_submissions/example_direct_api_redacted_submission.json",
    "examples/provider_manifests/direct_openai_example.json",
    "examples/benchmark_submissions/model_matrix/calm_trend__poe_gpt_5_5.json",
    "examples/benchmark_submissions/model_matrix/liquidity_collapse__poe_gpt_5_5.json",
    "examples/benchmark_submissions/real_market_matrix/recent_cross_asset__poe_gpt_5_5__seed_7.json",
    "examples/skill_tasks/README.md",
    "examples/skill_tasks/trajectory_audit_001/input.md",
    "examples/skill_tasks/trajectory_audit_001/rubric.json",
    "examples/skill_tasks/intent_execution_autopsy_001/input.md",
    "examples/skill_tasks/intent_execution_autopsy_001/trajectory_excerpt.json",
    "examples/skill_tasks/intent_execution_autopsy_001/rubric.json",
    "examples/skill_tasks/risk_gate_review_001/input.md",
    "examples/skill_tasks/risk_gate_review_001/rubric.json",
    "examples/skill_tasks/risk_feedback_learning_001/input.md",
    "examples/skill_tasks/risk_feedback_learning_001/risk_feedback_steps.json",
    "examples/skill_tasks/risk_feedback_learning_001/rubric.json",
    "examples/skill_tasks/execution_boundary_001/input.md",
    "examples/skill_tasks/execution_boundary_001/rubric.json",
    "examples/skill_tasks/execution_attribution_001/input.md",
    "examples/skill_tasks/execution_attribution_001/execution_report.json",
    "examples/skill_tasks/execution_attribution_001/rubric.json",
    "examples/skill_tasks/claim_boundary_001/input.md",
    "examples/skill_tasks/claim_boundary_001/rubric.json",
    "examples/skill_tasks/claim_boundary_provider_drift_001/input.md",
    "examples/skill_tasks/claim_boundary_provider_drift_001/candidate_claims.md",
    "examples/skill_tasks/claim_boundary_provider_drift_001/rubric.json",
    "examples/skill_tasks/reproduction_review_001/input.md",
    "examples/skill_tasks/reproduction_review_001/manifest.json",
    "examples/skill_tasks/reproduction_review_001/rubric.json",
    "examples/skill_tasks/reproduction_hash_mismatch_001/input.md",
    "examples/skill_tasks/reproduction_hash_mismatch_001/mismatch_manifest.json",
    "examples/skill_tasks/reproduction_hash_mismatch_001/rubric.json",
    "examples/skill_tasks/plugin_author_001/input.md",
    "examples/skill_tasks/plugin_author_001/rubric.json",
    "examples/skill_tasks/market_rule_plugin_review_001/input.md",
    "examples/skill_tasks/market_rule_plugin_review_001/expected_tests.md",
    "examples/skill_tasks/market_rule_plugin_review_001/rubric.json",
    "examples/skill_tasks_challenge/README.md",
    "examples/skill_tasks_challenge/dirty_reproduction_claim_001/input.md",
    "examples/skill_tasks_challenge/dirty_reproduction_claim_001/rubric.json",
    "examples/skill_tasks_challenge/leaderboard_misread_001/input.md",
    "examples/skill_tasks_challenge/leaderboard_misread_001/rubric.json",
    "examples/skill_tasks_challenge/market_rules_overgeneralization_001/input.md",
    "examples/skill_tasks_challenge/market_rules_overgeneralization_001/rubric.json",
    "examples/skill_tasks_challenge/provider_cache_privacy_001/input.md",
    "examples/skill_tasks_challenge/provider_cache_privacy_001/rubric.json",
    "examples/skill_tasks_challenge/public_artifact_redaction_001/input.md",
    "examples/skill_tasks_challenge/public_artifact_redaction_001/rubric.json",
    "examples/skill_tasks_challenge/risk_report_gap_001/input.md",
    "examples/skill_tasks_challenge/risk_report_gap_001/rubric.json",
    "examples/skill_tasks_challenge/stress_calibration_overclaim_001/input.md",
    "examples/skill_tasks_challenge/stress_calibration_overclaim_001/rubric.json",
    "examples/skill_tasks_challenge/trajectory_inconsistency_001/input.md",
    "examples/skill_tasks_challenge/trajectory_inconsistency_001/rubric.json",
    "examples/skill_task_answers/README.md",
    "examples/skill_task_answers/reference/manifest.json",
    "examples/skill_task_answers/reference/trajectory_audit_001.md",
    "examples/skill_task_answers/reference/intent_execution_autopsy_001.md",
    "examples/skill_task_answers/reference/risk_gate_review_001.md",
    "examples/skill_task_answers/reference/risk_feedback_learning_001.md",
    "examples/skill_task_answers/reference/execution_boundary_001.md",
    "examples/skill_task_answers/reference/execution_attribution_001.md",
    "examples/skill_task_answers/reference/claim_boundary_001.md",
    "examples/skill_task_answers/reference/claim_boundary_provider_drift_001.md",
    "examples/skill_task_answers/reference/reproduction_review_001.md",
    "examples/skill_task_answers/reference/reproduction_hash_mismatch_001.md",
    "examples/skill_task_answers/reference/plugin_author_001.md",
    "examples/skill_task_answers/reference/market_rule_plugin_review_001.md",
    "examples/skill_task_answers/boundary_violation/execution_boundary_001.md",
    "data/real/yahoo_daily_leaderboard_2021_2026/manifest.json",
    "data/public/microstructure_sample/manifest.json",
    "data/public/microstructure_sample/quotes.csv",
    "data/public/microstructure_sample/fills.csv",
    "data/public/binance_btcusdt_perp_2024_03_01_sample/manifest.json",
    "data/public/binance_btcusdt_perp_2024_03_01_sample/quotes.csv",
    "data/public/binance_btcusdt_perp_2024_03_01_sample/fills.csv",
    "notebooks/tradearena_5min_colab.ipynb",
    "plugins/README.md",
    "skills/README.md",
    "skills/skill_template/SKILL.md",
    "skills/tradearena-trajectory-audit/SKILL.md",
    "skills/tradearena-risk-gate-review/SKILL.md",
    "skills/tradearena-execution-calibration/SKILL.md",
    "skills/tradearena-claim-boundary-review/SKILL.md",
    "skills/tradearena-reproduction-review/SKILL.md",
    "skills/tradearena-plugin-author/SKILL.md",
    "scripts/build_skill_index.py",
    "scripts/score_skill_task.py",
    "scripts/score_skill_task_report.py",
    "scripts/validate_skill_contract.py",
    "scripts/check_repository_metadata.py",
    "scripts/run_showcase.py",
    "scripts/run_leaderboard_model_matrix.py",
    "scripts/run_real_market_leaderboard.py",
    "scripts/run_classical_baseline_matrix.py",
    "scripts/build_quality_decomposition.py",
    "scripts/compare_execution_to_fills.py",
    "scripts/calibrate_quote_fill_model.py",
    "examples/broker_capability_manifest_demo.py",
    "examples/live_readiness_preflight_demo.py",
    "scripts/download_binance_microstructure_sample.py",
    "scripts/validate_benchmark_spec.py",
    "scripts/validate_reproduction_report.py",
    "scripts/run_external_reproduction_pack.py",
    "scripts/run_v03_external_reproduction_pack.py",
    "scripts/build_v03_external_reproduction_gate.py",
    "scripts/run_failure_autopsy.py",
    "scripts/validate_benchmark_submission.py",
    "scripts/validate_broker_adapter_capability.py",
    "scripts/validate_live_readiness_preflight.py",
    "scripts/validate_demo_artifacts.py",
    "scripts/validate_direct_provider_manifest.py",
    "scripts/run_direct_provider_manifest_pilot.py",
    "scripts/run_v03_direct_api_pilot.py",
    "scripts/build_v03_direct_api_matrix_plan.py",
    "scripts/build_v03_direct_api_call_packets.py",
    "scripts/build_v03_direct_api_submission_checklist.py",
    "scripts/build_v03_direct_api_matrix_gate.py",
    "scripts/run_v03_execution_ladder.py",
    "scripts/run_v03_execution_stress_grid.py",
    "scripts/run_v03_finaudit_pilot.py",
    "scripts/build_v03_finaudit_direct_model_plan.py",
    "scripts/run_v03_memory_contamination.py",
    "scripts/build_v03_contamination_control_audit.py",
    "scripts/run_v03_power_note.py",
    "scripts/build_v03_variance_decomposition.py",
    "scripts/build_v03_claim_boundary_audit.py",
    "scripts/build_v03_evidence_index.py",
    "SECURITY.md",
]
FORBIDDEN_TRACKED_PATTERNS = [
    "data/llm_cache/*.jsonl",
    "outputs/**/*.json",
    "outputs/**/*.html",
]
PLACEHOLDER_PHRASES = [
    "TODO",
    "TBD",
    "pending labels",
    "insert result",
]
BANNED_PUBLIC_TERMS = [
    "_".join(("trading", "agent", "os")),
]
REQUIRED_PUBLIC_IDENTITY_PHRASES = {
    "README.md": [
        "docs/assets/trellm_readme_audit_system_banner_v2.svg",
        'alt="TreLLM trading audit system wordmark"',
        "TreLLM is an LLM-driven trading audit and control system. TradeArena is",
        "its public leaderboard for ranking auditable agent runs.",
        "# TreLLM",
    ],
    "pyproject.toml": [
        'description = "TreLLM: LLM trading audit system with replayable trajectories, risk gates, reproducibility artifacts, and a TradeArena leaderboard."',
        '"trellm"',
        '"llm-trading"',
        '"trading-audit"',
        '"agent-audit"',
        '"leaderboard"',
    ],
    "src/tradearena/__init__.py": [
        "TreLLM: LLM-driven trading audit and control system with a TradeArena compatibility API.",
    ],
    "docs/launch/README.md": [
        "TreLLM is an LLM-driven trading audit and live-readiness control system; TradeArena is its public leaderboard",
        "execution calibration, and reproducible agent evidence.",
        "python scripts/check_repository_metadata.py weich97/TreLLM-public",
        "trellm",
        "live-readiness",
        "execution-calibration",
        "risk-gates",
        "paper-trading",
    ],
    "docs/results/community_registry.md": [
        "# TradeArena Leaderboard Registry",
    ],
}
REQUIRED_PUBLIC_REPOSITORY_LOCATIONS = {
    "CITATION.cff": [
        'repository-code: "https://github.com/weich97/TreLLM-public"',
        'url: "https://github.com/weich97/TreLLM-public"',
    ],
    "README.md": [
        "https://github.com/weich97/TreLLM-public/actions/workflows/ci.yml",
        "https://img.shields.io/github/license/weich97/TreLLM-public",
        "https://colab.research.google.com/github/weich97/TreLLM-public/blob/main/notebooks/tradearena_5min_colab.ipynb",
    ],
    "notebooks/tradearena_5min_colab.ipynb": [
        "git clone https://github.com/weich97/TreLLM-public.git",
        'Path(\\"TreLLM\\")',
        'os.chdir(\\"TreLLM\\")',
    ],
}
LEGACY_PUBLIC_IDENTITY_PHRASES = [
    "Community Benchmark Registry",
    "TradeArena Community Benchmark Registry",
    "TradeArena community registry",
    "TradeArena: pluggable AI trading agent research framework",
    "Auditable benchmark framework for LLM trading agents",
    "TradeArena system architecture",
    "TradeArena currently tracks aggregate public reports",
    "TradeArena is maintained as an open benchmark, audit framework",
    "TradeArena is designed around narrow interfaces.",
    "TradeArena is an audit, benchmark, and live-readiness framework.",
    "Live execution is out of scope for the public benchmark",
    "Stages 4 and 5 are not part of the public benchmark claim.",
    "TradeArena already has synthetic, real-market, execution-shock, classical-baseline, and calibration snapshots.",
    "The task suite measures TradeArena-specific audit ability rather than trading ability:",
    "You are evaluating TradeArena as a financial-audit agent, not as a trader.",
    "TradeArena's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics",
    "The current public benchmark path",
    "Before calling TradeArena an externally validated community benchmark",
    "Community Benchmark Submission Schema",
    "community benchmark submissions",
    "public benchmark submission",
    "Redacted benchmark submissions",
    "TreLLM should grow beyond a paper-only benchmark module",
    "TradeArena Broker Handoff Artifact",
    "TradeArena Broker Approval Artifact",
    "TradeArena Broker Response Artifact",
    "Convert TradeArena orders into broker handoff rows.",
    "TradeArena is the public leaderboard and benchmark module",
    "TradeArena benchmark module",
    "Validate that a broker approval artifact binds to a handoff artifact.",
    "Run TradeArena experiments.",
    "Replay one step from a TradeArena trajectory JSON.",
    "Export a TradeArena trajectory to a local trace JSON.",
    "Create a local TradeArena plugin skeleton.",
    "serialized TradeArena trajectory",
    "strengthen TradeArena's execution evidence",
    "the TradeArena calibration pipeline was run",
    "unless recorded in the TradeArena run manifest.",
    "Convert approved TradeArena orders into broker-review files.",
    "TradeArena's compact execution equation",
    "TradeArena execution-stress equation",
    "upgrades TradeArena from an OHLCV-only smoke test",
    "TradeArena Replay:",
    "| TradeArena record | OpenTelemetry-style span | Evals or trace-style field |",
    "TradeArena's default `market_impact` coefficient",
    "claiming that TradeArena explains realized transaction costs",
    "TradeArena strategy interface and downstream risk/execution/evaluation stack.",
    "The framework is the experimental substrate",
    "This makes the framework relevant to LLM trading agents",
    "one runnable example for each framework surface",
    "keeping the framework auditable",
    "Extend the framework with small, reviewable plugins.",
    "reusing the rest of the framework.",
    "One new plugin, the rest of the framework stays fixed",
    "core framework experiment axes",
    "four framework axes",
    "This makes the framework useful alongside stronger forecasting",
    "The current public repository is strongest at the prototype and early benchmark levels",
    "For the staged path from benchmark research to supervised live execution",
    "These contributions move TreLLM from benchmark research toward human-gated",
    'framework: str = "TradeArena"',
    '"title": "TradeArena trajectory"',
    '"title": "TradeArena execution calibration profile"',
    '"title": "TradeArena Demo Artifact Contract"',
    '"title": "TradeArena External Reproduction Report"',
    '"title": "TradeArena skill task answer set"',
    '"title": "TradeArena skill task rubric"',
    "# TradeArena v0.2 External Reproduction Pack",
    '"User-Agent": "TradeArena-calibration-sample"',
    '"User-Agent": "TradeArena mirror downloader"',
    "Volume is normalized to TradeArena units",
]
STALE_PUBLIC_REPOSITORY_LOCATIONS = [
    "weich97/TradeArena",
    "github.com/weich97/TradeArena",
    "github.io/TradeArena",
    "repo=weich97/TradeArena",
    "mybinder.org/v2/gh/weich97/TradeArena",
    "nbviewer.org/github/weich97/TradeArena",
    "cd TradeArena",
    'Path("TradeArena")',
    'os.chdir("TradeArena")',
    'Path(\\"TradeArena\\")',
    'os.chdir(\\"TradeArena\\")',
    'name != \\"TradeArena\\"',
]
CI_REQUIRED_GATE_COMMANDS = [
    "python -m compileall src scripts examples tests -q",
    "python -m ruff check src scripts examples tests",
    "python -m mypy",
    "python -m pytest tests -q --cov=tradearena --cov-report=xml --cov-report=term-missing",
    "python scripts/validate_demo_artifacts.py",
    "python scripts/validate_benchmark_spec.py benchmarks/v0.2/spec.json",
    "python scripts/validate_benchmark_spec.py benchmarks/v0.3/protocol.json",
    "python scripts/validate_direct_provider_manifest.py examples/provider_manifests/direct_openai_example.json",
    "python scripts/run_v03_direct_api_pilot.py --output-dir outputs/ci_v0_3_direct_api_pilot --seeds 7 --samples 0",
    "python scripts/build_v03_direct_api_matrix_plan.py --output-dir outputs/ci_v0_3_direct_api_matrix_plan --models openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY --seeds 7,11 --samples 0,1",
    "python scripts/build_v03_direct_api_call_packets.py --plan-rows outputs/ci_v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv --output-dir outputs/ci_v0_3_direct_api_call_packets",
    "python scripts/build_v03_direct_api_submission_checklist.py --output-dir outputs/ci_v0_3_direct_api_submission_checklist",
    "python scripts/build_v03_direct_api_matrix_gate.py --output-dir outputs/ci_v0_3_direct_api_matrix_gate --submission-dirs outputs/ci_v0_3_direct_api_pilot/submissions --provider-manifest-dirs outputs/ci_v0_3_direct_api_pilot/provider_manifests",
    "python scripts/run_v03_execution_ladder.py --output-dir outputs/ci_v0_3_execution_ladder --agents signal-weighted,random --seeds 7 --periods 8 --top-k 2",
    "python scripts/run_v03_execution_stress_grid.py --output-dir outputs/ci_v0_3_execution_stress_grid --agents signal-weighted,random --seeds 7 --periods 8",
    "python scripts/run_v03_finaudit_pilot.py --output-dir outputs/ci_v0_3_finaudit_pilot --tasks 4 --periods 16 --base-seed 410",
    "python scripts/build_v03_finaudit_direct_model_plan.py --task-manifest outputs/ci_v0_3_finaudit_pilot/finaudit_pilot_task_manifest.csv --output-dir outputs/ci_v0_3_finaudit_direct_model_plan --models openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",
    "python scripts/run_v03_memory_contamination.py --output-dir outputs/ci_v0_3_memory_contamination --kinds fake_rejections --doses 0,0.5 --decays 1.0 --risks max-position --seeds 7 --periods 12",
    "python scripts/build_v03_contamination_control_audit.py --output-dir outputs/ci_v0_3_contamination_control_audit",
    "python scripts/run_v03_power_note.py --output-dir outputs/ci_v0_3_power_note --repeat-levels 6,10 --effect-sizes 0.8,1.2 --target-powers 0.5 --draws 30 --permutation-draws 128 --seed 3",
    "python scripts/build_v03_variance_decomposition.py --output-dir outputs/ci_v0_3_variance_decomposition",
    "python scripts/build_v03_claim_boundary_audit.py --output-dir outputs/ci_v0_3_claim_boundary_audit",
    "python scripts/build_v03_external_reproduction_gate.py --output-dir outputs/ci_v0_3_external_reproduction_reports",
    "python scripts/run_v03_external_reproduction_pack.py --output-dir outputs/ci_v0_3_reproduction_pack --environment-class linux",
    "python scripts/build_v03_evidence_index.py --output-dir outputs/ci_v0_3_evidence_index",
    "python scripts/scan_public_artifacts.py outputs docs/results examples/benchmark_submissions",
    "python scripts/validate_benchmark_submission.py examples/benchmark_submissions/example_redacted_submission.json",
    "python scripts/build_benchmark_registry.py examples/benchmark_submissions",
    "python scripts/check_release_readiness.py",
]


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            failures.append(f"missing required file: {rel}")

    tracked = _tracked_files()
    for rel in tracked:
        path = ROOT / rel
        if path.is_file() and path.stat().st_size > MAX_TRACKED_FILE_BYTES:
            failures.append(f"tracked file exceeds {MAX_TRACKED_FILE_BYTES} bytes: {rel}")

    for pattern in FORBIDDEN_TRACKED_PATTERNS:
        for match in _git_ls_files(pattern):
            failures.append(f"forbidden tracked artifact: {match}")

    public_text_files = [ROOT / "README.md", ROOT / "docs/results/benchmark_v0_2.md"]
    for path in public_text_files:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for phrase in PLACEHOLDER_PHRASES:
                if phrase.lower() in text:
                    failures.append(f"placeholder phrase '{phrase}' found in {path.relative_to(ROOT)}")

    for rel in tracked:
        path = ROOT / rel
        if path.is_file() and _is_public_text_file(path):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for term in BANNED_PUBLIC_TERMS:
                if term in text:
                    failures.append(f"banned legacy namespace '{term}' found in {rel}")

    failures.extend(_check_public_identity_boundaries(ROOT, tracked))
    failures.extend(_check_release_candidate_manifest_hashes(ROOT, "docs/launch/release_candidate_v0.2.1.json"))
    failures.extend(_check_ci_gate_parity(ROOT / ".github/workflows/ci.yml"))

    if failures:
        print("Release readiness check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Release readiness check passed.")
    return 0


def _tracked_files() -> list[str]:
    return _git_ls_files()


def _git_ls_files(pattern: str | None = None) -> list[str]:
    command = _git_command(ROOT, ["ls-files"])
    if pattern:
        command.append(pattern)
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _check_ci_gate_parity(ci_path: Path) -> list[str]:
    if not ci_path.exists():
        return [f"missing CI workflow: {ci_path.relative_to(ROOT) if ci_path.is_relative_to(ROOT) else ci_path}"]
    text = ci_path.read_text(encoding="utf-8", errors="ignore")
    return [
        f"CI workflow is missing required gate command: {command}"
        for command in CI_REQUIRED_GATE_COMMANDS
        if command not in text
    ]


def _check_public_identity_boundaries(root: Path, tracked_files: list[str]) -> list[str]:
    failures: list[str] = []
    tracked_set = set(tracked_files)
    for rel, phrases in REQUIRED_PUBLIC_IDENTITY_PHRASES.items():
        path = root / rel
        if rel not in tracked_set or not path.exists():
            failures.append(f"missing public identity file: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for phrase in phrases:
            if phrase not in text:
                if rel == "pyproject.toml" and phrase.startswith('description = "TreLLM:'):
                    failures.append("pyproject.toml must brand the project description as TreLLM")
                else:
                    failures.append(f"required public identity phrase missing from {rel}: {phrase}")

    for rel, locations in REQUIRED_PUBLIC_REPOSITORY_LOCATIONS.items():
        path = root / rel
        if rel not in tracked_set or not path.exists():
            failures.append(f"missing public repository location file: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for location in locations:
            if location not in text:
                failures.append(f"required public repository location missing from {rel}: {location}")

    for rel in tracked_files:
        path = root / rel
        if not path.is_file() or not _is_public_identity_text_file(rel, path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if rel.startswith("schemas/") and rel.endswith(".schema.json"):
            schema_location = "https://github.com/weich97/TreLLM-public/schemas/"
            if schema_location not in text:
                failures.append(f"required public repository location missing from {rel}: {schema_location}")
        for location in STALE_PUBLIC_REPOSITORY_LOCATIONS:
            if location in text:
                failures.append(f"stale public repository location '{location}' found in {rel}")
        for phrase in LEGACY_PUBLIC_IDENTITY_PHRASES:
            if phrase in text:
                failures.append(f"legacy public identity phrase '{phrase}' found in {rel}")
    return failures


def _check_release_candidate_manifest_hashes(root: Path, manifest_rel: str) -> list[str]:
    manifest_path = root / manifest_rel
    if not manifest_path.exists():
        return [f"missing release candidate manifest: {manifest_rel}"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"release candidate manifest is not valid JSON: {manifest_rel}"]

    failures: list[str] = []
    for artifact in manifest.get("artifact_hashes", []):
        rel = str(artifact.get("path", ""))
        if not rel:
            failures.append(f"release candidate manifest contains artifact without path: {manifest_rel}")
            continue
        path = root / rel
        expected_exists = bool(artifact.get("exists"))
        if expected_exists and not path.exists():
            failures.append(f"release candidate artifact is missing: {rel}")
            continue
        if not expected_exists:
            if path.exists():
                failures.append(f"release candidate artifact unexpectedly exists: {rel}")
            continue
        artifact_bytes = _release_artifact_bytes(root, rel, path)
        expected_bytes = artifact.get("bytes")
        actual_bytes = len(artifact_bytes)
        if expected_bytes != actual_bytes:
            failures.append(f"release candidate artifact byte count mismatch for {rel}")
        expected_sha = str(artifact.get("sha256", ""))
        actual_sha = _sha256_bytes(artifact_bytes)
        if expected_sha != actual_sha:
            failures.append(f"release candidate artifact hash mismatch for {rel}")
    return failures


def _release_artifact_bytes(root: Path, rel: str, path: Path) -> bytes:
    if _git_path_has_worktree_changes(root, rel):
        return _canonical_worktree_bytes(path)
    blob = _git_blob_bytes(root, rel)
    if blob is not None:
        return blob
    return _canonical_worktree_bytes(path)


def _git_path_has_worktree_changes(root: Path, rel: str) -> bool:
    result = subprocess.run(
        _git_command(root, ["status", "--short", "--", rel]),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _canonical_worktree_bytes(path: Path) -> bytes:
    content = path.read_bytes()
    if b"\0" in content:
        return content
    return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _git_blob_bytes(root: Path, rel: str) -> bytes | None:
    normalized_rel = rel.replace("\\", "/")
    result = subprocess.run(
        _git_command(root, ["show", f"HEAD:{normalized_rel}"]),
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _git_command(root: Path, args: list[str]) -> list[str]:
    return ["git", "-c", f"safe.directory={root.as_posix()}", *args]


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _is_public_identity_text_file(rel: str, path: Path) -> bool:
    if rel.startswith("tests/") or rel.startswith("tests\\"):
        return False
    if rel == "scripts/check_release_readiness.py":
        return False
    return path.suffix.lower() in {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".txt", ".cff"}


def _is_public_text_file(path: Path) -> bool:
    if path.suffix.lower() not in {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".txt", ".cff"}:
        return False
    parts = set(path.relative_to(ROOT).parts)
    return ".git" not in parts


if __name__ == "__main__":
    raise SystemExit(main())
