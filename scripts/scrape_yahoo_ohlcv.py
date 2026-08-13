"""Fetch daily OHLCV for an investable ETF/crypto universe from the public
Yahoo v8 chart endpoint and write back-adjusted CSVs (Close = adjusted close;
OHL scaled by adjclose/close) in the harness's expected format.

Usage: python scripts/scrape_yahoo_ohlcv.py
Writes data/real/yahoo_daily_etf_2021_2026/{TICKER}_Daily_2021_2026.csv
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/real/yahoo_daily_etf_2021_2026"
TICKERS = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "HYG", "BTC-USD"]
P1, P2 = 1640908800, 1781827200  # ~2021-12-31 .. ~2026-06-18 (covers recent window to 2026-05-14)


def fetch(ticker: str) -> dict:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={P1}&period2={P2}&interval=1d&events=div%2Csplit"
    )
    tmp = OUT / f"_{ticker}.json"
    subprocess.run(["curl", "-s", "-m", "30", "-H", "User-Agent: Mozilla/5.0", url, "-o", str(tmp)], check=True)
    data = json.loads(tmp.read_text())
    tmp.unlink()
    return data["chart"]["result"][0]


def write_csv(ticker: str, r: dict) -> int:
    import datetime

    ts = r["timestamp"]
    q = r["indicators"]["quote"][0]
    adj = r["indicators"]["adjclose"][0]["adjclose"]
    o, h, l, c, v = q["open"], q["high"], q["low"], q["close"], q["volume"]
    path = OUT / f"{ticker}_Daily_2021_2026.csv"
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        fh.write("Date,Open,High,Low,Close,Volume\n")
        for i in range(len(ts)):
            if None in (o[i], h[i], l[i], c[i], adj[i]) or c[i] in (0, None):
                continue
            f = adj[i] / c[i]  # back-adjustment factor
            d = datetime.date.fromtimestamp(ts[i]).isoformat()
            vol = v[i] or 0
            fh.write(f"{d},{o[i]*f:.6f},{h[i]*f:.6f},{l[i]*f:.6f},{adj[i]:.6f},{vol}\n")
            n += 1
    return n


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for t in TICKERS:
        try:
            r = fetch(t)
            n = write_csv(t, r)
            print(f"{t:10s} {n} rows")
        except Exception as exc:
            print(f"{t:10s} FAILED: {exc}")
        time.sleep(1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
