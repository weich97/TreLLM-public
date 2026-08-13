import hashlib
import subprocess
from pathlib import Path

from scripts import build_release_candidate_manifest
from scripts.check_release_readiness import (
    CI_REQUIRED_GATE_COMMANDS,
    REQUIRED_FILES,
    REQUIRED_PUBLIC_IDENTITY_PHRASES,
    _check_ci_gate_parity,
    _check_public_identity_boundaries,
    _check_release_candidate_manifest_hashes,
)


def test_release_readiness_flags_missing_ci_gate(tmp_path: Path):
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "\n".join(
            [
                "name: CI",
                "steps:",
                '  - run: python -m ruff check src scripts examples tests',
                "  - run: python -m pytest tests -q --cov=tradearena --cov-report=xml --cov-report=term-missing",
                "  - run: python scripts/validate_demo_artifacts.py",
                "  - run: python scripts/check_release_readiness.py",
            ]
        ),
        encoding="utf-8",
    )

    failures = _check_ci_gate_parity(ci_path)

    assert "CI workflow is missing required gate command: python -m mypy" in failures


def test_release_readiness_flags_public_identity_regressions(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    registry = tmp_path / "docs" / "results" / "community_registry.md"
    skill_doc = tmp_path / "docs" / "agent_skills.md"
    schema_doc = tmp_path / "docs" / "schemas.md"
    readme = tmp_path / "README.md"
    pyproject.write_text(
        'description = "LLM-driven trading audit and control system with TradeArena leaderboard artifacts."\n',
        encoding="utf-8",
    )
    registry.parent.mkdir(parents=True)
    registry.write_text("# Community Benchmark Registry\n", encoding="utf-8")
    skill_doc.parent.mkdir(parents=True, exist_ok=True)
    skill_doc.write_text(
        "The task suite measures TradeArena-specific audit ability rather than trading ability:\n",
        encoding="utf-8",
    )
    schema_doc.write_text(
        "# Schemas\n\n"
        "## Community Benchmark Submission Schema\n"
        '"title": "TradeArena Broker Handoff Artifact"\n'
        "Convert TradeArena orders into broker handoff rows.\n"
        "TradeArena is the public leaderboard and benchmark module.\n"
        "TradeArena benchmark module.\n"
        "Validate that a broker approval artifact binds to a handoff artifact.\n"
        "Run TradeArena experiments.\n"
        "Replay one step from a TradeArena trajectory JSON.\n"
        "Export a TradeArena trajectory to a local trace JSON.\n"
        "Create a local TradeArena plugin skeleton.\n"
        "strengthen TradeArena's execution evidence.\n"
        "the TradeArena calibration pipeline was run.\n"
        "unless recorded in the TradeArena run manifest.\n"
        "Convert approved TradeArena orders into broker-review files.\n"
        "TradeArena's compact execution equation.\n"
        "TradeArena execution-stress equation.\n"
        "upgrades TradeArena from an OHLCV-only smoke test.\n"
        "TradeArena Replay:\n"
        "| TradeArena record | OpenTelemetry-style span | Evals or trace-style field |\n"
        "TradeArena's default `market_impact` coefficient.\n"
        "claiming that TradeArena explains realized transaction costs.\n"
        "TradeArena strategy interface and downstream risk/execution/evaluation stack.\n"
        "The framework is the experimental substrate.\n"
        "This makes the framework relevant to LLM trading agents.\n"
        "one runnable example for each framework surface.\n"
        "keeping the framework auditable.\n"
        "Extend the framework with small, reviewable plugins.\n"
        "reusing the rest of the framework.\n"
        "One new plugin, the rest of the framework stays fixed.\n"
        "core framework experiment axes.\n"
        "four framework axes.\n"
        "This makes the framework useful alongside stronger forecasting.\n"
        "The current public repository is strongest at the prototype and early benchmark levels.\n"
        "For the staged path from benchmark research to supervised live execution.\n"
        "These contributions move TreLLM from benchmark research toward human-gated.\n"
        'framework: str = "TradeArena"\n'
        '"title": "TradeArena trajectory"\n'
        '"title": "TradeArena execution calibration profile"\n'
        '"title": "TradeArena Demo Artifact Contract"\n'
        '"title": "TradeArena External Reproduction Report"\n'
        '"title": "TradeArena skill task answer set"\n'
        '"title": "TradeArena skill task rubric"\n'
        '"User-Agent": "TradeArena-calibration-sample"\n'
        '"User-Agent": "TradeArena mirror downloader"\n'
        "Volume is normalized to TradeArena units\n"
        "# TradeArena v0.2 External Reproduction Pack\n",
        encoding="utf-8",
    )
    readme.write_text(
        "The current public benchmark path runs offline and paper/sandbox experiments.\n"
        "Before calling TradeArena an externally validated community benchmark, more evidence is required.\n",
        encoding="utf-8",
    )

    failures = _check_public_identity_boundaries(
        root=tmp_path,
        tracked_files=[
            "pyproject.toml",
            "docs/results/community_registry.md",
            "docs/agent_skills.md",
            "docs/schemas.md",
            "README.md",
        ],
    )

    assert "pyproject.toml must brand the project description as TreLLM" in failures
    assert "legacy public identity phrase 'Community Benchmark Registry' found in docs/results/community_registry.md" in failures
    assert (
        "legacy public identity phrase 'The task suite measures TradeArena-specific audit ability rather than trading ability:' "
        "found in docs/agent_skills.md"
    ) in failures
    assert "legacy public identity phrase 'The current public benchmark path' found in README.md" in failures
    assert (
        "legacy public identity phrase 'Before calling TradeArena an externally validated community benchmark' "
        "found in README.md"
    ) in failures
    assert "legacy public identity phrase 'Community Benchmark Submission Schema' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'TradeArena Broker Handoff Artifact' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'Convert TradeArena orders into broker handoff rows.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'TradeArena is the public leaderboard and benchmark module' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'TradeArena benchmark module' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'Validate that a broker approval artifact binds to a handoff artifact.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'Run TradeArena experiments.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'Replay one step from a TradeArena trajectory JSON.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'Export a TradeArena trajectory to a local trace JSON.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'Create a local TradeArena plugin skeleton.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'strengthen TradeArena's execution evidence' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'the TradeArena calibration pipeline was run' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'unless recorded in the TradeArena run manifest.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'Convert approved TradeArena orders into broker-review files.' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'TradeArena's compact execution equation' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'TradeArena execution-stress equation' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'upgrades TradeArena from an OHLCV-only smoke test' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'TradeArena Replay:' found in docs/schemas.md" in failures
    assert (
        "legacy public identity phrase '| TradeArena record | OpenTelemetry-style span | Evals or trace-style field |' "
        "found in docs/schemas.md"
    ) in failures
    assert "legacy public identity phrase 'TradeArena's default `market_impact` coefficient' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'claiming that TradeArena explains realized transaction costs' found in docs/schemas.md" in failures
    assert (
        "legacy public identity phrase 'TradeArena strategy interface and downstream risk/execution/evaluation stack.' "
        "found in docs/schemas.md"
    ) in failures
    assert "legacy public identity phrase 'The framework is the experimental substrate' found in docs/schemas.md" in failures
    assert (
        "legacy public identity phrase 'This makes the framework relevant to LLM trading agents' found in docs/schemas.md"
        in failures
    )
    assert (
        "legacy public identity phrase 'one runnable example for each framework surface' found in docs/schemas.md"
        in failures
    )
    assert "legacy public identity phrase 'keeping the framework auditable' found in docs/schemas.md" in failures
    assert (
        "legacy public identity phrase 'Extend the framework with small, reviewable plugins.' found in docs/schemas.md"
        in failures
    )
    assert "legacy public identity phrase 'reusing the rest of the framework.' found in docs/schemas.md" in failures
    assert (
        "legacy public identity phrase 'One new plugin, the rest of the framework stays fixed' found in docs/schemas.md"
        in failures
    )
    assert "legacy public identity phrase 'core framework experiment axes' found in docs/schemas.md" in failures
    assert "legacy public identity phrase 'four framework axes' found in docs/schemas.md" in failures
    assert (
        "legacy public identity phrase 'This makes the framework useful alongside stronger forecasting' found in docs/schemas.md"
        in failures
    )
    assert (
        "legacy public identity phrase 'The current public repository is strongest at the prototype and early benchmark levels' "
        "found in docs/schemas.md"
    ) in failures
    assert (
        "legacy public identity phrase 'For the staged path from benchmark research to supervised live execution' "
        "found in docs/schemas.md"
    ) in failures
    assert (
        "legacy public identity phrase 'These contributions move TreLLM from benchmark research toward human-gated' "
        "found in docs/schemas.md"
    ) in failures
    assert 'legacy public identity phrase \'framework: str = "TradeArena"\' found in docs/schemas.md' in failures
    for title in [
        "TradeArena trajectory",
        "TradeArena execution calibration profile",
        "TradeArena Demo Artifact Contract",
        "TradeArena External Reproduction Report",
        "TradeArena skill task answer set",
        "TradeArena skill task rubric",
    ]:
        assert f"legacy public identity phrase '\"title\": \"{title}\"' found in docs/schemas.md" in failures
    assert 'legacy public identity phrase \'"User-Agent": "TradeArena-calibration-sample"\' found in docs/schemas.md' in failures
    assert 'legacy public identity phrase \'"User-Agent": "TradeArena mirror downloader"\' found in docs/schemas.md' in failures
    assert "legacy public identity phrase 'Volume is normalized to TradeArena units' found in docs/schemas.md" in failures
    assert "legacy public identity phrase '# TradeArena v0.2 External Reproduction Pack' found in docs/schemas.md" in failures


def test_release_readiness_flags_stale_public_repository_locations(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "\n".join(
            [
                "Clone from https://github.com/weich97/TradeArena.git",
                "Open https://weich97.github.io/TradeArena/",
                "Launch https://colab.research.google.com/github/weich97/TradeArena/blob/main/notebook.ipynb",
                "Then run cd TradeArena",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    failures = _check_public_identity_boundaries(root=tmp_path, tracked_files=["README.md"])

    assert "stale public repository location 'github.com/weich97/TradeArena' found in README.md" in failures
    assert "stale public repository location 'github.io/TradeArena' found in README.md" in failures
    assert "stale public repository location 'cd TradeArena' found in README.md" in failures


def test_release_readiness_requires_current_trellm_repository_locations(tmp_path: Path):
    citation = tmp_path / "CITATION.cff"
    schema = tmp_path / "schemas" / "trajectory.schema.json"
    notebook = tmp_path / "notebooks" / "tradearena_5min_colab.ipynb"
    launch_readme = tmp_path / "docs" / "launch" / "README.md"
    citation.write_text(
        'repository-code: "https://github.com/weich97/TreLLM-archive"\nurl: "https://github.com/weich97/TreLLM-archive"\n',
        encoding="utf-8",
    )
    schema.parent.mkdir(parents=True)
    schema.write_text(
        '{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://example.com/schemas/trajectory.schema.json"}\n',
        encoding="utf-8",
    )
    notebook.parent.mkdir(parents=True)
    notebook.write_text(
        '{"cells": [{"source": ["!git clone https://github.com/weich97/TreLLM-archive.git\\n", "os.chdir(\\"TreLLM-archive\\")\\n"]}]}\n',
        encoding="utf-8",
    )
    launch_readme.parent.mkdir(parents=True, exist_ok=True)
    launch_readme.write_text(
        "# TreLLM Project Metadata\n\n"
        "Suggested repository description:\n\n"
        "LLM trading audit system with replayable trajectories and a TradeArena leaderboard.\n",
        encoding="utf-8",
    )

    failures = _check_public_identity_boundaries(
        root=tmp_path,
        tracked_files=[
            "CITATION.cff",
            "schemas/trajectory.schema.json",
            "notebooks/tradearena_5min_colab.ipynb",
            "docs/launch/README.md",
        ],
    )

    assert (
        "required public repository location missing from CITATION.cff: "
        'repository-code: "https://github.com/weich97/TreLLM-public"'
    ) in failures
    assert (
        "required public repository location missing from schemas/trajectory.schema.json: "
        "https://github.com/weich97/TreLLM-public/schemas/"
    ) in failures
    assert (
        "required public repository location missing from notebooks/tradearena_5min_colab.ipynb: "
        "git clone https://github.com/weich97/TreLLM-public.git"
    ) in failures
    assert (
        "required public identity phrase missing from docs/launch/README.md: "
        "TreLLM is an LLM-driven trading audit and live-readiness control system; TradeArena is its public leaderboard"
    ) in failures


def test_release_readiness_guards_repository_metadata_check_contract():
    assert "scripts/check_repository_metadata.py" in REQUIRED_FILES
    assert (
        "python scripts/check_repository_metadata.py weich97/TreLLM-public"
        in REQUIRED_PUBLIC_IDENTITY_PHRASES["docs/launch/README.md"]
    )


def test_release_readiness_guards_v0_3_protocol_contract():
    assert "benchmarks/v0.3/protocol.json" in REQUIRED_FILES
    assert "docs/benchmark_v0_3_protocol.md" in REQUIRED_FILES
    assert "docs/reproduction_pack_v0_3.md" in REQUIRED_FILES
    assert "schemas/direct_provider_manifest.schema.json" in REQUIRED_FILES
    assert "examples/provider_manifests/direct_openai_example.json" in REQUIRED_FILES
    assert "scripts/validate_direct_provider_manifest.py" in REQUIRED_FILES
    assert "scripts/run_direct_provider_manifest_pilot.py" in REQUIRED_FILES
    assert "scripts/run_v03_direct_api_pilot.py" in REQUIRED_FILES
    assert "scripts/build_v03_direct_api_matrix_plan.py" in REQUIRED_FILES
    assert "scripts/build_v03_direct_api_call_packets.py" in REQUIRED_FILES
    assert "scripts/build_v03_direct_api_submission_checklist.py" in REQUIRED_FILES
    assert "scripts/build_v03_direct_api_matrix_gate.py" in REQUIRED_FILES
    assert "scripts/run_v03_execution_ladder.py" in REQUIRED_FILES
    assert "scripts/run_v03_execution_stress_grid.py" in REQUIRED_FILES
    assert "scripts/run_v03_finaudit_pilot.py" in REQUIRED_FILES
    assert "scripts/build_v03_finaudit_direct_model_plan.py" in REQUIRED_FILES
    assert "scripts/run_v03_memory_contamination.py" in REQUIRED_FILES
    assert "scripts/build_v03_contamination_control_audit.py" in REQUIRED_FILES
    assert "scripts/run_v03_power_note.py" in REQUIRED_FILES
    assert "scripts/build_v03_variance_decomposition.py" in REQUIRED_FILES
    assert "scripts/build_v03_claim_boundary_audit.py" in REQUIRED_FILES
    assert "scripts/run_v03_external_reproduction_pack.py" in REQUIRED_FILES
    assert "scripts/build_v03_external_reproduction_gate.py" in REQUIRED_FILES
    assert "scripts/build_v03_evidence_index.py" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_pilot/direct_api_pilot_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_pilot/direct_api_pilot_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_pilot/direct_api_pilot_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_coverage.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_coverage.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.jsonl" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_call_packets/direct_api_call_packet_manifest.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.md" in REQUIRED_FILES
    assert "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist_items.csv" in REQUIRED_FILES
    assert (
        "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist_summary.json"
        in REQUIRED_FILES
    )
    assert "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist.md" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_ladder/execution_ladder_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_ladder/execution_ladder_aggregate.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_ladder/execution_ladder_ranking_stability.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_ladder/execution_ladder_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_ladder/execution_ladder_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_stress_grid/execution_stress_grid_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_stress_grid/execution_stress_grid_sensitivity.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_stress_grid/execution_stress_grid_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_execution_stress_grid/execution_stress_grid_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_pilot/finaudit_pilot_task_manifest.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_pilot/finaudit_pilot_scores.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_pilot/finaudit_pilot_difficulty_breakdown.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_pilot/finaudit_pilot_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_pilot/finaudit_pilot_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_coverage.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan.md" in REQUIRED_FILES
    assert "docs/results/v0_3_memory_contamination/memory_contamination_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_memory_contamination/memory_contamination_aggregate.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_memory_contamination/memory_contamination_dose_response.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_memory_contamination/contamination_tier_controls.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_memory_contamination/memory_contamination_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_memory_contamination/memory_contamination_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_contamination_control_audit/contamination_control_audit.csv" in REQUIRED_FILES
    assert (
        "docs/results/v0_3_contamination_control_audit/contamination_control_audit_summary.json"
        in REQUIRED_FILES
    )
    assert "docs/results/v0_3_contamination_control_audit/contamination_control_audit.md" in REQUIRED_FILES
    assert "docs/results/v0_3_power_note/v0_3_power_curves.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_power_note/v0_3_detectable_effects.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_power_note/v0_3_power_note_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_power_note/v0_3_power_note_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_variance_decomposition/variance_decomposition_rows.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_variance_decomposition/variance_decomposition_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_variance_decomposition/variance_decomposition.md" in REQUIRED_FILES
    assert "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit_findings.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit.md" in REQUIRED_FILES
    assert "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_reports.csv" in REQUIRED_FILES
    assert (
        "docs/results/v0_3_external_reproduction_reports/external_reproduction_environment_coverage.csv"
        in REQUIRED_FILES
    )
    assert "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.json" in REQUIRED_FILES
    assert "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.md" in REQUIRED_FILES
    assert "docs/results/v0_3_external_reproduction_reports/reports/README.md" in REQUIRED_FILES
    assert "docs/results/v0_3_evidence_index/v0_3_evidence_index.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_evidence_index/v0_3_claim_coverage.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_evidence_index/v0_3_open_gaps.csv" in REQUIRED_FILES
    assert "docs/results/v0_3_evidence_index/v0_3_evidence_index.json" in REQUIRED_FILES
    assert "docs/results/v0_3_evidence_index/v0_3_evidence_index.md" in REQUIRED_FILES
    assert (
        "python scripts/run_v03_execution_ladder.py --output-dir outputs/ci_v0_3_execution_ladder --agents signal-weighted,random --seeds 7 --periods 8 --top-k 2"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/run_v03_execution_stress_grid.py --output-dir outputs/ci_v0_3_execution_stress_grid --agents signal-weighted,random --seeds 7 --periods 8"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/run_v03_finaudit_pilot.py --output-dir outputs/ci_v0_3_finaudit_pilot --tasks 4 --periods 16 --base-seed 410"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_finaudit_direct_model_plan.py --task-manifest outputs/ci_v0_3_finaudit_pilot/finaudit_pilot_task_manifest.csv --output-dir outputs/ci_v0_3_finaudit_direct_model_plan --models openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/run_v03_memory_contamination.py --output-dir outputs/ci_v0_3_memory_contamination --kinds fake_rejections --doses 0,0.5 --decays 1.0 --risks max-position --seeds 7 --periods 12"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_contamination_control_audit.py --output-dir outputs/ci_v0_3_contamination_control_audit"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_direct_api_matrix_gate.py --output-dir outputs/ci_v0_3_direct_api_matrix_gate --submission-dirs outputs/ci_v0_3_direct_api_pilot/submissions --provider-manifest-dirs outputs/ci_v0_3_direct_api_pilot/provider_manifests"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_direct_api_matrix_plan.py --output-dir outputs/ci_v0_3_direct_api_matrix_plan --models openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY --seeds 7,11 --samples 0,1"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_direct_api_call_packets.py --plan-rows outputs/ci_v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv --output-dir outputs/ci_v0_3_direct_api_call_packets"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_direct_api_submission_checklist.py --output-dir outputs/ci_v0_3_direct_api_submission_checklist"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/run_v03_power_note.py --output-dir outputs/ci_v0_3_power_note --repeat-levels 6,10 --effect-sizes 0.8,1.2 --target-powers 0.5 --draws 30 --permutation-draws 128 --seed 3"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_variance_decomposition.py --output-dir outputs/ci_v0_3_variance_decomposition"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_claim_boundary_audit.py --output-dir outputs/ci_v0_3_claim_boundary_audit"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_external_reproduction_gate.py --output-dir outputs/ci_v0_3_external_reproduction_reports"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/run_v03_external_reproduction_pack.py --output-dir outputs/ci_v0_3_reproduction_pack --environment-class linux"
        in CI_REQUIRED_GATE_COMMANDS
    )
    assert (
        "python scripts/build_v03_evidence_index.py --output-dir outputs/ci_v0_3_evidence_index"
        in CI_REQUIRED_GATE_COMMANDS
    )


def test_release_readiness_requires_readme_trellm_system_banner(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        """
<p align="center">
  <img src="docs/assets/tradearena_readme_banner.svg"
       alt="TradeArena benchmark wordmark"
       width="780">
</p>

# TradeArena

Auditable benchmark framework for LLM trading agents.
TradeArena system architecture
""".strip()
        + "\n",
        encoding="utf-8",
    )

    failures = _check_public_identity_boundaries(root=tmp_path, tracked_files=["README.md"])

    assert (
        "required public identity phrase missing from README.md: "
        "docs/assets/trellm_readme_audit_system_banner_v2.svg"
    ) in failures
    assert (
        "required public identity phrase missing from README.md: "
        "TreLLM is an LLM-driven trading audit and control system. TradeArena is"
    ) in failures
    assert (
        "legacy public identity phrase 'Auditable benchmark framework for LLM trading agents' found in README.md"
        in failures
    )
    assert "legacy public identity phrase 'TradeArena system architecture' found in README.md" in failures


def test_release_readiness_flags_stale_release_candidate_artifact_hash(tmp_path: Path):
    artifact = tmp_path / "README.md"
    manifest = tmp_path / "docs" / "launch" / "release_candidate_v0.2.1.json"
    artifact.write_text("current artifact text\n", encoding="utf-8")
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
{
  "artifact_hashes": [
    {
      "bytes": 1,
      "exists": true,
      "path": "README.md",
      "sha256": "sha256:stale"
    }
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    failures = _check_release_candidate_manifest_hashes(root=tmp_path, manifest_rel="docs/launch/release_candidate_v0.2.1.json")

    assert "release candidate artifact hash mismatch for README.md" in failures
    assert "release candidate artifact byte count mismatch for README.md" in failures


def test_release_readiness_uses_git_blob_bytes_for_manifest_artifacts(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

    artifact = tmp_path / "README.md"
    manifest = tmp_path / "docs" / "launch" / "release_candidate_v0.2.1.json"
    artifact.write_bytes(b"line one\nline two\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "Add artifact"], cwd=tmp_path, check=True, capture_output=True, text=True)

    artifact.write_bytes(b"line one\r\nline two\r\n")
    digest = "sha256:" + hashlib.sha256(b"line one\nline two\n").hexdigest()
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        f"""
{{
  "artifact_hashes": [
    {{
      "bytes": 18,
      "exists": true,
      "path": "README.md",
      "sha256": "{digest}"
    }}
  ]
}}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    failures = _check_release_candidate_manifest_hashes(root=tmp_path, manifest_rel="docs/launch/release_candidate_v0.2.1.json")

    assert failures == []


def test_release_readiness_uses_canonical_worktree_bytes_for_dirty_manifest_artifacts(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

    artifact = tmp_path / "README.md"
    manifest = tmp_path / "docs" / "launch" / "release_candidate_v0.2.1.json"
    artifact.write_bytes(b"old line\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "Add artifact"], cwd=tmp_path, check=True, capture_output=True, text=True)

    current_bytes = b"new line\n"
    artifact.write_bytes(b"new line\r\n")
    digest = "sha256:" + hashlib.sha256(current_bytes).hexdigest()
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        f"""
{{
  "artifact_hashes": [
    {{
      "bytes": {len(current_bytes)},
      "exists": true,
      "path": "README.md",
      "sha256": "{digest}"
    }}
  ]
}}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    failures = _check_release_candidate_manifest_hashes(root=tmp_path, manifest_rel="docs/launch/release_candidate_v0.2.1.json")

    assert failures == []


def test_release_candidate_manifest_builder_uses_git_blob_bytes(tmp_path: Path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

    artifact = tmp_path / "README.md"
    artifact.write_bytes(b"line one\nline two\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "Add artifact"], cwd=tmp_path, check=True, capture_output=True, text=True)
    artifact.write_bytes(b"line one\r\nline two\r\n")

    monkeypatch.setattr(build_release_candidate_manifest, "ROOT", tmp_path)

    artifact_hash = build_release_candidate_manifest._artifact_hash("README.md")

    assert artifact_hash["bytes"] == 18
    assert artifact_hash["sha256"] == "sha256:" + hashlib.sha256(b"line one\nline two\n").hexdigest()


def test_release_candidate_manifest_builder_uses_canonical_worktree_bytes_when_dirty(tmp_path: Path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

    artifact = tmp_path / "README.md"
    artifact.write_bytes(b"old line\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "Add artifact"], cwd=tmp_path, check=True, capture_output=True, text=True)
    artifact.write_bytes(b"new line\r\n")

    monkeypatch.setattr(build_release_candidate_manifest, "ROOT", tmp_path)

    artifact_hash = build_release_candidate_manifest._artifact_hash("README.md")

    assert artifact_hash["bytes"] == len(b"new line\n")
    assert artifact_hash["sha256"] == "sha256:" + hashlib.sha256(b"new line\n").hexdigest()


def test_release_candidate_manifest_builder_does_not_pin_packaging_metadata():
    assert "pyproject.toml" not in build_release_candidate_manifest.DEFAULT_ARTIFACTS
