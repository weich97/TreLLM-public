from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from tradearena.evaluation.autopsy import autopsy_trajectory

DEFAULT_INPUT = "outputs/examples/audit_walkthrough_trajectory.json"
DEFAULT_OUTPUT = "outputs/examples/agent_autopsy_dashboard.html"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an Agent Autopsy Dashboard from a TreLLM trajectory.")
    parser.add_argument("--trajectory", default=DEFAULT_INPUT, help="Trajectory JSON written by a TreLLM run.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="HTML dashboard path.")
    args = parser.parse_args()

    trajectory_path = Path(args.trajectory)
    if not trajectory_path.exists():
        raise FileNotFoundError(f"Trajectory not found: {trajectory_path}")
    data = json.loads(trajectory_path.read_text(encoding="utf-8"))
    rows = _step_rows(data)
    if not rows:
        raise ValueError(f"Trajectory has no steps: {trajectory_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render(data, rows, trajectory_path), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


def _render(data: dict[str, Any], rows: list[dict[str, Any]], trajectory_path: Path) -> str:
    summary = _summary(rows)
    symbols = _symbols(data)
    slippage = _slippage_by_symbol(data)
    failure_autopsy = autopsy_trajectory(data)
    top_gap_rows = _top_gap_rows(rows)
    intervention_rows = [row for row in rows if row["risk_edits"] or row["pending_orders"] or row["rejected_orders"]]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Autopsy Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #102033;
      --muted: #5b6b7d;
      --line: #d9e2ec;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --blue: #2563eb;
      --teal: #0f766e;
      --amber: #b45309;
      --red: #dc2626;
      --violet: #7c3aed;
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
      padding: 44px 48px 36px;
      background:
        linear-gradient(120deg, rgba(37, 99, 235, 0.25), rgba(15, 118, 110, 0.22)),
        #101827;
      color: #f8fafc;
    }}
    header h1 {{ margin: 0 0 10px; font-size: 42px; letter-spacing: 0; }}
    header p {{ margin: 0; max-width: 940px; color: #dbeafe; font-size: 16px; }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 26px 48px 52px; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0; }}
    code {{ padding: 2px 5px; border-radius: 4px; background: #eef2ff; color: #3730a3; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 9px 8px; border-bottom: 1px solid #edf2f7; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }}
    .two {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.8fr); gap: 18px; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 18px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    .metric {{ background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-height: 92px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .leadrow {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 0.42fr); gap: 16px; align-items: stretch; }}
    .finding {{ border: 1px solid #bfdbfe; background: linear-gradient(180deg, #eff6ff, #ffffff); border-radius: 8px; padding: 16px; }}
    .finding strong {{ display: block; margin-bottom: 7px; font-size: 16px; }}
    .finding p {{ margin: 0; color: #334155; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }}
    .legend span {{ display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: 12px; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
    .pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 8px; font-size: 12px; font-weight: 750; }}
    .pill.warn {{ background: #fef3c7; color: #92400e; }}
    .pill.bad {{ background: #fee2e2; color: #991b1b; }}
    .pill.good {{ background: #dcfce7; color: #166534; }}
    .muted {{ color: var(--muted); }}
    .source {{ margin-top: 10px; color: var(--muted); font-size: 12px; word-break: break-all; }}
    .empty {{ color: var(--muted); padding: 18px; border: 1px dashed var(--line); border-radius: 8px; background: #fbfdff; }}
    @media (max-width: 1000px) {{
      header, main {{ padding-left: 20px; padding-right: 20px; }}
      .grid, .two, .leadrow {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Agent Autopsy Dashboard</h1>
    <p>Dissect one run into intent, approved risk exposure, realized portfolio weights, execution friction, and risk interventions. The dashboard is rendered from the same replayable trajectory JSON as the audit report.</p>
  </header>
  <main>
    <section class="grid">
      {_metric("Experiment", data.get("experiment_name", "unknown"))}
      {_metric("Steps", str(len(rows)))}
      {_metric("Total return", _pct(summary["total_return"]))}
      {_metric("Max drawdown", _pct(summary["max_drawdown"]))}
      {_metric("Total slippage", _money(summary["total_slippage"]))}
    </section>

    <section class="panel leadrow">
      <div class="finding">
        <strong>Autopsy finding</strong>
        <p>{_e(_headline(summary, rows))}</p>
      </div>
      <div>
        <h3>Run scope</h3>
        <div class="legend">
          <span><i class="dot" style="background:var(--blue)"></i>intended</span>
          <span><i class="dot" style="background:var(--teal)"></i>risk-approved</span>
          <span><i class="dot" style="background:var(--amber)"></i>executed</span>
          <span><i class="dot" style="background:var(--red)"></i>intervention</span>
        </div>
        <p class="source">Trajectory: <code>{_e(str(trajectory_path))}</code></p>
        <p class="muted">Symbols: {_e(', '.join(symbols) if symbols else 'unknown')}</p>
      </div>
    </section>

    <section class="panel">
      <h2>Intent vs Executed Weights Time-Series</h2>
      {_weights_svg(rows)}
      <p class="muted">Lines show aggregate gross target weight intended by the strategy, gross weight after risk gate approval, and realized gross portfolio weight after paper execution.</p>
    </section>

    <section class="two">
      <div class="panel">
        <h2>Slippage Attribution Waterfall</h2>
        {_slippage_waterfall_svg(slippage)}
        <p class="muted">Waterfall values are simulated slippage costs by symbol, computed from fill-level slippage times filled quantity.</p>
      </div>
      <div class="panel">
        <h2>Risk Intervention Timeline</h2>
        {_risk_timeline_svg(rows)}
        <p class="muted">Markers combine risk-gate edits and execution frictions: clipped or blocked decisions, pending orders, rejected orders, and partial fills.</p>
      </div>
    </section>

    <section class="two">
      <div class="panel">
        <h2>Largest Intent-Execution Gaps</h2>
        {_gap_table(top_gap_rows)}
      </div>
      <div class="panel">
        <h2>Intervention Events</h2>
        {_intervention_table(intervention_rows)}
      </div>
    </section>

    <section class="panel">
      <h2>Failure-Mode Autopsy</h2>
      {_failure_autopsy_table(failure_autopsy)}
      <p class="muted">The taxonomy is diagnostic, not a claim that one model is categorically better. It separates failure mechanisms such as pre-risk leverage, low-confidence bets, and insensitivity to liquidity or slippage.</p>
    </section>
  </main>
</body>
</html>
"""


def _step_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, step in enumerate(data.get("steps", [])):
        equity = _float(step.get("portfolio", {}).get("equity"))
        intended = _gross_decision_weight(step.get("decisions", []))
        approved = _gross_decision_weight(step.get("approved_decisions", []))
        executed_weights = _executed_weights(step)
        executed = sum(abs(value) for value in executed_weights.values())
        risk = step.get("risk_report", {}) or {}
        execution = step.get("execution_report", {}) or {}
        gap = abs(intended - executed)
        rows.append(
            {
                "index": index,
                "timestamp": str(step.get("timestamp", "")),
                "equity": equity,
                "intended_gross": intended,
                "approved_gross": approved,
                "executed_gross": executed,
                "intent_execution_gap": gap,
                "risk_edits": int(risk.get("clipped_count", 0) or 0) + int(risk.get("blocked_count", 0) or 0),
                "clipped": int(risk.get("clipped_count", 0) or 0),
                "blocked": int(risk.get("blocked_count", 0) or 0),
                "pending_orders": int(execution.get("pending_orders", 0) or 0),
                "rejected_orders": int(execution.get("rejected_orders", 0) or 0),
                "partial_fills": int(execution.get("partial_fills", 0) or 0),
                "filled_orders": int(execution.get("filled_orders", 0) or 0),
                "submitted_orders": int(execution.get("submitted_orders", 0) or 0),
                "total_slippage": _float(execution.get("total_slippage")),
                "total_commission": _float(execution.get("total_commission")),
            }
        )
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    first_equity = rows[0]["equity"] if rows else 0.0
    final_equity = rows[-1]["equity"] if rows else 0.0
    total_return = (final_equity / first_equity - 1.0) if first_equity else 0.0
    peak = first_equity
    max_drawdown = 0.0
    submitted = 0
    filled = 0
    for row in rows:
        peak = max(peak, row["equity"])
        if peak:
            max_drawdown = min(max_drawdown, row["equity"] / peak - 1.0)
        submitted += row["submitted_orders"]
        filled += row["filled_orders"]
    return {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "total_slippage": sum(row["total_slippage"] for row in rows),
        "total_commission": sum(row["total_commission"] for row in rows),
        "risk_edits": float(sum(row["risk_edits"] for row in rows)),
        "rejected_orders": float(sum(row["rejected_orders"] for row in rows)),
        "partial_fills": float(sum(row["partial_fills"] for row in rows)),
        "fill_rate": filled / submitted if submitted else 0.0,
        "max_gap": max((row["intent_execution_gap"] for row in rows), default=0.0),
    }


def _headline(summary: dict[str, float], rows: list[dict[str, Any]]) -> str:
    max_gap_row = max(rows, key=lambda row: row["intent_execution_gap"])
    edited_steps = sum(1 for row in rows if row["risk_edits"])
    return (
        f"The largest intent-execution gap is {max_gap_row['intent_execution_gap']:.3f} gross weight "
        f"at step {max_gap_row['index'] + 1}. Risk edited {edited_steps} step(s), simulated slippage "
        f"costs total {_money(summary['total_slippage'])}, and the run fill rate is {_pct(summary['fill_rate'])}."
    )


def _symbols(data: dict[str, Any]) -> list[str]:
    symbols: set[str] = set()
    for step in data.get("steps", []):
        symbols.update(str(symbol) for symbol in step.get("observation", {}).get("prices", {}).keys())
        symbols.update(str(decision.get("symbol", "")) for decision in step.get("decisions", []) if decision.get("symbol"))
        symbols.update(str(fill.get("symbol", "")) for fill in step.get("fills", []) if fill.get("symbol"))
    return sorted(symbols)


def _gross_decision_weight(decisions: list[dict[str, Any]]) -> float:
    return sum(abs(_float(decision.get("target_weight"))) for decision in decisions)


def _executed_weights(step: dict[str, Any]) -> dict[str, float]:
    portfolio = step.get("portfolio", {}) or {}
    equity = _float(portfolio.get("equity"))
    positions = portfolio.get("positions", {}) or {}
    prices = portfolio.get("last_prices", {}) or {}
    if not equity:
        return {}
    return {
        str(symbol): (_float(quantity) * _float(prices.get(symbol))) / equity
        for symbol, quantity in positions.items()
    }


def _slippage_by_symbol(data: dict[str, Any]) -> dict[str, float]:
    values: defaultdict[str, float] = defaultdict(float)
    fallback = 0.0
    for step in data.get("steps", []):
        fill_slippage = 0.0
        for fill in step.get("fills", []):
            symbol = str(fill.get("symbol", "UNKNOWN") or "UNKNOWN")
            cost = abs(_float(fill.get("slippage")) * _float(fill.get("quantity")))
            values[symbol] += cost
            fill_slippage += cost
        fallback += max(0.0, _float(step.get("execution_report", {}).get("total_slippage")) - fill_slippage)
    if fallback > 1e-9:
        values["unattributed"] += fallback
    return dict(sorted(values.items(), key=lambda item: item[1], reverse=True))


def _top_gap_rows(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: row["intent_execution_gap"], reverse=True)[:limit]


def _weights_svg(rows: list[dict[str, Any]]) -> str:
    width, height = 1000, 330
    left, right, top, bottom = 58, 28, 34, 58
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_max = max(
        0.05,
        max(
            max(row["intended_gross"], row["approved_gross"], row["executed_gross"])
            for row in rows
        )
        * 1.12,
    )

    def point(row: dict[str, Any], key: str) -> str:
        x = left + row["index"] * plot_w / max(1, len(rows) - 1)
        y = top + (y_max - row[key]) * plot_h / y_max
        return f"{x:.2f},{y:.2f}"

    intended = " ".join(point(row, "intended_gross") for row in rows)
    approved = " ".join(point(row, "approved_gross") for row in rows)
    executed = " ".join(point(row, "executed_gross") for row in rows)
    markers = []
    for row in rows:
        count = row["risk_edits"] + row["pending_orders"] + row["rejected_orders"] + row["partial_fills"]
        if not count:
            continue
        x = left + row["index"] * plot_w / max(1, len(rows) - 1)
        markers.append(
            f'<circle cx="{x:.2f}" cy="{height - bottom + 20}" r="{min(10, 3 + count)}" fill="#dc2626" opacity="0.82">'
            f"<title>step {row['index'] + 1}: {count} intervention/friction event(s)</title></circle>"
        )
    grid = []
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + (1 - frac) * plot_h
        grid.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" stroke="#e5edf5"/>')
        grid.append(f'<text x="12" y="{y + 4:.2f}" font-size="12" fill="#5b6b7d">{y_max * frac:.2f}</text>')
    return f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img" aria-label="Intent versus executed weights time series">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  {''.join(grid)}
  <line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#b8c5d3"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#b8c5d3"/>
  <polyline points="{intended}" fill="none" stroke="#2563eb" stroke-width="3"/>
  <polyline points="{approved}" fill="none" stroke="#0f766e" stroke-width="3"/>
  <polyline points="{executed}" fill="none" stroke="#b45309" stroke-width="3"/>
  {''.join(markers)}
  <text x="{left}" y="20" font-size="13" font-weight="700" fill="#2563eb">intended</text>
  <text x="{left + 95}" y="20" font-size="13" font-weight="700" fill="#0f766e">risk-approved</text>
  <text x="{left + 220}" y="20" font-size="13" font-weight="700" fill="#b45309">executed</text>
  <text x="{width - right}" y="{height - 14}" text-anchor="end" font-size="12" fill="#5b6b7d">step</text>
</svg>"""


def _slippage_waterfall_svg(values: dict[str, float]) -> str:
    width, height = 820, 330
    if not values or sum(values.values()) <= 1e-12:
        return '<div class="empty">No simulated slippage was recorded in this trajectory.</div>'
    top_items = list(values.items())[:7]
    if len(values) > 7:
        top_items.append(("other", sum(value for _, value in list(values.items())[7:])))
    total = sum(value for _, value in top_items)
    scale = (width - 210) / max(total, 1e-12)
    x0, y0 = 132, 48
    row_h = 30
    cumulative = 0.0
    parts = [f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for idx, (symbol, value) in enumerate(top_items):
        start = cumulative
        cumulative += value
        x = x0 + start * scale
        bar_w = max(2.0, value * scale)
        y = y0 + idx * row_h
        color = "#2563eb" if idx % 2 == 0 else "#0f766e"
        parts.append(f'<text x="18" y="{y + 17}" font-size="12" fill="#334155">{_e(symbol)}</text>')
        parts.append(f'<rect x="{x:.2f}" y="{y}" width="{bar_w:.2f}" height="18" rx="4" fill="{color}" opacity="0.82"/>')
        parts.append(f'<text x="{min(width - 74, x + bar_w + 8):.2f}" y="{y + 14}" font-size="12" fill="#334155">{_money(value)}</text>')
    y_total = y0 + len(top_items) * row_h + 18
    total_w = total * scale
    parts.append(f'<line x1="{x0}" y1="{y_total - 10}" x2="{x0 + total_w:.2f}" y2="{y_total - 10}" stroke="#94a3b8"/>')
    parts.append(f'<rect x="{x0}" y="{y_total}" width="{max(2.0, total_w):.2f}" height="22" rx="5" fill="#7c3aed" opacity="0.86"/>')
    parts.append(f'<text x="18" y="{y_total + 16}" font-size="12" font-weight="700" fill="#334155">total</text>')
    parts.append(f'<text x="{min(width - 82, x0 + total_w + 8):.2f}" y="{y_total + 16}" font-size="12" font-weight="700" fill="#334155">{_money(total)}</text>')
    return f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img" aria-label="Slippage attribution waterfall">{"".join(parts)}</svg>'


def _risk_timeline_svg(rows: list[dict[str, Any]]) -> str:
    width, height = 820, 330
    left, right, top = 132, 28, 46
    labels = [
        ("clipped", "Clipped", "#b45309"),
        ("blocked", "Blocked", "#dc2626"),
        ("pending_orders", "Pending", "#2563eb"),
        ("rejected_orders", "Rejected", "#991b1b"),
        ("partial_fills", "Partial fills", "#0f766e"),
    ]
    row_gap = 46
    plot_w = width - left - right
    parts = [f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for idx, (key, label, color) in enumerate(labels):
        y = top + idx * row_gap
        parts.append(f'<text x="18" y="{y + 5}" font-size="12" fill="#334155">{label}</text>')
        parts.append(f'<line x1="{left}" y1="{y}" x2="{width-right}" y2="{y}" stroke="#e5edf5"/>')
        for row in rows:
            value = int(row[key])
            if value <= 0:
                continue
            x = left + row["index"] * plot_w / max(1, len(rows) - 1)
            r = min(12, 4 + value * 2)
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y}" r="{r}" fill="{color}" opacity="0.84">'
                f"<title>step {row['index'] + 1}, {label}: {value}</title></circle>"
            )
    parts.append(f'<text x="{left}" y="{height - 24}" font-size="12" fill="#5b6b7d">step 1</text>')
    parts.append(f'<text x="{width-right}" y="{height - 24}" text-anchor="end" font-size="12" fill="#5b6b7d">step {len(rows)}</text>')
    return f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img" aria-label="Risk intervention timeline">{"".join(parts)}</svg>'


def _gap_table(rows: list[dict[str, Any]]) -> str:
    body = []
    for row in rows:
        status = "risk edit" if row["risk_edits"] else "execution lag" if row["pending_orders"] else "drift"
        kind = "warn" if status != "drift" else "good"
        body.append(
            "<tr>"
            f"<td>{row['index'] + 1}</td>"
            f"<td>{_e(row['timestamp'])}</td>"
            f"<td>{row['intended_gross']:.3f}</td>"
            f"<td>{row['approved_gross']:.3f}</td>"
            f"<td>{row['executed_gross']:.3f}</td>"
            f"<td>{row['intent_execution_gap']:.3f}</td>"
            f'<td><span class="pill {kind}">{_e(status)}</span></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Step</th><th>Timestamp</th><th>Intent</th><th>Approved</th>"
        "<th>Executed</th><th>Gap</th><th>Readout</th></tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def _intervention_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">No risk intervention or execution friction markers were recorded.</div>'
    body = []
    for row in rows[:14]:
        severity = "bad" if row["rejected_orders"] or row["blocked"] else "warn"
        body.append(
            "<tr>"
            f"<td>{row['index'] + 1}</td>"
            f"<td>{_e(row['timestamp'])}</td>"
            f"<td>{row['clipped']}</td>"
            f"<td>{row['blocked']}</td>"
            f"<td>{row['pending_orders']}</td>"
            f"<td>{row['rejected_orders']}</td>"
            f"<td>{row['partial_fills']}</td>"
            f'<td><span class="pill {severity}">{_e("review")}</span></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Step</th><th>Timestamp</th><th>Clipped</th><th>Blocked</th>"
        "<th>Pending</th><th>Rejected</th><th>Partial</th><th>Status</th></tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def _failure_autopsy_table(autopsy: dict[str, Any]) -> str:
    rows = [
        (mode, count)
        for mode, count in autopsy.get("failure_mode_counts", {}).items()
        if int(count) > 0
    ]
    if not rows:
        return '<div class="empty">No failure-mode markers were detected by the current taxonomy.</div>'
    body = []
    for mode, count in sorted(rows, key=lambda item: (-int(item[1]), item[0])):
        body.append(f"<tr><td><code>{_e(mode)}</code></td><td>{int(count)}</td></tr>")
    return "<table><thead><tr><th>Failure mode</th><th>Steps flagged</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{_e(label)}</span><strong>{_e(value)}</strong></div>'


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _money(value: Any) -> str:
    return f"${_float(value):,.2f}"


def _pct(value: Any) -> str:
    return f"{100.0 * _float(value):.2f}%"


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
