from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://data.binance.vision/data/futures/um/daily"


@dataclass(frozen=True)
class SourceFile:
    key: str
    url: str
    cache_name: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download Binance public-data futures bookTicker/trades/klines and "
            "extract a small quote/fill calibration sample."
        )
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--date", default="2024-03-01")
    parser.add_argument("--start", default="00:00:00", help="UTC window start, HH:MM:SS")
    parser.add_argument("--minutes", type=int, default=15)
    parser.add_argument("--max-fills", type=int, default=500)
    parser.add_argument("--quote-stride-ms", type=int, default=1000)
    parser.add_argument("--cache-dir", default=".tmp/binance_public_data")
    parser.add_argument("--output-dir", default="data/public/binance_btcusdt_perp_2024_03_01_sample")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    start = _parse_window_start(args.date, args.start)
    end = start + timedelta(minutes=args.minutes)
    cache_dir = ROOT / args.cache_dir
    output_dir = ROOT / args.output_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = _source_files(symbol, args.date)
    cached = {source.key: _download(source, cache_dir) for source in sources}
    source_records = [_source_record(source, cached[source.key]) for source in sources]

    klines = _read_klines(cached["klines"])
    quotes = _extract_quotes(cached["book_ticker"], symbol, start, end, args.quote_stride_ms)
    fills = _extract_fills(cached["trades"], symbol, start, end, klines, args.max_fills)
    _write_csv(output_dir / "quotes.csv", quotes)
    _write_csv(output_dir / "fills.csv", fills)

    manifest = {
        "schema": "tradearena_public_binance_microstructure_sample_v1",
        "source": "Binance public-data USD-M futures daily files",
        "symbol": symbol,
        "venue": "Binance USD-M Futures",
        "date": args.date,
        "window_start_utc": _iso(start),
        "window_end_utc": _iso(end),
        "quote_stride_ms": args.quote_stride_ms,
        "max_fills": args.max_fills,
        "files": {"quotes": "quotes.csv", "fills": "fills.csv"},
        "source_files": source_records,
        "rows": {"quotes": len(quotes), "fills": len(fills)},
        "provenance": {
            "live_api_used": False,
            "downloaded_market_data_used": True,
            "private_fills_used": False,
            "fill_interpretation": (
                "Public exchange trades are used as realized market fills for calibration plumbing. "
                "They are not broker-specific fills and do not reveal hidden queue position or private order intent."
            ),
            "latency_interpretation": (
                "bookTicker transaction_time to event_time is a public market-data lag proxy. "
                "It is not broker order-routing latency."
            ),
        },
        "claim_boundary": (
            "This sample upgrades TreLLM from an OHLCV-only smoke test to a public quote/fill replay "
            "calibration example. It is still a small Binance BTCUSDT perpetual sample, not a venue-wide "
            "transaction-cost model."
        ),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Wrote {(output_dir / 'quotes.csv').relative_to(ROOT)}")
    print(f"Wrote {(output_dir / 'fills.csv').relative_to(ROOT)}")
    print(f"Wrote {(output_dir / 'manifest.json').relative_to(ROOT)}")
    return 0


def _source_files(symbol: str, date: str) -> list[SourceFile]:
    return [
        SourceFile(
            "book_ticker",
            f"{BASE_URL}/bookTicker/{symbol}/{symbol}-bookTicker-{date}.zip",
            f"{symbol}-bookTicker-{date}.zip",
        ),
        SourceFile("trades", f"{BASE_URL}/trades/{symbol}/{symbol}-trades-{date}.zip", f"{symbol}-trades-{date}.zip"),
        SourceFile(
            "klines",
            f"{BASE_URL}/klines/{symbol}/1m/{symbol}-1m-{date}.zip",
            f"{symbol}-1m-{date}.zip",
        ),
    ]


def _download(source: SourceFile, cache_dir: Path) -> Path:
    path = cache_dir / source.cache_name
    if path.exists():
        return path
    request = urllib.request.Request(source.url, headers={"User-Agent": "TreLLM-calibration-sample"})
    with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    return path


def _extract_quotes(path: Path, symbol: str, start: datetime, end: datetime, stride_ms: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    next_emit = start
    with zipfile.ZipFile(path) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as raw:
            reader = csv.DictReader(line.decode("utf-8") for line in raw)
            for row in reader:
                transaction_time = _from_ms(row["transaction_time"])
                if transaction_time < start:
                    continue
                if transaction_time >= end:
                    break
                if transaction_time < next_emit:
                    continue
                event_time = _from_ms(row["event_time"])
                rows.append(
                    {
                        "timestamp": _iso(transaction_time),
                        "symbol": symbol,
                        "bid": row["best_bid_price"],
                        "ask": row["best_ask_price"],
                        "bid_qty": row["best_bid_qty"],
                        "ask_qty": row["best_ask_qty"],
                        "transaction_time": _iso(transaction_time),
                        "event_time": _iso(event_time),
                        "update_id": row["update_id"],
                    }
                )
                next_emit = transaction_time + timedelta(milliseconds=max(1, stride_ms))
    return rows


def _extract_fills(
    path: Path,
    symbol: str,
    start: datetime,
    end: datetime,
    klines: dict[int, dict[str, str]],
    max_fills: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as raw:
            reader = csv.DictReader(line.decode("utf-8") for line in raw)
            for row in reader:
                timestamp = _from_ms(row["time"])
                if timestamp < start:
                    continue
                if timestamp >= end:
                    break
                minute_key = _minute_ms(timestamp)
                kline = klines.get(minute_key, {})
                is_buyer_maker = row["is_buyer_maker"].strip().lower() == "true"
                side = "sell" if is_buyer_maker else "buy"
                candidates.append(
                    {
                        "timestamp": _iso(timestamp),
                        "symbol": symbol,
                        "side": side,
                        "quantity": row["qty"],
                        "reference_price": "",
                        "fill_price": row["price"],
                        "commission": "0",
                        "bar_volume": kline.get("volume", ""),
                        "bar_high": kline.get("high", ""),
                        "bar_low": kline.get("low", ""),
                        "bar_close": kline.get("close", ""),
                        "submitted_at": "",
                        "filled_at": _iso(timestamp),
                        "trade_id": row["id"],
                        "quote_qty": row["quote_qty"],
                        "is_buyer_maker": row["is_buyer_maker"],
                    }
                )
    return _even_sample(candidates, max_fills)


def _read_klines(path: Path) -> dict[int, dict[str, str]]:
    rows: dict[int, dict[str, str]] = {}
    with zipfile.ZipFile(path) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as raw:
            reader = csv.DictReader(line.decode("utf-8") for line in raw)
            for row in reader:
                rows[int(row["open_time"])] = row
    return rows


def _even_sample(rows: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    if max_rows <= 0 or len(rows) <= max_rows:
        return rows
    step = (len(rows) - 1) / (max_rows - 1)
    indexes = sorted({min(len(rows) - 1, round(i * step)) for i in range(max_rows)})
    return [rows[index] for index in indexes]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _source_record(source: SourceFile, path: Path) -> dict[str, Any]:
    return {
        "key": source.key,
        "url": source.url,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _parse_window_start(date: str, time_text: str) -> datetime:
    parsed_date = datetime.fromisoformat(date).date()
    hh, mm, ss = (int(part) for part in time_text.split(":"))
    return datetime(parsed_date.year, parsed_date.month, parsed_date.day, hh, mm, ss, tzinfo=timezone.utc)


def _from_ms(value: str) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000.0, tz=timezone.utc)


def _minute_ms(timestamp: datetime) -> int:
    minute = timestamp.replace(second=0, microsecond=0)
    return math.floor(minute.timestamp() * 1000)


def _iso(timestamp: datetime) -> str:
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
