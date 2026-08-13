from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tradearena.experiments.paper import PaperExperimentConfig, _intraday_complex_rows
from tradearena.experiments.reporting import write_csv, write_markdown_table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild 51-stock intraday tables and raw trajectories from tracked data plus the tracked LLM cache."
    )
    parser.add_argument("--output-dir", default="outputs/tradearena_paper")
    parser.add_argument("--cache", default="data/llm_cache/deepseek_analyst.jsonl")
    parser.add_argument("--provider", default="poe", choices=["poe", "deepseek"])
    parser.add_argument("--models", default="gpt-5.5,gemini-3.1-pro")
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--intraday-periods", type=int, default=40)
    parser.add_argument("--no-llm", action="store_true", help="Rebuild only deterministic and Markowitz intraday rows.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    models = tuple(model.strip() for model in args.models.split(",") if model.strip())
    config = PaperExperimentConfig(
        output_dir=args.output_dir,
        llm_cache_path=args.cache,
        include_intraday_llm_probe=not args.no_llm,
        intraday_llm_provider=args.provider,
        intraday_llm_models=models,
        intraday_llm_max_periods=args.steps,
        intraday_max_periods=args.intraday_periods,
    )
    intraday = _intraday_complex_rows(config)
    tables = Path(args.output_dir) / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    write_csv(tables / "intraday_complex.csv", intraday["case_rows"])
    write_markdown_table(
        tables / "intraday_complex.md",
        intraday["case_rows"],
        [
            "case",
            "model",
            "symbols",
            "steps",
            "total_return",
            "sharpe",
            "max_drawdown",
            "risk_clipped_decisions",
            "correlation_mean_abs",
            "effective_assets",
            "mean_herfindahl",
        ],
    )
    write_csv(tables / "intraday_correlation.csv", intraday["correlation_rows"])
    if intraday["blind_spot_rows"]:
        write_csv(tables / "intraday_blind_spots.csv", intraday["blind_spot_rows"])
        write_markdown_table(
            tables / "intraday_blind_spots.md",
            intraday["blind_spot_rows"],
            [
                "case",
                "model",
                "step",
                "pair",
                "correlation",
                "combined_intended_weight",
                "approved_pair_weight",
                "clipped_count",
                "rationale_theme",
            ],
        )
    print(f"Rebuilt {len(intraday['case_rows'])} intraday rows under {args.output_dir}")
    print(f"Raw trajectories are under {Path(args.output_dir) / 'raw'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
