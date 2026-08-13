from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download normalized Yahoo Finance OHLCV CSV files for TreLLM.")
    parser.add_argument("--start", default="2021-05-01")
    parser.add_argument("--end", default="2026-05-14")
    parser.add_argument("--output-dir", default="data/real/yahoo_daily_2021_2026")
    parser.add_argument("--tickers", default="^GSPC,BTC-USD,ETH-USD")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tickers = [item.strip() for item in args.tickers.split(",") if item.strip()]
    manifest = {
        "source": "Yahoo Finance chart API",
        "start": args.start,
        "end": args.end,
        "frequency": "1d",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "tickers": tickers,
    }
    for ticker in tickers:
        print(f"Downloading {ticker} from {args.start} to {args.end}...")
        target = output_dir / f"{safe_symbol(ticker)}_Daily_2021_2026.csv"
        rows = download_with_chart_api(ticker, args.start, args.end)
        if not rows:
            rows = download_with_yfinance(ticker, args.start, args.end)
        if not rows:
            raise RuntimeError(f"No data returned for {ticker}")
        write_rows(target, rows)
        print(f"Saved {target}")
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


def download_with_chart_api(ticker: str, start: str, end: str) -> list[dict[str, str | float]]:
    period1 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp())
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/"
        f"{quote(ticker, safe='')}?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"Chart API failed for {ticker}: {exc}")
        return []

    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        return []
    timestamps = result.get("timestamp") or []
    quote_data = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    rows: list[dict[str, str | float]] = []
    for idx, stamp in enumerate(timestamps):
        try:
            open_price = quote_data["open"][idx]
            high = quote_data["high"][idx]
            low = quote_data["low"][idx]
            close = quote_data["close"][idx]
            volume = quote_data["volume"][idx]
        except (KeyError, IndexError):
            continue
        if None in (open_price, high, low, close):
            continue
        rows.append(
            {
                "Date": datetime.fromtimestamp(int(stamp), tz=timezone.utc).date().isoformat(),
                "Open": float(open_price),
                "High": float(high),
                "Low": float(low),
                "Close": float(close),
                "Volume": float(volume or 0.0),
            }
        )
    return rows


def download_with_yfinance(ticker: str, start: str, end: str) -> list[dict[str, str | float]]:
    try:
        import yfinance as yf
    except ImportError:
        return []
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if data.empty:
        return []
    if hasattr(data.columns, "nlevels") and data.columns.nlevels > 1:
        data.columns = [column[0] for column in data.columns]
    data = data.reset_index()
    rows = []
    for _, row in data.iterrows():
        rows.append(
            {
                "Date": str(row["Date"])[:10],
                "Open": float(row["Open"]),
                "High": float(row["High"]),
                "Low": float(row["Low"]),
                "Close": float(row["Close"]),
                "Volume": float(row.get("Volume", 0.0) or 0.0),
            }
        )
    return rows


def write_rows(path: Path, rows: list[dict[str, str | float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Date", "Open", "High", "Low", "Close", "Volume"])
        writer.writeheader()
        writer.writerows(rows)


def safe_symbol(symbol: str) -> str:
    return symbol.replace("^", "").replace("/", "-")


if __name__ == "__main__":
    raise SystemExit(main())
