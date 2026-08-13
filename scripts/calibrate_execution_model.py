from __future__ import annotations

import argparse

from tradearena.tools.calibration import (
    ExecutionCalibrationConfig,
    discover_ohlcv_files,
    summarize_execution_calibration,
    write_calibration_json,
    write_calibration_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate OHLCV-based diagnostics for the TreLLM execution simulator."
    )
    parser.add_argument("--data-dir", default="data/real/yahoo_intraday_1h_50")
    parser.add_argument("--glob", default="*.csv", help="CSV filename glob under --data-dir.")
    parser.add_argument("--output", default="docs/results/execution_calibration_intraday_1h.json")
    parser.add_argument("--markdown-output", default="docs/results/execution_calibration_intraday_1h.md")
    parser.add_argument("--commission-bps", type=float, default=1.0)
    parser.add_argument("--spread-bps", type=float, default=None)
    parser.add_argument("--participation-rate", type=float, default=0.05)
    parser.add_argument("--latency-steps", type=int, default=1)
    parser.add_argument("--market-impact", type=float, default=0.15)
    parser.add_argument("--base-slippage-range-multiplier", type=float, default=0.02)
    args = parser.parse_args()

    files = discover_ohlcv_files(args.data_dir, args.glob)
    if not files:
        raise FileNotFoundError(f"No CSV files matched {args.glob!r} under {args.data_dir!r}")

    summary = summarize_execution_calibration(
        files,
        ExecutionCalibrationConfig(
            commission_bps=args.commission_bps,
            spread_bps=args.spread_bps,
            participation_rate=args.participation_rate,
            latency_steps=args.latency_steps,
            market_impact=args.market_impact,
            base_slippage_range_multiplier=args.base_slippage_range_multiplier,
        ),
    )
    write_calibration_json(summary, args.output)
    write_calibration_markdown(summary, args.markdown_output)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    print(summary["diagnostics"]["identification_warning"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
