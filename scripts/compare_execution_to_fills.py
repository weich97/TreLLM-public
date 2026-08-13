from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

REQUIRED_COLUMNS = {"symbol", "side", "quantity", "reference_price", "fill_price"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare TreLLM execution assumptions against historical order/fill logs."
    )
    parser.add_argument("--fills", required=True, help="CSV file containing historical fills.")
    parser.add_argument("--output", default="docs/results/execution_fill_comparison.json")
    parser.add_argument("--markdown-output", default="docs/results/execution_fill_comparison.md")
    parser.add_argument("--base-slippage-bps", type=float, default=2.0)
    parser.add_argument("--market-impact", type=float, default=0.15)
    parser.add_argument(
        "--default-spread-bps",
        type=float,
        default=0.0,
        help="Fallback full spread in bps when a row does not contain spread_bps.",
    )
    args = parser.parse_args()

    result = compare_fills_to_model(
        Path(args.fills),
        base_slippage_bps=args.base_slippage_bps,
        market_impact=args.market_impact,
        default_spread_bps=args.default_spread_bps,
    )
    _write_json(result, Path(args.output))
    _write_markdown(result, Path(args.markdown_output))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    return 0


def compare_fills_to_model(
    path: Path,
    *,
    base_slippage_bps: float,
    market_impact: float,
    default_spread_bps: float,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"fills CSV missing required columns: {', '.join(sorted(missing))}")
        for index, row in enumerate(reader, start=2):
            comparison = _compare_row(
                row,
                row_number=index,
                base_slippage_bps=base_slippage_bps,
                market_impact=market_impact,
                default_spread_bps=default_spread_bps,
            )
            if comparison:
                rows.append(comparison)

    if not rows:
        raise ValueError(f"fills CSV contains no comparable rows: {path}")

    residuals = [float(row["residual_bps"]) for row in rows]
    abs_residuals = [abs(value) for value in residuals]
    observed = [float(row["observed_shortfall_bps"]) for row in rows]
    modeled = [float(row["modeled_shortfall_bps"]) for row in rows]
    latencies = [float(row["latency_seconds"]) for row in rows if row.get("latency_seconds") is not None]
    return {
        "schema": "tradearena_execution_fill_comparison_v1",
        "input": {
            "fills_path": str(path).replace("\\", "/"),
            "required_columns": sorted(REQUIRED_COLUMNS),
            "optional_columns": [
                "commission",
                "spread_bps",
                "bar_volume",
                "bar_high",
                "bar_low",
                "bar_close",
                "submitted_at",
                "filled_at",
            ],
        },
        "model_parameters": {
            "base_slippage_bps": base_slippage_bps,
            "market_impact": market_impact,
            "default_spread_bps": default_spread_bps,
        },
        "summary": {
            "rows": len(rows),
            "observed_shortfall_mean_bps": round(mean(observed), 6),
            "modeled_shortfall_mean_bps": round(mean(modeled), 6),
            "residual_mean_bps": round(mean(residuals), 6),
            "residual_mae_bps": round(mean(abs_residuals), 6),
            "residual_max_abs_bps": round(max(abs_residuals), 6),
            "commission_mean_bps": round(mean(float(row["commission_bps"]) for row in rows), 6),
            "latency_mean_seconds": round(mean(latencies), 6) if latencies else None,
            "latency_max_seconds": round(max(latencies), 6) if latencies else None,
        },
        "rows": rows,
        "interpretation": (
            "Observed shortfall is side-adjusted relative to reference_price. "
            "Residual = observed_shortfall_bps - modeled_shortfall_bps. Large positive residuals "
            "mean the simulator underestimates realized execution cost for the supplied fills."
        ),
    }


