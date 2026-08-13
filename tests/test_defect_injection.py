from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from tradearena.evaluation.defect_injection import (
    DEFECT_KINDS,
    applicable_steps,
    inject_defect,
    score_findings,
)
from tradearena.factory import build_default_system

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def clean_trajectory() -> dict:
    trajectory, _ = build_default_system(
        name="defect_source",
        symbols=("SYN", "ALT"),
        periods=30,
        seed=9,
        strategy_name="signal-weighted",
        analyst_names=("momentum", "macro-news"),
    ).run()
    return trajectory.to_dict()


@pytest.mark.parametrize("kind", DEFECT_KINDS)
def test_inject_leaves_original_untouched_and_labels_ground_truth(clean_trajectory, kind):
    before = json.dumps(clean_trajectory, sort_keys=True, default=str)

    defective, truth = inject_defect(clean_trajectory, kind, seed=3)

    assert json.dumps(clean_trajectory, sort_keys=True, default=str) == before
    assert truth["kind"] == kind
    assert truth["difficulty"] in {"L1", "L2", "L3"}
    assert 0 <= truth["step_index"] < len(defective["steps"])
    # The defective copy must actually differ from the original.
    assert json.dumps(defective, sort_keys=True, default=str) != before


def test_unclipped_position_exceeds_cap_without_clip_evidence(clean_trajectory):
    defective, truth = inject_defect(clean_trajectory, "unclipped_position", seed=1)

    step = defective["steps"][truth["step_index"]]
    target = next(
        d for d in step["approved_decisions"] if d.get("symbol") == truth["detail"]["symbol"]
    )
    assert abs(float(target["target_weight"])) > 0.35
    assert "risk_clipped_from" not in (target.get("metadata") or {})


def test_provenance_drift_changes_exactly_one_step(clean_trajectory):
    defective, truth = inject_defect(clean_trajectory, "provenance_drift", seed=2)

    versions = [step["reproducibility_state"].get("model_version") for step in defective["steps"]]
    drifted = [index for index, version in enumerate(versions) if version == "unverified-model-v9"]
    assert drifted == [truth["step_index"]]


def test_tampered_fill_price_moves_price_but_not_slippage(clean_trajectory):
    defective, truth = inject_defect(clean_trajectory, "tampered_fill_price", seed=4)

    step_index = truth["step_index"]
    original_step = clean_trajectory["steps"][step_index]
    defective_step = defective["steps"][step_index]
    original_fill = next(
        f for f in original_step["fills"] if f.get("symbol") == truth["detail"]["symbol"]
    )
    tampered_fill = next(
        f for f in defective_step["fills"] if f.get("symbol") == truth["detail"]["symbol"]
    )
    assert tampered_fill["price"] == pytest.approx(float(original_fill["price"]) * 1.05)
    assert tampered_fill["slippage"] == original_fill["slippage"]


def test_applicable_steps_rejects_unknown_kind(clean_trajectory):
    with pytest.raises(ValueError):
        applicable_steps(clean_trajectory, "unknown_kind")


def test_score_findings_precision_recall():
    truth = [
        {"kind": "unclipped_position", "step_index": 4},
        {"kind": "provenance_drift", "step_index": 9},
    ]
    findings = [
        {"kind": "unclipped_position", "step_index": 4},  # hit
        {"kind": "tampered_fill_price", "step_index": 9},  # wrong kind
        {"kind": "provenance_drift", "step_index": 12},  # wrong step
    ]

    result = score_findings(findings, truth)

    assert result["true_positives"] == 1
    assert result["precision"] == pytest.approx(1 / 3)
    assert result["recall"] == pytest.approx(0.5)

    tolerant = score_findings(findings, truth, step_tolerance=3)
    assert tolerant["true_positives"] == 2

    empty = score_findings([], truth)
    assert empty["precision"] == 0.0
    assert empty["f1"] == 0.0


def test_generator_writes_tasks_and_answer_key(tmp_path: Path):
    path = ROOT / "scripts" / "generate_audit_tasks.py"
    spec = importlib.util.spec_from_file_location("generate_audit_tasks", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    exit_code = module.main(
        ["--tasks", "4", "--periods", "20", "--output-dir", str(tmp_path)]
    )

    assert exit_code == 0
    task_dirs = sorted((tmp_path / "tasks").iterdir())
    assert len(task_dirs) == 4
    for task_dir in task_dirs:
        assert (task_dir / "trajectory.json").exists()
        assert (task_dir / "prompt.md").exists()
    answers = [
        json.loads(line)
        for line in (tmp_path / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(answers) == 4
    assert {answer["kind"] for answer in answers} == set(DEFECT_KINDS)
