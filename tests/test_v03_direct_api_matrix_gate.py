from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_direct_api_matrix_gate_keeps_fixture_rows_as_pilot(tmp_path: Path):
    pilot_dir = tmp_path / "direct_api_pilot"
    gate_dir = tmp_path / "direct_api_gate"

    subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_direct_api_pilot.py",
            "--output-dir",
            str(pilot_dir),
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
            "scripts/build_v03_direct_api_matrix_gate.py",
            "--output-dir",
            str(gate_dir),
            "--submission-dirs",
            str(pilot_dir / "submissions"),
            "--provider-manifest-dirs",
            str(pilot_dir / "provider_manifests"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Rows: 4" in result.stdout
    assert "Coverage groups: 1" in result.stdout
    assert "Main-threshold groups: 0" in result.stdout

    summary = json.loads((gate_dir / "direct_api_matrix_gate_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((gate_dir / "direct_api_matrix_gate_rows.csv").open(encoding="utf-8")))
    coverage = list(csv.DictReader((gate_dir / "direct_api_matrix_gate_coverage.csv").open(encoding="utf-8")))
    markdown = (gate_dir / "direct_api_matrix_gate_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_direct_api_matrix_gate_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["row_count"] == 4
    assert summary["valid_row_count"] == 4
    assert summary["main_threshold_group_count"] == 0
    assert summary["headline_scientific_claim_ready"] is False
    assert "10 seeds and 3 samples per seed" in summary["open_gap_policy"]

    assert len(rows) == 4
    assert {row["row_validation_status"] for row in rows} == {"valid"}
    assert {row["threshold_eligible"] for row in rows} == {"false"}
    assert all(row["provider_manifest_sha256"].startswith("sha256:") for row in rows)
    assert all("direct-api" in row["evidence_tags"] for row in rows)
    assert all("protocol_fixture_not_scientific_model_evidence" in row["blocking_reasons"] for row in rows)
    assert all("fixture_provider_or_manifest_claim" in row["blocking_reasons"] for row in rows)

    assert len(coverage) == 1
    gate = coverage[0]
    assert gate["observed_seed_count"] == "2"
    assert gate["observed_minimum_samples_per_seed"] == "2"
    assert gate["seed_count"] == "0"
    assert gate["minimum_samples_per_seed"] == "0"
    assert gate["main_threshold_met"] == "false"
    assert gate["evidence_label"] == "pilot-or-incomplete"
    assert "insufficient_seed_count" in gate["blocking_reasons"]
    assert "insufficient_samples_per_seed" in gate["blocking_reasons"]
    assert "TreLLM v0.3 Direct API Matrix Gate" in markdown
    assert "does not promote fixture rows" in markdown
