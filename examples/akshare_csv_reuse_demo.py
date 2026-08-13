from __future__ import annotations

from pathlib import Path

from tradearena.core.serialization import write_json
from tradearena.factory import build_default_system

DATA_DIR = Path("outputs/examples/akshare_ashare_sample")
OUTPUT_DIR = Path("outputs/examples")


def main() -> int:
    _write_sample_akshare_output(DATA_DIR)
    system = build_default_system(
        name="akshare_csv_reuse_demo",
        symbols=("600519.SS", "300750.SZ"),
        data_source="csv",
        real_data_dir=str(DATA_DIR),
        real_data_frequency="daily",
        real_data_max_periods=10,
        analyst_names=("momentum", "macro-news"),
        strategy_name="signal-weighted",
        risk_name="max-position",
        execution_mode="realistic",
        max_position_weight=0.22,
    )
    trajectory, metrics = system.run()
    summary = {
        "data_dir": str(DATA_DIR),
        "symbols": ["600519.SS", "300750.SZ"],
        "steps": len(trajectory.steps),
        "first_timestamp": trajectory.steps[0].timestamp.isoformat(),
        "last_timestamp": trajectory.steps[-1].timestamp.isoformat(),
        "final_equity": metrics["final_equity"],
        "total_return": metrics["total_return"],
        "risk_clipped_decisions": metrics["risk_clipped_decisions"],
        "rejected_order_count": metrics["rejected_order_count"],
        "provider_reused": "CsvMarketDataProvider",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "akshare_csv_reuse_summary.json", summary)
    _write_svg(OUTPUT_DIR / "akshare_csv_reuse.svg", summary)

    print("AkShare -> normalized CSV -> TreLLM demo")
    print(f"  rows={summary['steps']} symbols={', '.join(summary['symbols'])}")
    print(f"  final_equity={summary['final_equity']:.2f} total_return={summary['total_return']:.4f}")
    print(f"  reused={summary['provider_reused']}")
    print(f"\nWrote {OUTPUT_DIR / 'akshare_csv_reuse_summary.json'}")
    print(f"Wrote {OUTPUT_DIR / 'akshare_csv_reuse.svg'}")
    return 0


def _write_sample_akshare_output(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_ohlcv(data_dir / "600519.SS_Daily.csv", "2026-01", 1530.0, [8.0, -4.0, 12.0, 10.0, -6.0, 4.0, 7.0, -3.0, 5.0, 9.0])
    _write_ohlcv(data_dir / "300750.SZ_Daily.csv", "2026-01", 188.0, [-2.0, 5.0, 4.0, -8.0, 6.0, 3.0, -4.0, 7.0, 5.0, -3.0])
    (data_dir / "manifest.json").write_text(
        "{\n"
        '  "source": "AkShare stock_zh_a_hist sample",\n'
        '  "note": "offline miniature fixture with the same normalized CSV shape as scripts/download_akshare_ashare_daily.py"\n'
        "}\n",
        encoding="utf-8",
    )


def _write_ohlcv(path: Path, month: str, start: float, deltas: list[float]) -> None:
    rows = ["Date,Open,High,Low,Close,Volume"]
    price = start
    for idx, delta in enumerate(deltas, start=2):
        open_price = price
        close = max(1.0, open_price + delta)
        high = max(open_price, close) * 1.006
        low = min(open_price, close) * 0.994
        volume = 8_000_000 + idx * 180_000
        rows.append(f"{month}-{idx:02d},{open_price:.2f},{high:.2f},{low:.2f},{close:.2f},{volume:.0f}")
        price = close
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_svg(path: Path, summary: dict[str, object]) -> None:
    width, height = 900, 260
    boxes = [
        ("AkShare", "stock_zh_a_hist"),
        ("Normalize", "Date, Open, High, Low, Close, Volume"),
        ("CSV Provider", "same Data Layer"),
        ("TreLLM", "risk + execution + trajectory"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="AkShare CSV reuse pipeline">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 42, "A-share data path: AkShare -> normalized CSV -> existing TreLLM runner", 22, "#0f172a", 800),
        _text(36, 70, "No realtime adapter is required; the stable boundary is the same OHLCV CSV schema used by Yahoo data.", 13, "#64748b", 400),
    ]
    for idx, (title, body) in enumerate(boxes):
        x = 38 + idx * 215
        parts.append(f'<rect x="{x}" y="105" width="178" height="86" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
        parts.append(_text(x + 16, 136, title, 16, "#0f172a", 800))
        parts.append(_text(x + 16, 162, body, 11, "#475569", 500))
        if idx < len(boxes) - 1:
            parts.append(f'<path d="M{x + 184} 148 L{x + 205} 148" stroke="#2563eb" stroke-width="2"/>')
            parts.append(f'<path d="M{x + 205} 148 L{x + 198} 143 M{x + 205} 148 L{x + 198} 153" stroke="#2563eb" stroke-width="2" fill="none"/>')
    parts.append(_text(36, 226, f"Demo output: {summary['steps']} daily steps, final equity {float(summary['final_equity']):.2f}", 13, "#64748b", 500))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{value}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
