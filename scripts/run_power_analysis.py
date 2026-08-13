"""Bootstrap power curves for paired matrix comparisons.

Answers "how many seeds do we need" before spending provider budget: given an
observed (or hypothesized) paired-delta distribution, estimate the probability
that the paired sign-flip permutation test detects the effect at each
repeat-count level.

Two modes:

- Synthetic: power vs standardized effect size (Cohen's d) using gaussian
  deltas. No data required.

  python scripts/run_power_analysis.py --output docs/results/power_curves.csv

- Empirical: resample observed paired deltas from a metrics CSV produced by a
  matrix or paper run.

  python scripts/run_power_analysis.py \
    --metrics-csv outputs/paper/tables/metrics.csv \
    --candidate risk_aware_realistic_agent --baseline buy_and_hold_realistic \
    --metric total_return --output docs/results/power_curves_empirical.csv
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.statistics import paired_cohens_d, paired_permutation_p_value

DEFAULT_REPEAT_LEVELS = (5, 10, 20, 30)
DEFAULT_EFFECT_SIZES = (0.2, 0.5, 0.8, 1.2)


def estimate_power_from_deltas(
    deltas: list[float],
    n: int,
    *,
    alpha: float = 0.05,
    draws: int = 400,
    permutation_draws: int = 1000,
    seed: int = 2026,
) -> float:
    """Probability that a resampled n-pair study rejects at alpha."""

    rng = random.Random(seed)
    hits = 0
    for _ in range(max(1, draws)):
        sample = [deltas[rng.randrange(len(deltas))] for _ in range(n)]
        p_value = paired_permutation_p_value(sample, draws=permutation_draws, seed=rng.randrange(2**31))
        if p_value is not None and p_value < alpha:
            hits += 1
    return hits / max(1, draws)


def estimate_power_synthetic(
    effect_size: float,
    n: int,
    *,
    alpha: float = 0.05,
    draws: int = 400,
    permutation_draws: int = 1000,
    seed: int = 2026,
) -> float:
    """Power for gaussian paired deltas with mean = effect_size and sd = 1."""

    rng = random.Random(seed)
    hits = 0
    for _ in range(max(1, draws)):
        sample = [rng.gauss(effect_size, 1.0) for _ in range(n)]
        p_value = paired_permutation_p_value(sample, draws=permutation_draws, seed=rng.randrange(2**31))
        if p_value is not None and p_value < alpha:
            hits += 1
    return hits / max(1, draws)


def load_paired_deltas(
    csv_path: Path,
    *,
    candidate: str,
    baseline: str,
    metric: str,
    case_column: str = "case",
    seed_column: str = "seed",
) -> list[float]:
    """Match candidate and baseline rows by seed and return their metric deltas."""

    candidate_by_seed: dict[str, float] = {}
    baseline_by_seed: dict[str, float] = {}
    with csv_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            case = str(row.get(case_column, ""))
            seed = str(row.get(seed_column, ""))
            try:
                value = float(row.get(metric, ""))
            except (TypeError, ValueError):
                continue
            base_case = case.rsplit("_seed", 1)[0] if "_seed" in case else case
            if base_case == candidate or case == candidate:
                candidate_by_seed[seed] = value
            elif base_case == baseline or case == baseline:
                baseline_by_seed[seed] = value
    shared = sorted(set(candidate_by_seed) & set(baseline_by_seed), key=str)
    return [candidate_by_seed[seed] - baseline_by_seed[seed] for seed in shared]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate paired-test power curves for repeat-count planning.")
    parser.add_argument("--metrics-csv", default="", help="Optional per-seed metrics CSV for empirical mode.")
    parser.add_argument("--candidate", default="", help="Candidate case name in the metrics CSV.")
    parser.add_argument("--baseline", default="", help="Baseline case name in the metrics CSV.")
    parser.add_argument("--metric", default="total_return")
    parser.add_argument("--case-column", default="case")
    parser.add_argument("--seed-column", default="seed")
    parser.add_argument(
        "--repeat-levels",
        default=",".join(str(level) for level in DEFAULT_REPEAT_LEVELS),
        help="Comma-separated repeat counts (seeds) to evaluate.",
    )
    parser.add_argument(
        "--effect-sizes",
        default=",".join(str(size) for size in DEFAULT_EFFECT_SIZES),
        help="Comma-separated standardized effect sizes for synthetic mode.",
    )
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--draws", type=int, default=400, help="Resampling draws per power estimate.")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", default="docs/results/power_curves.csv")
    parser.add_argument("--markdown-output", default="", help="Optional markdown table path.")
    args = parser.parse_args(argv)

    repeat_levels = [int(level.strip()) for level in args.repeat_levels.split(",") if level.strip()]
    rows: list[dict[str, Any]] = []

    if args.metrics_csv:
        if not args.candidate or not args.baseline:
            parser.error("--metrics-csv mode requires --candidate and --baseline")
        deltas = load_paired_deltas(
            ROOT / args.metrics_csv if not Path(args.metrics_csv).is_absolute() else Path(args.metrics_csv),
            candidate=args.candidate,
            baseline=args.baseline,
            metric=args.metric,
            case_column=args.case_column,
            seed_column=args.seed_column,
        )
        if len(deltas) < 2:
            raise SystemExit(
                f"Found {len(deltas)} paired deltas for candidate={args.candidate} vs baseline={args.baseline}; need at least 2."
            )
        observed_d = paired_cohens_d(deltas)
        for n in repeat_levels:
            power = estimate_power_from_deltas(deltas, n, alpha=args.alpha, draws=args.draws, seed=args.seed)
            rows.append(
                {
                    "mode": "empirical",
                    "effect_label": f"{args.candidate} vs {args.baseline} ({args.metric})",
                    "observed_cohens_d": observed_d,
                    "repeat_count": n,
                    "alpha": args.alpha,
                    "power": power,
                    "source_pairs": len(deltas),
                }
            )
    else:
        effect_sizes = [float(size.strip()) for size in args.effect_sizes.split(",") if size.strip()]
        for effect_size in effect_sizes:
            for n in repeat_levels:
                power = estimate_power_synthetic(effect_size, n, alpha=args.alpha, draws=args.draws, seed=args.seed)
                rows.append(
                    {
                        "mode": "synthetic",
                        "effect_label": f"cohens_d={effect_size}",
                        "observed_cohens_d": effect_size,
                        "repeat_count": n,
                        "alpha": args.alpha,
                        "power": power,
                        "source_pairs": "",
                    }
                )

    output_path = ROOT / args.output if not Path(args.output).is_absolute() else Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["mode", "effect_label", "observed_cohens_d", "repeat_count", "alpha", "power", "source_pairs"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} power rows to {output_path}")

    if args.markdown_output:
        markdown_path = ROOT / args.markdown_output if not Path(args.markdown_output).is_absolute() else Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Paired-Test Power Curves",
            "",
            "Probability that the paired sign-flip permutation test rejects at"
            f" alpha={args.alpha}, by repeat count. Use this to budget seeds and"
            " provider samples before running a matrix.",
            "",
            "| Mode | Effect | Cohen's d | Repeats | Power |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for row in rows:
            cohens = row["observed_cohens_d"]
            cohens_text = f"{float(cohens):.2f}" if cohens not in ("", None) else ""
            lines.append(
                f"| {row['mode']} | {row['effect_label']} | {cohens_text} | {row['repeat_count']} | {float(row['power']):.3f} |"
            )
        markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote markdown table to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
