from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from scripts.compare_execution_to_fills import compare_fills_to_model

ROOT = Path(__file__).resolve().parents[1]


def test_compare_execution_to_fills_computes_side_adjusted_residuals(tmp_path: Path):
    fills = tmp_path / "fills.csv"
    with fills.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "side",
                "quantity",
                "reference_price",
                "fill_price",
                "commission",
                "spread_bps",
                "bar_volume",
                "bar_high",
                "bar_low",
                "bar_close",
                "submitted_at",
                "filled_at",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "SYN",
                "side": "buy",
                "quantity": "100",
                "reference_price": "100",
                "fill_price": "100.20",
                "commission": "1",
                "spread_bps": "4",
                "bar_volume": "10000",
                "bar_high": "101",
                "bar_low": "99",
                "bar_close": "100",
                "submitted_at": "2026-01-01T14:30:00+00:00",
                "filled_at": "2026-01-01T14:30:03+00:00",
            }
        )
        writer.writerow(
            {
                "symbol": "SYN",
                "side": "sell",
                "quantity": "100",
                "reference_price": "100",
                "fill_price": "99.80",
                "commission": "1",
                "spread_bps": "4",
                "bar_volume": "10000",
                "bar_high": "101",
                "bar_low": "99",
                "bar_close": "100",
                "submitted_at": "2026-01-01T14:31:00Z",
                "filled_at": "2026-01-01T14:31:05Z",
            }
        )

    result = compare_fills_to_model(fills, base_slippage_bps=2.0, market_impact=0.15, default_spread_bps=0.0)

    assert result["summary"]["rows"] == 2
    assert result["rows"][0]["observed_shortfall_bps"] == 20.0
    assert result["rows"][1]["observed_shortfall_bps"] == 20.0
    assert result["summary"]["latency_mean_seconds"] == 4.0
    assert result["summary"]["residual_mae_bps"] > 0


def test_compare_execution_to_fills_cli_writes_reports(tmp_path: Path):
    fills = tmp_path / "fills.csv"
    fills.write_text(
        "\n".join(
            [
                "symbol,side,quantity,reference_price,fill_price,commission,spread_bps,bar_volume,bar_high,bar_low,bar_close",
                "ALT,buy,10,50,50.05,0.25,3,5000,50.5,49.5,50",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "comparison.json"
    markdown = tmp_path / "comparison.md"

    subprocess.run(
        [
            sys.executable,
            "scripts/compare_execution_to_fills.py",
            "--fills",
            str(fills),
            "--output",
            str(output),
            "--markdown-output",
            str(markdown),
        ],
        cwd=ROOT,
        check=True,
    )

    assert output.exists()
    assert markdown.exists()
    assert "Execution Fill Calibration Comparison" in markdown.read_text(encoding="utf-8")


def test_quote_fill_calibration_cli_writes_reports_without_installed_package(tmp_path: Path):
    output = tmp_path / "quote_fill.json"
    markdown = tmp_path / "quote_fill.md"

    subprocess.run(
        [
            sys.executable,
            "scripts/calibrate_quote_fill_model.py",
            "--output",
            str(output),
            "--markdown-output",
            str(markdown),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.exists()
    assert markdown.exists()
    assert "Quote/Fill Execution Calibration" in markdown.read_text(encoding="utf-8")
