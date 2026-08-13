from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.statistics import (
    benjamini_hochberg,
    mean,
    paired_bootstrap_difference,
    summarize_metric,
)
from tradearena.factory import build_default_system

PROTOCOL_ID = "trellm-v0.3-protocol"
SCENARIO_ID = "synthetic_memory_contamination_c0_v0_3"
CONTAMINATION_TIER = "C0"
DEFAULT_KINDS = ("fake_rejections", "fake_violations")
DEFAULT_DOSES = (0.0, 0.5)
DEFAULT_DECAYS = (1.0, 0.6)
DEFAULT_RISKS = ("max-position",)
DEFAULT_SEEDS = (7, 11)
PRIMARY_OUTCOME = "memory_driven_leverage_amplification"
OUTCOMES = (
    "memory_pollution_ratio",
    "memory_driven_leverage_amplification",
    "max_memory_driven_leverage_amplification",
    "total_return",
    "max_drawdown",
    "risk_violation_count",
)
ROW_FIELDS = [
    "protocol_id",
    "scenario_id",
    "contamination_tier",
    "memory_contamination_kind",
    "memory_contamination_dose",
    "memory_decay_rate",
    "risk_manager",
    "seed",
    *OUTCOMES,
    "evidence_tier",
    "claim_scope",
]
AGGREGATE_FIELDS = [
    "protocol_id",
    "scenario_id",
    "contamination_tier",
    "memory_contamination_kind",
    "memory_contamination_dose",
    "memory_decay_rate",
    "risk_manager",
    "run_count",
    "memory_pollution_ratio_mean",
    "memory_pollution_ratio_std",
    "memory_pollution_ratio_ci_low",
    "memory_pollution_ratio_ci_high",
    "memory_driven_leverage_amplification_mean",
    "memory_driven_leverage_amplification_std",
    "memory_driven_leverage_amplification_ci_low",
    "memory_driven_leverage_amplification_ci_high",
    "max_memory_driven_leverage_amplification_mean",
    "total_return_mean",
    "max_drawdown_mean",
    "risk_violation_count_mean",
]
RESPONSE_FIELDS = [
    "protocol_id",
    "scenario_id",
    "contamination_tier",
    "memory_contamination_kind",
    "memory_decay_rate",
    "risk_manager",
    "memory_contamination_dose",
    "outcome",
    "paired_n",
    "mean_delta_vs_dose0",
    "delta_ci_low",
    "delta_ci_high",
    "permutation_p_value",
    "q_value",
    "cohens_d",
]
CONTROL_FIELDS = [
    "protocol_id",
    "contamination_tier",
    "tier_name",
    "status_in_this_artifact",
    "required_controls",
    "claim_scope",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the TreLLM v0.3 memory-contamination protocol artifact."
    )
    parser.add_argument("--output-dir", default="docs/results/v0_3_memory_contamination")
    parser.add_argument("--kinds", default=",".join(DEFAULT_KINDS))
    parser.add_argument("--doses", default=",".join(str(dose) for dose in DEFAULT_DOSES))
    parser.add_argument("--decays", default=",".join(str(decay) for decay in DEFAULT_DECAYS))
    parser.add_argument("--risks", default=",".join(DEFAULT_RISKS))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--periods", type=int, default=24)
    parser.add_argument("--symbols", default="SYN,ALT")
    args = parser.parse_args(argv)

    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    kinds = _parse_list(args.kinds, "kinds")
    doses = _parse_floats(args.doses, "doses", require_zero=True)
    decays = _parse_floats(args.decays, "decays")
    risks = _parse_list(args.risks, "risks")
    seeds = _parse_ints(args.seeds, "seeds")
    symbols = tuple(_parse_list(args.symbols, "symbols"))

    rows = [
        _run_case(
            kind=kind,
            dose=dose,
            decay=decay,
            risk=risk,
            seed=seed,
            periods=args.periods,
            symbols=symbols,
        )
        for kind in kinds
        for dose in doses
        for decay in decays
        for risk in risks
        for seed in seeds
    ]
    aggregate_rows = _aggregate_rows(rows)
    response_rows = _dose_response_rows(rows)
    control_rows = _contamination_control_rows()
    summary = _summary(
        rows,
        aggregate_rows,
        response_rows,
        control_rows,
        kinds=kinds,
        doses=doses,
        decays=decays,
        risks=risks,
        seeds=seeds,
        periods=args.periods,
        symbols=symbols,
    )

    _write_csv(output_dir / "memory_contamination_rows.csv", rows, ROW_FIELDS)
    _write_csv(output_dir / "memory_contamination_aggregate.csv", aggregate_rows, AGGREGATE_FIELDS)
    _write_csv(output_dir / "memory_contamination_dose_response.csv", response_rows, RESPONSE_FIELDS)
    _write_csv(output_dir / "contamination_tier_controls.csv", control_rows, CONTROL_FIELDS)
    _write_json(output_dir / "memory_contamination_summary.json", summary)
    (output_dir / "memory_contamination_summary.md").write_text(
        _summary_markdown(summary, aggregate_rows, response_rows, control_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display_path(output_dir / 'memory_contamination_rows.csv')}")
    print(f"Wrote {_display_path(output_dir / 'memory_contamination_aggregate.csv')}")
    print(f"Wrote {_display_path(output_dir / 'memory_contamination_dose_response.csv')}")
    print(f"Wrote {_display_path(output_dir / 'contamination_tier_controls.csv')}")
    print(f"Wrote {_display_path(output_dir / 'memory_contamination_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'memory_contamination_summary.md')}")
    print(f"Rows: {len(rows)}")
    return 0


def _run_case(
    *,
    kind: str,
    dose: float,
    decay: float,
    risk: str,
    seed: int,
    periods: int,
    symbols: tuple[str, ...],
) -> dict[str, Any]:
    pollution_kwargs: dict[str, Any] = {}
    if dose > 0.0:
        pollution_kwargs = {
            "memory_pollution_kind": kind,
            "memory_pollution_dose": dose,
            "memory_pollution_seed": seed,
        }
    _, metrics = build_default_system(
        name=f"v03_memory_contamination_{kind}_{dose}_{decay}_{risk}_{seed}",
        symbols=symbols,
        periods=periods,
        seed=seed,
        strategy_name="memory-aware",
        analyst_names=("momentum", "macro-news"),
        risk_name=risk,
        memory_decay_rate=decay,
        **pollution_kwargs,
    ).run()
    row = {
        "protocol_id": PROTOCOL_ID,
        "scenario_id": SCENARIO_ID,
        "contamination_tier": CONTAMINATION_TIER,
        "memory_contamination_kind": kind,
        "memory_contamination_dose": dose,
        "memory_decay_rate": decay,
        "risk_manager": risk,
        "seed": seed,
        "evidence_tier": "protocol-fixture",
        "claim_scope": "C0 memory-contamination mechanism fixture; not model-performance or trading-profit evidence.",
    }
    for outcome in OUTCOMES:
        row[outcome] = _round(metrics.get(outcome, 0.0))
    return row


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float, float, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["memory_contamination_kind"]),
            float(row["memory_contamination_dose"]),
            float(row["memory_decay_rate"]),
            str(row["risk_manager"]),
        )
        grouped.setdefault(key, []).append(row)
    output: list[dict[str, Any]] = []
    for (kind, dose, decay, risk), group in sorted(grouped.items()):
        pollution_stats = summarize_metric((float(row["memory_pollution_ratio"]) for row in group), prefix="memory_pollution_ratio")
        leverage_stats = summarize_metric(
            (float(row["memory_driven_leverage_amplification"]) for row in group),
            prefix="memory_driven_leverage_amplification",
        )
        output.append(
            {
                "protocol_id": PROTOCOL_ID,
                "scenario_id": SCENARIO_ID,
                "contamination_tier": CONTAMINATION_TIER,
                "memory_contamination_kind": kind,
                "memory_contamination_dose": dose,
                "memory_decay_rate": decay,
                "risk_manager": risk,
                "run_count": len(group),
                **{key: _nullable_round(value) for key, value in pollution_stats.items()},
                **{key: _nullable_round(value) for key, value in leverage_stats.items()},
                "max_memory_driven_leverage_amplification_mean": _mean_metric(group, "max_memory_driven_leverage_amplification"),
                "total_return_mean": _mean_metric(group, "total_return"),
                "max_drawdown_mean": _mean_metric(group, "max_drawdown"),
                "risk_violation_count_mean": _mean_metric(group, "risk_violation_count"),
            }
        )
    return output


