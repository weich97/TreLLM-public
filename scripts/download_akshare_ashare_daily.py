from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SYMBOLS = "600519.SS,300750.SZ,000001.SZ,601318.SS,000858.SZ"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download A-share daily OHLCV from AkShare and normalize it for CsvMarketDataProvider."
    )
    parser.add_argument("--start", default="2021-01-01", help="Start date, YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--end", default=_today(), help="End date, YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--output-dir", default="data/real/akshare_ashare_daily")
    parser.add_argument("--symbols", default=DEFAULT_SYMBOLS, help="Comma-separated A-share symbols, e.g. 600519.SS,300750.SZ.")
    parser.add_argument("--adjust", default="qfq", choices=["none", "qfq", "hfq"], help="AkShare adjustment mode.")
    parser.add_argument(
        "--volume-multiplier",
        type=float,
        default=100.0,
        help="Multiplier applied to AkShare 成交量. Eastmoney-style A-share volume is commonly reported in lots.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError('AkShare is not installed. Run: python -m pip install -e ".[ashare]"') from exc

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    symbols = [item.strip() for item in args.symbols.split(",") if item.strip()]
    manifest = {
        "source": "AkShare stock_zh_a_hist",
        "source_library": "akshare",
        "start": _compact_date(args.start),
        "end": _compact_date(args.end),
        "frequency": "daily",
        "adjust": "" if args.adjust == "none" else args.adjust,
        "volume_multiplier": args.volume_multiplier,
        "volume_note": "Volume is normalized to TreLLM-compatible CSV units by multiplying AkShare 成交量 by volume_multiplier.",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbols": [],
    }
    for raw_symbol in symbols:
        spec = normalize_ashare_symbol(raw_symbol)
        print(f"Downloading {spec['akshare_symbol']} as {spec['tradearena_symbol']}...")
        frame = ak.stock_zh_a_hist(
            symbol=spec["akshare_symbol"],
            period="daily",
            start_date=_compact_date(args.start),
            end_date=_compact_date(args.end),
            adjust="" if args.adjust == "none" else args.adjust,
        )
        rows = normalize_akshare_rows(frame, spec["tradearena_symbol"], args.volume_multiplier)
        if not rows:
            raise RuntimeError(f"No AkShare rows returned for {raw_symbol}")
        target = output_dir / f"{safe_symbol(spec['tradearena_symbol'])}_Daily.csv"
        write_rows(target, rows)
        manifest["symbols"].append({**spec, "rows": len(rows), "file": target.name})
        print(f"Saved {len(rows):4d} rows: {target}")
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


def normalize_ashare_symbol(raw_symbol: str) -> dict[str, str]:
    symbol = raw_symbol.strip().upper().replace("_", ".")
    if not symbol:
        raise ValueError("Empty A-share symbol")
    if symbol.startswith(("SH", "SZ", "BJ")) and len(symbol) >= 8:
        exchange = symbol[:2]
        code = symbol[2:]
    elif "." in symbol:
        code, suffix = symbol.split(".", 1)
        exchange = "SH" if suffix in {"SS", "SH"} else suffix
    else:
        code = symbol
        exchange = _infer_exchange(code)
    suffix = "SS" if exchange == "SH" else exchange
    return {
        "input_symbol": raw_symbol,
        "akshare_symbol": code,
        "exchange": exchange,
        "tradearena_symbol": f"{code}.{suffix}",
    }


def normalize_akshare_rows(frame_or_rows: Any, symbol: str, volume_multiplier: float = 100.0) -> list[dict[str, str | float]]:
    rows = list(_records(frame_or_rows))
    normalized = []
    for item in rows:
        date_value = _value(item, "日期", "Date", "date")
        open_price = _float(_value(item, "开盘", "Open", "open"))
        close = _float(_value(item, "收盘", "Close", "close"))
        high = _float(_value(item, "最高", "High", "high"))
        low = _float(_value(item, "最低", "Low", "low"))
        volume = _float(_value(item, "成交量", "Volume", "volume")) * volume_multiplier
        if not date_value or None in (open_price, high, low, close):
            continue
        normalized.append(
            {
                "Date": _date_string(date_value),
                "Open": float(open_price),
                "High": float(high),
                "Low": float(low),
                "Close": float(close),
                "Volume": float(volume),
            }
        )
    normalized.sort(key=lambda row: str(row["Date"]))
    return normalized


def write_rows(path: Path, rows: list[dict[str, str | float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Date", "Open", "High", "Low", "Close", "Volume"])
        writer.writeheader()
        writer.writerows(rows)


def safe_symbol(symbol: str) -> str:
    return symbol.replace("^", "").replace("/", "-")


def _records(frame_or_rows: Any) -> Iterable[dict[str, Any]]:
    if hasattr(frame_or_rows, "to_dict"):
        return frame_or_rows.to_dict("records")
    return frame_or_rows or []


def _value(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _date_string(value: Any) -> str:
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else text


def _compact_date(value: str) -> str:
    return value.replace("-", "")[:8]


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _infer_exchange(code: str) -> str:
    if code.startswith(("6", "5", "9")):
        return "SH"
    if code.startswith(("0", "2", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
