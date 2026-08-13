from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "examples" / "skill_tasks"
ANSWERS_DIR = ROOT / "examples" / "skill_task_answers"
SCHEMA_PATH = ROOT / "schemas" / "skill_task_rubric.schema.json"
ANSWER_SET_SCHEMA_PATH = ROOT / "schemas" / "skill_answer_set.schema.json"


def test_skill_tasks_have_inputs_and_rubrics():
    task_dirs = sorted(path for path in TASKS_DIR.iterdir() if path.is_dir())

    assert {path.name for path in task_dirs} == {
        "claim_boundary_001",
        "claim_boundary_provider_drift_001",
        "execution_attribution_001",
        "execution_boundary_001",
        "intent_execution_autopsy_001",
        "market_rule_plugin_review_001",
        "plugin_author_001",
        "reproduction_hash_mismatch_001",
        "reproduction_review_001",
        "risk_feedback_learning_001",
        "risk_gate_review_001",
        "trajectory_audit_001",
    }
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    abilities = set()
    for task_dir in task_dirs:
        assert (task_dir / "input.md").exists()
        rubric = json.loads((task_dir / "rubric.json").read_text(encoding="utf-8"))
        validator.validate(rubric)
        assert rubric["task_id"] == task_dir.name
        assert rubric["skill"].startswith("tradearena-")
        abilities.add(rubric["ability"])
        assert len(rubric["criteria"]) >= 4
        assert 1 <= int(rubric["pass_threshold"]) <= sum(criterion["points"] for criterion in rubric["criteria"])

    assert abilities == {
        "audit_accuracy",
        "claim_discipline",
        "execution_boundary_awareness",
        "plugin_engineering",
        "reproduction_awareness",
        "risk_understanding",
    }


def test_skill_task_scorer_scores_reference_like_answer(tmp_path: Path):
    answer = tmp_path / "answer.md"
    answer.write_text(
        "\n".join(
            [
                "Use tradearena hash-run and replay to report the trajectory hash.",
                "Compare raw and approved decisions and note any risk edit diff.",
                "Check both the risk report and execution report.",
                "Flag rejected orders or partial filled orders.",
                "This supports an engineering claim, not a scientific claim.",
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task.py",
            "examples/skill_tasks/trajectory_audit_001",
            "--answer",
            str(answer),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "passed=True" in result.stdout


def test_reference_skill_task_answers_pass():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task.py",
            "--tasks-dir",
            "examples/skill_tasks",
            "--answers-dir",
            "examples/skill_task_answers/reference",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "passed=True" in result.stdout
    assert "answer_set=reference" in result.stdout
    assert "Ability summary:" in result.stdout


def test_boundary_violation_answer_hard_fails():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task.py",
            "examples/skill_tasks/execution_boundary_001",
            "--answer",
            "examples/skill_task_answers/boundary_violation/execution_boundary_001.md",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "passed=False" in result.stdout


def test_reference_answers_cover_all_tasks():
    reference_answers = {path.stem for path in (ANSWERS_DIR / "reference").glob("*.md")}
    task_ids = {path.name for path in TASKS_DIR.iterdir() if path.is_dir()}

    assert reference_answers == task_ids


def test_reference_answer_manifest_matches_schema_and_tasks():
    schema = json.loads(ANSWER_SET_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    manifest = json.loads((ANSWERS_DIR / "reference" / "manifest.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)

    task_ids = {path.name for path in TASKS_DIR.iterdir() if path.is_dir()}

    assert set(manifest["task_ids"]) == task_ids
    assert manifest["hidden_artifacts_used"] is False


def test_batch_answer_scoring_requires_manifest(tmp_path: Path):
    for task_dir in TASKS_DIR.iterdir():
        if task_dir.is_dir():
            (tmp_path / f"{task_dir.name}.md").write_text("placeholder", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task.py",
            "--tasks-dir",
            "examples/skill_tasks",
            "--answers-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "missing answer-set manifest" in result.stdout


def test_skill_task_scorer_reports_malformed_rubric_json(tmp_path: Path):
    task_dir = tmp_path / "broken_task"
    task_dir.mkdir()
    (task_dir / "input.md").write_text("Task input", encoding="utf-8")
    (task_dir / "rubric.json").write_text('{"task_id": ', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task.py",
            str(task_dir),
            "--validate-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "rubric.json must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def test_skill_task_report_reports_malformed_rubric_json(tmp_path: Path):
    task_dir = tmp_path / "broken_task"
    task_dir.mkdir()
    (task_dir / "input.md").write_text("Task input", encoding="utf-8")
    (task_dir / "rubric.json").write_text('{"task_id": ', encoding="utf-8")
    output = tmp_path / "matrix.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task_report.py",
            "--tasks-dir",
            str(tmp_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Skill task matrix validation failed" in result.stdout
    assert "rubric.json must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_skill_task_report_renderer_reports_malformed_rubric_json(tmp_path: Path):
    task_dir = tmp_path / "broken_task"
    task_dir.mkdir()
    (task_dir / "rubric.json").write_text('{"task_id": ', encoding="utf-8")
    module = _load_skill_task_report_module()

    with pytest.raises(ValueError, match=r"rubric\.json must contain valid JSON"):
        module.render_report([task_dir])


def _load_skill_task_report_module():
    scripts_dir = ROOT / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location("score_skill_task_report", scripts_dir / "score_skill_task_report.py")
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))
