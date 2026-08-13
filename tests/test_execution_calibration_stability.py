from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_execution_calibration_stability_reports_window_reductions(tmp_path: Path):
    output = tmp_path / "stability.json"
    markdown = tmp_path / "stability.md"

    subprocess.run(
        [
            sys.executable,
            "scripts/run_execution_calibration_stability.py",
            "--window-size",
            "50",
            "--windows",
            "2",
            "--output",
            str(output),
            "--markdown-output",
            str(markdown),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["schema"] == "tradearena_execution_calibration_stability_v0.1"
    assert report["summary"]["window_count"] == 2
    assert report["summary"]["windows_where_calibrated_beats_stress"] >= 1
    assert "not venue-wide or broker-grade" in report["claim_boundary"]
    assert "Window Results" in markdown.read_text(encoding="utf-8")
