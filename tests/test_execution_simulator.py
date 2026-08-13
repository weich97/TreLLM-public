from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.crypto_microstructure_stress_demo import build_crypto_microstructure_stress_summary

ROOT = Path(__file__).resolve().parents[1]


def test_crypto_fee_tier_spread_shock_presets_change_realized_costs():
    summary = build_crypto_microstructure_stress_summary(periods=24)
    presets = {row["preset"]: row for row in summary["presets"]}

    assert summary["schema"] == "trellm_crypto_microstructure_stress_v0.2"
    assert summary["reproducible_inputs"]["seed"] == 21
    assert presets["baseline_fee_tier"]["fee_tier_bps"] < presets["fee_tier_spread_shock"]["fee_tier_bps"]
    assert presets["baseline_fee_tier"]["spread_bps"] < presets["fee_tier_spread_shock"]["spread_bps"]
    assert presets["fee_tier_spread_shock"]["total_commission"] > presets["baseline_fee_tier"]["total_commission"]
    assert presets["fee_tier_spread_shock"]["total_slippage_cost"] > presets["baseline_fee_tier"]["total_slippage_cost"]
    assert presets["fee_tier_spread_shock"]["execution_fill_rate"] <= presets["baseline_fee_tier"]["execution_fill_rate"]


def test_crypto_microstructure_demo_exposes_execution_artifact_fields():
    subprocess.run([sys.executable, "examples/crypto_microstructure_stress_demo.py"], cwd=ROOT, check=True)

    summary_path = ROOT / "outputs/examples/crypto_microstructure_stress/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    stress = next(row for row in summary["presets"] if row["preset"] == "fee_tier_spread_shock")

    assert summary["paper_only"] is True
    assert summary["downloads_data"] is False
    assert summary["calibration_boundary"] == "stress_assumption_not_venue_calibrated"
    assert stress["execution_fill_rate"] >= 0.0
    assert stress["total_slippage_cost"] >= 0.0
    assert stress["rejected_order_count"] >= 0
    assert stress["pending_orders_last"] >= 0
    assert (ROOT / "outputs/examples/crypto_microstructure_stress/crypto_microstructure_stress.svg").exists()