def _dose_response_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_cell: dict[tuple[str, float, str, float], dict[int, dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["memory_contamination_kind"]),
            float(row["memory_decay_rate"]),
            str(row["risk_manager"]),
            float(row["memory_contamination_dose"]),
        )
        by_cell.setdefault(key, {})[int(row["seed"])] = row
    output: list[dict[str, Any]] = []
    for (kind, decay, risk, dose), runs_by_seed in sorted(by_cell.items()):
        if dose == 0.0:
            continue
        baseline = by_cell.get((kind, decay, risk, 0.0), {})
        if not baseline:
            continue
        for outcome in OUTCOMES:
            candidate = {seed: float(row[outcome]) for seed, row in runs_by_seed.items()}
            reference = {seed: float(row[outcome]) for seed, row in baseline.items()}
            result = paired_bootstrap_difference(candidate, reference)
            output.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "scenario_id": SCENARIO_ID,
                    "contamination_tier": CONTAMINATION_TIER,
                    "memory_contamination_kind": kind,
                    "memory_decay_rate": decay,
                    "risk_manager": risk,
                    "memory_contamination_dose": dose,
                    "outcome": outcome,
                    "paired_n": result["paired_n"],
                    "mean_delta_vs_dose0": _nullable_round(result["mean_delta"]),
                    "delta_ci_low": _nullable_round(result["delta_ci_low"]),
                    "delta_ci_high": _nullable_round(result["delta_ci_high"]),
                    "permutation_p_value": _nullable_round(result["permutation_p_value"]),
                    "q_value": None,
                    "cohens_d": _nullable_round(result["cohens_d"]),
                }
            )
    q_values = benjamini_hochberg({index: row["permutation_p_value"] for index, row in enumerate(output)})
    for index, row in enumerate(output):
        row["q_value"] = _nullable_round(q_values[index])
    return output


