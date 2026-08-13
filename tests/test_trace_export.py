from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradearena.evaluation.trace_export import export_trajectory_to_trace_json

ROOT = Path(__file__).resolve().parents[1]


def test_trace_export_maps_trajectory_to_redacted_spans(tmp_path: Path):
    trajectory = ROOT / "outputs/examples/audit_walkthrough_trajectory.json"
    if not trajectory.exists():
        subprocess.run([sys.executable, "examples/audit_trajectory_walkthrough.py"], cwd=ROOT, check=True)
    output = tmp_path / "trace.json"

    trace = export_trajectory_to_trace_json(trajectory, output)

    assert trace["schema"] == "tradearena_opentelemetry_trace_v0.1"
    assert trace["redaction"]["prompt_payloads_exported"] is False
    assert trace["redaction"]["provider_outputs_exported"] is False
    assert output.exists()
    names = {span["name"] for span in trace["spans"]}
    assert {"tradearena.run", "market.observe", "agent.analyze", "risk.approve", "execution.simulate"}.issubset(names)
    serialized = json.dumps(trace)
    assert "response_text" not in serialized
    assert "raw_response" not in serialized
    assert "raw_prompts" not in serialized


def test_cli_export_trace_writes_json(tmp_path: Path):
    trajectory = ROOT / "outputs/examples/audit_walkthrough_trajectory.json"
    if not trajectory.exists():
        subprocess.run([sys.executable, "examples/audit_trajectory_walkthrough.py"], cwd=ROOT, check=True)
    output = tmp_path / "trace.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "export-trace",
            str(trajectory),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    trace = json.loads(output.read_text(encoding="utf-8"))

    assert trace["trace_id"]
    assert any(span["name"] == "execution.simulate" for span in trace["spans"])
