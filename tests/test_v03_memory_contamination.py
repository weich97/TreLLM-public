from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_memory_contamination_generates_protocol_artifacts(tmp_path: Path):
    output_dir = tmp_path / "memory_contamination"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_memory_contamination.py",
            "--output-dir",
            str(output_dir),
            "--kinds",
            "fake_rejections",
            "--doses",
            "0,0.5",
            "--decays",
            "1.0",
            "--risks",
            "max-position",
            "--seeds",
            "7",
            "--periods",
            "12",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Rows: 2" in result.stdout
    summary = json.loads((output_dir / "memory_contamination_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "memory_contamination_rows.csv").open(encoding="utf-8")))
    aggregate_rows = list(csv.DictReader((output_dir / "memory_contamination_aggregate.csv").open(encoding="utf-8")))
    response_rows = list(csv.DictReader((output_dir / "memory_contamination_dose_response.csv").open(encoding="utf-8")))
    controls = list(csv.DictReader((output_dir / "contamination_tier_controls.csv").open(encoding="utf-8")))
    markdown = (output_dir / "memory_contamination_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_memory_contamination_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["contamination_tier"] == "C0"
    assert summary["implemented_tiers"] == ["C0"]
    assert summary["control_contract_only_tiers"] == ["C1", "C2"]
    assert summary["contamination_tiers_declared"] == ["C0", "C1", "C2"]
    assert summary["row_count"] == 2
    assert summary["aggregate_row_count"] == 2
    assert summary["primary_outcome"] == "memory_driven_leverage_amplification"
    assert "not model-performance or trading-profit evidence" in summary["claim_boundary"]

    assert {row["contamination_tier"] for row in rows} == {"C0"}
    assert {row["memory_contamination_kind"] for row in rows} == {"fake_rejections"}
    assert {row["memory_contamination_dose"] for row in rows} == {"0.0", "0.5"}
    assert {row["evidence_tier"] for row in rows} == {"protocol-fixture"}
    assert all(row["protocol_id"] == "trellm-v0.3-protocol" for row in rows)

    polluted = next(row for row in aggregate_rows if row["memory_contamination_dose"] == "0.5")
    baseline = next(row for row in aggregate_rows if row["memory_contamination_dose"] == "0.0")
    assert float(polluted["memory_pollution_ratio_mean"]) > float(baseline["memory_pollution_ratio_mean"])
    assert polluted["memory_driven_leverage_amplification_mean"]

    assert {row["contamination_tier"] for row in controls} == {"C0", "C1", "C2"}
    assert next(row for row in controls if row["contamination_tier"] == "C0")["status_in_this_artifact"] == "implemented"
    assert all(row["status_in_this_artifact"] for row in controls)
    assert any(row["outcome"] == "memory_pollution_ratio" for row in response_rows)
    assert any(row["outcome"] == "memory_driven_leverage_amplification" for row in response_rows)
    assert all(row["q_value"] for row in response_rows)

    assert "# TreLLM v0.3 Memory Contamination Pilot" in markdown
    assert "Contamination Tier Controls" in markdown
    assert "C1, C2" in markdown
