from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_power_analysis import estimate_power_synthetic

PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_REPEAT_LEVELS = (6, 10, 20, 30)
DEFAULT_EFFECT_SIZES = (0.2, 0.5, 0.8, 1.2, 1.6, 2.0)
DEFAULT_TARGET_POWERS = (0.5, 0.8)
POWER_FIELDS = [
    "protocol_id",
    "mode",
    "effect_label",
    "observed_cohens_d",
    "repeat_count",
    "alpha",
    "power",
    "draws",
    "permutation_draws",
    "claim_scope",
]
DETECTABLE_FIELDS = [
    "protocol_id",
    "repeat_count",
    "target_power",
    "minimum_detectable_cohens_d",
    "grid_status",
    "alpha",
    "effect_grid",
    "claim_scope",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the TreLLM v0.3 detectable-effect and power-note artifact."
    )
    parser.add_argument("--output-dir", default="docs/results/v0_3_power_note")
    parser.add_argument("--repeat-levels", default=",".join(str(level) for level in DEFAULT_REPEAT_LEVELS))
    parser.add_argument("--effect-sizes", default=",".join(str(effect) for effect in DEFAULT_EFFECT_SIZES))
    parser.add_argument("--target-powers", default=",".join(str(power) for power in DEFAULT_TARGET_POWERS))
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--draws", type=int, default=80, help="Resampling draws per power estimate.")
    parser.add_argument("--permutation-draws", type=int, default=256, help="Sign-flip draws per paired test.")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    repeat_levels = _parse_ints(args.repeat_levels, "repeat-levels")
    effect_sizes = _parse_floats(args.effect_sizes, "effect-sizes")
    target_powers = _parse_floats(args.target_powers, "target-powers")
    _validate_args(repeat_levels, effect_sizes, target_powers, args.alpha, args.draws, args.permutation_draws)

    power_rows = _power_rows(
        repeat_levels=repeat_levels,
        effect_sizes=effect_sizes,
        alpha=args.alpha,
        draws=args.draws,
        permutation_draws=args.permutation_draws,
        seed=args.seed,
    )
    detectable_rows = _detectable_rows(
        power_rows=power_rows,
        repeat_levels=repeat_levels,
        target_powers=target_powers,
        effect_sizes=effect_sizes,
        alpha=args.alpha,
    )
    summary = _summary(
        power_rows=power_rows,
        detectable_rows=detectable_rows,
        repeat_levels=repeat_levels,
        effect_sizes=effect_sizes,
        target_powers=target_powers,
        alpha=args.alpha,
        draws=args.draws,
        permutation_draws=args.permutation_draws,
        seed=args.seed,
    )

    _write_csv(output_dir / "v0_3_power_curves.csv", power_rows, POWER_FIELDS)
    _write_csv(output_dir / "v0_3_detectable_effects.csv", detectable_rows, DETECTABLE_FIELDS)
    _write_json(output_dir / "v0_3_power_note_summary.json", summary)
    (output_dir / "v0_3_power_note_summary.md").write_text(
        _summary_markdown(summary, detectable_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display_path(output_dir / 'v0_3_power_curves.csv')}")
    print(f"Wrote {_display_path(output_dir / 'v0_3_detectable_effects.csv')}")
    print(f"Wrote {_display_path(output_dir / 'v0_3_power_note_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'v0_3_power_note_summary.md')}")
    print(f"Power rows: {len(power_rows)}")
    print(f"Detectable-effect rows: {len(detectable_rows)}")
    return 0


def _power_rows(
    *,
    repeat_levels: list[int],
    effect_sizes: list[float],
    alpha: float,
    draws: int,
    permutation_draws: int,
    seed: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for effect_index, effect_size in enumerate(effect_sizes):
        for repeat_index, repeat_count in enumerate(repeat_levels):
            row_seed = seed + effect_index * 1000 + repeat_index
            power = estimate_power_synthetic(
                effect_size,
                repeat_count,
                alpha=alpha,
                draws=draws,
                permutation_draws=permutation_draws,
                seed=row_seed,
            )
            rows.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "mode": "synthetic",
                    "effect_label": f"cohens_d={effect_size:g}",
                    "observed_cohens_d": effect_size,
                    "repeat_count": repeat_count,
                    "alpha": alpha,
                    "power": power,
                    "draws": draws,
                    "permutation_draws": permutation_draws,
                    "claim_scope": "planning-note-not-model-performance-evidence",
                }
            )
    return rows


def _detectable_rows(
    *,
    power_rows: list[dict[str, Any]],
    repeat_levels: list[int],
    target_powers: list[float],
    effect_sizes: list[float],
    alpha: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_repeat: dict[int, list[dict[str, Any]]] = {}
    for row in power_rows:
        by_repeat.setdefault(int(row["repeat_count"]), []).append(row)

    effect_grid = ",".join(f"{effect:g}" for effect in effect_sizes)
    for repeat_count in repeat_levels:
        repeat_rows = sorted(by_repeat.get(repeat_count, []), key=lambda row: float(row["observed_cohens_d"]))
        for target_power in target_powers:
            detected = next((row for row in repeat_rows if float(row["power"]) >= target_power), None)
            rows.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "repeat_count": repeat_count,
                    "target_power": target_power,
                    "minimum_detectable_cohens_d": (
                        f"{float(detected['observed_cohens_d']):g}" if detected is not None else ""
                    ),
                    "grid_status": "detected" if detected is not None else "not_detected_in_grid",
                    "alpha": alpha,
                    "effect_grid": effect_grid,
                    "claim_scope": "detectable-effect planning threshold; not a model superiority claim",
                }
            )
    return rows


