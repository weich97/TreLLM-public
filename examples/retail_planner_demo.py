from __future__ import annotations

import html
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tradearena.core.serialization import write_json
from tradearena.planning import (
    FinancialGoal,
    Holding,
    InvestorProfile,
    RetailPlanningAgent,
    default_retail_universe,
    load_holdings_csv,
)

OUTPUT_DIR = Path("outputs/examples")
HOLDINGS_FIXTURE = Path("examples/fixtures/retail_holdings.csv")


def main() -> int:
    timestamp = datetime(2026, 5, 17, 9, 30)
    agent = RetailPlanningAgent()
    universe = default_retail_universe()
    prices = {
        "SGOV": 100.50,
        "BND": 72.40,
        "VTI": 286.20,
        "VXUS": 64.80,
        "XLK": 229.10,
        "AAPL": 188.40,
        "MSFT": 421.70,
        "MES": 5240.00,
        "MCL": 78.20,
    }

    ordinary_report = agent.create_report(
        profile=InvestorProfile(
            investor_id="demo-retail-moderate",
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
        goals=(
            FinancialGoal("emergency reserve", target_amount=30_000, horizon_years=1, priority=1),
            FinancialGoal("retirement bridge", target_amount=750_000, horizon_years=12, priority=2),
        ),
        holdings=load_holdings_csv(HOLDINGS_FIXTURE),
        universe=universe,
        prices=prices,
        timestamp=timestamp,
    )

    futures_report = agent.create_report(
        profile=InvestorProfile(
            investor_id="demo-experienced-futures-overlay",
            age=44,
            annual_income=240_000,
            net_worth=1_250_000,
            emergency_fund_months=12,
            time_horizon_years=9,
            risk_tolerance="aggressive",
            liquidity_need_ratio=0.05,
            max_drawdown_tolerance=0.30,
            investment_objective="growth portfolio with small audited futures overlay",
            allowed_asset_classes=("cash_equivalent", "bond_etf", "equity_etf", "sector_etf", "equity", "index_future"),
            allow_margin=True,
            allow_futures=True,
            max_single_stock_weight=0.06,
            max_single_asset_weight=0.40,
            max_derivatives_weight=0.04,
        ),
        goals=(FinancialGoal("taxable growth portfolio", target_amount=1_800_000, horizon_years=9, priority=1),),
        holdings=(
            Holding("SGOV", 20_000),
            Holding("BND", 45_000),
            Holding("VTI", 88_000),
            Holding("VXUS", 32_000),
            Holding("AAPL", 15_000),
        ),
        universe=universe,
        prices=prices,
        timestamp=timestamp,
    )

    reports = {"ordinary_stock_etf_plan": ordinary_report, "experienced_futures_overlay": futures_report}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = _summary(reports)
    summary["holdings_csv_fixture"] = str(HOLDINGS_FIXTURE)
    write_json(OUTPUT_DIR / "retail_planning_summary.json", summary)
    _write_svg(OUTPUT_DIR / "retail_planning_allocation.svg", reports)
    _write_html(OUTPUT_DIR / "retail_planning_report.html", reports)
    write_json(OUTPUT_DIR / "retail_planning_audit.json", _jsonable(reports))

    print("Retail planning demo")
    for name, report in reports.items():
        print(
            f"  {name}: risk={report.suitability_report.budget.risk_score:.2f} "
            f"orders={len(report.rebalance_orders)} blocked={len(report.suitability_report.blocked_symbols)} "
            f"futures_margin={len(report.futures_margin)}"
        )
    print(f"\nWrote {OUTPUT_DIR / 'retail_planning_report.html'}")
    return 0


def _summary(reports: dict[str, Any]) -> dict[str, Any]:
    return {
        "api_free": True,
        "live_trading": False,
        "manual_approval_required": True,
        "scenarios": {
            name: {
                "investor_id": report.profile.investor_id,
                "risk_score": report.suitability_report.budget.risk_score,
                "approved_allocation_count": len(report.approved_allocations),
                "rebalance_order_count": len(report.rebalance_orders),
                "blocked_symbols": list(report.suitability_report.blocked_symbols),
                "clipped_symbols": list(report.suitability_report.clipped_symbols),
                "futures_margin_estimates": len(report.futures_margin),
                "suitability_passed": report.suitability_report.passed,
                "top_allocations": [
                    {
                        "symbol": allocation.symbol,
                        "weight": allocation.target_weight,
                        "asset_class": allocation.asset_class,
                    }
                    for allocation in sorted(report.approved_allocations, key=lambda item: item.target_weight, reverse=True)[:5]
                ],
            }
            for name, report in reports.items()
        },
        "artifacts": {
            "html_report": "outputs/examples/retail_planning_report.html",
            "summary": "outputs/examples/retail_planning_summary.json",
            "audit_json": "outputs/examples/retail_planning_audit.json",
            "allocation_svg": "outputs/examples/retail_planning_allocation.svg",
        },
    }


def _write_svg(path: Path, reports: dict[str, Any]) -> None:
    width, height = 1040, 540
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Retail planning allocation demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(42, 52, "Retail planning sandbox: suitability first, paper execution only", 24, "#0f172a", 800),
        _text(42, 82, "Two profiles flow through the same planner, suitability gate, rebalance planner, futures margin estimator, and audit report.", 13, "#64748b", 500),
    ]
    y = 124
    for idx, (name, report) in enumerate(reports.items()):
        x = 42 + idx * 500
        parts.append(f'<rect x="{x}" y="{y}" width="460" height="336" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
        parts.append(_text(x + 18, y + 34, name.replace("_", " ").title(), 17, "#0f172a", 800))
        parts.append(
            _text(
                x + 18,
                y + 58,
                f"risk score {report.suitability_report.budget.risk_score:.2f} | orders {len(report.rebalance_orders)} | futures estimates {len(report.futures_margin)}",
                12,
                "#64748b",
                700,
            )
        )
        bar_y = y + 92
        sorted_allocations = sorted(report.approved_allocations, key=lambda item: item.target_weight, reverse=True)[:7]
        colors = ["#2563eb", "#059669", "#f59e0b", "#7c3aed", "#dc2626", "#0f766e", "#64748b"]
        for row, allocation in enumerate(sorted_allocations):
            yy = bar_y + row * 32
            bar_width = max(4, allocation.target_weight * 360)
            color = colors[row % len(colors)]
            parts.append(f'<rect x="{x + 18}" y="{yy}" width="360" height="18" rx="5" fill="#e2e8f0"/>')
            parts.append(f'<rect x="{x + 18}" y="{yy}" width="{bar_width:.1f}" height="18" rx="5" fill="{color}"/>')
            parts.append(_text(x + 390, yy + 14, f"{allocation.symbol} {allocation.target_weight:.1%}", 11, "#334155", 800))
        warning_y = y + 302
        blocked = ", ".join(report.suitability_report.blocked_symbols) or "none"
        parts.append(_text(x + 18, warning_y, f"blocked: {blocked}", 12, "#dc2626", 800))
        parts.append(_text(x + 18, warning_y + 22, "all outputs are paper recommendations requiring human approval", 11, "#64748b", 500))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _write_html(path: Path, reports: dict[str, Any]) -> None:
    sections = "\n".join(_report_section(name, report) for name, report in reports.items())
    html_text = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>TreLLM Retail Planning Demo</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 38px 28px 52px; }}
