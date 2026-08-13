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

from tradearena.evaluation.statistics import variance_components

PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_INPUT_ROWS = "docs/results/v0_3_direct_api_pilot/direct_api_pilot_rows.csv"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_variance_decomposition"
METRICS = ("total_return", "max_drawdown", "execution_fill_rate", "risk_clipped_decisions")
FIELDS = [
    "protocol_id",
    "source_artifact",
    "provider",
    "model_id",
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "metric",
    "seed_group_count",
    "total_sample_count",
    "between_seed_variance",
    "within_seed_variance",
    "within_seed_share",
    "evidence_stage",
    "claim_scope",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the TreLLM v0.3 variance decomposition artifact.")
    parser.add_argument("--input-rows", default=DEFAULT_INPUT_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    input_path = _resolve(args.input_rows)
    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_rows = _read_rows(input_path)
    rows = _variance_rows(source_rows, source_artifact=_display(input_path))
    summary = _summary(rows, source_rows, source_artifact=_display(input_path))

    _write_csv(output_dir / "variance_decomposition_rows.csv", rows)
    _write_json(output_dir / "variance_decomposition_summary.json", summary)
    (output_dir / "variance_decomposition.md").write_text(_summary_markdown(summary, rows), encoding="utf-8")

    print(f"Wrote {_display(output_dir / 'variance_decomposition_rows.csv')}")
    print(f"Wrote {_display(output_dir / 'variance_decomposition_summary.json')}")
    print(f"Wrote {_display(output_dir / 'variance_decomposition.md')}")
    print(f"Variance rows: {len(rows)}")
    return 0


def _variance_rows(source_rows: list[dict[str, str]], *, source_artifact: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = {}
    for row in source_rows:
        key = (
            row["provider"],
            row["model_id"],
            row["scenario_id"],
            row["contamination_tier"],
            row["execution_level"],
        )
        grouped.setdefault(key, []).append(row)

    output: list[dict[str, Any]] = []
    for (provider, model_id, scenario_id, tier, execution_level), rows in sorted(grouped.items()):
        for metric in METRICS:
            by_seed: dict[int, list[float]] = {}
            for row in rows:
                by_seed.setdefault(int(row["seed"]), []).append(float(row[metric]))
            components = variance_components(by_seed)
            output.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "source_artifact": source_artifact,
                    "provider": provider,
                    "model_id": model_id,
                    "scenario_id": scenario_id,
                    "contamination_tier": tier,
                    "execution_level": execution_level,
                    "metric": metric,
                    "seed_group_count": components["group_count"],
                    "total_sample_count": components["total_n"],
                    "between_seed_variance": _nullable_round(components["between_group_variance"]),
                    "within_seed_variance": _nullable_round(components["within_group_variance"]),
                    "within_seed_share": _nullable_round(components["within_group_share"]),
                    "evidence_stage": "protocol-fixture",
                    "claim_scope": (
                        "Variance decomposition schema fixture: separates seed/path variance from repeated-sample "
                        "variance, but does not support provider-performance claims."
                    ),
                }
            )
    return output


def _summary(rows: list[dict[str, Any]], source_rows: list[dict[str, str]], *, source_artifact: str) -> dict[str, Any]:
    testable = [row for row in rows if row["within_seed_variance"] is not None]
    return {
        "schema": "trellm_v0_3_variance_decomposition_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "variance_decomposition",
        "source_artifact": source_artifact,
        "source_row_count": len(source_rows),
        "variance_row_count": len(rows),
        "testable_metric_count": len(testable),
        "metrics": list(METRICS),
        "minimum_seed_group_count": min((int(row["seed_group_count"]) for row in rows), default=0),
        "minimum_total_sample_count": min((int(row["total_sample_count"]) for row in rows), default=0),
        "claim_boundary": (
            "This fixture validates variance-decomposition reporting for v0.3. It uses protocol-fixture rows "
            "and does not support model-performance or model-stochasticity claims."
        ),
        "artifacts": [
            "variance_decomposition_rows.csv",
            "variance_decomposition_summary.json",
            "variance_decomposition.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 Variance Decomposition",
        "",
        "This artifact verifies the v0.3 variance-decomposition table shape on fixture direct API pilot rows.",
        "It separates between-seed market-path variance from within-seed repeated-sample variance.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Source artifact: `{summary['source_artifact']}`",
        f"- Source rows: `{summary['source_row_count']}`",
        f"- Variance rows: `{summary['variance_row_count']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Rows",
        "",
        "| Provider | Model | Scenario | Tier | Execution | Metric | Seeds | Samples | Between seed var | Within seed var | Within share |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['provider']} | {row['model_id']} | {row['scenario_id']} | {row['contamination_tier']} | "
            f"{row['execution_level']} | {row['metric']} | {row['seed_group_count']} | {row['total_sample_count']} | "
            f"{row['between_seed_variance']} | {row['within_seed_variance']} | {row['within_seed_share']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _nullable_round(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 12)


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