def _compare_row(
    row: dict[str, str],
    *,
    row_number: int,
    base_slippage_bps: float,
    market_impact: float,
    default_spread_bps: float,
) -> dict[str, Any] | None:
    side = str(row.get("side", "")).strip().lower()
    if side not in {"buy", "sell"}:
        return None
    quantity = _float(row.get("quantity"))
    reference_price = _float(row.get("reference_price"))
    fill_price = _float(row.get("fill_price"))
    if quantity <= 0 or reference_price <= 0 or fill_price <= 0:
        return None

    direction = 1.0 if side == "buy" else -1.0
    observed_shortfall_bps = direction * (fill_price - reference_price) / reference_price * 10_000.0
    commission = max(0.0, _float(row.get("commission")))
    notional = quantity * fill_price
    commission_bps = commission / notional * 10_000.0 if notional > 0 else 0.0
    spread_bps = _float(row.get("spread_bps"), default_spread_bps)
    bar_volume = max(0.0, _float(row.get("bar_volume")))
    participation = quantity / max(1.0, bar_volume) if bar_volume > 0 else 0.0
    high = _float(row.get("bar_high"))
    low = _float(row.get("bar_low"))
    close = _float(row.get("bar_close"))
    intrabar_range_bps = (high - low) / close * 10_000.0 if close > 0 and high >= low else 0.0
    half_spread_bps = max(0.0, spread_bps) / 2.0
    impact_bps = market_impact * participation * 10_000.0
    volatility_bps = 0.1 * intrabar_range_bps
    modeled_shortfall_bps = half_spread_bps + base_slippage_bps + impact_bps + volatility_bps + commission_bps
    latency_seconds = _latency_seconds(row.get("submitted_at"), row.get("filled_at"))
    return {
        "row_number": row_number,
        "symbol": str(row.get("symbol", "")).strip(),
        "side": side,
        "quantity": quantity,
        "reference_price": reference_price,
        "fill_price": fill_price,
        "observed_shortfall_bps": round(observed_shortfall_bps, 6),
        "modeled_shortfall_bps": round(modeled_shortfall_bps, 6),
        "residual_bps": round(observed_shortfall_bps - modeled_shortfall_bps, 6),
        "half_spread_bps": round(half_spread_bps, 6),
        "base_slippage_bps": base_slippage_bps,
        "impact_bps": round(impact_bps, 6),
        "volatility_bps": round(volatility_bps, 6),
        "commission_bps": round(commission_bps, 6),
        "participation": round(participation, 8),
        "latency_seconds": round(latency_seconds, 6) if latency_seconds is not None else None,
    }


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_markdown(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = payload["summary"]
    params = payload["model_parameters"]
    lines = [
        "# Execution Fill Calibration Comparison",
        "",
        "This report compares side-adjusted realized shortfall from historical fills",
        "against the current TreLLM execution-stress equation.",
        "",
        "## Model Parameters",
        "",
        "| Parameter | Value |",
        "| --- | ---: |",
        f"| `base_slippage_bps` | {params['base_slippage_bps']} |",
        f"| `market_impact` | {params['market_impact']} |",
        f"| `default_spread_bps` | {params['default_spread_bps']} |",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Rows | {summary['rows']} |",
        f"| Observed shortfall mean | {summary['observed_shortfall_mean_bps']} bps |",
        f"| Modeled shortfall mean | {summary['modeled_shortfall_mean_bps']} bps |",
        f"| Residual mean | {summary['residual_mean_bps']} bps |",
        f"| Residual MAE | {summary['residual_mae_bps']} bps |",
        f"| Residual max abs | {summary['residual_max_abs_bps']} bps |",
        f"| Commission mean | {summary['commission_mean_bps']} bps |",
        f"| Latency mean | {_format_optional(summary['latency_mean_seconds'], 's')} |",
        f"| Latency max | {_format_optional(summary['latency_max_seconds'], 's')} |",
        "",
        "## Row Sample",
        "",
        "| Symbol | Side | Qty | Observed bps | Modeled bps | Residual bps | Participation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["rows"][:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["symbol"]),
                    str(row["side"]),
                    str(row["quantity"]),
                    str(row["observed_shortfall_bps"]),
                    str(row["modeled_shortfall_bps"]),
                    str(row["residual_bps"]),
                    str(row["participation"]),
                ]
            )
            + " |"
        )
    lines.extend(["", payload["interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _float(value: object, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def _latency_seconds(submitted_at: object, filled_at: object) -> float | None:
    submitted = _parse_timestamp(submitted_at)
    filled = _parse_timestamp(filled_at)
    if not submitted or not filled:
        return None
    latency = (filled - submitted).total_seconds()
    return latency if latency >= 0 else None


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _format_optional(value: object, suffix: str) -> str:
    if value is None:
        return "not supplied"
    return f"{value} {suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
