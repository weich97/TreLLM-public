from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from tradearena.core.serialization import write_json

OUTPUT_DIR = Path("outputs/examples")


@dataclass(frozen=True)
class AshareProposal:
    trade_date: date
    symbol: str
    side: str
    quantity: int
    close: float
    previous_close: float
    rationale: str


def main() -> int:
    proposals = [
        AshareProposal(date(2026, 1, 2), "600519.SS", "buy", 250, 100.00, 99.20, "enter core liquor position"),
        AshareProposal(date(2026, 1, 2), "600519.SS", "sell", 100, 100.00, 99.20, "same-day stop loss attempt"),
        AshareProposal(date(2026, 1, 5), "600519.SS", "buy", 100, 110.00, 100.00, "chase limit-up momentum"),
        AshareProposal(date(2026, 1, 6), "600519.SS", "sell", 100, 99.00, 110.00, "exit at limit-down"),
        AshareProposal(date(2026, 1, 7), "600519.SS", "sell", 100, 102.00, 99.00, "valid next-day exit"),
    ]
    events = _evaluate_rules(proposals)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(
        OUTPUT_DIR / "ashare_market_rules_summary.json",
        {
            "schema": "trellm_ashare_market_rules_demo_v0.1",
            "paper_only": True,
            "downloads_data": False,
            "events": events,
            "summary": _summary(events),
        },
    )
    _write_csv(OUTPUT_DIR / "ashare_market_rules_orders.csv", events)
    _write_svg(OUTPUT_DIR / "ashare_market_rules.svg", events)

    summary = _summary(events)
    print("A-share market-rule risk demo")
    print(f"  proposals={summary['proposals']} approved={summary['approved']} blocked={summary['blocked']} clipped={summary['clipped']}")
    for reason, count in summary["blocked_by_reason"].items():
        print(f"  blocked[{reason}]={count}")
    print(f"\nWrote {OUTPUT_DIR / 'ashare_market_rules_summary.json'}")
    print(f"Wrote {OUTPUT_DIR / 'ashare_market_rules.svg'}")
    return 0


def _evaluate_rules(proposals: list[AshareProposal]) -> list[dict[str, Any]]:
    settled_positions: dict[str, int] = {}
    unsettled_by_day: dict[tuple[str, date], int] = {}
    events = []
    for proposal in proposals:
        upper_limit = round(proposal.previous_close * 1.10, 2)
        lower_limit = round(proposal.previous_close * 0.90, 2)
        event = {
            "date": proposal.trade_date.isoformat(),
            "symbol": proposal.symbol,
            "side": proposal.side,
            "requested_quantity": proposal.quantity,
            "approved_quantity": proposal.quantity,
            "close": proposal.close,
            "upper_limit": upper_limit,
            "lower_limit": lower_limit,
            "status": "approved",
            "risk_reason": "",
            "rationale": proposal.rationale,
        }
        if proposal.side == "buy" and proposal.quantity % 100:
            event["approved_quantity"] = (proposal.quantity // 100) * 100
            event["status"] = "clipped"
            event["risk_reason"] = "board_lot_100"
        if proposal.side == "buy" and proposal.close >= upper_limit:
            event["approved_quantity"] = 0
            event["status"] = "blocked"
            event["risk_reason"] = "limit_up_buy_block"
        elif proposal.side == "sell" and proposal.close <= lower_limit:
            event["approved_quantity"] = 0
            event["status"] = "blocked"
            event["risk_reason"] = "limit_down_sell_block"
        elif proposal.side == "sell":
            same_day_buys = unsettled_by_day.get((proposal.symbol, proposal.trade_date), 0)
            sellable = max(0, settled_positions.get(proposal.symbol, 0) - same_day_buys)
            if proposal.quantity > sellable:
                event["approved_quantity"] = 0
                event["status"] = "blocked"
                event["risk_reason"] = "t_plus_1_sell_block"

        approved = int(event["approved_quantity"])
        if approved and proposal.side == "buy":
            settled_positions[proposal.symbol] = settled_positions.get(proposal.symbol, 0) + approved
            unsettled_by_day[(proposal.symbol, proposal.trade_date)] = unsettled_by_day.get((proposal.symbol, proposal.trade_date), 0) + approved
        elif approved and proposal.side == "sell":
            settled_positions[proposal.symbol] = max(0, settled_positions.get(proposal.symbol, 0) - approved)
        event["settled_position_after"] = settled_positions.get(proposal.symbol, 0)
        events.append(event)
    return events


def _summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    blocked_by_reason: dict[str, int] = {}
    for event in events:
        if event["status"] == "blocked":
            blocked_by_reason[event["risk_reason"]] = blocked_by_reason.get(event["risk_reason"], 0) + 1
    return {
        "proposals": len(events),
        "approved": sum(1 for event in events if event["status"] == "approved"),
        "blocked": sum(1 for event in events if event["status"] == "blocked"),
        "clipped": sum(1 for event in events if event["status"] == "clipped"),
        "blocked_by_reason": blocked_by_reason,
    }


def _write_csv(path: Path, events: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(events)


def _write_svg(path: Path, events: list[dict[str, Any]]) -> None:
    counts = {status: sum(1 for event in events if event["status"] == status) for status in ("approved", "clipped", "blocked")}
    colors = {"approved": "#059669", "clipped": "#d97706", "blocked": "#dc2626"}
    width, height = 760, 360
    max_count = max(1, max(counts.values()))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="A-share market rule interventions">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 48, "A-share rule interventions: T+1, price limits, board lots", 22, "#0f172a", 800),
        _text(36, 78, "A small local demo for how hard market rules become auditable risk-gate outcomes.", 13, "#64748b", 400),
    ]
    for idx, status in enumerate(("approved", "clipped", "blocked")):
        x = 90 + idx * 210
        bar_height = 190 * counts[status] / max_count
        y = 285 - bar_height
        parts.append(f'<rect x="{x}" y="{y:.1f}" width="92" height="{bar_height:.1f}" rx="7" fill="{colors[status]}"/>')
        parts.append(_text(x + 46, y - 12, str(counts[status]), 16, "#0f172a", 800, "middle"))
        parts.append(_text(x + 46, 315, status, 14, "#0f172a", 700, "middle"))
    parts.append(_text(36, 345, "Output: outputs/examples/ashare_market_rules_summary.json", 12, "#64748b", 400))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{value}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