h1 {{ margin: 0 0 8px; font-size: 34px; }}
h2 {{ margin: 30px 0 10px; font-size: 22px; }}
p {{ color: #475569; line-height: 1.55; }}
.notice {{ border-left: 4px solid #dc2626; background: #fff7ed; padding: 12px 14px; margin: 18px 0 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }}
.card {{ background: white; border: 1px solid #d8e2ed; border-radius: 8px; padding: 14px; }}
.metric {{ font-size: 26px; font-weight: 800; color: #2563eb; }}
table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8e2ed; border-radius: 8px; overflow: hidden; }}
th, td {{ padding: 9px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 13px; }}
th {{ background: #f1f5f9; color: #334155; }}
code {{ background: #eef2ff; padding: 2px 5px; border-radius: 4px; }}
</style>
<main>
  <h1>TreLLM Retail Planning Demo</h1>
  <p>This report demonstrates an auditable planning workflow: investor profile, suitability gate, target allocation, paper rebalance instructions, and futures margin estimates. It makes no live API calls and does not place live trades.</p>
  <div class="notice"><strong>Important:</strong> Educational and research artifact only. Recommendations require human review and are not investment, tax, legal, or futures trading advice.</div>
  <img src="retail_planning_allocation.svg" alt="Retail planning allocation chart" style="width:100%;max-width:1040px">
  {sections}
</main>
</html>
"""
    path.write_text(html_text, encoding="utf-8")


def _report_section(name: str, report: Any) -> str:
    allocations = "\n".join(
        f"<tr><td>{_e(allocation.symbol)}</td><td>{_e(allocation.asset_class)}</td><td>{allocation.target_weight:.1%}</td><td>{_e(allocation.rationale)}</td></tr>"
        for allocation in sorted(report.approved_allocations, key=lambda item: item.target_weight, reverse=True)
    )
    orders = "\n".join(
        f"<tr><td>{_e(order.symbol)}</td><td>{_e(order.side)}</td><td>${order.dollar_amount:,.0f}</td><td>{order.current_weight:.1%}</td><td>{order.target_weight:.1%}</td><td>{_e(order.status)}</td></tr>"
        for order in report.rebalance_orders
    )
    checks = "\n".join(
        f"<tr><td>{_e(check.name)}</td><td>{_e(check.severity)}</td><td>{'pass' if check.passed else 'flag'}</td><td>{_e(check.symbol or '-')}</td><td>{_e(check.message)}</td></tr>"
        for check in report.suitability_report.checks
    )
    futures = "\n".join(
        f"<tr><td>{_e(item.symbol)}</td><td>${item.target_notional:,.0f}</td><td>{item.estimated_contracts:.2f}</td><td>${item.initial_margin:,.0f}</td><td>{item.leverage_ratio:.1f}x</td></tr>"
        for item in report.futures_margin
    )
    futures = futures or '<tr><td colspan="5">No approved futures exposure.</td></tr>'
    return f"""
  <h2>{_e(name.replace("_", " ").title())}</h2>
  <div class="grid">
    <div class="card"><div>Investor</div><div class="metric">{_e(report.profile.investor_id)}</div></div>
    <div class="card"><div>Risk Score</div><div class="metric">{report.suitability_report.budget.risk_score:.2f}</div></div>
    <div class="card"><div>Portfolio Value</div><div class="metric">${report.total_portfolio_value:,.0f}</div></div>
    <div class="card"><div>Manual Approval</div><div class="metric">Required</div></div>
  </div>
  <h3>Approved Target Allocation</h3>
  <table><tr><th>Symbol</th><th>Class</th><th>Weight</th><th>Rationale</th></tr>{allocations}</table>
  <h3>Paper Rebalance Instructions</h3>
  <table><tr><th>Symbol</th><th>Side</th><th>Amount</th><th>Current</th><th>Target</th><th>Status</th></tr>{orders}</table>
  <h3>Suitability Checks</h3>
  <table><tr><th>Check</th><th>Severity</th><th>Result</th><th>Symbol</th><th>Message</th></tr>{checks}</table>
  <h3>Futures Margin Estimate</h3>
  <table><tr><th>Symbol</th><th>Target Notional</th><th>Contracts</th><th>Initial Margin</th><th>Leverage</th></tr>{futures}</table>
"""


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{_e(value)}</text>'


def _e(value: object) -> str:
    return html.escape(str(value))


if __name__ == "__main__":
    raise SystemExit(main())
