from __future__ import annotations

from pathlib import Path

from tradearena.factory import build_default_system

DATA_DIR = Path("outputs/examples/sidecar_data")


def main() -> int:
    _write_demo_dataset(DATA_DIR)
    system = build_default_system(
        name="sidecar_data_demo",
        symbols=("SYN", "ALT"),
        data_source="csv",
        real_data_dir=str(DATA_DIR),
        real_data_frequency="daily",
        real_data_max_periods=8,
        analyst_names=("macro-news",),
        strategy_name="signal-weighted",
        risk_name="max-position",
        execution_mode="realistic",
        max_position_weight=0.25,
    )
    trajectory, metrics = system.run()
    first = trajectory.steps[0]
    last = trajectory.steps[-1]

    print("Loaded optional sidecars into the observation schema:")
    print(f"  first_step news={first.observation['news_count']} macro={first.observation['macro_count']}")
    print(f"  first_step filings={first.observation['filings_count']} alt_data={first.observation['alt_data_count']}")
    print("\nFirst-step analyst signal:")
    for signal in first.signals:
        print(f"  {signal['symbol']}: score={float(signal['score']):.3f} rationale={signal['rationale']}")
    print("\nRisk and execution summary:")
    print(f"  final_equity={float(last.portfolio['equity']):.2f}")
    print(f"  total_return={float(metrics['total_return']):.4f}")
    print(f"  clipped_decisions={metrics['risk_clipped_decisions']}")
    print(f"  rejected_orders={metrics['rejected_order_count']}")
    print(f"\nDemo CSVs live in {DATA_DIR}")
    return 0


def _write_demo_dataset(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    dates = [f"2026-01-{day:02d}" for day in range(2, 10)]
    _write_ohlcv(data_dir / "SYN_Daily_2021_2026.csv", dates, 100.0, 1.4)
    _write_ohlcv(data_dir / "ALT_Daily_2021_2026.csv", dates, 80.0, -0.2)
    (data_dir / "news.csv").write_text(
        "Date,Symbol,Source,Title,Body,Sentiment\n"
        "2026-01-02,SYN,research-wire,Product demand surprise,Demo news item,0.45\n"
        "2026-01-03,ALT,research-wire,Margin warning,Demo news item,-0.30\n",
        encoding="utf-8",
    )
    (data_dir / "macro.csv").write_text(
        "Date,Name,Value,Unit\n"
        "2026-01-02,synthetic_growth,0.60,index\n"
        "2026-01-03,synthetic_growth,0.45,index\n",
        encoding="utf-8",
    )
    (data_dir / "filings.csv").write_text(
        "Date,Symbol,Source,Form,Title,Body,Sentiment,Accession\n"
        "2026-01-02,SYN,demo-sec,8-K,Contract expansion,Demo filing,0.35,000-demo-1\n"
        "2026-01-03,ALT,demo-sec,10-Q,Inventory risk,Demo filing,-0.25,000-demo-2\n",
        encoding="utf-8",
    )
    (data_dir / "alternative_data.csv").write_text(
        "Date,Symbol,Name,Value,Unit,Source\n"
        "2026-01-02,SYN,web_traffic_zscore,0.40,z,demo-alt\n"
        "2026-01-03,ALT,app_rank_zscore,-0.20,z,demo-alt\n",
        encoding="utf-8",
    )


def _write_ohlcv(path: Path, dates: list[str], start: float, drift: float) -> None:
    rows = ["Date,Open,High,Low,Close,Volume"]
    price = start
    for idx, date in enumerate(dates):
        open_price = price
        close = max(1.0, open_price + drift + (idx % 3 - 1) * 0.25)
        high = max(open_price, close) + 0.75
        low = min(open_price, close) - 0.75
        volume = 1_000_000 + idx * 50_000
        rows.append(f"{date},{open_price:.2f},{high:.2f},{low:.2f},{close:.2f},{volume}")
        price = close
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
