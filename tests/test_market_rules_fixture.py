from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.market_rules_fixture_demo import build_market_rules_fixture

ROOT = Path(__file__).resolve().parents[1]


def test_market_rules_fixture_covers_blocks_clips_and_costs():
    report = build_market_rules_fixture()
    rows = {row["case_id"]: row for row in report["cases"]}

    assert report["summary"]["blocked"] >= 2
    assert report["summary"]["clipped"] >= 2
    assert rows["ashare_same_day_sell"]["status"] == "clipped"
    assert "t_plus_one_sellable_clip" in rows["ashare_same_day_sell"]["reasons"]
    assert rows["ashare_limit_up_buy"]["status"] == "blocked"
    assert "limit_up_buy_block" in rows["ashare_limit_up_buy"]["reasons"]
    assert rows["hk_board_lot_rounding"]["approved_quantity"] == 500.0
    assert rows["crypto_fee_funding"]["estimated_fee"] > 0
    assert rows["crypto_fee_funding"]["estimated_funding"] > 0
    assert rows["liquidity_halt_clip"]["estimated_market_impact"] > 0


def test_market_rules_fixture_script_writes_reports(tmp_path: Path):
    subprocess.run([sys.executable, "examples/market_rules_fixture_demo.py"], cwd=ROOT, check=True)

    json_path = ROOT / "docs/results/market_rules_fixture.json"
    md_path = ROOT / "docs/results/market_rules_fixture.md"
    report = json.loads(json_path.read_text(encoding="utf-8"))

    assert report["schema"] == "tradearena_market_rules_fixture_v0.1"
    assert "Market Rules Fixture" in md_path.read_text(encoding="utf-8")
