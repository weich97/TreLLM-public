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

from validate_reproduction_report import validate_reproduction_report

PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_REPORT_DIRS = ("docs/results/v0_3_external_reproduction_reports/reports",)
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_external_reproduction_reports"
REQUIRED_ENVIRONMENT_CLASSES = ("windows_or_macos", "linux", "colab_or_binder")
REQUIRED_INDEPENDENT_REPORTS = 3
REPORT_FIELDS = [
    "protocol_id",
    "report_path",
    "schema",
    "repository",
    "commit_or_tag",
    "environment_class",
    "report_author_type",
    "independent_reviewer",
    "command_count",
    "failed_command_count",
    "artifact_count",
    "missing_artifact_count",
    "live_api_used",
    "private_fills_used",
    "trajectory_reproducibility_hash",
    "validation_status",
    "accepted_for_v0_3",
    "blocking_reasons",
]
COVERAGE_FIELDS = [
    "protocol_id",
    "environment_class",
    "required",
    "accepted_report_count",
    "coverage_status",
    "accepted_reports",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the TreLLM v0.3 external reproduction gate artifact.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dirs", default=",".join(DEFAULT_REPORT_DIRS))
    parser.add_argument("--required-independent-reports", type=int, default=REQUIRED_INDEPENDENT_REPORTS)
    args = parser.parse_args(argv)

    if args.required_independent_reports < 1:
        raise SystemExit("--required-independent-reports must be >= 1")

    output_dir = _resolve(args.output_dir)
    report_dirs = [_resolve(path) for path in _parse_csv_list(args.report_dirs)]
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)

    report_rows = _report_rows(report_dirs)
    coverage_rows = _coverage_rows(report_rows)
    summary = _summary(
        report_rows,
        coverage_rows,
        report_dirs=report_dirs,
        required_independent_reports=args.required_independent_reports,
    )

    _write_csv(output_dir / "external_reproduction_gate_reports.csv", report_rows, REPORT_FIELDS)
    _write_csv(output_dir / "external_reproduction_environment_coverage.csv", coverage_rows, COVERAGE_FIELDS)
    _write_json(output_dir / "external_reproduction_gate_summary.json", summary)
    (output_dir / "external_reproduction_gate_summary.md").write_text(
        _summary_markdown(summary, coverage_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display_path(output_dir / 'external_reproduction_gate_reports.csv')}")
    print(f"Wrote {_display_path(output_dir / 'external_reproduction_environment_coverage.csv')}")
    print(f"Wrote {_display_path(output_dir / 'external_reproduction_gate_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'external_reproduction_gate_summary.md')}")
    print(f"Reports scanned: {len(report_rows)}")
    print(f"Accepted reports: {summary['accepted_report_count']}")
    print(f"External reproduction ready: {summary['external_reproduction_ready']}")
    return 0


def _report_rows(report_dirs: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for directory in report_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            payload = _load_json(path)
            if payload.get("schema") != "tradearena_external_reproduction_pack_v1":
                continue
            schema_errors = validate_reproduction_report(payload, allow_command_failures=False)
            blocking_reasons = _blocking_reasons(payload, schema_errors)
            commands = [
                command for command in payload.get("commands", []) if isinstance(command, dict)
            ] if isinstance(payload.get("commands"), list) else []
            artifacts = [
                artifact for artifact in payload.get("artifacts", []) if isinstance(artifact, dict)
            ] if isinstance(payload.get("artifacts"), list) else []
            failed_commands = [command for command in commands if command.get("returncode") not in {0, None}]
            missing_artifacts = [artifact for artifact in artifacts if not artifact.get("exists")]
            trajectory_hash = payload.get("trajectory_hash", {})
            rows.append(
                {
                    "protocol_id": payload.get("protocol_id", ""),
                    "report_path": _display_path(path),
                    "schema": payload.get("schema", ""),
                    "repository": payload.get("repository", ""),
                    "commit_or_tag": payload.get("commit_or_tag", ""),
                    "environment_class": payload.get("environment_class", ""),
                    "report_author_type": payload.get("report_author_type", ""),
                    "independent_reviewer": str(bool(payload.get("independent_reviewer", False))).lower(),
                    "command_count": len(commands),
                    "failed_command_count": len(failed_commands),
                    "artifact_count": len(artifacts),
                    "missing_artifact_count": len(missing_artifacts),
                    "live_api_used": str(bool(payload.get("live_api_used", False))).lower(),
                    "private_fills_used": str(bool(payload.get("private_fills_used", False))).lower(),
                    "trajectory_reproducibility_hash": (
                        trajectory_hash.get("reproducibility_hash", "") if isinstance(trajectory_hash, dict) else ""
                    ),
                    "validation_status": "valid" if not schema_errors else "invalid",
                    "accepted_for_v0_3": str(not blocking_reasons).lower(),
                    "blocking_reasons": ";".join(blocking_reasons),
                }
            )
    return rows


def _blocking_reasons(payload: dict[str, Any], schema_errors: list[str]) -> list[str]:
    reasons: list[str] = []
    if schema_errors:
        reasons.append("schema_or_artifact_validation_failed")
    if payload.get("protocol_id") != PROTOCOL_ID:
        reasons.append("missing_or_wrong_protocol_id")
    if payload.get("environment_class") not in REQUIRED_ENVIRONMENT_CLASSES:
        reasons.append("missing_or_invalid_environment_class")
    if payload.get("report_author_type") != "independent" or payload.get("independent_reviewer") is not True:
        reasons.append("not_independent_external_report")
    if payload.get("repository") != "https://github.com/weich97/TreLLM-public":
        reasons.append("repository_mismatch")
    if payload.get("private_fills_used") is not False:
        reasons.append("private_fills_used")
    return reasons


def _coverage_rows(report_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for environment_class in REQUIRED_ENVIRONMENT_CLASSES:
        accepted = [
            row["report_path"]
            for row in report_rows
            if row["environment_class"] == environment_class and row["accepted_for_v0_3"] == "true"
        ]
        rows.append(
            {
                "protocol_id": PROTOCOL_ID,
                "environment_class": environment_class,
                "required": "true",
                "accepted_report_count": len(accepted),
                "coverage_status": "covered" if accepted else "missing",
                "accepted_reports": ";".join(accepted),
            }
        )
    return rows


def _summary(
    report_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    *,
    report_dirs: list[Path],
    required_independent_reports: int,
) -> dict[str, Any]:
    accepted_rows = [row for row in report_rows if row["accepted_for_v0_3"] == "true"]
    covered_environment_count = sum(1 for row in coverage_rows if row["coverage_status"] == "covered")
    ready = len(accepted_rows) >= required_independent_reports and covered_environment_count == len(REQUIRED_ENVIRONMENT_CLASSES)
    blocking_reasons = []
    if len(accepted_rows) < required_independent_reports:
        blocking_reasons.append("insufficient_independent_report_count")
    if covered_environment_count < len(REQUIRED_ENVIRONMENT_CLASSES):
        blocking_reasons.append("missing_required_environment_class")
    return {
        "schema": "trellm_v0_3_external_reproduction_gate_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "external_reproduction_gate",
        "report_count": len(report_rows),
        "accepted_report_count": len(accepted_rows),
        "required_independent_reports": required_independent_reports,
        "required_environment_classes": list(REQUIRED_ENVIRONMENT_CLASSES),
        "covered_environment_count": covered_environment_count,
        "external_reproduction_ready": ready,
        "blocking_reasons": blocking_reasons,
        "report_dirs": [_display_path(path) for path in report_dirs],
        "claim_boundary": (
            "This gate validates external reproduction reports against the v0.3 protocol. "
            "It does not count project-maintainer, failed, private-data, or wrong-environment reports as independent evidence."
        ),
        "open_gap_policy": (
            "Amended 2026-07-05 (pre-registered fallback): the protocol's reproduction criterion is satisfied "
            "by the pack's machine self-verification (replication_pack_verification artifact) or by at least "
            "one accepted independent report. This intake gate remains open either way; full external "
            "validation (three independent reports covering windows_or_macos, linux, and colab_or_binder) "
            "is tracked as an optional stretch tier via external_reproduction_ready."
        ),
        "artifacts": [
            "external_reproduction_gate_reports.csv",
            "external_reproduction_environment_coverage.csv",
            "external_reproduction_gate_summary.json",
            "external_reproduction_gate_summary.md",
            "reports/*.json",
        ],
    }


def _summary_markdown(summary: dict[str, Any], coverage_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 External Reproduction Gate",
        "",
        "This artifact tracks whether independent reproduction reports satisfy the v0.3 protocol.",
        "It is intentionally conservative: project-maintainer reports, failed command logs, private-data runs, and missing environment labels do not count as independent evidence.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Reports scanned: `{summary['report_count']}`",
        f"- Accepted reports: `{summary['accepted_report_count']} / {summary['required_independent_reports']}`",
        f"- Covered environment classes: `{summary['covered_environment_count']} / {len(summary['required_environment_classes'])}`",
        f"- External reproduction ready: `{summary['external_reproduction_ready']}`",
        f"- Blocking reasons: `{';'.join(summary['blocking_reasons']) or 'none'}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        f"- Open-gap policy: {summary['open_gap_policy']}",
        "",
        "## Environment Coverage",
        "",
        "| Environment class | Accepted reports | Status |",
        "| --- | ---: | --- |",
    ]
    for row in coverage_rows:
        lines.append(f"| {row['environment_class']} | {row['accepted_report_count']} | {row['coverage_status']} |")
    lines += [
        "",
        "## Report Requirements",
        "",
        "A report counts only when it is schema-valid, uses `protocol_id=trellm-v0.3-protocol`, marks `report_author_type=independent`, sets `independent_reviewer=true`, records one required environment class, and contains no failed required commands or missing artifacts.",
        "",
    ]
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


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
