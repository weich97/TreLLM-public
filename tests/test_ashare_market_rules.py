from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from examples.ashare_market_rules_demo import AshareProposal, _evaluate_rules

ROOT = Path(__file__).resolve().parents[1]


def test_ashare_fixture_blocks_same_day_sell_and_price_limits():
    proposals = [
        AshareProposal(date(2026, 1, 2), "600519.SS", "buy", 200, 100.00, 99.20, "open position"),
        AshareProposal(date(2026, 1, 2), "600519.SS", "sell", 100, 100.00, 99.20, "same-day sell"),
        AshareProposal(date(2026, 1, 5), "600519.SS", "buy", 100, 110.00, 100.00, "limit-up buy"),
        AshareProposal(date(2026, 1, 6), "600519.SS", "sell", 100, 99.00, 110.00, "limit-down sell"),
    ]

    rows = _evaluate_rules(proposals)
    reasons = {row["risk_reason"]: row for row in rows if row["status"] == "blocked"}

    assert rows[1]["status"] == "blocked"
    assert rows[1]["risk_reason"] == "t_plus_1_sell_block"
    assert reasons["limit_up_buy_block"]["approved_quantity"] == 0
    assert reasons["limit_down_sell_block"]["approved_quantity"] == 0


def test_ashare_demo_writes_paper_only_no_download_summary():
    subprocess.run([sys.executable, "examples/ashare_market_rules_demo.py"], cwd=ROOT, check=True)

    summary_path = ROOT / "outputs/examples/ashare_market_rules_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["paper_only"] is True
    assert summary["downloads_data"] is False
    assert summary["summary"]["blocked_by_reason"]["t_plus_1_sell_block"] == 1
    assert summary["summary"]["blocked_by_reason"]["limit_up_buy_block"] == 1
    assert summary["summary"]["blocked_by_reason"]["limit_down_sell_block"] == 1
    assert (ROOT / "outputs/examples/ashare_market_rules_orders.csv").exists()
    assert (ROOT / "outputs/examples/ashare_market_rules.svg").exists()
