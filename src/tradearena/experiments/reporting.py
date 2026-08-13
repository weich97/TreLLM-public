from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from tradearena.core.serialization import to_jsonable, write_json
from tradearena.core.trajectory import Trajectory

KEY_METRICS = (
    "total_return",
    "sharpe",
    "volatility",
    "max_drawdown",
    "final_equity",
    "execution_fill_rate",
    "partial_fill_rate",
    "rejected_order_count",
    "pending_order_count",
    "total_commission",
    "total_slippage_cost",
    "avg_latency_steps",
    "risk_clipped_decisions",
    "risk_violation_count",
    "risk_lifecycle_coverage",
    "trajectory_reproducibility_coverage",
    "agent_trace_coverage",
)


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_csv(path: str | Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        target.write_text("", encoding="utf-8")
        return
    fieldnames = columns or sorted({key for row in rows for key in row})
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _format_cell(row.get(key, "")) for key in fieldnames})


def write_markdown_table(path: str | Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(column, "")) for column in columns) + " |")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def trajectory_rows(case_name: str, trajectory: Trajectory) -> list[dict[str, Any]]:
    rows = []
    for idx, step in enumerate(trajectory.steps):
        rows.append(
            {
                "case": case_name,
                "step": idx,
                "timestamp": step.timestamp.isoformat(),
                "equity": step.portfolio["equity"],
                "cash": step.portfolio["cash"],
                "orders": len(step.orders),
                "fills": len(step.fills),
                "risk_violations": len(step.risk_violations),
                "commission": step.execution_report.get("total_commission", 0.0),
                "slippage_cost": step.execution_report.get("total_slippage", 0.0),
                "pending_orders": step.execution_report.get("pending_orders", 0),
                "rejected_orders": step.execution_report.get("rejected_orders", 0),
            }
        )
    return rows


def execution_event_rows(case_name: str, trajectory: Trajectory) -> list[dict[str, Any]]:
    rows = []
    for step_idx, step in enumerate(trajectory.steps):
        for fill_idx, fill in enumerate(step.fills):
            rows.append(
                {
                    "case": case_name,
                    "step": step_idx,
                    "fill_index": fill_idx,
                    "timestamp": step.timestamp.isoformat(),
                    "symbol": fill.get("symbol"),
                    "side": fill.get("side"),
                    "quantity": fill.get("quantity"),
                    "requested_quantity": fill.get("requested_quantity"),
                    "fill_ratio": fill.get("fill_ratio"),
                    "price": fill.get("price"),
                    "commission": fill.get("commission"),
                    "slippage": fill.get("slippage"),
                    "latency_steps": fill.get("latency_steps"),
                    "liquidity_available": fill.get("liquidity_available"),
                    "status": fill.get("status"),
                }
            )
    return rows


def risk_event_rows(case_name: str, trajectory: Trajectory) -> list[dict[str, Any]]:
    rows = []
    for step_idx, step in enumerate(trajectory.steps):
        for phase_name, report in (
            ("pre_trade", step.risk_report),
            ("in_trade", step.in_trade_report),
            ("post_trade", step.post_trade_report),
        ):
            for check_idx, check in enumerate(report.get("checks", [])):
                rows.append(
                    {
                        "case": case_name,
                        "step": step_idx,
                        "timestamp": step.timestamp.isoformat(),
                        "phase": phase_name,
                        "check_index": check_idx,
                        "check_name": check.get("name"),
                        "passed": check.get("passed"),
                        "severity": check.get("severity"),
                        "message": check.get("message"),
                    }
                )
        for violation_idx, violation in enumerate(step.risk_violations):
            rows.append(
                {
                    "case": case_name,
                    "step": step_idx,
                    "timestamp": step.timestamp.isoformat(),
                    "phase": violation.get("phase"),
                    "check_index": violation_idx,
                    "check_name": violation.get("constraint"),
                    "passed": False,
                    "severity": violation.get("severity"),
                    "message": violation.get("message"),
                }
            )
    return rows


