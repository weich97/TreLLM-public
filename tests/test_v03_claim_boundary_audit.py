from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_claim_boundary_audit_keeps_public_narrative_bounded(tmp_path: Path):
    output_dir = tmp_path / "claim_boundary_audit"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_claim_boundary_audit.py",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Audit checks: 13" in result.stdout
    assert "Violations: 0" in result.stdout

    summary = json.loads((output_dir / "claim_boundary_audit_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "claim_boundary_audit_findings.csv").open(encoding="utf-8")))
    markdown = (output_dir / "claim_boundary_audit.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_claim_boundary_audit_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "claim_boundary_audit"
    assert summary["audit_target_count"] == 5
    assert summary["check_count"] == 13
    assert summary["violation_count"] == 0
    assert summary["blocking_violation_count"] == 0
    assert summary["headline_scientific_claim_ready"] is False
    assert "not evidence of model performance" in summary["claim_boundary"]

    assert len(rows) == 13
    assert {row["status"] for row in rows} == {"pass"}
    assert any(row["check_id"] == "evidence-index-headline-ready" for row in rows)
    assert any(row["check_id"] == "evidence-index-open-gaps" for row in rows)
    assert any(row["check_id"] == "risky-claim-context" for row in rows)
    assert "TreLLM v0.3 Claim Boundary Audit" in markdown
    assert "Violations: `0`" in markdown
