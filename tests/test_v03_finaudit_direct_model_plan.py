from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_finaudit_direct_model_plan_preregisters_private_scoring_boundary(tmp_path: Path):
    pilot_dir = tmp_path / "finaudit"
    output_dir = tmp_path / "finaudit_direct_model_plan"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_finaudit_pilot.py",
            "--output-dir",
            str(pilot_dir),
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

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_finaudit_direct_model_plan.py",
            "--task-manifest",
            str(pilot_dir / "finaudit_pilot_task_manifest.csv"),
            "--output-dir",
            str(output_dir),
            "--models",
            "openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Planned audit rows: 8" in result.stdout
    assert "Ready groups: 0" in result.stdout

    summary = json.loads((output_dir / "finaudit_direct_model_plan_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "finaudit_direct_model_plan_rows.csv").open(encoding="utf-8")))
    coverage = list(csv.DictReader((output_dir / "finaudit_direct_model_plan_coverage.csv").open(encoding="utf-8")))
    markdown = (output_dir / "finaudit_direct_model_plan.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_finaudit_direct_model_plan_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "finaudit_direct_model_plan"
    assert summary["planned_row_count"] == 8
    assert summary["task_count"] == 4
    assert summary["conditions"] == ["cross-audit", "self-audit"]
    assert summary["answer_key_public"] is False
    assert summary["all_rows_not_run"] is True
    assert "does not call providers" in summary["claim_boundary"]
    assert "publish answer keys" in summary["claim_boundary"]

    assert len(rows) == 8
    assert {row["condition"] for row in rows} == {"cross-audit", "self-audit"}
    assert {row["execution_status"] for row in rows} == {"not_run"}
    assert {row["blocking_reasons"] for row in rows} == {"credential_env_var_missing"}
    assert {row["answer_key_public"] for row in rows} == {"false"}
    assert all(row["audit_request_packet_sha256"].startswith("sha256:") for row in rows)
    assert all("private_responses" in row["expected_private_response_path"] for row in rows)
    assert all("public_scores" in row["expected_public_score_path"] for row in rows)

    assert len(coverage) == 2
    assert {row["execution_status"] for row in coverage} == {"blocked"}
    assert {row["blocking_reasons"] for row in coverage} == {"credential_env_var_missing"}
    assert markdown.startswith("# TreLLM v0.3 FinAudit Direct-Model Plan")
    assert "does not call providers" in markdown
