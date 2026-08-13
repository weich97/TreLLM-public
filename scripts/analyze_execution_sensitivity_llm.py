"""Merge per-model execution-sensitivity sweeps and run the LLM-vs-classical analysis.

The full LLM matrix runs as one sweep process per model (parallelism +
independent checkpoints), each directory containing the same deterministic
baselines plus one LLM agent. This script merges those runs, deduplicates the
shared baseline rows, and produces the study's headline tables:

1. merged per-(scenario, level) leaderboards with every agent;
2. ranking stability (Kendall tau-b, top-k Jaccard) between execution levels
   with LLM agents included;
3. idealization bias per agent: how much return/fill quality the idealized
   execution level overstates relative to stressed levels;
4. friction-fragility difference-in-differences: per seed,
   (LLM at E0 - LLM at stressed) minus (baseline at E0 - baseline at
   stressed), paired tests with BH-FDR - does friction hurt LLM agents more
   than the classical anchor?

Usage:

  python scripts/analyze_execution_sensitivity_llm.py \
    --input-dirs outputs/execution_sensitivity_llm/gpt_5_5,outputs/execution_sensitivity_llm/gemini_3_1_pro \
    --output-dir docs/results/execution_sensitivity_llm
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.statistics import (
    benjamini_hochberg,
    kendall_tau,
    mean,
    paired_bootstrap_difference,
    summarize_metric,
    top_k_jaccard,
    variance_components,
)

RANK_METRIC = "sharpe"
IDEAL_LEVEL = "E0_ideal"
DEFAULT_STRESS_LEVELS = ("E1_default_stress", "E2_harsh_corner")
DEFAULT_DID_BASELINE = "buy-and-hold"
RELEASED_RUN_FIELDS = (
    "scenario",
    "level",
    "agent",
    "seed",
    "sample",
    "total_return",
    "sharpe",
    "max_drawdown",
    "execution_fill_rate",
    "total_slippage_cost",
)


def load_merged_runs(input_dirs: list[Path]) -> list[dict[str, Any]]:
    """Read every runs CSV and deduplicate identical (scenario, level, agent, seed, sample) rows."""

    merged: dict[tuple[str, str, str, int, int], dict[str, Any]] = {}
    for directory in input_dirs:
        path = directory / "execution_sensitivity_runs.csv"
        if not path.exists():
            raise SystemExit(f"Missing runs CSV: {path}")
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (
                    str(row["scenario"]),
                    str(row["level"]),
                    str(row["agent"]),
                    int(row["seed"]),
                    int(row.get("sample", 0) or 0),
                )
                merged.setdefault(key, row)
    return list(merged.values())


def load_existing_merged_runs(path: Path) -> list[dict[str, Any]]:
    """Load an exact released snapshot while preserving provider samples.

    Unlike the multi-directory merger, a released snapshot must already be
    canonical: one row per scenario/level/agent/seed/sample key, the frozen
    public schema, and finite numeric metrics. Silently accepting duplicate or
    malformed rows would change cell weights during reanalysis.
    """

    if not path.exists():
        raise SystemExit(f"Missing merged runs CSV: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        if set(fields) != set(RELEASED_RUN_FIELDS) or len(fields) != len(RELEASED_RUN_FIELDS):
            missing = sorted(set(RELEASED_RUN_FIELDS) - set(fields))
            extra = sorted(set(fields) - set(RELEASED_RUN_FIELDS))
            raise SystemExit(
                f"Unexpected merged-runs schema in {path}: missing={missing}, extra={extra}"
            )
        rows = list(reader)

    seen: set[tuple[str, str, str, int, int]] = set()
    numeric_fields = RELEASED_RUN_FIELDS[5:]
    for line_number, row in enumerate(rows, start=2):
        for field in RELEASED_RUN_FIELDS[:3]:
            if not str(row.get(field, "")).strip():
                raise SystemExit(f"Blank {field} in {path}:{line_number}")
        try:
            seed = int(row["seed"])
            sample = int(row["sample"])
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"Invalid seed/sample in {path}:{line_number}") from exc
        if seed < 0 or sample < 0:
            raise SystemExit(f"Negative seed/sample in {path}:{line_number}")
        for field in numeric_fields:
            try:
                value = float(row[field])
            except (TypeError, ValueError) as exc:
                raise SystemExit(f"Invalid {field} in {path}:{line_number}") from exc
            if not math.isfinite(value):
                raise SystemExit(f"Non-finite {field} in {path}:{line_number}")
        key = (str(row["scenario"]), str(row["level"]), str(row["agent"]), seed, sample)
        if key in seen:
            raise SystemExit(f"Duplicate merged-run key in {path}: {key}")
        seen.add(key)
    return rows


def _seed_scores(rows: list[dict[str, Any]], metric: str) -> dict[tuple[str, str, str, int], float]:
    """Per (scenario, level, agent, seed) metric, averaging provider samples."""

    grouped: dict[tuple[str, str, str, int], list[float]] = {}
    for row in rows:
        key = (str(row["scenario"]), str(row["level"]), str(row["agent"]), int(row["seed"]))
        grouped.setdefault(key, []).append(float(row[metric]))
    return {key: mean(values) for key, values in grouped.items()}


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_cell: dict[tuple[str, str, str], list[float]] = {}
    fill_by_cell: dict[tuple[str, str, str], list[float]] = {}
    return_by_cell: dict[tuple[str, str, str], list[float]] = {}
    for (scenario, level, agent, _seed), value in _seed_scores(rows, RANK_METRIC).items():
        by_cell.setdefault((scenario, level, agent), []).append(value)
    for (scenario, level, agent, _seed), value in _seed_scores(rows, "total_return").items():
        return_by_cell.setdefault((scenario, level, agent), []).append(value)
    for row in rows:
        if row.get("execution_fill_rate") not in ("", None):
            fill_by_cell.setdefault((str(row["scenario"]), str(row["level"]), str(row["agent"])), []).append(
                float(row["execution_fill_rate"])
            )
    output: list[dict[str, Any]] = []
    for (scenario, level, agent), values in sorted(by_cell.items()):
        record = {
            "scenario": scenario,
            "level": level,
            "agent": agent,
            "agent_type": "llm" if ":" in agent else "classical",
            "seed_count": len(values),
            **summarize_metric(values, prefix=RANK_METRIC),
            "return_mean": mean(return_by_cell.get((scenario, level, agent), [0.0])),
            "fill_rate_mean": mean(fill_by_cell[(scenario, level, agent)])
            if (scenario, level, agent) in fill_by_cell
            else None,
            "rank": None,
        }
        output.append(record)
    cells: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in output:
        cells.setdefault((record["scenario"], record["level"]), []).append(record)
    for records in cells.values():
        records.sort(key=lambda item: -float(item[f"{RANK_METRIC}_mean"]))
        for position, record in enumerate(records, start=1):
            record["rank"] = position
    return output


def stability_rows(aggregates: list[dict[str, Any]], *, top_k: int = 3) -> list[dict[str, Any]]:
    scores: dict[tuple[str, str], dict[str, float]] = {}
    for record in aggregates:
        scores.setdefault((record["scenario"], record["level"]), {})[record["agent"]] = float(
            record[f"{RANK_METRIC}_mean"]
        )
    output = []
    scenarios = sorted({scenario for scenario, _ in scores})
    for scenario in scenarios:
        levels = sorted(level for cell_scenario, level in scores if cell_scenario == scenario)
        for i in range(len(levels)):
            for j in range(i + 1, len(levels)):
                left = scores[(scenario, levels[i])]
                right = scores[(scenario, levels[j])]
                output.append(
                    {
                        "scenario": scenario,
                        "level_a": levels[i],
                        "level_b": levels[j],
                        "agent_count": len(set(left) & set(right)),
                        "kendall_tau": kendall_tau(left, right),
                        f"top_{top_k}_jaccard": top_k_jaccard(left, right, k=top_k),
                    }
                )
    return output


def fragility_did_rows(
    rows: list[dict[str, Any]],
    *,
    baseline_agent: str = DEFAULT_DID_BASELINE,
    stress_levels: tuple[str, ...] = DEFAULT_STRESS_LEVELS,
) -> list[dict[str, Any]]:
    """Difference-in-differences: does friction cost the agent more than the baseline anchor?

    Per seed and scenario: (agent at E0 - agent at stressed) minus
    (baseline at E0 - baseline at stressed), on total_return. Positive deltas
    mean the agent loses more to friction than the baseline.
    """

    seed_returns = _seed_scores(rows, "total_return")
    agents = sorted({str(row["agent"]) for row in rows if str(row["agent"]) != baseline_agent})
    scenarios = sorted({str(row["scenario"]) for row in rows})
    output: list[dict[str, Any]] = []
    for stress_level in stress_levels:
        for agent in agents:
            did_by_key: dict[tuple[str, int], float] = {}
            for scenario in scenarios:
                seeds = {
                    seed
                    for (cell_scenario, level, cell_agent, seed) in seed_returns
                    if cell_scenario == scenario and cell_agent == agent and level == IDEAL_LEVEL
                }
                for seed in seeds:
                    try:
                        agent_drop = (
                            seed_returns[(scenario, IDEAL_LEVEL, agent, seed)]
                            - seed_returns[(scenario, stress_level, agent, seed)]
                        )
                        baseline_drop = (
                            seed_returns[(scenario, IDEAL_LEVEL, baseline_agent, seed)]
                            - seed_returns[(scenario, stress_level, baseline_agent, seed)]
                        )
                    except KeyError:
                        continue
                    did_by_key[(scenario, seed)] = agent_drop - baseline_drop
            if not did_by_key:
                continue
            result = paired_bootstrap_difference(did_by_key, dict.fromkeys(did_by_key, 0.0))
            output.append(
                {
                    "agent": agent,
                    "agent_type": "llm" if ":" in agent else "classical",
                    "stress_level": stress_level,
                    "baseline": baseline_agent,
                    "paired_n": result["paired_n"],
                    "mean_did": result["mean_delta"],
                    "did_ci_low": result["delta_ci_low"],
                    "did_ci_high": result["delta_ci_high"],
                    "permutation_p_value": result["permutation_p_value"],
                    "q_value": None,
                    "cohens_d": result["cohens_d"],
                }
            )
    q_values = benjamini_hochberg({index: row["permutation_p_value"] for index, row in enumerate(output)})
    for index, row in enumerate(output):
        row["q_value"] = q_values[index]
    return output


def sampling_variance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Between-seed (market path) vs within-seed (provider sampling) variance.

    Only cells where at least one seed carries repeated provider samples are
    reported; deterministic agents never qualify. A small within-seed share
    means conclusions ride on market variation, not provider stochasticity.
    """

    grouped: dict[tuple[str, str, str], dict[int, list[float]]] = {}
    for row in rows:
        agent = str(row["agent"])
        if ":" not in agent:
            continue
        key = (str(row["scenario"]), str(row["level"]), agent)
        grouped.setdefault(key, {}).setdefault(int(row["seed"]), []).append(float(row["total_return"]))
    output = []
    for (scenario, level, agent), by_seed in sorted(grouped.items()):
        if not any(len(values) >= 2 for values in by_seed.values()):
            continue
        components = variance_components(by_seed)
        output.append(
            {
                "scenario": scenario,
                "level": level,
                "agent": agent,
                "metric": "total_return",
                "seed_count": components["group_count"],
                "total_runs": components["total_n"],
                "between_seed_variance": components["between_group_variance"],
                "within_seed_variance": components["within_group_variance"],
                "within_seed_share": components["within_group_share"],
            }
        )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge per-model sweeps and analyze LLM execution sensitivity.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-dirs", help="Comma-separated sweep output directories.")
    source.add_argument(
        "--merged-runs",
        help="Released merged_runs.csv to reanalyze while preserving repeat-provider samples.",
    )
    parser.add_argument("--output-dir", default="docs/results/execution_sensitivity_llm")
    parser.add_argument("--did-baseline", default=DEFAULT_DID_BASELINE)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args(argv)

    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.merged_runs:
        merged_path = Path(args.merged_runs)
        if not merged_path.is_absolute():
            merged_path = ROOT / merged_path
        rows = load_existing_merged_runs(merged_path)
        source_label = f"released snapshot {merged_path}"
    else:
        assert args.input_dirs is not None
        input_dirs = [
            Path(item) if Path(item).is_absolute() else ROOT / item
            for item in args.input_dirs.split(",")
            if item.strip()
        ]
        rows = load_merged_runs(input_dirs)
        source_label = f"{len(input_dirs)} sweeps"
    aggregates = aggregate_rows(rows)
    stability = stability_rows(aggregates, top_k=args.top_k)
    fragility = fragility_did_rows(rows, baseline_agent=args.did_baseline)
    sampling_variance = sampling_variance_rows(rows)

    _write_csv(
        output_dir / "merged_runs.csv",
        rows,
        ["scenario", "level", "agent", "seed", "sample", "total_return", "sharpe", "max_drawdown", "execution_fill_rate", "total_slippage_cost"],
    )
    _write_csv(
        output_dir / "merged_aggregate.csv",
        aggregates,
        [
            "scenario",
            "level",
            "agent",
            "agent_type",
            "seed_count",
            f"{RANK_METRIC}_mean",
            f"{RANK_METRIC}_std",
            f"{RANK_METRIC}_ci_low",
            f"{RANK_METRIC}_ci_high",
            "return_mean",
            "fill_rate_mean",
            "rank",
        ],
    )
    _write_csv(
        output_dir / "rank_stability.csv",
        stability,
        ["scenario", "level_a", "level_b", "agent_count", "kendall_tau", f"top_{args.top_k}_jaccard"],
    )
    _write_csv(
        output_dir / "fragility_did.csv",
        fragility,
        [
            "agent",
            "agent_type",
            "stress_level",
            "baseline",
            "paired_n",
            "mean_did",
            "did_ci_low",
            "did_ci_high",
            "permutation_p_value",
            "q_value",
            "cohens_d",
        ],
    )
    if sampling_variance:
        _write_csv(
            output_dir / "sampling_variance.csv",
            sampling_variance,
            [
                "scenario",
                "level",
                "agent",
                "metric",
                "seed_count",
                "total_runs",
                "between_seed_variance",
                "within_seed_variance",
                "within_seed_share",
            ],
        )
    _write_markdown(
        output_dir / "execution_sensitivity_llm.md",
        aggregates,
        stability,
        fragility,
        sampling_variance,
        top_k=args.top_k,
    )
    print(
        f"Analyzed {len(rows)} runs from {source_label} -> {len(aggregates)} cells, "
        f"{len(stability)} stability pairs, {len(fragility)} DiD rows, "
        f"{len(sampling_variance)} sampling-variance cells in {output_dir}"
    )
    return 0


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(
    path: Path,
    aggregates: list[dict[str, Any]],
    stability: list[dict[str, Any]],
    fragility: list[dict[str, Any]],
    sampling_variance: list[dict[str, Any]] | None = None,
    *,
    top_k: int,
) -> None:
    lines = [
        "# Execution Sensitivity With LLM Agents",
        "",
        "Provider-routed LLM agents and deterministic baselines in identical",
        "(scenario, execution level, seed) cells. Positive friction-fragility",
        "DiD means the agent loses more return to execution frictions than the",
        "baseline anchor does on the same market paths.",
        "",
        "## Friction Fragility (DiD vs baseline, BH-FDR)",
        "",
        "| Agent | Type | Stress level | Mean DiD | 95% CI | q | Cohen's d |",
        "| --- | --- | --- | ---: | --- | ---: | ---: |",
    ]
    for row in fragility:
        ci = (
            f"[{float(row['did_ci_low']):+.4f}, {float(row['did_ci_high']):+.4f}]"
            if row["did_ci_low"] is not None
            else ""
        )
        q_text = f"{float(row['q_value']):.4f}" if row["q_value"] is not None else ""
        d_text = f"{float(row['cohens_d']):.2f}" if row["cohens_d"] is not None else ""
        lines.append(
            f"| {row['agent']} | {row['agent_type']} | {row['stress_level']} "
            f"| {float(row['mean_did']):+.4f} | {ci} | {q_text} | {d_text} |"
        )
    if sampling_variance:
        lines += [
            "",
            "## Provider-Sampling Variance Decomposition",
            "",
            "Within-seed share is the fraction of total-return variance due to",
            "provider sampling at a fixed market path; the remainder is market",
            "variation across seeds.",
            "",
            "| Scenario | Level | Agent | Seeds | Runs | Within-seed share |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
        for row in sampling_variance:
            share = row["within_seed_share"]
            share_text = f"{float(share):.3f}" if share is not None else ""
            lines.append(
                f"| {row['scenario']} | {row['level']} | {row['agent']} "
                f"| {row['seed_count']} | {row['total_runs']} | {share_text} |"
            )
    lines += [
        "",
        "## Ranking Stability Between Levels",
        "",
        f"| Scenario | Level A | Level B | Kendall tau | Top-{top_k} Jaccard |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in stability:
        tau = row["kendall_tau"]
        jaccard = row[f"top_{top_k}_jaccard"]
        lines.append(
            f"| {row['scenario']} | {row['level_a']} | {row['level_b']} "
            f"| {f'{float(tau):.3f}' if tau is not None else ''} "
            f"| {f'{float(jaccard):.3f}' if jaccard is not None else ''} |"
        )
    lines += [
        "",
        "## Per-Level Leaderboards",
        "",
        "| Scenario | Level | Rank | Agent | Type | Sharpe mean | Return mean | Fill rate |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | ---: |",
    ]
    ordered = sorted(aggregates, key=lambda row: (row["scenario"], row["level"], int(row["rank"])))
    for row in ordered:
        fill = f"{float(row['fill_rate_mean']):.2f}" if row["fill_rate_mean"] is not None else ""
        lines.append(
            f"| {row['scenario']} | {row['level']} | {row['rank']} | {row['agent']} | {row['agent_type']} "
            f"| {float(row[f'{RANK_METRIC}_mean']):.3f} | {float(row['return_mean']):.4f} | {fill} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