def write_artifacts(
    output_dir: str | Path,
    metrics_rows: list[dict[str, Any]],
    trajectories: dict[str, Trajectory],
    raw_payload: dict[str, Any],
) -> dict[str, str]:
    output = ensure_dir(output_dir)
    charts = ensure_dir(output / "charts")
    tables = ensure_dir(output / "tables")
    raw = ensure_dir(output / "raw")

    base_columns = ["case", "group", "seed", "execution_mode", "risk_mode", *KEY_METRICS]
    extra_columns = sorted({key for row in metrics_rows for key in row if key not in base_columns})
    metric_columns = [*base_columns, *extra_columns]
    write_csv(tables / "metrics.csv", metrics_rows, metric_columns)
    write_markdown_table(tables / "metrics.md", metrics_rows, ["case", "group", "seed", "total_return", "sharpe", "max_drawdown", "execution_fill_rate", "total_slippage_cost", "risk_lifecycle_coverage"])

    equity_rows = []
    execution_rows = []
    risk_rows = []
    for case_name, trajectory in trajectories.items():
        equity_rows.extend(trajectory_rows(case_name, trajectory))
        execution_rows.extend(execution_event_rows(case_name, trajectory))
        risk_rows.extend(risk_event_rows(case_name, trajectory))
        write_json(raw / f"{case_name}_trajectory.json", trajectory.to_dict())

    write_csv(tables / "equity_curves.csv", equity_rows)
    write_csv(tables / "execution_events.csv", execution_rows)
    write_csv(tables / "risk_events.csv", risk_rows)
    write_json(output / "summary.json", raw_payload)

    write_line_chart(charts / "equity_curves.svg", "Equity Curves", "step", "equity", _series_from_rows(equity_rows, "case", "step", "equity"))
    write_bar_chart(charts / "returns.svg", "Total Return by Case", [(row["case"], float(row.get("total_return", 0.0))) for row in metrics_rows if row.get("group") == "core"])
    write_bar_chart(charts / "execution_costs.svg", "Execution Cost by Case", [(row["case"], float(row.get("total_commission", 0.0)) + float(row.get("total_slippage_cost", 0.0))) for row in metrics_rows if row.get("group") == "core"])
    write_bar_chart(charts / "risk_audit.svg", "Risk Lifecycle Coverage", [(row["case"], float(row.get("risk_lifecycle_coverage", 0.0))) for row in metrics_rows if row.get("group") == "core"], y_min=0.0, y_max=1.0)
    aggregate_rows = [row for row in metrics_rows if str(row.get("group", "")).endswith("_aggregate")]
    write_bar_chart(charts / "aggregate_returns.svg", "Mean Total Return by Experiment", [(row["case"], float(row.get("total_return", 0.0))) for row in aggregate_rows])
    write_bar_chart(charts / "aggregate_fill_rates.svg", "Mean Fill Rate by Experiment", [(row["case"], float(row.get("execution_fill_rate", 0.0))) for row in aggregate_rows], y_min=0.0, y_max=1.0)

    return {
        "metrics_csv": str(tables / "metrics.csv"),
        "metrics_md": str(tables / "metrics.md"),
        "equity_csv": str(tables / "equity_curves.csv"),
        "execution_csv": str(tables / "execution_events.csv"),
        "risk_csv": str(tables / "risk_events.csv"),
        "summary_json": str(output / "summary.json"),
        "charts_dir": str(charts),
        "aggregate_returns_svg": str(charts / "aggregate_returns.svg"),
        "aggregate_fill_rates_svg": str(charts / "aggregate_fill_rates.svg"),
    }


