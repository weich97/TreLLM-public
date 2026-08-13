from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.tools.calibration import (
    QuoteFillCalibrationConfig,
    summarize_quote_fill_calibration,
    write_quote_fill_calibration_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fit TreLLM execution parameters from top-of-book quotes and realized fills."
    )
    parser.add_argument("--quotes", default="data/public/microstructure_sample/quotes.csv")
    parser.add_argument("--fills", default="data/public/microstructure_sample/fills.csv")
    parser.add_argument("--output", default="docs/results/execution_quote_fill_calibration_sample.json")
    parser.add_argument("--markdown-output", default="docs/results/execution_quote_fill_calibration_sample.md")
    parser.add_argument("--commission-bps-default", type=float, default=1.0)
    parser.add_argument("--volatility-multiplier", type=float, default=0.1)
    args = parser.parse_args()

    summary = summarize_quote_fill_calibration(
        args.quotes,
        args.fills,
        QuoteFillCalibrationConfig(
            commission_bps_default=args.commission_bps_default,
            volatility_multiplier=args.volatility_multiplier,
        ),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_quote_fill_calibration_markdown(summary, args.markdown_output)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    print(
        "Suggested config: "
        + ", ".join(f"{key}={value}" for key, value in summary["suggested_simulator_config"].items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
