from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_power_note_outputs_detectable_effect_artifact(tmp_path: Path):
    output_dir = tmp_path / "power_note"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_power_note.py",
            "--output-dir",
            str(output_dir),
            "--repeat-levels",
            "6,10",
            "--effect-sizes",
            "0.8,1.2",
            "--target-powers",
            "0.5",
            "--draws",
            "30",
            "--permutation-draws",
            "128",
            "--seed",
            "3",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Power rows: 4" in result.stdout
    assert "Detectable-effect rows: 2" in result.stdout

    summary = json.loads((output_dir / "v0_3_power_note_summary.json").read_text(encoding="utf-8"))
    power_rows = list(csv.DictReader((output_dir / "v0_3_power_curves.csv").open(encoding="utf-8")))
    detectable_rows = list(csv.DictReader((output_dir / "v0_3_detectable_effects.csv").open(encoding="utf-8")))
    markdown = (output_dir / "v0_3_power_note_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_power_note_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "power_detectable_effect_note"
    assert summary["minimum_repeats_for_alpha_005"] == 6
    assert "2/32=0.0625" in summary["structural_note"]
    assert "not evidence of model superiority" in summary["claim_boundary"]
    assert summary["llm_main_comparison_threshold"] == {
        "minimum_seeds": 10,
        "samples_per_seed": 3,
        "below_threshold_label": "pilot evidence",
    }
    assert set(summary["artifacts"]) == {
        "v0_3_power_curves.csv",
        "v0_3_detectable_effects.csv",
        "v0_3_power_note_summary.json",
        "v0_3_power_note_summary.md",
    }

    assert len(power_rows) == 4
    assert {row["mode"] for row in power_rows} == {"synthetic"}
    assert {row["claim_scope"] for row in power_rows} == {"planning-note-not-model-performance-evidence"}
    assert all(0.0 <= float(row["power"]) <= 1.0 for row in power_rows)
    assert {int(row["repeat_count"]) for row in power_rows} == {6, 10}

    assert len(detectable_rows) == 2
    assert {float(row["target_power"]) for row in detectable_rows} == {0.5}
    assert {int(row["repeat_count"]) for row in detectable_rows} == {6, 10}
    assert {row["grid_status"] for row in detectable_rows} <= {"detected", "not_detected_in_grid"}
    assert "TreLLM v0.3 Power and Detectable-Effect Note" in markdown
    assert "Rows below the v0.3 LLM main-comparison threshold" in markdown
