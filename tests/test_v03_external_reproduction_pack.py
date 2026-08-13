from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_external_reproduction_pack_writes_valid_maintainer_report():
    output_dir = ROOT / "outputs" / "test_v03_external_reproduction_pack"
    shutil.rmtree(output_dir, ignore_errors=True)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_v03_external_reproduction_pack.py",
                "--output-dir",
                "outputs/test_v03_external_reproduction_pack",
                "--environment-class",
                "linux",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert "Wrote outputs/test_v03_external_reproduction_pack/manifest.json" in result.stdout
        manifest_path = output_dir / "manifest.json"
        readme_path = output_dir / "README.md"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        readme = readme_path.read_text(encoding="utf-8")

        assert manifest["schema"] == "tradearena_external_reproduction_pack_v1"
        assert manifest["protocol_id"] == "trellm-v0.3-protocol"
        assert manifest["environment_class"] == "linux"
        assert manifest["report_author_type"] == "project-maintainer"
        assert manifest["independent_reviewer"] is False
        assert manifest["live_api_used"] is False
        assert manifest["private_fills_used"] is False
        assert manifest["trajectory_hash"]["reproducibility_hash"].startswith("sha256:")
        assert {command["returncode"] for command in manifest["commands"]} == {0}
        assert all(artifact["exists"] and str(artifact["sha256"]).startswith("sha256:") for artifact in manifest["artifacts"])
        assert any(command["id"] == "v03_direct_api_matrix_plan" for command in manifest["commands"])
        assert any(command["id"] == "v03_direct_api_call_packets" for command in manifest["commands"])
        assert any(command["id"] == "v03_direct_api_submission_checklist" for command in manifest["commands"])
        assert any(command["id"] == "v03_contamination_control_audit" for command in manifest["commands"])
        assert any(command["id"] == "v03_execution_stress_grid" for command in manifest["commands"])
        assert any(command["id"] == "v03_variance_decomposition" for command in manifest["commands"])
        assert any(command["id"] == "v03_finaudit_direct_model_plan" for command in manifest["commands"])
        assert any(command["id"] == "v03_claim_boundary_audit" for command in manifest["commands"])
        assert any(command["id"] == "v03_evidence_index" for command in manifest["commands"])
        assert any(
            artifact["path"].endswith("v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.json")
            for artifact in manifest["artifacts"]
        )
        assert any(
            artifact["path"].endswith("v0_3_direct_api_call_packets/direct_api_call_packets_summary.json")
            for artifact in manifest["artifacts"]
        )
        assert any(
            artifact["path"].endswith(
                "v0_3_direct_api_submission_checklist/direct_api_submission_checklist_summary.json"
            )
            for artifact in manifest["artifacts"]
        )
        assert any(
            artifact["path"].endswith("v0_3_execution_stress_grid/execution_stress_grid_summary.json")
            for artifact in manifest["artifacts"]
        )
        assert any(
            artifact["path"].endswith("v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_summary.json")
            for artifact in manifest["artifacts"]
        )
        assert any(
            artifact["path"].endswith(
                "v0_3_contamination_control_audit/contamination_control_audit_summary.json"
            )
            for artifact in manifest["artifacts"]
        )
        assert any(
            artifact["path"].endswith("v0_3_variance_decomposition/variance_decomposition_summary.json")
            for artifact in manifest["artifacts"]
        )
        assert any(
            artifact["path"].endswith("v0_3_claim_boundary_audit/claim_boundary_audit_summary.json")
            for artifact in manifest["artifacts"]
        )
        assert any(artifact["path"].endswith("v0_3_evidence_index/v0_3_evidence_index.json") for artifact in manifest["artifacts"])
        assert readme.startswith("# TreLLM v0.3 External Reproduction Pack")
        assert "Independent reviewer: `False`" in readme

        subprocess.run(
            [sys.executable, "scripts/validate_reproduction_report.py", str(manifest_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        gate_dir = output_dir / "gate_check"
        subprocess.run(
            [
                sys.executable,
                "scripts/build_v03_external_reproduction_gate.py",
                "--output-dir",
                str(gate_dir),
                "--report-dirs",
                str(output_dir),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        gate_summary = json.loads((gate_dir / "external_reproduction_gate_summary.json").read_text(encoding="utf-8"))
        assert gate_summary["report_count"] == 1
        assert gate_summary["accepted_report_count"] == 0
        assert gate_summary["external_reproduction_ready"] is False
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
