from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_poe_skill_task_matrix.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_poe_skill_task_matrix", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_prompt_variant_parser_keeps_order_and_deduplicates():
    runner = _load_runner()

    assert runner._parse_prompt_variants("standard,skeptical_reviewer,standard") == (
        "standard",
        "skeptical_reviewer",
    )


def test_prompt_variant_parser_rejects_unknown_variant():
    runner = _load_runner()

    with pytest.raises(SystemExit):
        runner._parse_prompt_variants("standard,profit_maximizer")


def test_deepseek_models_must_use_direct_provider_namespace():
    runner = _load_runner()

    with pytest.raises(SystemExit):
        runner._parse_model_specs("poe:deepseek-v4-pro")

    assert runner._parse_model_specs("deepseek:deepseek-v4-pro") == (("deepseek", "deepseek-v4-pro"),)


def test_challenge_prompt_includes_variant_and_claim_boundary_language():
    runner = _load_runner()
    prompt = runner._build_prompt(
        ROOT / "examples" / "skill_tasks_challenge" / "stress_calibration_overclaim_001",
        ROOT / "skills",
        "adversarial_claim_boundary",
    )

    assert "adversarial_claim_boundary" in prompt
    assert "Stress-test every claim boundary" in prompt
    assert "stress simulator" in prompt
    assert "Required Answer Format" in prompt


def test_skill_matrix_prompt_and_report_assign_audit_evaluation_to_trellm(tmp_path: Path):
    runner = _load_runner()
    prompt = runner._build_prompt(
        ROOT / "examples" / "skill_tasks_challenge" / "stress_calibration_overclaim_001",
        ROOT / "skills",
    )
    output = tmp_path / "report.md"
    csv_output = tmp_path / "report.csv"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_poe_skill_task_matrix.py",
            "--tasks-dir",
            "examples/skill_tasks_challenge",
            "--models",
            "poe:gpt-5.5",
            "--limit-tasks",
            "leaderboard_misread_001",
            "--repeats",
            "1",
            "--public-output",
            str(output),
            "--public-csv",
            str(csv_output),
            "--dry-run",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report = output.read_text(encoding="utf-8")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "You are evaluating TreLLM audit skills, not TradeArena trading performance." in prompt
    assert "evaluating TradeArena as a financial-audit agent" not in prompt
    assert "TreLLM's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics" in report
    assert "TradeArena's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics" not in report


def test_tracked_skill_matrix_results_assign_audit_rubrics_to_trellm():
    result_paths = [
        ROOT / "docs" / "results" / "poe_skill_task_matrix.md",
        ROOT / "docs" / "results" / "poe_skill_challenge_matrix.md",
        ROOT / "docs" / "results" / "poe_skill_challenge_followup_matrix.md",
        ROOT / "docs" / "results" / "poe_skill_challenge_followup_claude_adversarial.md",
    ]

    for path in result_paths:
        text = path.read_text(encoding="utf-8")
        assert "TreLLM's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics" in text
        assert "TradeArena's public audit, risk, execution-boundary, reproduction, claim-boundary, and plugin-review rubrics" not in text


def test_challenge_skill_task_rubrics_validate():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task.py",
            "--tasks-dir",
            "examples/skill_tasks_challenge",
            "--validate-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_provider_cache_privacy_task_uses_trellm_for_public_artifact_policy():
    task_input = (
        ROOT
        / "examples"
        / "skill_tasks_challenge"
        / "provider_cache_privacy_001"
        / "input.md"
    ).read_text(encoding="utf-8")

    assert "TreLLM currently publishes aggregate public reports and TradeArena redacted manifests" in task_input
    assert "TradeArena currently tracks aggregate public reports" not in task_input


def test_dry_run_records_sample_start_index(tmp_path: Path):
    output = tmp_path / "report.md"
    csv_output = tmp_path / "report.csv"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_poe_skill_task_matrix.py",
            "--tasks-dir",
            "examples/skill_tasks_challenge",
            "--models",
            "poe:gpt-5.5",
            "--limit-tasks",
            "leaderboard_misread_001",
            "--repeats",
            "1",
            "--sample-start-index",
            "3",
            "--prompt-variants",
            "adversarial_claim_boundary",
            "--public-output",
            str(output),
            "--public-csv",
            str(csv_output),
            "--dry-run",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"sample_start_index": 3' in result.stdout
    assert "Sample start index: 3" in output.read_text(encoding="utf-8")
