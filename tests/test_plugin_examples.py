from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

from tradearena.core.domain import Bar, Decision, MarketSnapshot, PortfolioState, Side

ROOT = Path(__file__).resolve().parents[1]


def test_curated_sector_concentration_guard_imports_and_clips_deterministically():
    module = import_module("plugins.examples.sector_concentration_guard")
    guard = module.SectorConcentrationGuard(
        sector_map={"AAA": "technology", "BBB": "technology", "CCC": "energy"},
        max_sector_weight=0.50,
    )
    snapshot = _snapshot()
    portfolio = PortfolioState(cash=100_000.0, last_prices={"AAA": 100.0, "BBB": 100.0, "CCC": 100.0})
    decisions = [
        Decision("AAA", Side.BUY, 0.40, 0.9, "tech leg one"),
        Decision("BBB", Side.BUY, 0.30, 0.8, "tech leg two"),
        Decision("CCC", Side.BUY, 0.10, 0.7, "energy diversifier"),
    ]

    approved = guard.approve(snapshot, decisions, portfolio, memory=None)

    assert [decision.symbol for decision in approved] == ["AAA", "BBB", "CCC"]
    assert approved[0].target_weight == 0.28571428571428575
    assert approved[1].target_weight == 0.21428571428571427
    assert approved[2].target_weight == 0.10
    assert approved[0].metadata["sector"] == "technology"
    assert approved[0].metadata["sector_concentration_scaled_by"] == 0.7142857142857143
    assert guard.last_report is not None
    assert guard.last_report.clipped_count == 2
    assert guard.last_report.checks[-1].name == "sector_concentration"


def test_plugin_readmes_explain_scaffold_vs_curated_example():
    registry_readme = (ROOT / "plugins/README.md").read_text(encoding="utf-8")
    example_readme = (ROOT / "plugins/examples/sector_concentration_guard/README.md").read_text(encoding="utf-8")

    assert "tradearena new-plugin" in registry_readme
    assert "curated example" in registry_readme
    assert "generated local scaffold" in registry_readme
    assert "python -m pytest tests/test_plugin_examples.py -q" in example_readme


def _snapshot() -> MarketSnapshot:
    timestamp = datetime(2026, 6, 1, tzinfo=timezone.utc)
    return MarketSnapshot(
        timestamp=timestamp,
        bars={
            symbol: Bar(
                symbol=symbol,
                timestamp=timestamp,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=10_000.0,
            )
            for symbol in ("AAA", "BBB", "CCC")
        },
    )
