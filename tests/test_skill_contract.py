from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_skill_contract_validator_passes():
    result = subprocess.run(
        [sys.executable, "scripts/validate_skill_contract.py", "skills"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_skill_index_is_current():
    result = subprocess.run(
        [sys.executable, "scripts/build_skill_index.py", "skills", "--output", "docs/agent_skills_index.md", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_skill_task_rubrics_validate():
    result = subprocess.run(
        [sys.executable, "scripts/score_skill_task.py", "--tasks-dir", "examples/skill_tasks", "--validate-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_skill_task_matrix_is_current():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_skill_task_report.py",
            "--tasks-dir",
            "examples/skill_tasks",
            "--output",
            "docs/results/skill_task_matrix.md",
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