def _summary(
    *,
    power_rows: list[dict[str, Any]],
    detectable_rows: list[dict[str, Any]],
    repeat_levels: list[int],
    effect_sizes: list[float],
    target_powers: list[float],
    alpha: float,
    draws: int,
    permutation_draws: int,
    seed: int,
) -> dict[str, Any]:
    minimum_repeats_for_alpha = _minimum_repeats_for_alpha(alpha)
    detected_by_target = {
        f"power_{target:g}": [
            {
                "repeat_count": int(row["repeat_count"]),
                "minimum_detectable_cohens_d": row["minimum_detectable_cohens_d"],
                "grid_status": row["grid_status"],
            }
            for row in detectable_rows
            if float(row["target_power"]) == target
        ]
        for target in target_powers
    }
    return {
        "schema": "trellm_v0_3_power_note_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "power_detectable_effect_note",
        "alpha": alpha,
        "draws": draws,
        "permutation_draws": permutation_draws,
        "seed": seed,
        "repeat_levels": repeat_levels,
        "effect_sizes": effect_sizes,
        "target_powers": target_powers,
        "row_count": len(power_rows),
        "detectable_effect_row_count": len(detectable_rows),
        "minimum_repeats_for_alpha_005": minimum_repeats_for_alpha,
        "structural_note": (
            "With n=5 paired rows, an exact two-sided sign-flip test has minimum p=2/32=0.0625, "
            "so it cannot reject under alpha=0.05. The v0.3 planning grid therefore starts at n=6."
        ),
        "llm_main_comparison_threshold": {
            "minimum_seeds": 10,
            "samples_per_seed": 3,
            "below_threshold_label": "pilot evidence",
        },
        "claim_boundary": (
            "This power note constrains repeat-count and detectable-effect claims for v0.3 planning; "
            "it is not evidence of model superiority or trading profitability."
        ),
        "detected_by_target": detected_by_target,
        "artifacts": [
            "v0_3_power_curves.csv",
            "v0_3_detectable_effects.csv",
            "v0_3_power_note_summary.json",
            "v0_3_power_note_summary.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], detectable_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 Power and Detectable-Effect Note",
        "",
        "This artifact is a planning and claim-boundary note for the v0.3 protocol.",
        "It estimates synthetic paired-test power over repeat counts and effect sizes, then records the smallest effect size in the grid that reaches each target power.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Alpha: `{summary['alpha']}`",
        f"- Power rows: `{summary['row_count']}`",
        f"- Detectable-effect rows: `{summary['detectable_effect_row_count']}`",
        f"- Minimum repeats for alpha 0.05: `{summary['minimum_repeats_for_alpha_005']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        f"- Structural note: {summary['structural_note']}",
        "",
        "## Detectable Effects",
        "",
        "| Repeats | Target power | Minimum detectable Cohen's d | Status |",
        "| ---: | ---: | ---: | --- |",
    ]
    for row in detectable_rows:
        effect = row["minimum_detectable_cohens_d"] or "not reached"
        lines.append(f"| {row['repeat_count']} | {float(row['target_power']):.2f} | {effect} | {row['grid_status']} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "Rows below the v0.3 LLM main-comparison threshold of 10 seeds and 3 samples per seed remain pilot evidence.",
        "The note should be cited when choosing matrix size or explaining why a model comparison is underpowered.",
        "",
    ]
    return "\n".join(lines)


def _minimum_repeats_for_alpha(alpha: float) -> int:
    n = 1
    while 2 / (2**n) >= alpha:
        n += 1
    return n


def _validate_args(
    repeat_levels: list[int],
    effect_sizes: list[float],
    target_powers: list[float],
    alpha: float,
    draws: int,
    permutation_draws: int,
) -> None:
    if not repeat_levels or any(level < 2 for level in repeat_levels):
        raise SystemExit("--repeat-levels must contain integers >= 2")
    if not effect_sizes or any(effect <= 0 for effect in effect_sizes):
        raise SystemExit("--effect-sizes must contain positive values")
    if not target_powers or any(power <= 0 or power > 1 for power in target_powers):
        raise SystemExit("--target-powers must contain values in (0, 1]")
    if alpha <= 0 or alpha >= 1:
        raise SystemExit("--alpha must be in (0, 1)")
    if draws < 1:
        raise SystemExit("--draws must be >= 1")
    if permutation_draws < 1:
        raise SystemExit("--permutation-draws must be >= 1")


def _parse_ints(value: str, label: str) -> list[int]:
    try:
        return [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise SystemExit(f"--{label} must be comma-separated integers") from exc


def _parse_floats(value: str, label: str) -> list[float]:
    try:
        return [float(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise SystemExit(f"--{label} must be comma-separated numbers") from exc


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_output_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
