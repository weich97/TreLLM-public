from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json
from tradearena.planning import (
    FinancialGoal,
    InvestorProfile,
    RetailPlanningAgent,
    default_retail_universe,
    load_holdings_csv,
)

FIXTURE = Path("examples/fixtures/retail_holdings.csv")
OUTPUT_DIR = Path("outputs/examples/holdings_csv_import")


def main() -> int:
    holdings = load_holdings_csv(FIXTURE)
    report = RetailPlanningAgent().create_report(
        profile=InvestorProfile(
            investor_id="csv-import-demo",
            age=36,
            annual_income=125_000,
            net_worth=340_000,
            emergency_fund_months=7,
            time_horizon_years=12,
            risk_tolerance="moderate",
            liquidity_need_ratio=0.08,
            max_drawdown_tolerance=0.18,
            investment_objective="long-term wealth accumulation with controlled drawdown",
            allowed_asset_classes=("cash_equivalent", "bond_etf", "equity_etf", "sector_etf", "equity"),
            allow_margin=False,
            allow_futures=False,
            max_single_stock_weight=0.08,
            max_single_asset_weight=0.45,
        ),
        goals=(FinancialGoal("retirement bridge", target_amount=750_000, horizon_years=12, priority=1),),
        holdings=holdings,
        universe=default_retail_universe(),
        prices={"SGOV": 100.5, "BND": 72.4, "VTI": 286.2, "VXUS": 64.8, "XLK": 229.1, "AAPL": 188.4, "MSFT": 421.7},
        timestamp=datetime(2026, 5, 17, 9, 30),
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "input_csv": str(FIXTURE),
        "holding_count": len(holdings),
        "total_portfolio_value": report.total_portfolio_value,
        "rebalance_order_count": len(report.rebalance_orders),
        "manual_approval_required": all(order.manual_approval_required for order in report.rebalance_orders),
        "top_allocations": [
            {"symbol": item.symbol, "target_weight": item.target_weight, "asset_class": item.asset_class}
            for item in sorted(report.approved_allocations, key=lambda row: row.target_weight, reverse=True)[:5]
        ],
    }
    write_json(OUTPUT_DIR / "summary.json", summary)
    print("Holdings CSV import demo")
    print(f"  holdings={summary['holding_count']} portfolio=${summary['total_portfolio_value']:,.0f}")
    print(f"  wrote={OUTPUT_DIR / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
