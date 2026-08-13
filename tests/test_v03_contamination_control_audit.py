from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_contamination_control_audit_separates_fixture_and_contract_tiers(tmp_path: Path):
    output_dir = tmp_path / "contamination_control_audit"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_contamination_control_audit.py",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Contamination tiers audited: 3" in result.stdout
    assert "Scientific-ready tiers: 0" in result.stdout

    summary = json.loads((output_dir / "contamination_control_audit_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "contamination_control_audit.csv").open(encoding="utf-8")))
    markdown = (output_dir / "contamination_control_audit.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_contamination_control_audit_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "contamination_control_audit"
    assert summary["tier_count"] == 3
    assert summary["fixture_ready_tier_count"] == 1
    assert summary["contract_only_tier_count"] == 2
    assert summary["scientific_ready_tier_count"] == 0
    assert summary["forward_freeze_tooling_present"] is True
    assert summary["memory_artifact_control_contract_only_tiers"] == ["C1", "C2"]
    assert "C1 and C2 remain contract-only" in summary["claim_boundary"]

    assert {row["contamination_tier"] for row in rows} == {"C0", "C1", "C2"}
    c0 = next(row for row in rows if row["contamination_tier"] == "C0")
    c1 = next(row for row in rows if row["contamination_tier"] == "C1")
    c2 = next(row for row in rows if row["contamination_tier"] == "C2")
    assert c0["readiness_status"] == "fixture-mechanism-ready"
    assert c0["blocking_gaps"] == ""
    assert c1["readiness_status"] == "contract-only"
    assert "memorization_probe_rows_missing" in c1["blocking_gaps"]
    assert c2["readiness_status"] == "tooling-present-contract-only"
    assert "forward_window_commitment_missing" in c2["blocking_gaps"]
    assert c2["verification_path"] == "scripts/freeze_forward_window.py"
    assert "Scientific-ready tiers: `0`" in markdown
