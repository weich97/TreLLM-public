from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.domain import Bar, Fill, MarketSnapshot, Order, PortfolioState, Side
from tradearena.core.serialization import write_json
from tradearena.execution.fill_replay import FillReplayOrderSimulator
from tradearena.execution.stress import QuoteReplayOrderSimulator, RealisticOrderSimulator
from tradearena.execution.utils import float_or_none, parse_datetime
from tradearena.tools.calibration import QuoteFillCalibrationConfig, summarize_quote_fill_calibration


@dataclass(frozen=True)
class SampleSpec:
    sample_id: str
    label: str
    directory: Path
    max_fills: int
    provenance_note: str


DEFAULT_SAMPLES = {
    "fixture": SampleSpec(
        sample_id="fixture",
        label="BTCUSDT redistributable microstructure fixture",
        directory=ROOT / "data/public/microstructure_sample",
        max_fills=8,
        provenance_note="Checked-in redistributable fixture for calibration plumbing; not a venue-wide cost claim.",
    ),
    "binance": SampleSpec(
        sample_id="binance",
        label="BTCUSDT Binance USD-M public sample",
        directory=ROOT / "data/public/binance_btcusdt_perp_2024_03_01_sample",
        max_fills=50,
        provenance_note=(
            "Public Binance bookTicker/trades sample; stronger than OHLCV stress, "
            "but not broker-specific private-fill evidence."
        ),
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a small execution calibration loop across stress, quote replay, and fill replay modes."
    )
    parser.add_argument("--samples", default="fixture,binance", help="Comma-separated sample ids: fixture, binance.")
    parser.add_argument("--max-fills", type=int, default=0, help="Override max fills per sample when positive.")
    parser.add_argument("--output", default="docs/results/execution_replay_calibration_loop.json")
    parser.add_argument("--markdown-output", default="docs/results/execution_replay_calibration_loop.md")
    args = parser.parse_args()

    sample_ids = [item.strip() for item in args.samples.split(",") if item.strip()]
    rows = []
    samples = []
    for sample_id in sample_ids:
        if sample_id not in DEFAULT_SAMPLES:
            raise SystemExit(f"Unknown sample {sample_id!r}. Use one of: {', '.join(DEFAULT_SAMPLES)}")
        spec = DEFAULT_SAMPLES[sample_id]
        max_fills = args.max_fills if args.max_fills > 0 else spec.max_fills
        sample_summary, mode_rows = run_sample(spec, max_fills=max_fills)
        samples.append(sample_summary)
        rows.extend(mode_rows)

    summary = {
        "schema": "tradearena_execution_replay_calibration_loop_v1",
        "claim_boundary": (
            "This is a small execution evidence loop. Stress mode is a conservative proxy under shared "
            "OHLCV assumptions, not ground truth. Quote replay uses observed top-of-book and available "
            "best-size constraints. Fill replay applies realized sample fills for audit replay; public "
            "exchange trades are not broker-specific private fills."
        ),
        "samples": samples,
        "mode_rows": rows,
    }
    write_json(ROOT / args.output, summary)
    write_markdown(summary, ROOT / args.markdown_output)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    return 0


def run_sample(spec: SampleSpec, *, max_fills: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    quote_file = spec.directory / "quotes.csv"
    fill_file = spec.directory / "fills.csv"
    manifest_file = spec.directory / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    quotes = _read_quotes(quote_file)
    fills = _read_fills(fill_file, quotes, max_fills=max_fills)
    if not fills:
        raise ValueError(f"No replayable fills found for sample {spec.sample_id}")

    calibration = summarize_quote_fill_calibration(
        quote_file,
        fill_file,
        QuoteFillCalibrationConfig(commission_bps_default=0.0 if spec.sample_id == "binance" else 1.0),
    )
    suggested = calibration["suggested_simulator_config"]
    mode_rows = [
        _run_mode(spec, fills, "ohlcv_stress", _stress_simulator()),
        _run_mode(spec, fills, "quote_replay", _quote_replay_simulator(suggested)),
        _run_mode(spec, fills, "fill_replay", None),
    ]
    sample_summary = {
        "sample_id": spec.sample_id,
        "label": spec.label,
        "symbols": sorted({str(row["symbol"]) for row in fills}),
        "fills_used": len(fills),
        "quote_rows": sum(len(value) for value in quotes.values()),
        "source": manifest.get("source", manifest.get("schema", "checked-in fixture")),
        "venue": manifest.get("venue", "fixture"),
        "window_start_utc": manifest.get("window_start_utc"),
        "window_end_utc": manifest.get("window_end_utc"),
        "provenance_note": spec.provenance_note,
        "calibration_residual_mae_bps": calibration["fit_quality"]["residual_mae_bps"],
        "stress_residual_mae_bps": calibration["stress_only_comparison"]["residual_mae_bps"],
    }
    return sample_summary, mode_rows


def _stress_simulator() -> RealisticOrderSimulator:
    return RealisticOrderSimulator(
        commission_bps=1.0,
        base_slippage_bps=2.0,
        spread_bps=0.0,
        participation_rate=0.05,
        latency_steps=1,
        market_impact=0.15,
    )


def _quote_replay_simulator(config: dict[str, Any]) -> QuoteReplayOrderSimulator:
    return QuoteReplayOrderSimulator(
        commission_bps=float(config["commission_bps"]),
        base_slippage_bps=float(config["base_slippage_bps"]),
        spread_bps=float(config["spread_bps"]),
        participation_rate=max(1e-8, float(config["participation_rate"])),
        latency_steps=0,
        market_impact=float(config["market_impact"]),
    )


def _run_mode(
    spec: SampleSpec,
    rows: list[dict[str, Any]],
    mode: str,
    simulator_template: RealisticOrderSimulator | QuoteReplayOrderSimulator | None,
) -> dict[str, Any]:
    fills: list[tuple[Fill, dict[str, Any]]] = []
    rejected = 0
    partial = 0
    fill_ratios: list[float] = []
    latency_steps: list[float] = []
    latency_seconds: list[float] = []
    spread_bps: list[float] = []
    quote_staleness_seconds: list[float] = []
    event_lag_seconds: list[float] = []
    submitted = len(rows)

    for row in rows:
        order = _order_from_row(row)
        snapshot = _snapshot_from_row(row, quote_enabled=(mode == "quote_replay"))
        portfolio = _portfolio_for_order(order, row)
        if mode == "fill_replay":
            simulator = FillReplayOrderSimulator(replay_fills=[_replay_fill_from_row(row)], enforce_cash=True)
            row_fills = simulator.execute(snapshot, [order], portfolio)
        else:
            assert simulator_template is not None
            simulator = _clone_simulator(simulator_template)
            row_fills = simulator.execute(snapshot, [order], portfolio)
            if simulator.latency_steps > 0:
                row_fills = row_fills + simulator.execute(snapshot, [], portfolio)

        if row["spread_bps"] is not None:
            spread_bps.append(float(row["spread_bps"]))
        if row["quote_staleness_seconds"] is not None:
            quote_staleness_seconds.append(float(row["quote_staleness_seconds"]))
        if row["quote_event_lag_seconds"] is not None:
            event_lag_seconds.append(float(row["quote_event_lag_seconds"]))
        if row["latency_seconds"] is not None and mode == "fill_replay":
            latency_seconds.append(float(row["latency_seconds"]))

        if not row_fills:
            rejected += 1
            fill_ratios.append(0.0)
            continue
        fill = row_fills[0]
        fills.append((fill, row))
        fill_ratios.append(fill.fill_ratio)
        latency_steps.append(float(fill.latency_steps))
        if fill.fill_ratio < 0.999999:
            partial += 1

    filled = len(fills)
    slippage_bps = [_side_adjusted_bps(fill, row) for fill, row in fills]
    slippage_cost = [abs(fill.slippage) * fill.quantity for fill, _ in fills]
    commissions = [fill.commission for fill, _ in fills]
    filled_quantity = sum(fill.quantity for fill, _ in fills)
    requested_quantity = sum(float(row["quantity"]) for row in rows)
    evidence = {
        "ohlcv_stress": ["stress-only", "conservative-proxy"],
        "quote_replay": ["quote-replay", "public-top-of-book", "depth-constrained"],
        "fill_replay": ["fill-replay", "sample-realized-fills"],
    }[mode]
    return {
        "sample_id": spec.sample_id,
        "mode": mode,
        "evidence_labels": evidence,
        "orders": submitted,
        "filled_orders": filled,
        "rejected_orders": rejected,
        "rejection_rate": round(rejected / submitted if submitted else 0.0, 6),
        "partial_fills": partial,
        "fill_ratio_mean": round(_mean(fill_ratios), 6),
        "quantity_fill_ratio": round(filled_quantity / requested_quantity if requested_quantity else 0.0, 6),
        "median_spread_bps": round(_percentile(spread_bps, 0.50), 6),
        "p90_spread_bps": round(_percentile(spread_bps, 0.90), 6),
        "mean_slippage_bps": round(_mean(slippage_bps), 6),
        "p90_abs_slippage_bps": round(_percentile([abs(value) for value in slippage_bps], 0.90), 6),
        "total_slippage_cost": round(sum(slippage_cost), 6),
        "total_commission": round(sum(commissions), 6),
        "average_latency_steps": round(_mean(latency_steps), 6),
        "median_latency_seconds": _rounded_or_none(_percentile(latency_seconds, 0.50)) if latency_seconds else None,
        "median_quote_event_lag_seconds": _rounded_or_none(_percentile(event_lag_seconds, 0.50))
        if event_lag_seconds
        else None,
        "median_quote_staleness_seconds": _rounded_or_none(_percentile(quote_staleness_seconds, 0.50))
        if quote_staleness_seconds
        else None,
        "boundary": _mode_boundary(mode, spec),
    }


def _clone_simulator(simulator: RealisticOrderSimulator | QuoteReplayOrderSimulator) -> RealisticOrderSimulator:
    simulator_type = type(simulator)
    return simulator_type(
        commission_bps=simulator.commission_bps,
        base_slippage_bps=simulator.base_slippage_bps,
        spread_bps=simulator.spread_bps,
        participation_rate=simulator.participation_rate,
        latency_steps=simulator.latency_steps,
        market_impact=simulator.market_impact,
    )


def _mode_boundary(mode: str, spec: SampleSpec) -> str:
    if mode == "ohlcv_stress":
        return "Conservative OHLCV stress proxy; not ground-truth transaction-cost evidence."
    if mode == "quote_replay":
        return "Uses observed top-of-book and best-size constraints; no hidden queue or broker-routing evidence."
    return f"Replays realized fills from {spec.sample_id}; {spec.provenance_note}"


def _read_quotes(path: Path) -> dict[str, list[dict[str, Any]]]:
    quotes: dict[str, list[dict[str, Any]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            timestamp = _parse_optional_datetime(row.get("timestamp"))
            bid = float_or_none(row.get("bid"))
            ask = float_or_none(row.get("ask"))
            symbol = str(row.get("symbol", "")).strip()
            if timestamp is None or bid is None or ask is None or not symbol or ask < bid:
                continue
            quote = {
                "timestamp": timestamp,
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "bid_qty": float_or_none(row.get("bid_qty") or row.get("best_bid_qty")),
                "ask_qty": float_or_none(row.get("ask_qty") or row.get("best_ask_qty")),
                "transaction_time": _parse_optional_datetime(row.get("transaction_time")),
                "event_time": _parse_optional_datetime(row.get("event_time")),
            }
            quotes.setdefault(symbol, []).append(quote)
    for values in quotes.values():
        values.sort(key=lambda item: item["timestamp"])
    return quotes


def _read_fills(path: Path, quotes: dict[str, list[dict[str, Any]]], *, max_fills: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            timestamp = _parse_optional_datetime(raw.get("timestamp"))
            symbol = str(raw.get("symbol", "")).strip()
            side = str(raw.get("side", "")).strip().lower()
            quantity = float_or_none(raw.get("quantity"))
            fill_price = float_or_none(raw.get("fill_price") or raw.get("price"))
            if timestamp is None or side not in {"buy", "sell"} or quantity is None or quantity <= 0 or not fill_price:
                continue
            quote = _latest_quote(quotes.get(symbol, []), timestamp)
            if quote is None:
                continue
            mid = (float(quote["bid"]) + float(quote["ask"])) / 2.0
            reference_price = float_or_none(raw.get("reference_price")) or mid
            submitted_at = _parse_optional_datetime(raw.get("submitted_at"))
            filled_at = _parse_optional_datetime(raw.get("filled_at")) or timestamp
            row = {
                "timestamp": timestamp,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "requested_quantity": float_or_none(raw.get("requested_quantity")) or quantity,
                "fill_price": fill_price,
                "reference_price": reference_price,
                "commission": float_or_none(raw.get("commission")) or 0.0,
                "bar_volume": max(1.0, float_or_none(raw.get("bar_volume")) or 1.0),
                "bar_high": float_or_none(raw.get("bar_high")) or max(fill_price, reference_price),
                "bar_low": float_or_none(raw.get("bar_low")) or min(fill_price, reference_price),
                "bar_close": float_or_none(raw.get("bar_close")) or reference_price,
                "quote": quote,
                "spread_bps": (float(quote["ask"]) - float(quote["bid"])) / mid * 10_000.0 if mid else None,
                "latency_seconds": _seconds_between(submitted_at, filled_at),
                "quote_event_lag_seconds": _seconds_between(quote.get("transaction_time"), quote.get("event_time")),
                "quote_staleness_seconds": _seconds_between(quote.get("timestamp"), timestamp),
            }
            rows.append(row)
            if len(rows) >= max_fills:
                break
    return rows


def _latest_quote(quotes: list[dict[str, Any]], timestamp: Any) -> dict[str, Any] | None:
    latest = None
    for quote in quotes:
        if quote["timestamp"] <= timestamp:
            latest = quote
        else:
            break
    return latest


def _snapshot_from_row(row: dict[str, Any], *, quote_enabled: bool) -> MarketSnapshot:
    timestamp = row["timestamp"]
    symbol = str(row["symbol"])
    close = float(row["bar_close"])
    bar = Bar(
        symbol=symbol,
        timestamp=timestamp,
        open=float(row["reference_price"]),
        high=float(row["bar_high"]),
        low=float(row["bar_low"]),
        close=close,
        volume=float(row["bar_volume"]),
    )
    alt_data: dict[str, Any] = {}
    if quote_enabled:
        quote = row["quote"]
        alt_data["quotes"] = {symbol: {"bid": quote["bid"], "ask": quote["ask"]}}
        level2: dict[str, Any] = {}
        if quote.get("bid_qty") is not None:
            level2["bid_size"] = quote["bid_qty"]
        if quote.get("ask_qty") is not None:
            level2["ask_size"] = quote["ask_qty"]
        if level2:
            alt_data["level2"] = {symbol: level2}
    return MarketSnapshot(timestamp=timestamp, bars={symbol: bar}, alt_data=alt_data)


def _order_from_row(row: dict[str, Any]) -> Order:
    side = Side.BUY if row["side"] == "buy" else Side.SELL
    return Order(
        symbol=str(row["symbol"]),
        side=side,
        quantity=float(row["requested_quantity"]),
        reason="execution-calibration-loop",
    )


def _portfolio_for_order(order: Order, row: dict[str, Any]) -> PortfolioState:
    price = float(row["reference_price"])
    cash = max(1_000_000.0, order.quantity * price * 100.0)
    positions = {order.symbol: order.quantity * 2.0} if order.side == Side.SELL else {}
    return PortfolioState(cash=cash, positions=positions, last_prices={order.symbol: price})


def _replay_fill_from_row(row: dict[str, Any]) -> Fill:
    side = Side.BUY if row["side"] == "buy" else Side.SELL
    latency_seconds = row.get("latency_seconds")
    latency_steps = math.ceil(float(latency_seconds) / 60.0) if latency_seconds else 0
    return Fill(
        symbol=str(row["symbol"]),
        side=side,
        quantity=float(row["quantity"]),
        price=float(row["fill_price"]),
        commission=float(row["commission"]),
        timestamp=row["timestamp"],
        requested_quantity=float(row["requested_quantity"]),
        latency_steps=latency_steps,
        liquidity_available=float(row["bar_volume"]),
        fill_ratio=float(row["quantity"]) / max(float(row["requested_quantity"]), 1e-9),
        slippage=float(row["fill_price"]) - float(row["reference_price"]),
        status="filled",
    )


def _side_adjusted_bps(fill: Fill, row: dict[str, Any]) -> float:
    reference = max(1e-9, float(row["reference_price"]))
    direction = 1.0 if fill.side == Side.BUY else -1.0
    return direction * (fill.price - reference) / reference * 10_000.0


def write_markdown(summary: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Execution Replay Calibration Loop",
        "",
        summary["claim_boundary"],
        "",
        "## Samples",
        "",
        "| Sample | Symbols | Fills | Quote rows | Source | Boundary |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for sample in summary["samples"]:
        lines.append(
            f"| {sample['label']} | {', '.join(sample['symbols'])} | {sample['fills_used']} | "
            f"{sample['quote_rows']} | {sample['source']} | {sample['provenance_note']} |"
        )
    lines.extend(
        [
            "",
            "## Mode Comparison",
            "",
            "| Sample | Mode | Evidence | Orders | Fill ratio | Reject rate | Partials | Median spread | Mean slippage | P90 abs slippage | Latency | Slippage cost |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for row in summary["mode_rows"]:
        latency = _format_latency(row)
        lines.append(
            f"| {row['sample_id']} | `{row['mode']}` | {', '.join(f'`{item}`' for item in row['evidence_labels'])} | "
            f"{row['orders']} | {row['quantity_fill_ratio']:.3f} | {row['rejection_rate']:.3f} | "
            f"{row['partial_fills']} | {row['median_spread_bps']:.4f} bps | "
            f"{row['mean_slippage_bps']:.4f} bps | {row['p90_abs_slippage_bps']:.4f} bps | "
            f"{latency} | {row['total_slippage_cost']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `ohlcv_stress` is the conservative proxy used by default benchmark rows. It is useful for shared stress comparisons, not for ground-truth transaction-cost prediction.",
            "- `quote_replay` upgrades the evidence by using observed top-of-book spread and best-size constraints, but it still lacks hidden queue position and broker-routing outcomes.",
            "- `fill_replay` applies realized sample fills. In the Binance row these are public exchange trades, not private broker fills, so the row supports calibration plumbing rather than venue-wide execution claims.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "python scripts/run_execution_replay_calibration_loop.py",
            "```",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def _format_latency(row: dict[str, Any]) -> str:
    if row.get("mode") == "ohlcv_stress":
        return f"{row['average_latency_steps']:.3f} steps"
    seconds = row.get("median_latency_seconds")
    if seconds is not None:
        return f"{seconds:.3f} s"
    event_lag = row.get("median_quote_event_lag_seconds")
    if event_lag is not None:
        return f"market-data lag {event_lag:.3f} s"
    return f"{row['average_latency_steps']:.3f} steps"


def _parse_optional_datetime(value: object) -> Any:
    text = str(value or "").strip()
    if not text:
        return None
    return parse_datetime(text)


def _seconds_between(start: object, end: object) -> float | None:
    if start is None or end is None:
        return None
    seconds = (end - start).total_seconds()
    return round(seconds, 6) if seconds >= 0 else None


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, quantile)) * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _rounded_or_none(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


if __name__ == "__main__":
    raise SystemExit(main())
