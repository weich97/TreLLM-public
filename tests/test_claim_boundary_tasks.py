from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "generate_claim_boundary_tasks.py"
    spec = importlib.util.spec_from_file_location("generate_claim_boundary_tasks", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_task_mixes_violations_and_controls():
    module = _load_module()

    prompt, truth = module.generate_task(0, seed=42)

    assert len(truth) == 5
    supported = [row for row in truth if row["supported"]]
    unsupported = [row for row in truth if not row["supported"]]
    assert len(supported) == 2
    assert len(unsupported) == 3
    assert all(row["claim_level"] in module.CLAIM_LEVELS for row in truth)
    assert all(row["why_unsupported"] for row in unsupported)
    for row in truth:
        assert f"{row['claim_index']}." in prompt


def test_generation_is_deterministic_per_seed():
    module = _load_module()

    first = module.generate_task(0, seed=7)
    second = module.generate_task(0, seed=7)
    different = module.generate_task(0, seed=8)

    assert first == second
    assert first != different


def test_score_claim_answers_grades_levels_support_and_recall():
    module = _load_module()
    truth = [
        {"claim_index": 1, "claim_level": "engineering", "supported": True},
        {"claim_index": 2, "claim_level": "scientific", "supported": False},
        {"claim_index": 3, "claim_level": "execution-realism", "supported": False},
    ]
    answers = [
        {"claim_index": 1, "claim_level": "Engineering", "supported": True},  # both right
        {"claim_index": 2, "claim_level": "benchmark", "supported": False},  # level wrong, support right
        # claim 3 unanswered
    ]

    result = module.score_claim_answers(answers, truth)

    assert result["claims"] == 3
    assert result["graded"] == 2
    assert result["level_accuracy"] == 1 / 3
    assert result["support_accuracy"] == 2 / 3
    assert result["violation_recall"] == 1 / 2


def test_main_writes_tasks_and_answer_key(tmp_path: Path):
    module = _load_module()

    exit_code = module.main(["--tasks", "3", "--output-dir", str(tmp_path)])

    assert exit_code == 0
    task_dirs = sorted((tmp_path / "tasks").iterdir())
    assert len(task_dirs) == 3
    assert all((task_dir / "prompt.md").exists() for task_dir in task_dirs)
    rows = [
        json.loads(line)
        for line in (tmp_path / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 15  # 3 tasks x 5 claims
