from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json
from tradearena.tools.calibration import QuoteFillCalibrationConfig, summarize_quote_fill_calibration


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate quote/fill calibration stability across small rolling fill windows."
    )
    parser.add_argument("--quotes", default="data/public/binance_btcusdt_perp_2024_03_01_sample/quotes.csv")
    parser.add_argument("--fills", default="data/public/binance_btcusdt_perp_2024_03_01_sample/fills.csv")
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--windows", type=int, default=5)
    parser.add_argument("--output", default="docs/results/execution_calibration_stability.json")
    parser.add_argument("--markdown-output", default="docs/results/execution_calibration_stability.md")
    args = parser.parse_args(argv)

    rows = _read_csv_rows(ROOT / args.fills)
    windows = []
    tmp_dir = ROOT / ".tmp" / "execution_calibration_stability"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        for index, chunk in enumerate(_chunks(rows, args.window_size, args.windows), start=1):
            if len(chunk) < 2:
                continue
            chunk_path = tmp_dir / f"fills_window_{index}.csv"
            _write_csv_rows(chunk_path, chunk)
            summary = summarize_quote_fill_calibration(
                ROOT / args.quotes,
                chunk_path,
                QuoteFillCalibrationConfig(commission_bps_default=0.0),
            )
            windows.append(_window_row(index, chunk, summary))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if not windows:
        raise SystemExit("No calibration windows were generated.")
    report = {
        "schema": "tradearena_execution_calibration_stability_v0.1",
        "quote_file": args.quotes,
        "fill_file": args.fills,
        "window_size": args.window_size,
        "windows": windows,
        "claim_boundary": (
            "This report checks stability of a public quote/fill calibration sample across rolling windows. "
            "It supports calibration-plumbing robustness, not venue-wide or broker-grade execution claims."
        ),
        "summary": _aggregate(windows),
    }
    write_json(ROOT / args.output, report)
    write_markdown(report, ROOT / args.markdown_output)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    return 0


def _window_row(index: int, chunk: list[dict[str, str]], summary: dict[str, Any]) -> dict[str, Any]:
    params = summary["fitted_parameters"]
    quality = summary["fit_quality"]
    stress = summary["stress_only_comparison"]
    return {
        "window": index,
        "start_timestamp": chunk[0].get("timestamp", ""),
        "end_timestamp": chunk[-1].get("timestamp", ""),
        "fills": len(chunk),
        "aligned_rows": summary["input"]["aligned_rows"],
        "median_spread_bps": params["spread_bps_median"],
        "p90_spread_bps": params["spread_bps_p90"],
        "market_impact": params["market_impact"],
        "participation_rate_p90": params["participation_rate_p90"],
        "median_shortfall_bps": quality["median_shortfall_bps"],
        "calibrated_residual_mae_bps": quality["residual_mae_bps"],
        "stress_residual_mae_bps": stress["residual_mae_bps"],
        "mae_reduction_vs_stress_bps": stress["mae_reduction_vs_stress"],
    }


def _aggregate(windows: list[dict[str, Any]]) -> dict[str, Any]:
    calibrated = [float(row["calibrated_residual_mae_bps"]) for row in windows]
    stress = [float(row["stress_residual_mae_bps"]) for row in windows]
    reductions = [float(row["mae_reduction_vs_stress_bps"]) for row in windows]
    return {
        "window_count": len(windows),
        "calibrated_residual_mae_mean_bps": round(_mean(calibrated), 6),
        "calibrated_residual_mae_min_bps": round(min(calibrated), 6),
        "calibrated_residual_mae_max_bps": round(max(calibrated), 6),
        "stress_residual_mae_mean_bps": round(_mean(stress), 6),
        "mae_reduction_mean_bps": round(_mean(reductions), 6),
        "windows_where_calibrated_beats_stress": sum(1 for row in windows if row["mae_reduction_vs_stress_bps"] > 0),
    }


def write_markdown(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    lines = [
        "# Execution Calibration Stability",
        "",
        report["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Windows: {summary['window_count']}",
        f"- Mean calibrated residual MAE: {summary['calibrated_residual_mae_mean_bps']} bps",
        f"- Mean stress residual MAE: {summary['stress_residual_mae_mean_bps']} bps",
        f"- Mean MAE reduction vs stress: {summary['mae_reduction_mean_bps']} bps",
        f"- Windows where calibrated beats stress: {summary['windows_where_calibrated_beats_stress']} / {summary['window_count']}",
        "",
        "## Window Results",
        "",
        "| Window | Fill window | Fills | Spread median | Calibrated MAE | Stress MAE | Reduction | P90 participation |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["windows"]:
        lines.append(
            f"| {row['window']} | {row['start_timestamp']} to {row['end_timestamp']} | {row['fills']} | "
            f"{row['median_spread_bps']:.6f} bps | {row['calibrated_residual_mae_bps']:.6f} bps | "
            f"{row['stress_residual_mae_bps']:.6f} bps | {row['mae_reduction_vs_stress_bps']:.6f} bps | "
            f"{row['participation_rate_p90']:.8f} |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python scripts/run_execution_calibration_stability.py",
            "```",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _chunks(rows: list[dict[str, str]], size: int, count: int) -> list[list[dict[str, str]]]:
    size = max(2, int(size))
    count = max(1, int(count))
    return [rows[start : start + size] for start in range(0, min(len(rows), size * count), size)]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
