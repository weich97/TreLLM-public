from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_execution_stress_grid_generates_axis_sensitivity_artifacts(tmp_path: Path):
    output_dir = tmp_path / "execution_stress_grid"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_execution_stress_grid.py",
            "--output-dir",
            str(output_dir),
            "--agents",
            "signal-weighted,random",
            "--seeds",
            "7",
            "--periods",
            "8",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Rows: 12" in result.stdout
    assert "Sensitivity rows: 10" in result.stdout

    summary = json.loads((output_dir / "execution_stress_grid_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "execution_stress_grid_rows.csv").open(encoding="utf-8")))
    sensitivity = list(csv.DictReader((output_dir / "execution_stress_grid_sensitivity.csv").open(encoding="utf-8")))
    markdown = (output_dir / "execution_stress_grid_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_execution_stress_grid_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["execution_levels"] == ["E1", "E2"]
    assert summary["baseline_profile"] == "e1_reference"
    assert summary["row_count"] == 12
    assert summary["sensitivity_row_count"] == 10
    assert summary["method"] == "paired_seed_delta_vs_e1_reference"
    assert "not live cost prediction" in summary["claim_boundary"]
    assert set(summary["stress_axes"]) == {"combined", "impact", "latency", "participation", "reference", "spread"}

    assert len(rows) == 12
    assert {row["evidence_tier"] for row in rows} == {"protocol-fixture"}
    assert {row["execution_level"] for row in rows} == {"E1", "E2"}
    assert {row["stress_profile"] for row in rows} == set(summary["stress_profiles"])

    assert len(sensitivity) == 10
    assert {row["baseline_profile"] for row in sensitivity} == {"e1_reference"}
    assert {row["paired_seed_count"] for row in sensitivity} == {"1"}
    assert {row["stress_axis"] for row in sensitivity} == {"combined", "impact", "latency", "participation", "spread"}
    assert any(abs(float(row["slippage_delta_mean"])) > 0 for row in sensitivity)
    assert any(abs(float(row["intent_execution_gap_delta_mean"])) > 0 for row in sensitivity)

    assert markdown.startswith("# TreLLM v0.3 Execution Stress Grid")
    assert "Axis Summary" in markdown
    assert "not a trading-profit claim" in markdown