def write_line_chart(path: str | Path, title: str, x_label: str, y_label: str, series: dict[str, list[tuple[float, float]]]) -> None:
    width, height = 960, 520
    margin = 64
    values = [point for points in series.values() for point in points]
    if not values:
        Path(path).write_text("", encoding="utf-8")
        return
    xs = [point[0] for point in values]
    ys = [point[1] for point in values]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    colors = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c", "#0891b2", "#4b5563"]
    elements = [_svg_header(width, height, title), _axis(width, height, margin, x_label, y_label)]
    for idx, (name, points) in enumerate(series.items()):
        color = colors[idx % len(colors)]
        coords = [
            f"{_scale(x, x_min, x_max, margin, width - margin):.2f},{_scale(y, y_min, y_max, height - margin, margin):.2f}"
            for x, y in points
        ]
        elements.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.4" points="{" ".join(coords)}" />')
        legend_y = 32 + idx * 20
        elements.append(f'<rect x="{width - 250}" y="{legend_y - 10}" width="12" height="12" fill="{color}" />')
        elements.append(f'<text x="{width - 232}" y="{legend_y}" font-size="12" fill="#111827">{_escape(name)}</text>')
    elements.append("</svg>")
    Path(path).write_text("\n".join(elements), encoding="utf-8")


def write_bar_chart(path: str | Path, title: str, bars: list[tuple[str, float]], y_min: float | None = None, y_max: float | None = None) -> None:
    width, height = 960, 520
    margin = 72
    if not bars:
        Path(path).write_text("", encoding="utf-8")
        return
    values = [value for _, value in bars]
    lo = min(0.0, min(values)) if y_min is None else y_min
    hi = max(values) if y_max is None else y_max
    if lo == hi:
        hi = lo + 1
    bar_area = width - margin * 2
    slot = bar_area / len(bars)
    elements = [_svg_header(width, height, title), _axis(width, height, margin, "case", "value")]
    zero_y = _scale(0.0, lo, hi, height - margin, margin)
    for idx, (name, value) in enumerate(bars):
        x = margin + idx * slot + slot * 0.15
        bar_width = slot * 0.7
        y = _scale(value, lo, hi, height - margin, margin)
        top = min(y, zero_y)
        bar_height = abs(zero_y - y)
        elements.append(f'<rect x="{x:.2f}" y="{top:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="#2563eb" />')
        elements.append(f'<text x="{x + bar_width / 2:.2f}" y="{height - 42}" font-size="10" text-anchor="end" transform="rotate(-35 {x + bar_width / 2:.2f},{height - 42})" fill="#111827">{_escape(name[:28])}</text>')
        elements.append(f'<text x="{x + bar_width / 2:.2f}" y="{top - 6:.2f}" font-size="10" text-anchor="middle" fill="#111827">{value:.3g}</text>')
    elements.append("</svg>")
    Path(path).write_text("\n".join(elements), encoding="utf-8")


def _series_from_rows(rows: list[dict[str, Any]], group_key: str, x_key: str, y_key: str) -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        series.setdefault(str(row[group_key]), []).append((float(row[x_key]), float(row[y_key])))
    return series


def _format_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.8g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(to_jsonable(value), sort_keys=True)
    return str(value)


def _scale(value: float, src_min: float, src_max: float, dst_min: float, dst_max: float) -> float:
    if src_max == src_min:
        return (dst_min + dst_max) / 2
    return dst_min + (value - src_min) * (dst_max - dst_min) / (src_max - src_min)


def _svg_header(width: int, height: int, title: str) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff" />',
            f'<text x="{width / 2}" y="28" font-size="20" font-family="Arial, sans-serif" text-anchor="middle" fill="#111827">{_escape(title)}</text>',
        ]
    )


def _axis(width: int, height: int, margin: int, x_label: str, y_label: str) -> str:
    return "\n".join(
        [
            f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#374151" />',
            f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#374151" />',
            f'<text x="{width / 2}" y="{height - 14}" font-size="12" text-anchor="middle" fill="#374151">{_escape(x_label)}</text>',
            f'<text x="18" y="{height / 2}" font-size="12" text-anchor="middle" transform="rotate(-90 18,{height / 2})" fill="#374151">{_escape(y_label)}</text>',
        ]
    )


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
