from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.hk_market_rules_demo import build_hk_market_rules_fixture

ROOT = Path(__file__).resolve().parents[1]


def test_hk_fixture_translates_target_weights_to_board_lots():
    report = build_hk_market_rules_fixture()
    rows = {row["case_id"]: row for row in report["cases"]}

    assert report["schema"] == "trellm_hk_market_rules_demo_v0.1"
    assert report["paper_only"] is True
    assert report["downloads_data"] is False
    assert rows["tencent_round_down"]["target_weight"] == 0.25
    assert rows["tencent_round_down"]["raw_quantity"] == 781.25
    assert rows["tencent_round_down"]["approved_quantity"] == 500.0
    assert rows["tencent_round_down"]["status"] == "clipped"
    assert "lot_size_500" in rows["tencent_round_down"]["reasons"]
    assert rows["tencent_round_down"]["estimated_fee"] > 0


def test_hk_demo_writes_deterministic_artifacts():
    subprocess.run([sys.executable, "examples/hk_market_rules_demo.py"], cwd=ROOT, check=True)

    summary_path = ROOT / "outputs/examples/hk_market_rules_summary.json"
    report = json.loads(summary_path.read_text(encoding="utf-8"))

    assert report["assumptions"]["session"] == "cash_equity_regular_session"
    assert report["assumptions"]["stamp_duty_bps"] == 13.0
    assert report["summary"]["case_count"] == 3
    assert report["summary"]["clipped"] >= 2
    assert (ROOT / "outputs/examples/hk_market_rules_orders.csv").exists()
    assert (ROOT / "outputs/examples/hk_market_rules.svg").exists()
