from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_TICKERS = (
    "AAPL,MSFT,NVDA,AMZN,META,GOOGL,GOOG,TSLA,AVGO,JPM,V,MA,UNH,XOM,COST,"
    "WMT,HD,PG,JNJ,ABBV,BAC,KO,PEP,CRM,NFLX,ORCL,AMD,CSCO,MRK,CVX,TMO,"
    "ACN,LIN,MCD,IBM,GE,CAT,DIS,QCOM,INTU,AMAT,TXN,NOW,ISRG,PM,NEE,RTX,SPGI,GS,HON,LOW"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download normalized Yahoo Finance intraday OHLCV CSV files.")
    parser.add_argument("--range", default="60d", help="Yahoo Finance chart range, e.g. 30d, 60d, 730d.")
    parser.add_argument("--interval", default="1h", choices=["1h", "5m", "15m"], help="Intraday bar interval.")
    parser.add_argument("--output-dir", default="data/real/yahoo_intraday_1h_50")
    parser.add_argument("--tickers", default=DEFAULT_TICKERS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tickers = [ticker.strip() for ticker in args.tickers.split(",") if ticker.strip()]
    manifest = {
        "source": "Yahoo Finance chart API",
        "range": args.range,
        "interval": args.interval,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "tickers": tickers,
    }
    for ticker in tickers:
        rows = download_chart(ticker, args.range, args.interval)
        if not rows:
            raise RuntimeError(f"No intraday rows returned for {ticker}")
        suffix = "Hourly_1h" if args.interval == "1h" else args.interval
        target = output_dir / f"{safe_symbol(ticker)}_{suffix}.csv"
        write_rows(target, rows)
        print(f"Saved {len(rows):4d} rows: {target}")
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


def download_chart(ticker: str, range_value: str, interval: str) -> list[dict[str, str | float]]:
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/"
        f"{quote(ticker, safe='')}?range={quote(range_value)}&interval={quote(interval)}&events=history"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
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
                "Date": datetime.fromtimestamp(int(stamp), tz=timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
                "Open": float(open_price),
                "High": float(high),
                "Low": float(low),
                "Close": float(close),
                "Volume": float(volume or 0.0),
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
