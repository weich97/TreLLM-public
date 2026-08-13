from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from validate_direct_provider_manifest import validate_direct_provider_manifest_file

from tradearena.core.reproducibility import sha256_file
from tradearena.evaluation.submissions import validate_submission_file

PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_SUBMISSION_DIRS = ("docs/results/v0_3_direct_api_pilot/submissions",)
DEFAULT_PROVIDER_MANIFEST_DIRS = ("docs/results/v0_3_direct_api_pilot/provider_manifests",)
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_direct_api_matrix_gate"
MINIMUM_SEEDS = 10
SAMPLES_PER_SEED = 3
ROW_FIELDS = [
    "protocol_id",
    "submission_path",
    "scenario_id",
    "provider",
    "model_family",
    "model_display_name",
    "contamination_tier",
    "execution_level",
    "seed",
    "sample_index",
    "evidence_tags",
    "total_return",
    "max_drawdown",
    "sharpe",
    "provider_manifest_path",
    "provider_manifest_sha256",
    "provider_route",
    "manifest_model_id",
    "manifest_model_version_or_release",
    "row_validation_status",
    "threshold_eligible",
    "blocking_reasons",
]
COVERAGE_FIELDS = [
    "protocol_id",
    "provider",
    "model_family",
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "row_count",
    "threshold_eligible_row_count",
    "observed_seed_count",
    "observed_minimum_samples_per_seed",
    "seed_count",
    "minimum_samples_per_seed",
    "required_seed_count",
    "required_samples_per_seed",
    "main_threshold_met",
    "evidence_label",
    "blocking_reasons",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the TreLLM v0.3 direct API matrix threshold-gate artifact."
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--submission-dirs", default=",".join(DEFAULT_SUBMISSION_DIRS))
    parser.add_argument("--provider-manifest-dirs", default=",".join(DEFAULT_PROVIDER_MANIFEST_DIRS))
    parser.add_argument("--minimum-seeds", type=int, default=MINIMUM_SEEDS)
    parser.add_argument("--samples-per-seed", type=int, default=SAMPLES_PER_SEED)
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    submission_dirs = [_resolve(path) for path in _parse_csv_list(args.submission_dirs)]
    provider_manifest_dirs = [_resolve(path) for path in _parse_csv_list(args.provider_manifest_dirs)]
    if args.minimum_seeds < 1 or args.samples_per_seed < 1:
        raise SystemExit("--minimum-seeds and --samples-per-seed must be >= 1")

    provider_manifests = _provider_manifest_index(provider_manifest_dirs)
    row_records = _row_records(submission_dirs, provider_manifests)
    coverage_rows = _coverage_rows(
        row_records,
        minimum_seeds=args.minimum_seeds,
        samples_per_seed=args.samples_per_seed,
    )
    summary = _summary(
        row_records,
        coverage_rows,
        submission_dirs=submission_dirs,
        provider_manifest_dirs=provider_manifest_dirs,
        minimum_seeds=args.minimum_seeds,
        samples_per_seed=args.samples_per_seed,
    )

    _write_csv(output_dir / "direct_api_matrix_gate_rows.csv", row_records, ROW_FIELDS)
    _write_csv(output_dir / "direct_api_matrix_gate_coverage.csv", coverage_rows, COVERAGE_FIELDS)
    _write_json(output_dir / "direct_api_matrix_gate_summary.json", summary)
    (output_dir / "direct_api_matrix_gate_summary.md").write_text(
        _summary_markdown(summary, coverage_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_gate_rows.csv')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_gate_coverage.csv')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_gate_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_gate_summary.md')}")
    print(f"Rows: {len(row_records)}")
    print(f"Coverage groups: {len(coverage_rows)}")
    print(f"Main-threshold groups: {sum(1 for row in coverage_rows if row['main_threshold_met'] == 'true')}")
    return 0


def _provider_manifest_index(provider_manifest_dirs: list[Path]) -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    for directory in provider_manifest_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            payload, errors = validate_direct_provider_manifest_file(path)
            digest = sha256_file(path)
            manifests[digest] = {
                "path": path,
                "payload": payload,
                "errors": errors,
            }
    return manifests


def _row_records(submission_dirs: list[Path], provider_manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for directory in submission_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            submission, submission_errors = validate_submission_file(path)
            manifest_hash = (
                submission.get("trajectory_manifest", {})
                .get("artifact_hashes", {})
                .get("direct_provider_manifest", "")
            )
            provider_record = provider_manifests.get(str(manifest_hash), {})
            provider_manifest = provider_record.get("payload", {})
            provider_errors = list(provider_record.get("errors", []))
            blocking_reasons = _blocking_reasons(submission, submission_errors, manifest_hash, provider_record, provider_errors)
            tags = list(submission.get("evidence", {}).get("tags", []))
            run_binding = provider_manifest.get("run_binding", {})
            metrics = submission.get("metrics", {})
            agent = submission.get("agent", {})
            row_ok = not submission_errors and not provider_errors and bool(provider_record)
            threshold_eligible = row_ok and "direct-api" in tags and "protocol-fixture" not in tags
            rows.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "submission_path": _display_path(path),
                    "scenario_id": submission.get("scenario_id", ""),
                    "provider": agent.get("provider", ""),
                    "model_family": agent.get("model_family", ""),
                    "model_display_name": agent.get("model_display_name", ""),
                    "contamination_tier": run_binding.get("contamination_tier", ""),
                    "execution_level": run_binding.get("execution_level", submission.get("execution_config", {}).get("execution_level", "")),
                    "seed": run_binding.get("seed", ""),
                    "sample_index": run_binding.get("sample_index", ""),
                    "evidence_tags": ";".join(tags),
                    "total_return": metrics.get("total_return", ""),
                    "max_drawdown": metrics.get("max_drawdown", ""),
                    "sharpe": metrics.get("sharpe", ""),
                    "provider_manifest_path": _display_path(provider_record["path"]) if provider_record else "",
                    "provider_manifest_sha256": manifest_hash,
                    "provider_route": provider_manifest.get("provider_route", ""),
                    "manifest_model_id": provider_manifest.get("model_id", ""),
                    "manifest_model_version_or_release": provider_manifest.get("model_version_or_release", ""),
                    "row_validation_status": "valid" if row_ok else "invalid",
                    "threshold_eligible": str(threshold_eligible).lower(),
                    "blocking_reasons": ";".join(blocking_reasons),
                }
            )
    return rows


def _blocking_reasons(
    submission: dict[str, Any],
    submission_errors: list[str],
    manifest_hash: str,
    provider_record: dict[str, Any],
    provider_errors: list[str],
) -> list[str]:
    reasons: list[str] = []
    tags = set(submission.get("evidence", {}).get("tags", []))
    if submission_errors:
        reasons.append("submission_validation_failed")
    if not manifest_hash:
        reasons.append("missing_direct_provider_manifest_hash")
    if manifest_hash and not provider_record:
        reasons.append("direct_provider_manifest_not_found")
    if provider_errors:
        reasons.append("provider_manifest_validation_failed")
    provider_route = provider_record.get("payload", {}).get("provider_route", "") if provider_record else ""
    if provider_route != "direct-api":
        reasons.append("provider_route_not_direct_api")
    provider_manifest = provider_record.get("payload", {}) if provider_record else {}
    provider = str(provider_manifest.get("provider", ""))
    model_id = str(provider_manifest.get("model_id", ""))
    claim_scope = str(provider_manifest.get("evidence", {}).get("claim_scope", ""))
    if "fixture" in provider.lower() or "fixture" in model_id.lower() or "fixture" in claim_scope.lower():
        reasons.append("fixture_provider_or_manifest_claim")
    if "direct-api" not in tags:
        reasons.append("missing_direct_api_evidence_tag")
    if "protocol-fixture" in tags:
        reasons.append("protocol_fixture_not_scientific_model_evidence")
    return reasons


def _coverage_rows(
    row_records: list[dict[str, Any]],
    *,
    minimum_seeds: int,
    samples_per_seed: int,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in row_records:
        grouped[
            (
                str(row["provider"]),
                str(row["model_family"]),
                str(row["scenario_id"]),
                str(row["contamination_tier"]),
                str(row["execution_level"]),
            )
        ].append(row)

    rows: list[dict[str, Any]] = []
    for (provider, model_family, scenario_id, tier, execution_level), group_rows in sorted(grouped.items()):
        eligible_rows = [row for row in group_rows if row["threshold_eligible"] == "true"]
        observed_samples_by_seed: dict[str, set[str]] = defaultdict(set)
        for row in group_rows:
            if row["seed"] != "" and row["sample_index"] != "":
                observed_samples_by_seed[str(row["seed"])].add(str(row["sample_index"]))
        samples_by_seed: dict[str, set[str]] = defaultdict(set)
        for row in eligible_rows:
            if row["seed"] != "" and row["sample_index"] != "":
                samples_by_seed[str(row["seed"])].add(str(row["sample_index"]))
        observed_seed_count = len(observed_samples_by_seed)
        observed_minimum_samples = min((len(samples) for samples in observed_samples_by_seed.values()), default=0)
        seed_count = len(samples_by_seed)
        minimum_samples = min((len(samples) for samples in samples_by_seed.values()), default=0)
        blocking = set()
        for row in group_rows:
            blocking.update(item for item in str(row["blocking_reasons"]).split(";") if item)
        if seed_count < minimum_seeds:
            blocking.add("insufficient_seed_count")
        if minimum_samples < samples_per_seed:
            blocking.add("insufficient_samples_per_seed")
        main_threshold_met = seed_count >= minimum_seeds and minimum_samples >= samples_per_seed and not blocking
        rows.append(
            {
                "protocol_id": PROTOCOL_ID,
                "provider": provider,
                "model_family": model_family,
                "scenario_id": scenario_id,
                "contamination_tier": tier,
                "execution_level": execution_level,
                "row_count": len(group_rows),
                "threshold_eligible_row_count": len(eligible_rows),
                "observed_seed_count": observed_seed_count,
                "observed_minimum_samples_per_seed": observed_minimum_samples,
                "seed_count": seed_count,
                "minimum_samples_per_seed": minimum_samples,
                "required_seed_count": minimum_seeds,
                "required_samples_per_seed": samples_per_seed,
                "main_threshold_met": str(main_threshold_met).lower(),
                "evidence_label": "main-candidate" if main_threshold_met else "pilot-or-incomplete",
                "blocking_reasons": ";".join(sorted(blocking)),
            }
        )
    return rows


def _summary(
    row_records: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    *,
    submission_dirs: list[Path],
    provider_manifest_dirs: list[Path],
    minimum_seeds: int,
    samples_per_seed: int,
) -> dict[str, Any]:
    main_groups = [row for row in coverage_rows if row["main_threshold_met"] == "true"]
    invalid_rows = [row for row in row_records if row["row_validation_status"] != "valid"]
    return {
        "schema": "trellm_v0_3_direct_api_matrix_gate_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "direct_api_matrix_gate",
        "row_count": len(row_records),
        "coverage_group_count": len(coverage_rows),
        "valid_row_count": len(row_records) - len(invalid_rows),
        "invalid_row_count": len(invalid_rows),
        "main_threshold_group_count": len(main_groups),
        "headline_scientific_claim_ready": bool(main_groups),
        "minimum_seeds": minimum_seeds,
        "samples_per_seed": samples_per_seed,
        "submission_dirs": [_display_path(path) for path in submission_dirs],
        "provider_manifest_dirs": [_display_path(path) for path in provider_manifest_dirs],
        "claim_boundary": (
            "This gate verifies direct API row provenance and seed/sample coverage. "
            "Rows tagged as protocol fixtures or below the threshold remain pilot evidence."
        ),
        "open_gap_policy": (
            "The direct_api_model_matrix gap remains open until at least one non-fixture direct API group "
            "meets the v0.3 threshold of 10 seeds and 3 samples per seed."
        ),
        "artifacts": [
            "direct_api_matrix_gate_rows.csv",
            "direct_api_matrix_gate_coverage.csv",
            "direct_api_matrix_gate_summary.json",
            "direct_api_matrix_gate_summary.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], coverage_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 Direct API Matrix Gate",
        "",
        "This artifact verifies whether direct API model rows satisfy the v0.3 seed/sample threshold for main-paper scientific comparisons.",
        "It does not run provider calls and does not promote fixture rows to model-performance evidence.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Rows: `{summary['row_count']}`",
        f"- Valid rows: `{summary['valid_row_count']}`",
        f"- Coverage groups: `{summary['coverage_group_count']}`",
        f"- Main-threshold groups: `{summary['main_threshold_group_count']}`",
        f"- Headline scientific claim ready: `{summary['headline_scientific_claim_ready']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        f"- Open-gap policy: {summary['open_gap_policy']}",
        "",
        "## Coverage Groups",
        "",
        "| Provider | Model | Scenario | Tier | Execution | Rows | Seeds | Min samples/seed | Main threshold | Blocking reasons |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in coverage_rows:
        lines.append(
            f"| {row['provider']} | {row['model_family']} | {row['scenario_id']} | {row['contamination_tier']} | "
            f"{row['execution_level']} | {row['row_count']} | {row['observed_seed_count']} "
            f"observed / {row['seed_count']} eligible | {row['observed_minimum_samples_per_seed']} "
            f"observed / {row['minimum_samples_per_seed']} eligible | {row['main_threshold_met']} | "
            f"{row['blocking_reasons']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
