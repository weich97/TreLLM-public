from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.liquidity_halt_demo import build_liquidity_halt_fixture

ROOT = Path(__file__).resolve().parents[1]


def test_liquidity_halt_fixture_captures_pending_partial_rejected_and_blocked_orders():
    report = build_liquidity_halt_fixture()
    steps = {step["step_id"]: step for step in report["trajectory"]["steps"]}

    assert report["schema"] == "trellm_liquidity_halt_stress_v0.1"
    assert report["paper_only"] is True
    assert report["downloads_data"] is False
    assert report["summary"]["pending_before_halt"] >= 1
    assert report["summary"]["partial_fills"] >= 1
    assert report["summary"]["rejected_orders"] >= 1
    assert report["summary"]["blocked_by_halt"] >= 1
    assert steps["pre_halt_pending"]["execution_report"]["pending_orders"] == 1
    assert steps["thin_liquidity_partial"]["execution_report"]["partial_fills"] == 1
    assert steps["halt_release_reject"]["execution_report"]["rejected_orders"] == 1
    assert steps["halt_release_reject"]["risk_report"]["checks"][0]["name"] == "circuit_halt"
    assert steps["halt_release_reject"]["risk_report"]["passed"] is False


def test_liquidity_halt_demo_writes_replayable_artifacts():
    subprocess.run([sys.executable, "examples/liquidity_halt_demo.py"], cwd=ROOT, check=True)

    summary_path = ROOT / "outputs/examples/liquidity_halt/summary.json"
    report = json.loads(summary_path.read_text(encoding="utf-8"))

    assert report["artifact_paths"]["trajectory"].endswith("trajectory.json")
    assert report["replay"]["command"] == "python examples/liquidity_halt_demo.py"
    assert report["trajectory"]["schema_version"] == "tradearena_trajectory_v1"
    assert (ROOT / "outputs/examples/liquidity_halt/trajectory.json").exists()
    assert (ROOT / "outputs/examples/liquidity_halt/summary.md").exists()
    assert (ROOT / "outputs/examples/liquidity_halt/liquidity_halt.svg").exists()
