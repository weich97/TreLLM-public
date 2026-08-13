from __future__ import annotations

import html
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.domain import Bar, MarketSnapshot, Order, PortfolioState, Side
from tradearena.core.serialization import to_jsonable, write_json
from tradearena.core.trajectory import StepRecord, Trajectory
from tradearena.execution import RealisticOrderSimulator
from tradearena.tools import MarketRuleState, liquidity_halt_rule_package, review_market_rule_order

OUTPUT_DIR = Path("outputs/examples/liquidity_halt")


def main() -> int:
    report = build_liquidity_halt_fixture()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "summary.json", report)
    write_json(OUTPUT_DIR / "trajectory.json", report["trajectory"])
    (OUTPUT_DIR / "summary.md").write_text(render_markdown(report), encoding="utf-8")
    _write_svg(OUTPUT_DIR / "liquidity_halt.svg", report)
    print("Black-swan liquidity halt demo")
    print(
        f"  pending={report['summary']['pending_before_halt']} partial={report['summary']['partial_fills']} "
        f"rejected={report['summary']['rejected_orders']} blocked={report['summary']['blocked_by_halt']}"
    )
    print(f"  wrote={OUTPUT_DIR / 'summary.json'}")
    print(f"  wrote={OUTPUT_DIR / 'trajectory.json'}")
    return 0


def build_liquidity_halt_fixture() -> dict[str, Any]:
    trajectory = Trajectory(
        experiment_name="black_swan_liquidity_halt",
        seed=35,
        metadata={
            "paper_only": True,
            "downloads_data": False,
            "stress": "liquidity_halt_with_pending_orders",
        },
    )
    delayed = RealisticOrderSimulator(participation_rate=0.10, latency_steps=1, spread_bps=20.0, market_impact=0.30)
    thin = RealisticOrderSimulator(participation_rate=0.10, latency_steps=0, spread_bps=20.0, market_impact=0.30)
    delayed_portfolio = PortfolioState(cash=100_000.0)
    thin_portfolio = PortfolioState(cash=100_000.0)

    pre_halt = _snapshot("2026-06-01T14:30:00+00:00", volume=10_000.0, close=25.0)
    pending_order = Order(symbol="SYN", side=Side.BUY, quantity=800.0, reason="risk-on order submitted before halt")
    pending_fills = delayed.execute(pre_halt, [pending_order], delayed_portfolio)
    trajectory.append(
        _step(
            "pre_halt_pending",
            pre_halt,
            orders=[pending_order],
            fills=pending_fills,
            portfolio=delayed_portfolio,
            execution_report=delayed.last_report,
            risk_report=_pass_report(pre_halt.timestamp, "pre_halt_liquidity_available"),
        )
    )

    thin_snapshot = _snapshot("2026-06-01T14:31:00+00:00", volume=50.0, close=24.0)
    partial_order = Order(symbol="SYN", side=Side.BUY, quantity=20.0, reason="order meets thin displayed liquidity")
    partial_fills = thin.execute(thin_snapshot, [partial_order], thin_portfolio)
    trajectory.append(
        _step(
            "thin_liquidity_partial",
            thin_snapshot,
            orders=[partial_order],
            fills=partial_fills,
            portfolio=thin_portfolio,
            execution_report=thin.last_report,
            risk_report=_pass_report(thin_snapshot.timestamp, "thin_liquidity_partial_allowed"),
        )
    )

    halt_snapshot = _snapshot("2026-06-01T14:32:00+00:00", volume=0.0, close=20.0)
    rejected_fills = delayed.execute(halt_snapshot, [], delayed_portfolio)
    halt_rule = review_market_rule_order(
        symbol="SYN",
        side=Side.BUY,
        quantity=100.0,
        state=MarketRuleState(price=20.0, volume=0.0, circuit_halt=True),
        package=liquidity_halt_rule_package(participation_rate=0.01, eta=0.25),
    )
    trajectory.append(
        _step(
            "halt_release_reject",
            halt_snapshot,
            orders=[],
            fills=rejected_fills,
            portfolio=delayed_portfolio,
            execution_report=delayed.last_report,
            risk_report=_halt_report(halt_snapshot.timestamp, halt_rule),
        )
    )

    trajectory_dict = trajectory.to_dict(redaction_policy="public_artifact")
    for step in trajectory_dict["steps"]:
        step["step_id"] = step["observation"]["step_id"]
    summary = _summary(trajectory_dict)
    return {
        "schema": "trellm_liquidity_halt_stress_v0.1",
        "paper_only": True,
        "downloads_data": False,
        "calibration_boundary": "deterministic_stress_fixture_not_venue_calibrated",
        "trajectory": trajectory_dict,
        "summary": summary,
        "artifact_paths": {
            "summary": "outputs/examples/liquidity_halt/summary.json",
            "trajectory": "outputs/examples/liquidity_halt/trajectory.json",
            "markdown": "outputs/examples/liquidity_halt/summary.md",
            "svg": "outputs/examples/liquidity_halt/liquidity_halt.svg",
        },
        "replay": {"command": "python examples/liquidity_halt_demo.py"},
    }


