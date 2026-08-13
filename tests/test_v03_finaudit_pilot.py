from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_finaudit_pilot_generates_public_protocol_artifacts(tmp_path: Path):
    output_dir = tmp_path / "finaudit"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_finaudit_pilot.py",
            "--output-dir",
            str(output_dir),
            "--tasks",
            "4",
            "--periods",
            "16",
            "--base-seed",
            "410",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Tasks: 4" in result.stdout
    assert not (output_dir / "ground_truth.jsonl").exists()
    assert not (output_dir / "tasks").exists()

    summary = json.loads((output_dir / "finaudit_pilot_summary.json").read_text(encoding="utf-8"))
    task_rows = list(csv.DictReader((output_dir / "finaudit_pilot_task_manifest.csv").open(encoding="utf-8")))
    score_rows = list(csv.DictReader((output_dir / "finaudit_pilot_scores.csv").open(encoding="utf-8")))
    breakdown_rows = list(csv.DictReader((output_dir / "finaudit_pilot_difficulty_breakdown.csv").open(encoding="utf-8")))
    markdown = (output_dir / "finaudit_pilot_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_finaudit_pilot_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["contamination_tier"] == "C0"
    assert summary["task_count"] == 4
    assert summary["score_row_count"] == 8
    assert summary["answer_key_public"] is False
    assert summary["answer_key_sha256"].startswith("sha256:")
    assert summary["task_manifest_sha256"].startswith("sha256:")
    assert summary["required_metrics"] == ["precision", "recall", "f1", "wilson_interval", "difficulty_breakdown"]
    assert summary["conditions"] == ["cross-audit", "self-audit"]
    assert "not model-performance evidence" in summary["claim_boundary"]
    assert summary["cross_audit_f1"] > summary["self_audit_f1"]
    assert summary["self_audit_bias_recall_delta"] > 0

    assert len(task_rows) == 4
    assert {row["protocol_id"] for row in task_rows} == {"trellm-v0.3-protocol"}
    assert {row["scenario_id"] for row in task_rows} == {"synthetic_finaudit_c0_v0_3"}
    assert {row["contamination_tier"] for row in task_rows} == {"C0"}
    assert {row["answer_key_public"] for row in task_rows} == {"False"}
    assert all(row["trajectory_sha256"].startswith("sha256:") for row in task_rows)
    assert "kind" not in task_rows[0]
    assert "step_index" not in task_rows[0]

    assert {row["condition"] for row in score_rows} == {"cross-audit", "self-audit"}
    assert {row["auditor_id"] for row in score_rows} == {"fixture-cross-auditor-v0", "fixture-self-auditor-v0"}
    assert all(row["precision"] for row in score_rows)
    assert all(row["recall"] for row in score_rows)
    assert all(row["f1"] for row in score_rows)

    assert {row["difficulty"] for row in breakdown_rows} == {"L1", "L2", "L3", "all"}
    assert all(row["precision_wilson_low"] for row in breakdown_rows)
    assert all(row["recall_wilson_high"] for row in breakdown_rows)
    assert any(row["condition"] == "self-audit" and row["difficulty"] == "all" for row in breakdown_rows)

    assert "# TreLLM v0.3 FinAudit Pilot" in markdown
    assert "Difficulty Breakdown" in markdown
    assert "Answer key public: `False`" in markdown
