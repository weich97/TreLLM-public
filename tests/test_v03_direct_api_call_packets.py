from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_direct_api_call_packets_bind_plan_rows_without_provider_calls(tmp_path: Path):
    plan_dir = tmp_path / "matrix_plan"
    output_dir = tmp_path / "call_packets"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_direct_api_matrix_plan.py",
            "--output-dir",
            str(plan_dir),
            "--models",
            "openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",
            "--seeds",
            "7,11",
            "--samples",
            "0,1",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_direct_api_call_packets.py",
            "--plan-rows",
            str(plan_dir / "direct_api_matrix_plan_rows.csv"),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Call packets: 4" in result.stdout
    assert "Credential-ready packets: 0" in result.stdout

    summary = json.loads((output_dir / "direct_api_call_packets_summary.json").read_text(encoding="utf-8"))
    manifest = list(csv.DictReader((output_dir / "direct_api_call_packet_manifest.csv").open(encoding="utf-8")))
    packets = [
        json.loads(line)
        for line in (output_dir / "direct_api_call_packets.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    markdown = (output_dir / "direct_api_call_packets.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_direct_api_call_packets_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "direct_api_call_packets"
    assert summary["call_packet_count"] == 4
    assert summary["credential_ready_packet_count"] == 0
    assert summary["not_run_packet_count"] == 4
    assert "do not call providers" in summary["claim_boundary"]
    assert "raw provider prompts/responses stay private" in summary["redaction_contract"]

    assert len(manifest) == 4
    assert len(packets) == 4
    assert {row["execution_status"] for row in manifest} == {"not_run"}
    assert {row["blocking_reasons"] for row in manifest} == {"credential_env_var_missing"}
    assert all(row["prompt_packet_sha256"].startswith("sha256:") for row in manifest)
    assert all("provider_manifests" in row["expected_provider_manifest_path"] for row in manifest)
    assert all("submissions" in row["expected_submission_path"] for row in manifest)

    first = packets[0]
    assert first["schema"] == "trellm_v0_3_direct_api_call_packet_v0.1"
    assert first["request_envelope"]["raw_prompt_public"] is False
    assert first["request_envelope"]["raw_response_public"] is False
    assert first["request_envelope"]["prompt_packet"]["raw_prompt_public"] is False
    assert first["output_contract"]["privacy_scan_required"] is True
    assert first["output_contract"]["matrix_gate_required"] is True
    assert first["execution_status"] == "not_run"
    assert "Store raw provider text only in private workspace storage." in first["operator_steps"]

    assert markdown.startswith("# TreLLM v0.3 Direct API Call Packets")
    assert "does not make provider calls" in markdown
