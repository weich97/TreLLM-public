from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_direct_api_matrix_plan_preregisters_rows_without_provider_calls(tmp_path: Path):
    output_dir = tmp_path / "matrix_plan"
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_direct_api_matrix_plan.py",
            "--output-dir",
            str(output_dir),
            "--models",
            "openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",
        ],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Planned rows: 30" in result.stdout
    assert "Coverage groups: 1" in result.stdout
    assert "Ready groups: 0" in result.stdout

    summary = json.loads((output_dir / "direct_api_matrix_plan_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "direct_api_matrix_plan_rows.csv").open(encoding="utf-8")))
    coverage = list(csv.DictReader((output_dir / "direct_api_matrix_plan_coverage.csv").open(encoding="utf-8")))
    markdown = (output_dir / "direct_api_matrix_plan_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_direct_api_matrix_plan_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "direct_api_model_matrix_plan"
    assert summary["planned_row_count"] == 30
    assert summary["coverage_group_count"] == 1
    assert summary["threshold_target_group_count"] == 1
    assert summary["ready_group_count"] == 0
    assert summary["ready_to_run"] is False
    assert "not model-performance evidence" in summary["claim_boundary"]
    assert "gap remains open" in summary["claim_boundary"]

    assert len(rows) == 30
    assert {row["credential_env_var"] for row in rows} == {"OPENAI_API_KEY"}
    assert {row["credential_env_var_present"] for row in rows} == {"false"}
    assert all("provider_manifests" in row["expected_provider_manifest_path"] for row in rows)
    assert all("submissions" in row["expected_submission_path"] for row in rows)

    assert len(coverage) == 1
    row = coverage[0]
    assert row["planned_row_count"] == "30"
    assert row["planned_seed_count"] == "10"
    assert row["planned_minimum_samples_per_seed"] == "3"
    assert row["main_threshold_target_met_by_plan"] == "true"
    assert row["credential_env_var_present"] == "false"
    assert row["preflight_status"] == "blocked"
    assert row["blocking_reasons"] == "credential_env_var_missing"
    assert "does not make provider calls" in markdown
