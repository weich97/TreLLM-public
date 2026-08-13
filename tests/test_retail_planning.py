from __future__ import annotations

from datetime import datetime

from tradearena.planning import FinancialGoal, Holding, InvestorProfile, RetailPlanningAgent, default_retail_universe


def test_retail_planner_blocks_unapproved_futures_and_requires_paper_approval():
    agent = RetailPlanningAgent()
    report = agent.create_report(
        profile=InvestorProfile(
            investor_id="unit-futures-gate",
            age=45,
            annual_income=220_000,
            net_worth=900_000,
            emergency_fund_months=10,
            time_horizon_years=8,
            risk_tolerance="aggressive",
            liquidity_need_ratio=0.05,
            max_drawdown_tolerance=0.30,
            investment_objective="growth with a small index futures overlay",
            allowed_asset_classes=("cash_equivalent", "bond_etf", "equity_etf", "sector_etf", "equity", "index_future"),
            allow_margin=True,
            allow_futures=True,
            max_derivatives_weight=0.04,
        ),
        goals=(FinancialGoal("growth", 1_200_000, 8),),
        holdings=(Holding("VTI", 100_000), Holding("BND", 50_000)),
        universe=default_retail_universe(),
        prices={"MES": 5200.0, "MCL": 80.0},
        timestamp=datetime(2026, 5, 17),
    )

    assert "MCL" in report.suitability_report.blocked_symbols
    assert all(order.manual_approval_required for order in report.rebalance_orders)
    assert len(report.futures_margin) == 1
    assert report.futures_margin[0].symbol == "MES"
    assert report.futures_margin[0].initial_margin > 0


def test_retail_planner_keeps_ordinary_profile_out_of_futures():
    agent = RetailPlanningAgent()
    report = agent.create_report(
        profile=InvestorProfile(
            investor_id="unit-ordinary",
            age=34,
            annual_income=110_000,
            net_worth=260_000,
            emergency_fund_months=6,
            time_horizon_years=10,
            risk_tolerance="moderate",
            liquidity_need_ratio=0.08,
            max_drawdown_tolerance=0.18,
            investment_objective="long-term diversified allocation",
            allow_margin=False,
            allow_futures=False,
        ),
        goals=(FinancialGoal("retirement", 700_000, 10),),
        holdings=(Holding("CASH", 10_000), Holding("AAPL", 20_000), Holding("VTI", 60_000)),
        universe=default_retail_universe(),
        prices={"MES": 5200.0, "MCL": 80.0},
        timestamp=datetime(2026, 5, 17),
    )

    assert not report.futures_margin
    assert all(item.asset_class not in ("index_future", "commodity_future") for item in report.approved_allocations)
    assert report.suitability_report.budget.allow_futures is False
    assert report.suitability_report.budget.max_derivatives_weight == 0.0
