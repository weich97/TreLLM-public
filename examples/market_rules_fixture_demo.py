from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.domain import Side
from tradearena.core.serialization import write_json
from tradearena.tools.market_rules import (
    MarketRulePackage,
    MarketRuleState,
    ashare_rule_package,
    crypto_rule_package,
    hong_kong_rule_package,
    liquidity_halt_rule_package,
    review_market_rule_order,
)


def main() -> int:
    report = build_market_rules_fixture()
    json_path = ROOT / "docs/results/market_rules_fixture.json"
    md_path = ROOT / "docs/results/market_rules_fixture.md"
    write_json(json_path, report)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path.relative_to(ROOT).as_posix()}")
    print(f"Wrote {md_path.relative_to(ROOT).as_posix()}")
    return 0


def build_market_rules_fixture() -> dict[str, Any]:
    cases = [
        _case(
            case_id="ashare_same_day_sell",
            package=ashare_rule_package(),
            symbol="600000.SH",
            side=Side.SELL,
            quantity=500,
            state=MarketRuleState(price=9.85, previous_close=10.0, settled_position=400, same_day_buy_quantity=300),
        ),
        _case(
            case_id="ashare_limit_up_buy",
            package=ashare_rule_package(),
            symbol="600000.SH",
            side=Side.BUY,
            quantity=300,
            state=MarketRuleState(price=11.0, previous_close=10.0, available_cash=100_000),
        ),
        _case(
            case_id="hk_board_lot_rounding",
            package=hong_kong_rule_package(lot_size=500),
            symbol="0700.HK",
            side=Side.BUY,
            quantity=760,
            state=MarketRuleState(price=320.0, previous_close=318.0, available_cash=500_000),
        ),
        _case(
            case_id="crypto_fee_funding",
            package=crypto_rule_package(fee_bps=6.0, funding_bps=1.5),
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=2.0,
            state=MarketRuleState(price=61_200.0, volume=120.0, available_cash=100_000),
        ),
        _case(
            case_id="liquidity_halt_clip",
            package=liquidity_halt_rule_package(participation_rate=0.02, eta=0.20),
            symbol="SYN",
            side=Side.BUY,
            quantity=4_000,
            state=MarketRuleState(price=25.0, volume=50_000, available_cash=200_000),
        ),
        _case(
            case_id="suspension_block",
            package=liquidity_halt_rule_package(participation_rate=0.02, eta=0.20),
            symbol="SYN",
            side=Side.SELL,
            quantity=1_000,
            state=MarketRuleState(price=25.0, volume=50_000, settled_position=2_000, suspended=True),
        ),
    ]
    return {
        "schema": "tradearena_market_rules_fixture_v0.1",
        "claim_boundary": (
            "These are deterministic exchange-rule fixtures for auditability. They are not live-trading "
            "advice and do not claim full regulatory coverage for any venue."
        ),
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "blocked": sum(1 for row in cases if row["status"] == "blocked"),
            "clipped": sum(1 for row in cases if row["status"] == "clipped"),
            "approved": sum(1 for row in cases if row["status"] == "approved"),
        },
    }


def _case(
    *,
    case_id: str,
    package: MarketRulePackage,
    symbol: str,
    side: Side,
    quantity: float,
    state: MarketRuleState,
) -> dict[str, Any]:
    decision = review_market_rule_order(
        symbol=symbol,
        side=side,
        quantity=quantity,
        state=state,
        package=package,
    )
    return {
        "case_id": case_id,
        "package": package.name,
        "symbol": decision.symbol,
        "side": decision.side.value,
        "requested_quantity": decision.requested_quantity,
        "approved_quantity": decision.approved_quantity,
        "status": decision.status,
        "reasons": list(decision.reasons),
        "estimated_fee": round(decision.estimated_fee, 6),
        "estimated_funding": round(decision.estimated_funding, 6),
        "estimated_market_impact": round(decision.estimated_market_impact, 6),
        "estimated_margin_required": round(decision.estimated_margin_required, 6),
        "metadata": decision.metadata,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Market Rules Fixture",
        "",
        report["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Cases: {report['summary']['case_count']}",
        f"- Approved: {report['summary']['approved']}",
        f"- Clipped: {report['summary']['clipped']}",
        f"- Blocked: {report['summary']['blocked']}",
        "",
        "## Cases",
        "",
        "| Case | Package | Symbol | Side | Requested | Approved | Status | Reasons | Fees | Funding | Impact |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: |",
    ]
    for row in report["cases"]:
        lines.append(
            f"| `{row['case_id']}` | `{row['package']}` | {row['symbol']} | {row['side']} | "
            f"{row['requested_quantity']:.4g} | {row['approved_quantity']:.4g} | {row['status']} | "
            f"{', '.join(row['reasons']) or 'none'} | {row['estimated_fee']:.4f} | "
            f"{row['estimated_funding']:.4f} | {row['estimated_market_impact']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python examples/market_rules_fixture_demo.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