def _snapshot(timestamp: str, *, volume: float, close: float) -> MarketSnapshot:
    dt = datetime.fromisoformat(timestamp)
    return MarketSnapshot(
        timestamp=dt,
        bars={
            "SYN": Bar(
                symbol="SYN",
                timestamp=dt,
                open=close,
                high=close * 1.02,
                low=close * 0.98,
                close=close,
                volume=volume,
            )
        },
        alt_data={"stress_event": "liquidity_halt" if volume == 0.0 else "thin_liquidity"},
    )


def _step(
    step_id: str,
    snapshot: MarketSnapshot,
    *,
    orders: list[Order],
    fills: list[object],
    portfolio: PortfolioState,
    execution_report: object,
    risk_report: dict[str, Any],
) -> StepRecord:
    return StepRecord(
        timestamp=snapshot.timestamp,
        observation={
            "step_id": step_id,
            "symbols": list(snapshot.bars),
            "volume": snapshot.bars["SYN"].volume,
            "stress_event": snapshot.alt_data["stress_event"],
        },
        signals=[],
        decisions=[],
        approved_decisions=[],
        orders=to_jsonable(orders),
        fills=to_jsonable(fills),
        portfolio={
            "cash": portfolio.cash,
            "positions": dict(portfolio.positions),
            "equity": portfolio.equity(),
        },
        risk_report=risk_report,
        execution_report=to_jsonable(execution_report),
    )


def _pass_report(timestamp: datetime, name: str) -> dict[str, Any]:
    return {
        "timestamp": timestamp.isoformat(),
        "phase": "pre_trade",
        "passed": True,
        "approved_count": 1,
        "blocked_count": 0,
        "clipped_count": 0,
        "checks": [{"name": name, "passed": True, "severity": "info", "message": "paper stress step allowed"}],
        "violations": [],
    }


def _halt_report(timestamp: datetime, decision: object) -> dict[str, Any]:
    reasons = list(getattr(decision, "reasons", ()))
    reason = reasons[0] if reasons else "circuit_halt"
    return {
        "timestamp": timestamp.isoformat(),
        "phase": "pre_trade",
        "passed": False,
        "approved_count": 0,
        "blocked_count": 1,
        "clipped_count": 0,
        "checks": [
            {
                "name": reason,
                "passed": False,
                "severity": "error",
                "message": "market-rule layer blocked new orders during liquidity halt",
            }
        ],
        "violations": [
            {
                "constraint": reason,
                "severity": "error",
                "observed": "halted",
                "limit": "tradable session",
                "message": "new order blocked while circuit halt is active",
            }
        ],
    }


def _summary(trajectory: dict[str, Any]) -> dict[str, int]:
    reports = [step.get("execution_report", {}) for step in trajectory["steps"]]
    risk_reports = [step.get("risk_report", {}) for step in trajectory["steps"]]
    return {
        "steps": len(trajectory["steps"]),
        "pending_before_halt": max(int(report.get("pending_orders", 0)) for report in reports),
        "partial_fills": sum(int(report.get("partial_fills", 0)) for report in reports),
        "rejected_orders": sum(int(report.get("rejected_orders", 0)) for report in reports),
        "blocked_by_halt": sum(int(report.get("blocked_count", 0)) for report in risk_reports),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Liquidity Halt Stress Fixture",
        "",
        "Deterministic paper-only scenario where one delayed order is still pending when a circuit halt begins.",
        "",
        "| Step | Pending | Partial | Rejected | Risk passed |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for step in report["trajectory"]["steps"]:
        execution = step["execution_report"]
        risk = step["risk_report"]
        lines.append(
            f"| `{step['observation']['step_id']}` | {execution.get('pending_orders', 0)} | "
            f"{execution.get('partial_fills', 0)} | {execution.get('rejected_orders', 0)} | {risk.get('passed')} |"
        )
    lines.extend(["", "## Reproduce", "", "```bash", report["replay"]["command"], "```", ""])
    return "\n".join(lines)


def _write_svg(path: Path, report: dict[str, Any]) -> None:
    width, height = 820, 360
    metrics = [
        ("pending", report["summary"]["pending_before_halt"], "#2563eb"),
        ("partial", report["summary"]["partial_fills"], "#d97706"),
        ("rejected", report["summary"]["rejected_orders"], "#dc2626"),
        ("blocked", report["summary"]["blocked_by_halt"], "#7c3aed"),
    ]
    max_value = max(1, max(int(value) for _, value, _ in metrics))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Liquidity halt stress demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 48, "Black-swan liquidity halt", 22, "#0f172a", 800),
        _text(36, 78, "Pending orders meet a halt; thin liquidity causes partial fills and rejected execution.", 13, "#64748b", 500),
    ]
    for idx, (label, value, color) in enumerate(metrics):
        x = 88 + idx * 170
        bar_height = 190 * int(value) / max_value
        y = 285 - bar_height
        parts.append(f'<rect x="{x}" y="{y:.1f}" width="80" height="{bar_height:.1f}" rx="7" fill="{color}"/>')
        parts.append(_text(x + 40, y - 12, value, 15, "#0f172a", 800, "middle"))
        parts.append(_text(x + 40, 315, label, 13, "#334155", 700, "middle"))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: object, size: int, color: str, weight: int, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
