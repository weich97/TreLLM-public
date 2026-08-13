from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.domain import Side
from tradearena.core.serialization import write_json
from tradearena.tools import MarketRuleState, hong_kong_rule_package, review_market_rule_order

OUTPUT_DIR = Path("outputs/examples")


@dataclass(frozen=True)
class HkTargetWeightCase:
    case_id: str
    symbol: str
    side: Side
    target_weight: float
    equity_hkd: float
    price_hkd: float
    lot_size: int
    rationale: str

    @property
    def raw_quantity(self) -> float:
        return self.equity_hkd * self.target_weight / self.price_hkd


def main() -> int:
    report = build_hk_market_rules_fixture()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "hk_market_rules_summary.json", report)
    _write_csv(OUTPUT_DIR / "hk_market_rules_orders.csv", report["cases"])
    _write_svg(OUTPUT_DIR / "hk_market_rules.svg", report)

    print("Hong Kong market-rule demo")
    print(
        f"  cases={report['summary']['case_count']} approved={report['summary']['approved']} "
        f"clipped={report['summary']['clipped']}"
    )
    print(f"  stamp_duty_bps={report['assumptions']['stamp_duty_bps']}")
    print(f"\nWrote {OUTPUT_DIR / 'hk_market_rules_summary.json'}")
    print(f"Wrote {OUTPUT_DIR / 'hk_market_rules.svg'}")
    return 0


def build_hk_market_rules_fixture() -> dict[str, Any]:
    cases = [
        HkTargetWeightCase(
            case_id="tencent_round_down",
            symbol="0700.HK",
            side=Side.BUY,
            target_weight=0.25,
            equity_hkd=1_000_000.0,
            price_hkd=320.0,
            lot_size=500,
            rationale="target 25% allocation must trade in 500-share board lots",
        ),
        HkTargetWeightCase(
            case_id="hsbc_board_lot",
            symbol="0005.HK",
            side=Side.BUY,
            target_weight=0.11,
            equity_hkd=500_000.0,
            price_hkd=62.5,
            lot_size=400,
            rationale="bank lot-size example with stamp-duty estimate",
        ),
        HkTargetWeightCase(
            case_id="meituan_exact_lot",
            symbol="3690.HK",
            side=Side.SELL,
            target_weight=0.12,
            equity_hkd=1_000_000.0,
            price_hkd=120.0,
            lot_size=100,
            rationale="target already maps to a tradable lot quantity",
        ),
    ]
    rows = [_evaluate_case(case) for case in cases]
    return {
        "schema": "trellm_hk_market_rules_demo_v0.1",
        "paper_only": True,
        "downloads_data": False,
        "assumptions": {
            "session": "cash_equity_regular_session",
            "calendar": "single deterministic paper session; no exchange calendar download",
            "currency": "HKD",
            "stamp_duty_bps": 13.0,
            "short_sale_eligibility": "not modeled in this lot-size fixture",
        },
        "cases": rows,
        "summary": {
            "case_count": len(rows),
            "approved": sum(1 for row in rows if row["status"] == "approved"),
            "clipped": sum(1 for row in rows if row["status"] == "clipped"),
            "blocked": sum(1 for row in rows if row["status"] == "blocked"),
        },
    }


def _evaluate_case(case: HkTargetWeightCase) -> dict[str, Any]:
    package = hong_kong_rule_package(lot_size=case.lot_size, stamp_duty_bps=13.0)
    decision = review_market_rule_order(
        symbol=case.symbol,
        side=case.side,
        quantity=case.raw_quantity,
        state=MarketRuleState(price=case.price_hkd, previous_close=case.price_hkd, available_cash=case.equity_hkd),
        package=package,
    )
    return {
        "case_id": case.case_id,
        "symbol": case.symbol,
        "side": case.side.value,
        "target_weight": case.target_weight,
        "equity_hkd": case.equity_hkd,
        "price_hkd": case.price_hkd,
        "lot_size": case.lot_size,
        "raw_quantity": case.raw_quantity,
        "approved_quantity": decision.approved_quantity,
        "status": decision.status,
        "reasons": list(decision.reasons),
        "estimated_fee": round(decision.estimated_fee, 6),
        "approved_notional_hkd": round(decision.approved_quantity * case.price_hkd, 6),
        "package": decision.metadata["package"],
        "rationale": case.rationale,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_svg(path: Path, report: dict[str, Any]) -> None:
    rows = report["cases"]
    width, height = 820, 380
    max_qty = max(row["raw_quantity"] for row in rows)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Hong Kong board-lot conversion demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 48, "Hong Kong board-lot conversion", 22, "#0f172a", 800),
        _text(36, 78, "Target weights become raw shares, then tradable board-lot quantities with stamp-duty notes.", 13, "#64748b", 400),
    ]
    for idx, row in enumerate(rows):
        y = 124 + idx * 72
        raw_width = 360 * row["raw_quantity"] / max_qty
        approved_width = 360 * row["approved_quantity"] / max_qty
        parts.append(_text(36, y + 19, row["symbol"], 14, "#0f172a", 800))
        parts.append(f'<rect x="150" y="{y}" width="{raw_width:.1f}" height="18" rx="4" fill="#cbd5e1"/>')
        parts.append(f'<rect x="150" y="{y + 24}" width="{approved_width:.1f}" height="18" rx="4" fill="#0f766e"/>')
        parts.append(_text(530, y + 14, f"raw {row['raw_quantity']:.2f}", 12, "#475569", 500))
        parts.append(_text(530, y + 38, f"approved {row['approved_quantity']:.0f} ({row['status']})", 12, "#0f172a", 700))
        parts.append(_text(690, y + 38, f"fee HKD {row['estimated_fee']:.2f}", 12, "#64748b", 500))
    parts.append(_text(36, 350, "Output: outputs/examples/hk_market_rules_summary.json", 12, "#64748b", 400))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{value}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