def _contamination_control_rows() -> list[dict[str, Any]]:
    return [
        {
            "protocol_id": PROTOCOL_ID,
            "contamination_tier": "C0",
            "tier_name": "synthetic",
            "status_in_this_artifact": "implemented",
            "required_controls": "repository-generated paths; published seeds; no historical symbol identity",
            "claim_scope": "no-known-training-contamination controlled memory mechanism evaluation",
        },
        {
            "protocol_id": PROTOCOL_ID,
            "contamination_tier": "C1",
            "tier_name": "anonymized_real",
            "status_in_this_artifact": "control-contract-only",
            "required_controls": "symbol anonymization; relative timestamp masking; memorization probe; data hash",
            "claim_scope": "residual contamination risk must be measured before C1 rows support scientific claims",
        },
        {
            "protocol_id": PROTOCOL_ID,
            "contamination_tier": "C2",
            "tier_name": "forward_frozen",
            "status_in_this_artifact": "control-contract-only",
            "required_controls": "dated hash commitment; future evaluation window; no post-freeze scenario edits; walk-forward provenance",
            "claim_scope": "strongest public contamination evidence, not produced by this fixture bundle",
        },
    ]


def _summary(
    rows: list[dict[str, Any]],
    aggregate_rows: list[dict[str, Any]],
    response_rows: list[dict[str, Any]],
    control_rows: list[dict[str, Any]],
    *,
    kinds: list[str],
    doses: list[float],
    decays: list[float],
    risks: list[str],
    seeds: list[int],
    periods: int,
    symbols: tuple[str, ...],
) -> dict[str, Any]:
    primary_rows = [row for row in response_rows if row["outcome"] == PRIMARY_OUTCOME]
    max_effect = max((abs(float(row["mean_delta_vs_dose0"])) for row in primary_rows if row["mean_delta_vs_dose0"] is not None), default=0.0)
    return {
        "schema": "trellm_v0_3_memory_contamination_v0.1",
        "protocol_id": PROTOCOL_ID,
        "scenario_id": SCENARIO_ID,
        "contamination_tier": CONTAMINATION_TIER,
        "contamination_tiers_declared": [row["contamination_tier"] for row in control_rows],
        "implemented_tiers": ["C0"],
        "control_contract_only_tiers": ["C1", "C2"],
        "memory_contamination_kinds": kinds,
        "memory_contamination_doses": doses,
        "memory_decay_rates": decays,
        "risk_managers": risks,
        "seeds": seeds,
        "periods": periods,
        "symbols": list(symbols),
        "row_count": len(rows),
        "aggregate_row_count": len(aggregate_rows),
        "dose_response_row_count": len(response_rows),
        "primary_outcome": PRIMARY_OUTCOME,
        "max_abs_primary_delta_vs_dose0": _round(max_effect),
        "required_metrics": [
            "memory_pollution_ratio",
            "memory_driven_leverage_amplification",
            "paired_bootstrap_delta",
            "BH-FDR q_value",
        ],
        "claim_boundary": (
            "Memory-contamination protocol fixture for C0 mechanism validation. "
            "It quantifies read-time memory pollution effects and tier controls; "
            "it is not model-performance or trading-profit evidence."
        ),
        "artifacts": [
            "memory_contamination_rows.csv",
            "memory_contamination_aggregate.csv",
            "memory_contamination_dose_response.csv",
            "contamination_tier_controls.csv",
            "memory_contamination_summary.json",
            "memory_contamination_summary.md",
        ],
    }


