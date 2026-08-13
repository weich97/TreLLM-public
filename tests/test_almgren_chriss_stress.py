from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradearena.tools.impact import AlmgrenChrissImpactStress

ROOT = Path(__file__).resolve().parents[1]


def test_almgren_chriss_stress_compares_linear_and_concave_impact():
    plugin = AlmgrenChrissImpactStress(eta=0.25, gamma=0.03, exponent=0.5)
    linear = plugin.estimate(
        symbol="SYN",
        side="buy",
        quantity=5_000.0,
        price=25.0,
        volume=50_000.0,
        model="linear",
    )
    concave = plugin.estimate(
        symbol="SYN",
        side="buy",
        quantity=5_000.0,
        price=25.0,
        volume=50_000.0,
        model="concave",
    )

    assert plugin.paper_only is True
    assert linear["assumption_class"] == "paper_impact_stress"
    assert linear["temporary_impact_cost"] > 0.0
    assert concave["temporary_impact_cost"] > linear["temporary_impact_cost"]
    assert concave["calibration_boundary"] == "stress_proxy_not_broker_calibrated"


def test_almgren_chriss_fixture_writes_artifacts_and_default_comparison():
    subprocess.run([sys.executable, "examples/almgren_chriss_stress_demo.py"], cwd=ROOT, check=True)

    summary_path = ROOT / "outputs/examples/almgren_chriss_stress/summary.json"
    report = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = {row["case_id"]: row for row in report["cases"]}

    assert report["schema"] == "trellm_almgren_chriss_impact_stress_v0.1"
    assert report["paper_only"] is True
    assert report["calibration_boundary"] == "stress_proxy_not_broker_calibrated"
    assert rows["default_linear"]["modeled_shortfall_bps"] == 0.0
    assert rows["linear_impact"]["modeled_shortfall_bps"] > rows["default_linear"]["modeled_shortfall_bps"]
    assert rows["concave_impact"]["modeled_shortfall_bps"] > rows["linear_impact"]["modeled_shortfall_bps"]
    assert (ROOT / "outputs/examples/almgren_chriss_stress/summary.md").exists()
    assert (ROOT / "outputs/examples/almgren_chriss_stress/almgren_chriss_stress.svg").exists()
