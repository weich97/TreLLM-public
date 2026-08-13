from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_direct_api_submission_checklist_covers_protocol_fields(tmp_path: Path):
    output_dir = tmp_path / "submission_checklist"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_direct_api_submission_checklist.py",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Checklist items: 14" in result.stdout
    assert "Protocol manifest fields covered: True" in result.stdout

    summary = json.loads((output_dir / "direct_api_submission_checklist_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "direct_api_submission_checklist_items.csv").open(encoding="utf-8")))
    markdown = (output_dir / "direct_api_submission_checklist.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_direct_api_submission_checklist_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "direct_api_submission_checklist"
    assert summary["checklist_item_count"] == 14
    assert summary["blocking_item_count"] == 14
    assert summary["protocol_manifest_field_count"] == 16
    assert summary["protocol_manifest_fields_covered"] is True
    assert summary["missing_protocol_manifest_fields"] == []
    assert "not provider-performance evidence" in summary["claim_boundary"]
    assert "does not close the direct_api_model_matrix gap" in summary["claim_boundary"]

    assert len(rows) == 14
    assert {row["phase"] for row in rows} >= {
        "planning",
        "manifest",
        "redaction",
        "binding",
        "submission",
        "validation",
        "claim-boundary",
    }
    assert any(row["item_id"] == "hash-only-prompt-response" for row in rows)
    assert any(row["item_id"] == "privacy-scan" for row in rows)
    assert any(row["item_id"] == "no-profitability-claim" for row in rows)
    assert "TreLLM v0.3 Direct API Submission Checklist" in markdown
    assert "raw provider prompt or response text" in markdown