def _summary_markdown(
    summary: dict[str, Any],
    aggregate_rows: list[dict[str, Any]],
    response_rows: list[dict[str, Any]],
    control_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# TreLLM v0.3 Memory Contamination Pilot",
        "",
        "This fixture bundle validates the v0.3 memory-contamination mechanism path.",
        "It is not model-performance or trading-profit evidence.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Scenario: `{summary['scenario_id']}`",
        f"- Implemented tier: `{summary['contamination_tier']}`",
        f"- Declared tiers: `{', '.join(summary['contamination_tiers_declared'])}`",
        f"- Control-contract-only tiers: `{', '.join(summary['control_contract_only_tiers'])}`",
        f"- Kinds: `{', '.join(summary['memory_contamination_kinds'])}`",
        f"- Doses: `{', '.join(str(item) for item in summary['memory_contamination_doses'])}`",
        f"- Decays: `{', '.join(str(item) for item in summary['memory_decay_rates'])}`",
        f"- Primary outcome: `{summary['primary_outcome']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Contamination Tier Controls",
        "",
        "| Tier | Status | Required controls | Claim scope |",
        "| --- | --- | --- | --- |",
    ]
    for row in control_rows:
        lines.append(
            f"| {row['contamination_tier']} | {row['status_in_this_artifact']} | "
            f"{row['required_controls']} | {row['claim_scope']} |"
        )
    lines += [
        "",
        "## Dose Response",
        "",
        "| Kind | Decay | Risk | Dose | Outcome | Delta vs dose 0 | q value | Cohen's d |",
        "| --- | ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in response_rows:
        if row["outcome"] not in {"memory_pollution_ratio", PRIMARY_OUTCOME}:
            continue
        lines.append(
            f"| {row['memory_contamination_kind']} | {row['memory_decay_rate']} | {row['risk_manager']} "
            f"| {row['memory_contamination_dose']} | {row['outcome']} | {_fmt(row['mean_delta_vs_dose0'])} "
            f"| {_fmt(row['q_value'])} | {_fmt(row['cohens_d'])} |"
        )
    lines += [
        "",
        "## Manipulation Check",
        "",
        "| Kind | Dose | Decay | Risk | Runs | Pollution ratio | Leverage amplification |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in aggregate_rows:
        lines.append(
            f"| {row['memory_contamination_kind']} | {row['memory_contamination_dose']} | {row['memory_decay_rate']} "
            f"| {row['risk_manager']} | {row['run_count']} | {_fmt(row['memory_pollution_ratio_mean'])} "
            f"| {_fmt(row['memory_driven_leverage_amplification_mean'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
    return _round(mean(float(row[key]) for row in rows))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_list(value: str, label: str) -> list[str]:
    values = [part.strip() for part in value.split(",") if part.strip()]
    if not values:
        raise SystemExit(f"{label} must contain at least one item")
    return values


def _parse_floats(value: str, label: str, *, require_zero: bool = False) -> list[float]:
    try:
        values = [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise SystemExit(f"{label} must be a comma-separated list of numbers") from exc
    if not values:
        raise SystemExit(f"{label} must contain at least one item")
    if require_zero and 0.0 not in values:
        raise SystemExit(f"{label} must include 0.0 so paired dose-response baselines exist")
    return values


def _parse_ints(value: str, label: str) -> list[int]:
    try:
        values = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise SystemExit(f"{label} must be a comma-separated list of integers") from exc
    if not values:
        raise SystemExit(f"{label} must contain at least one item")
    return values


def _resolve_output_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _round(value: Any) -> float:
    return round(float(value or 0.0), 6)


def _nullable_round(value: Any) -> float | None:
    if value is None:
        return None
    return _round(value)


def _fmt(value: Any) -> str:
    if value in ("", None):
        return ""
    return f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
