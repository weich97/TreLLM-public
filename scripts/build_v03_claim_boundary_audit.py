from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_claim_boundary_audit"
EVIDENCE_INDEX_PATH = ROOT / "docs" / "results" / "v0_3_evidence_index" / "v0_3_evidence_index.json"
OPEN_GAPS_PATH = ROOT / "docs" / "results" / "v0_3_evidence_index" / "v0_3_open_gaps.csv"
AUDIT_TARGETS = [
    "README.md",
    "docs/benchmark_v0_3_protocol.md",
    "docs/claim_boundaries.md",
    "docs/technical_report.md",
    "docs/research_report.md",
]
REQUIRED_PHRASES = {
    "README.md": [
        "TreLLM is not investment advice or a promise of profitable trading.",
        "The repo distinguishes three claims:",
        "Current public LLM runs are deliberately labeled as protocol fixtures,",
    ],
    "docs/benchmark_v0_3_protocol.md": [
        "headline_scientific_claim_ready",
        "false until direct API model matrices and independent external reproduction",
        "Do not use the v0.3 protocol to claim:",
    ],
    "docs/claim_boundaries.md": [
        "TreLLM separates three kinds of claims.",
        "Scientific rows should be rare and conservative.",
    ],
}
RISKY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bproves?\s+that\b",
        r"\bproven\s+to\s+be\s+profitable\b",
        r"\bpromise\s+of\s+profitable\s+trading\b",
        r"\bbest\s+trading\s+model\b",
        r"\binvestment\s+advice\b",
        r"\blive\s+profitability\s+claim\b",
    )
]
SAFE_CONTEXT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bnot\b",
        r"\bdo\s+not\b",
        r"\bdoes\s+not\b",
        r"\bcannot\b",
        r"\bshould\s+not\b",
        r"\bavoid\b",
        r"\bforbidden\b",
        r"\bnot\s+in\s+scope\b",
        r"\bkill\s+criteria\b",
    )
]
FIELDNAMES = ["check_id", "target", "status", "severity", "detail", "evidence"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the TreLLM v0.3 claim-boundary audit artifact.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _audit_rows()
    summary = _summary(rows)

    _write_csv(output_dir / "claim_boundary_audit_findings.csv", rows)
    _write_json(output_dir / "claim_boundary_audit_summary.json", summary)
    (output_dir / "claim_boundary_audit.md").write_text(_summary_markdown(summary, rows), encoding="utf-8")

    print(f"Wrote {_display(output_dir / 'claim_boundary_audit_findings.csv')}")
    print(f"Wrote {_display(output_dir / 'claim_boundary_audit_summary.json')}")
    print(f"Wrote {_display(output_dir / 'claim_boundary_audit.md')}")
    print(f"Audit checks: {len(rows)}")
    print(f"Violations: {summary['violation_count']}")
    return 0 if summary["violation_count"] == 0 else 1


def _audit_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    evidence = _load_json(EVIDENCE_INDEX_PATH)
    open_gaps = _load_open_gap_ids()
    # The headline boolean must be *derived*, never asserted: true is only
    # legal when the matrix gate reports gate-passing non-fixture rows AND an
    # accepted independent reproduction report exists. A 2026-07-05 amendment
    # previously let the release pack's own self-verification satisfy the
    # reproduction criterion; that was withdrawn on 2026-08-11 because it
    # contradicted the external-reproduction intake gate, which rejects
    # self-reports by design, and because it allowed a headline claim to read
    # as reproduction-ready on the authors' own check of their own artifact.
    matrix_gate = _load_json(ROOT / "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json")
    repro_gate = _load_json(ROOT / "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.json")
    matrix_ok = bool(matrix_gate.get("headline_scientific_claim_ready")) and int(
        matrix_gate.get("main_threshold_group_count", 0)
    ) > 0
    repro_ok = int(repro_gate.get("accepted_report_count", 0)) >= 1
    expected_ready = matrix_ok and repro_ok
    actual_ready = evidence.get("headline_scientific_claim_ready")
    rows.append(
        _row(
            "evidence-index-headline-ready",
            _display(EVIDENCE_INDEX_PATH),
            "pass" if actual_ready is expected_ready else "fail",
            "blocking",
            "headline_scientific_claim_ready must equal the derived gate state (matrix gate passing AND reproduction criterion met), never be asserted.",
            f"headline_scientific_claim_ready={actual_ready}; derived={expected_ready} (matrix_ok={matrix_ok}, repro_ok={repro_ok})",
        )
    )
    expected_gaps = set()
    if not matrix_ok:
        expected_gaps.add("direct_api_model_matrix")
    if not repro_ok:
        expected_gaps.add("external_reproduction_reports")
    rows.append(
        _row(
            "evidence-index-open-gaps",
            _display(OPEN_GAPS_PATH),
            "pass" if open_gaps == expected_gaps else "fail",
            "blocking",
            "The open-gap list must match the derived gate state exactly: explicit while evidence is pilot/fixture, closed only when the underlying gates genuinely pass.",
            "open_gaps=" + ";".join(sorted(open_gaps)) + "; expected=" + ";".join(sorted(expected_gaps)),
        )
    )

    for target in AUDIT_TARGETS:
        path = ROOT / target
        if not path.exists():
            rows.append(_row("target-present", target, "fail", "blocking", "Claim audit target must exist.", "missing"))
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for phrase in REQUIRED_PHRASES.get(target, []):
            rows.append(
                _row(
                    "required-boundary-phrase",
                    target,
                    "pass" if phrase in text else "fail",
                    "blocking",
                    f"Required claim-boundary phrase is present: {phrase}",
                    phrase,
                )
            )
        rows.extend(_risky_phrase_rows(target, text))
    return rows


def _risky_phrase_rows(target: str, text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        for pattern in RISKY_PATTERNS:
            if not pattern.search(line):
                continue
            context = " ".join(
                part.strip()
                for part in lines[max(0, index - 3) : min(len(lines), index + 2)]
                if part.strip()
            )
            safe = any(safe_pattern.search(context) for safe_pattern in SAFE_CONTEXT_PATTERNS)
            rows.append(
                _row(
                    "risky-claim-context",
                    f"{target}:{index}",
                    "pass" if safe else "fail",
                    "blocking",
                    f"Risky phrase `{pattern.pattern}` must appear only in a negated, forbidden, or limitation context.",
                    context,
                )
            )
    return rows


def _summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    violations = [row for row in rows if row["status"] == "fail"]
    return {
        "schema": "trellm_v0_3_claim_boundary_audit_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "claim_boundary_audit",
        "audit_target_count": len(AUDIT_TARGETS),
        "check_count": len(rows),
        "violation_count": len(violations),
        "blocking_violation_count": sum(1 for row in violations if row["severity"] == "blocking"),
        "headline_scientific_claim_ready": False,
        "claim_boundary": (
            "This audit checks whether public narrative surfaces preserve TreLLM's claim boundaries. "
            "It is not evidence of model performance and does not close the direct API or external reproduction gaps."
        ),
        "audited_targets": AUDIT_TARGETS,
        "artifacts": [
            "claim_boundary_audit_findings.csv",
            "claim_boundary_audit_summary.json",
            "claim_boundary_audit.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], rows: list[dict[str, str]]) -> str:
    lines = [
        "# TreLLM v0.3 Claim Boundary Audit",
        "",
        "This artifact checks whether public narrative surfaces keep pilot, fixture, benchmark, and scientific claims separated.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Audit targets: `{summary['audit_target_count']}`",
        f"- Checks: `{summary['check_count']}`",
        f"- Violations: `{summary['violation_count']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Findings",
        "",
        "| Check | Target | Status | Severity | Detail |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['check_id']} | `{row['target']}` | {row['status']} | {row['severity']} | {row['detail']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _row(check_id: str, target: str, status: str, severity: str, detail: str, evidence: str) -> dict[str, str]:
    return {
        "check_id": check_id,
        "target": target,
        "status": status,
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{_display(path)} must contain a JSON object")
    return payload


def _load_open_gap_ids() -> set[str]:
    with OPEN_GAPS_PATH.open(newline="", encoding="utf-8") as handle:
        return {row["gap_id"] for row in csv.DictReader(handle) if row.get("gap_id")}


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
