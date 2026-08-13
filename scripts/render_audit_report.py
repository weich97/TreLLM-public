from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any

DEFAULT_INPUT = "outputs/examples/audit_walkthrough_trajectory.json"
DEFAULT_OUTPUT = "outputs/examples/audit_report.html"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a TreLLM trajectory as a compact HTML audit report.")
    parser.add_argument("--trajectory", default=DEFAULT_INPUT, help="Trajectory JSON written by a TreLLM run.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="HTML report path.")
    parser.add_argument("--step", type=int, default=-1, help="Step index to render. Defaults to the first risk/execution event.")
    args = parser.parse_args()

    trajectory_path = Path(args.trajectory)
    if not trajectory_path.exists():
        raise FileNotFoundError(f"Trajectory not found: {trajectory_path}")
    data = json.loads(trajectory_path.read_text(encoding="utf-8"))
    steps = data.get("steps", [])
    if not steps:
        raise ValueError(f"Trajectory has no steps: {trajectory_path}")

    step_index = args.step if args.step >= 0 else _first_interesting_step(steps)
    step_index = max(0, min(step_index, len(steps) - 1))
    report = _render(data, step_index, trajectory_path)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


def _render(data: dict[str, Any], step_index: int, trajectory_path: Path) -> str:
    steps = data.get("steps", [])
    step = steps[step_index]
    summary = _summary(data)
    metadata = data.get("metadata", {})
    repro = step.get("reproducibility_state", {})
    observation = step.get("observation", {})
    execution = step.get("execution_report", {})
    risk = step.get("risk_report", {})
    in_trade = step.get("in_trade_report", {})
    post_trade = step.get("post_trade_report", {})
    portfolio = step.get("portfolio", {})
    equity_points = [float(item.get("portfolio", {}).get("equity", 0.0) or 0.0) for item in steps]
    highlight = _step_highlight(step)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TreLLM Audit Report: Replayable Decision Trace</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #d9e2ec;
      --panel: #ffffff;
      --bg: #f6f8fb;
      --soft: #eef6ff;
      --blue: #2563eb;
      --green: #059669;
      --orange: #d97706;
      --red: #dc2626;
      --purple: #7c3aed;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
    }}
    header {{
      padding: 42px 48px 34px;
      background:
        linear-gradient(135deg, rgba(37, 99, 235, 0.34), rgba(5, 150, 105, 0.18)),
        #0f172a;
      color: white;
    }}
    header p {{ max-width: 980px; color: #dbeafe; margin: 10px 0 0; }}
    .hero {{ display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.7fr); gap: 22px; align-items: end; }}
    .hero-card {{
      border: 1px solid rgba(255,255,255,0.22);
      background: rgba(15, 23, 42, 0.52);
      border-radius: 8px;
      padding: 16px;
    }}
    .hero-card strong {{ display: block; font-size: 13px; color: #bfdbfe; margin-bottom: 6px; }}
    .hero-card div {{ font-size: 26px; font-weight: 800; }}
    .hero-card span {{ color: #cbd5e1; font-size: 12px; }}
    main {{ padding: 28px 48px 48px; max-width: 1280px; margin: 0 auto; }}
    h1 {{ margin: 0; font-size: 34px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 14px; letter-spacing: 0; color: var(--muted); text-transform: uppercase; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 22px; }}
    .two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      margin-bottom: 18px;
    }}
    .metric {{ background: white; border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .metric .label {{ color: var(--muted); font-size: 12px; }}
    .metric .value {{ font-size: 22px; font-weight: 750; margin-top: 4px; }}
    .insight {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(240px, 0.56fr);
      gap: 16px;
      align-items: stretch;
    }}
    .callout {{
      border: 1px solid #bfdbfe;
      background: linear-gradient(180deg, #eff6ff, #ffffff);
      border-radius: 8px;
      padding: 16px;
    }}
    .callout strong {{ display: block; margin-bottom: 8px; font-size: 16px; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .tag {{ border: 1px solid var(--line); background: #f8fafc; border-radius: 999px; padding: 5px 9px; font-size: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 9px 8px; border-bottom: 1px solid #edf2f7; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; font-weight: 700; }}
    code {{ background: #eef2ff; color: #3730a3; border-radius: 4px; padding: 2px 5px; }}
    .pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 3px 8px; font-size: 12px; font-weight: 700; }}
    .pill.good {{ background: #dcfce7; color: #166534; }}
    .pill.warn {{ background: #fef3c7; color: #92400e; }}
    .pill.bad {{ background: #fee2e2; color: #991b1b; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; word-break: break-all; }}
    .muted {{ color: var(--muted); }}
    .timeline {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; }}
    .stage {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fbfdff; min-height: 106px; }}
    .stage:nth-child(1) {{ border-top: 4px solid var(--blue); }}
    .stage:nth-child(2) {{ border-top: 4px solid var(--purple); }}
    .stage:nth-child(3) {{ border-top: 4px solid var(--orange); }}
    .stage:nth-child(4) {{ border-top: 4px solid var(--green); }}
    .stage:nth-child(5) {{ border-top: 4px solid var(--red); }}
    .stage:nth-child(6) {{ border-top: 4px solid #0891b2; }}
    .stage strong {{ display: block; margin-bottom: 6px; }}
    .stage span {{ color: var(--muted); font-size: 12px; }}
    .weight-cell {{ min-width: 150px; }}
    .weight-bar {{ height: 8px; border-radius: 999px; background: #e5e7eb; overflow: hidden; margin-top: 5px; }}
    .weight-bar > i {{ display: block; height: 100%; background: var(--blue); }}
    .weight-bar.approved > i {{ background: var(--green); }}
    .svgbox {{ width: 100%; overflow: hidden; }}
    @media (max-width: 900px) {{
      header, main {{ padding-left: 20px; padding-right: 20px; }}
      .grid, .two, .timeline, .hero, .insight {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <div>
        <h1>TreLLM Audit Report: Replayable Decision Trace</h1>
        <p>One replayable trading decision, rendered from the same trajectory JSON used by TreLLM and summarized in TradeArena leaderboard artifacts. This report shows what the agent saw, what it proposed, how the risk gate revised it, what the execution simulator did, and which reproducibility fields make the step auditable.</p>
      </div>
      <div class="hero-card">
        <strong>Rendered step</strong>
        <div>{step_index + 1} / {len(steps)}</div>
        <span>{_e(step.get("timestamp", ""))}</span>
      </div>
    </div>
  </header>
  <main>
    <section class="grid">
      {_metric("Experiment", data.get("experiment_name", "unknown"))}
      {_metric("Rendered step", f"{step_index + 1} / {len(steps)}")}
      {_metric("Final equity", _money(summary["final_equity"]))}
      {_metric("Max drawdown", _pct(summary["max_drawdown"]))}
      {_metric("Risk clipped", str(summary["risk_clipped"]))}
      {_metric("Rejected orders", str(summary["rejected_orders"]))}
      {_metric("Pending orders", str(summary["pending_orders"]))}
      {_metric("Fill rate", _pct(summary["fill_rate"]))}
    </section>

    <section class="panel insight">
      <div class="callout">
        <strong>Why this step is interesting</strong>
        <div>{_e(highlight)}</div>
      </div>
      <div>
        <h3>Market Observation Summary</h3>
        {_observation_tags(observation)}
      </div>
    </section>

    <section class="panel">
      <h2>Decision Trace: Observe, Plan, Risk, Execute, Reflect</h2>
      <div class="timeline">
        {_stage("Observe", f"{len(observation.get('prices', {}))} symbols", f"news {observation.get('news_count', 0)}, macro {observation.get('macro_count', 0)}")}
        {_stage("Plan", f"{len(step.get('signals', []))} signals", f"{len(step.get('decisions', []))} proposed decisions")}
        {_stage("Risk Gate", f"{risk.get('clipped_count', 0)} clipped", f"{risk.get('blocked_count', 0)} blocked")}
        {_stage("Revise", f"{len(step.get('approved_decisions', []))} approved", "pre-trade constraints applied")}
        {_stage("Execute", f"{execution.get('filled_orders', 0)} filled", f"{execution.get('pending_orders', 0)} pending, {execution.get('rejected_orders', 0)} rejected")}
        {_stage("Reflect", _money(portfolio.get('equity', 0.0)), f"{len(step.get('memory_events', []))} memory events")}
      </div>
    </section>

    <section class="two">
      <div class="panel">
        <h2>Portfolio Equity Path</h2>
        <div class="svgbox">{_equity_svg(equity_points)}</div>
        <p class="muted">Source: <code>{_e(str(trajectory_path))}</code></p>
      </div>
      <div class="panel">
        <h2>Reproducibility Fingerprint</h2>
        <table>
          <tbody>
            {_kv("timestamp", step.get("timestamp"))}
            {_kv("prompt_version", repro.get("prompt_version"))}
            {_kv("model_version", repro.get("model_version"))}
            {_kv("market_data_timestamp", repro.get("market_data_timestamp"))}
            {_kv("memory_digest", repro.get("memory_digest"), mono=True)}
            {_kv("random_seed", repro.get("random_seed"))}
            {_kv("simulator", metadata.get("order_simulator"))}
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <h2>Proposed vs Risk-Approved Decisions: Comparison Table</h2>
      {_decision_table(step.get("decisions", []), step.get("approved_decisions", []))}
    </section>

    <section class="two">
      <div class="panel">
        <h2>Risk Lifecycle Reports</h2>
        {_risk_lifecycle_table(risk, in_trade, post_trade)}
      </div>
      <div class="panel">
        <h2>Execution Simulator Outcomes</h2>
        {_execution_table(step)}
      </div>
    </section>

    <section class="panel">
      <h2>Agent Signals and Rationales</h2>
      {_signals_table(step.get("signals", []))}
    </section>
  </main>
</body>
</html>
"""


def _summary(data: dict[str, Any]) -> dict[str, float | int]:
    steps = data.get("steps", [])
    equities = [float(step.get("portfolio", {}).get("equity", 0.0) or 0.0) for step in steps]
    final_equity = equities[-1] if equities else 0.0
    max_drawdown = 0.0
    peak = equities[0] if equities else 0.0
    for equity in equities:
        peak = max(peak, equity)
        if peak:
            max_drawdown = min(max_drawdown, equity / peak - 1.0)
    submitted = sum(int(step.get("execution_report", {}).get("submitted_orders", 0) or 0) for step in steps)
    filled = sum(int(step.get("execution_report", {}).get("filled_orders", 0) or 0) for step in steps)
    return {
        "final_equity": final_equity,
        "max_drawdown": max_drawdown,
        "risk_clipped": sum(int(step.get("risk_report", {}).get("clipped_count", 0) or 0) for step in steps),
        "rejected_orders": sum(int(step.get("execution_report", {}).get("rejected_orders", 0) or 0) for step in steps),
        "pending_orders": int(steps[-1].get("execution_report", {}).get("pending_orders", 0) or 0) if steps else 0,
        "fill_rate": filled / submitted if submitted else 0.0,
    }


def _first_interesting_step(steps: list[dict[str, Any]]) -> int:
    for idx, step in enumerate(steps):
        risk = step.get("risk_report", {})
        execution = step.get("execution_report", {})
        if (
            risk.get("clipped_count", 0)
            or risk.get("blocked_count", 0)
            or execution.get("pending_orders", 0)
            or execution.get("rejected_orders", 0)
            or execution.get("partial_fills", 0)
        ):
            return idx
    return min(len(steps) - 1, 0)


def _decision_table(decisions: list[dict[str, Any]], approved: list[dict[str, Any]]) -> str:
    approved_by_symbol = {str(item.get("symbol", "")): item for item in approved}
    rows = []
    for decision in decisions:
        symbol = str(decision.get("symbol", ""))
        approved_decision = approved_by_symbol.get(symbol, {})
        target = _to_float(decision.get("target_weight"), 0.0)
        approved_weight = _to_float(approved_decision.get("target_weight"), 0.0)
        delta = approved_weight - target
        status = "clipped" if abs(delta) > 1e-12 else "unchanged"
        rows.append(
            "<tr>"
            f"<td><strong>{_e(symbol)}</strong></td>"
            f"<td>{_e(decision.get('side', ''))}</td>"
            f"<td class=\"weight-cell\">{target:.3f}{_weight_bar(target, 'proposed')}</td>"
            f"<td class=\"weight-cell\">{approved_weight:.3f}{_weight_bar(approved_weight, 'approved')}</td>"
            f"<td>{delta:+.3f}</td>"
            f"<td>{_pill(status, 'warn' if status == 'clipped' else 'good')}</td>"
            f"<td>{_e(decision.get('rationale', ''))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Symbol</th><th>Side</th><th>Proposed</th><th>Approved</th>"
        "<th>Delta</th><th>Status</th><th>Rationale</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _step_highlight(step: dict[str, Any]) -> str:
    decisions = step.get("decisions", [])
    approved = {str(item.get("symbol", "")): item for item in step.get("approved_decisions", [])}
    for decision in decisions:
        symbol = str(decision.get("symbol", ""))
        approved_decision = approved.get(symbol, {})
        target = _to_float(decision.get("target_weight"), 0.0)
        approved_weight = _to_float(approved_decision.get("target_weight"), target)
        if abs(target - approved_weight) > 1e-12:
            return (
                f"The strategy proposed {symbol} at {target:.3f} target weight, but the pre-trade risk gate "
                f"approved {approved_weight:.3f}. The same step then entered the execution simulator with "
                f"{step.get('execution_report', {}).get('pending_orders', 0)} pending order(s), making the "
                "risk and execution assumptions visible rather than hidden inside a return curve."
            )
    execution = step.get("execution_report", {})
    if execution.get("rejected_orders", 0):
        return (
            f"The execution simulator rejected {execution.get('rejected_orders', 0)} order(s), surfacing a "
            "realistic fill constraint that an idealized backtest would usually hide."
        )
    return "This step is rendered because it is part of a replayable trajectory with complete observe-plan-risk-act-reflect fields."


def _observation_tags(observation: dict[str, Any]) -> str:
    prices = observation.get("prices", {})
    tags = [
        f'<span class="tag">{_e(symbol)} {_money(price)}</span>'
        for symbol, price in prices.items()
    ]
    tags.extend(
        [
            f'<span class="tag">news {observation.get("news_count", 0)}</span>',
            f'<span class="tag">macro {observation.get("macro_count", 0)}</span>',
            f'<span class="tag">filings {observation.get("filings_count", 0)}</span>',
            f'<span class="tag">alt {observation.get("alt_data_count", 0)}</span>',
        ]
    )
    return '<div class="tags">' + "".join(tags) + "</div>"


def _weight_bar(value: float, kind: str) -> str:
    width = max(0.0, min(100.0, abs(value) * 100.0))
    class_name = "approved" if kind == "approved" else "proposed"
    return f'<div class="weight-bar {class_name}"><i style="width:{width:.1f}%"></i></div>'


def _risk_lifecycle_table(*reports: dict[str, Any]) -> str:
    rows = []
    for report in reports:
        phase = str(report.get("phase", ""))
        checks = report.get("checks", [])
        failed = sum(1 for check in checks if not check.get("passed", False))
        warnings = sum(1 for check in checks if str(check.get("severity", "")) == "warning")
        rows.append(
            "<tr>"
            f"<td><strong>{_e(phase)}</strong></td>"
            f"<td>{len(checks)}</td>"
            f"<td>{report.get('clipped_count', 0)}</td>"
            f"<td>{report.get('blocked_count', 0)}</td>"
            f"<td>{failed}</td>"
            f"<td>{warnings}</td>"
            f"<td>{_e(_first_check_message(checks))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Phase</th><th>Checks</th><th>Clipped</th><th>Blocked</th>"
        "<th>Failed</th><th>Warnings</th><th>First message</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _execution_table(step: dict[str, Any]) -> str:
    report = step.get("execution_report", {})
    rows = [
        ("submitted_orders", report.get("submitted_orders", 0)),
        ("eligible_orders", report.get("eligible_orders", 0)),
        ("filled_orders", report.get("filled_orders", 0)),
        ("partial_fills", report.get("partial_fills", 0)),
        ("pending_orders", report.get("pending_orders", 0)),
        ("rejected_orders", report.get("rejected_orders", 0)),
        ("total_commission", _money(report.get("total_commission", 0.0))),
        ("total_slippage", _money(report.get("total_slippage", 0.0))),
        ("average_latency_steps", f"{_to_float(report.get('average_latency_steps'), 0.0):.2f}"),
    ]
    body = "".join(_kv(key, value) for key, value in rows)
    if step.get("orders"):
        order = step["orders"][0]
        body += _kv("first_order", f"{order.get('side')} {order.get('symbol')} qty={_to_float(order.get('quantity'), 0.0):.2f}")
    return f"<table><tbody>{body}</tbody></table>"


def _signals_table(signals: list[dict[str, Any]]) -> str:
    rows = []
    for signal in signals:
        metadata = signal.get("metadata", {})
        rows.append(
            "<tr>"
            f"<td><strong>{_e(signal.get('symbol', ''))}</strong></td>"
            f"<td>{_e(metadata.get('analyst', ''))}</td>"
            f"<td>{_to_float(signal.get('score'), 0.0):+.3f}</td>"
            f"<td>{_to_float(signal.get('confidence'), 0.0):.3f}</td>"
            f"<td>{_e(signal.get('rationale', ''))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Symbol</th><th>Analyst</th><th>Score</th><th>Confidence</th><th>Rationale</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _equity_svg(values: list[float]) -> str:
    width, height = 560, 210
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        lo -= 1.0
        hi += 1.0
    points = []
    for idx, value in enumerate(values):
        x = 28 + idx * (width - 56) / max(1, len(values) - 1)
        y = 172 - (value - lo) * 134 / (hi - lo)
        points.append(f"{x:.2f},{y:.2f}")
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="210" role="img" aria-label="Equity curve">'
        '<rect x="0" y="0" width="560" height="210" fill="#fbfdff"/>'
        '<line x1="28" y1="172" x2="532" y2="172" stroke="#d9e2ec"/>'
        '<line x1="28" y1="38" x2="28" y2="172" stroke="#d9e2ec"/>'
        f'<polyline fill="none" stroke="#2563eb" stroke-width="2.4" points="{" ".join(points)}"/>'
        f'<text x="28" y="24" font-size="12" fill="#64748b">high {_money(hi)}</text>'
        f'<text x="28" y="198" font-size="12" fill="#64748b">low {_money(lo)}</text>'
        "</svg>"
    )


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><div class="label">{_e(label)}</div><div class="value">{_e(value)}</div></div>'


def _stage(title: str, value: str, note: str) -> str:
    return f'<div class="stage"><strong>{_e(title)}</strong><div>{_e(value)}</div><span>{_e(note)}</span></div>'


def _kv(key: str, value: Any, mono: bool = False) -> str:
    cls = ' class="mono"' if mono else ""
    return f"<tr><th>{_e(key)}</th><td{cls}>{_e(value)}</td></tr>"


def _pill(text: str, kind: str) -> str:
    return f'<span class="pill {kind}">{_e(text)}</span>'


def _first_check_message(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return ""
    return str(checks[0].get("message", ""))


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _money(value: Any) -> str:
    return f"${_to_float(value, 0.0):,.2f}"


def _pct(value: Any) -> str:
    return f"{100.0 * _to_float(value, 0.0):.2f}%"


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
