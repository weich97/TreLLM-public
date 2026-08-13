from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_evidence_index"

ARTIFACT_SPECS = [
    {
        "artifact_id": "direct_api_pilot",
        "claim_area": "direct API provenance",
        "summary_path": "docs/results/v0_3_direct_api_pilot/direct_api_pilot_summary.json",
        "primary_rows": "docs/results/v0_3_direct_api_pilot/direct_api_pilot_rows.csv",
        "claim_class": "engineering",
        "evidence_stage": "protocol-fixture",
        "supports_headline_claim": False,
        "statistical_methods": ["seed/sample manifest coverage"],
        "claim_boundary": "Validates direct API evidence plumbing without live provider calls.",
    },
    {
        "artifact_id": "direct_api_matrix_gate",
        "claim_area": "direct API model matrix threshold gate",
        "summary_path": "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json",
        "primary_rows": "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_coverage.csv",
        "claim_class": "engineering",
        "evidence_stage": "threshold-gate",
        "supports_headline_claim": False,
        "statistical_methods": ["direct_manifest_hash_binding", "seed_sample_threshold_gate"],
        "claim_boundary": "Verifies direct API matrix provenance and 10x3 coverage; see direct_api_matrix_results for the gate-passing rows.",
    },
    {
        "artifact_id": "direct_api_model_matrix_plan",
        "claim_area": "direct API model matrix run plan and credential preflight",
        "summary_path": "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.json",
        "primary_rows": "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_coverage.csv",
        "claim_class": "engineering",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["pre_registered_10x3_matrix_plan", "credential_env_var_preflight"],
        "claim_boundary": "Pre-registers direct API matrix rows and credential readiness; not provider-performance evidence.",
    },
    {
        "artifact_id": "direct_api_call_packets",
        "claim_area": "direct API call-packet execution queue",
        "summary_path": "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets_summary.json",
        "primary_rows": "docs/results/v0_3_direct_api_call_packets/direct_api_call_packet_manifest.csv",
        "claim_class": "engineering",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["deterministic_call_packet_hashing", "redaction_contract_binding"],
        "claim_boundary": "Turns pre-registered rows into hash-bound no-key call packets; not provider-performance evidence.",
    },
    {
        "artifact_id": "direct_api_submission_checklist",
        "claim_area": "direct API redaction and submission checklist",
        "summary_path": "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist_summary.json",
        "primary_rows": "docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist_items.csv",
        "claim_class": "engineering",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["schema_field_coverage_check", "redaction_submission_checklist"],
        "claim_boundary": "Constrains direct API redaction, manifest binding, and claim boundaries; not provider-performance evidence.",
    },
    {
        "artifact_id": "claim_boundary_audit",
        "claim_area": "public narrative claim-boundary audit",
        "summary_path": "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit_summary.json",
        "primary_rows": "docs/results/v0_3_claim_boundary_audit/claim_boundary_audit_findings.csv",
        "claim_class": "engineering",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["claim_boundary_text_audit", "evidence_index_gap_check"],
        "claim_boundary": "Checks public narrative surfaces for overclaiming; not model-performance evidence.",
    },
    {
        "artifact_id": "execution_ladder",
        "claim_area": "execution assumption sensitivity",
        "summary_path": "docs/results/v0_3_execution_ladder/execution_ladder_summary.json",
        "primary_rows": "docs/results/v0_3_execution_ladder/execution_ladder_rows.csv",
        "claim_class": "benchmark",
        "evidence_stage": "protocol-fixture",
        "supports_headline_claim": False,
        "statistical_methods": ["kendall_tau", "top_k_jaccard", "bootstrap_ci"],
        "claim_boundary": "Reports deterministic E0-E3 fixture sensitivity, not live-provider model skill.",
    },
    {
        "artifact_id": "execution_stress_grid",
        "claim_area": "E2 execution stress-grid sensitivity",
        "summary_path": "docs/results/v0_3_execution_stress_grid/execution_stress_grid_summary.json",
        "primary_rows": "docs/results/v0_3_execution_stress_grid/execution_stress_grid_sensitivity.csv",
        "claim_class": "benchmark",
        "evidence_stage": "protocol-fixture",
        "supports_headline_claim": False,
        "statistical_methods": ["paired_seed_delta_vs_e1_reference", "execution_assumption_axis_sweep"],
        "claim_boundary": "Isolates spread, latency, participation, and impact stress axes on fixture agents; not live cost prediction.",
    },
    {
        "artifact_id": "finaudit_pilot",
        "claim_area": "financial trace audit",
        "summary_path": "docs/results/v0_3_finaudit_pilot/finaudit_pilot_summary.json",
        "primary_rows": "docs/results/v0_3_finaudit_pilot/finaudit_pilot_scores.csv",
        "claim_class": "engineering",
        "evidence_stage": "protocol-fixture",
        "supports_headline_claim": False,
        "statistical_methods": ["precision", "recall", "f1", "wilson_interval", "difficulty_breakdown"],
        "claim_boundary": "Validates injected-defect scoring path with fixture auditors, not model audit performance.",
    },
    {
        "artifact_id": "finaudit_direct_model_plan",
        "claim_area": "FinAudit direct-model auditor call plan",
        "summary_path": "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_summary.json",
        "primary_rows": "docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_rows.csv",
        "claim_class": "engineering",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["direct_model_auditor_plan", "private_answer_key_boundary"],
        "claim_boundary": "Pre-registers direct-model FinAudit auditor calls; not model audit-performance evidence.",
    },
    {
        "artifact_id": "memory_contamination",
        "claim_area": "memory contamination mechanism",
        "summary_path": "docs/results/v0_3_memory_contamination/memory_contamination_summary.json",
        "primary_rows": "docs/results/v0_3_memory_contamination/memory_contamination_dose_response.csv",
        "claim_class": "benchmark",
        "evidence_stage": "protocol-fixture",
        "supports_headline_claim": False,
        "statistical_methods": ["paired_bootstrap_delta", "BH-FDR q_value", "bootstrap_ci"],
        "claim_boundary": "Reports C0 read-time memory pollution fixture effects, not LLM model-level robustness.",
    },
    {
        "artifact_id": "contamination_control_audit",
        "claim_area": "contamination-tier readiness and claim boundaries",
        "summary_path": "docs/results/v0_3_contamination_control_audit/contamination_control_audit_summary.json",
        "primary_rows": "docs/results/v0_3_contamination_control_audit/contamination_control_audit.csv",
        "claim_class": "engineering",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["contamination_tier_readiness_audit", "forward_freeze_tooling_check"],
        "claim_boundary": "Maps C0/C1/C2 contamination controls to current evidence; C1/C2 remain contract-only.",
    },
    {
        "artifact_id": "power_detectable_effect_note",
        "claim_area": "statistical power and detectable effects",
        "summary_path": "docs/results/v0_3_power_note/v0_3_power_note_summary.json",
        "primary_rows": "docs/results/v0_3_power_note/v0_3_detectable_effects.csv",
        "claim_class": "benchmark",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["paired_sign_flip_permutation_power", "detectable_effect_grid"],
        "claim_boundary": "Constrains sample-size and detectable-effect claims; not model-superiority evidence.",
    },
    {
        "artifact_id": "variance_decomposition",
        "claim_area": "between-seed and within-seed variance decomposition",
        "summary_path": "docs/results/v0_3_variance_decomposition/variance_decomposition_summary.json",
        "primary_rows": "docs/results/v0_3_variance_decomposition/variance_decomposition_rows.csv",
        "claim_class": "benchmark",
        "evidence_stage": "planning-note",
        "supports_headline_claim": False,
        "statistical_methods": ["variance_decomposition", "between_within_seed_variance_components"],
        "claim_boundary": "Validates variance decomposition reporting on fixture direct API pilot rows; not model-performance evidence.",
    },
    {
        "artifact_id": "external_reproduction_gate",
        "claim_area": "external reproduction intake and environment coverage",
        "summary_path": "docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.json",
        "primary_rows": "docs/results/v0_3_external_reproduction_reports/external_reproduction_environment_coverage.csv",
        "claim_class": "engineering",
        "evidence_stage": "threshold-gate",
        "supports_headline_claim": False,
        "statistical_methods": ["environment_coverage_gate", "independent_report_count_gate"],
        "claim_boundary": (
            "Open intake gate for optional independent reports; the protocol's reproduction "
            "criterion is satisfied by the pack's machine self-verification "
            "(replication_pack_verification), per the 2026-07-05 amendment."
        ),
    },
    {
        "artifact_id": "replication_pack_verification",
        "claim_area": "no-key reproduction pack machine self-verification",
        "summary_path": "docs/results/v0_3_replication_pack_verification/replication_report.json",
        "primary_rows": "docs/results/v0_3_replication_pack_verification/REPLICATION_REPORT.md",
        "claim_class": "engineering",
        "evidence_stage": "threshold-passing",
        "supports_headline_claim": False,
        "statistical_methods": ["frozen_expected_value_comparison", "trajectory_hash_verification"],
        "claim_boundary": (
            "Fresh-unzip single-command verification of the released pack against frozen expected "
            "values (hard checks plus strict trajectory hashes). Artifact-validation evidence, not "
            "an independent third-party reproduction."
        ),
    },
    {
        "artifact_id": "direct_api_matrix_results",
        "claim_area": "headline direct API matrix results (E0/E1 x three C0 regimes)",
        "summary_path": "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json",
        "primary_rows": "docs/results/v0_3_direct_api_matrix/matrix_by_model.csv",
        "claim_class": "scientific",
        "evidence_stage": "threshold-passing",
        "supports_headline_claim": True,
        "statistical_methods": ["seed_sample_threshold_gate", "kendall_tau_ranking_stability"],
        "claim_boundary": (
            "Gate-passing non-fixture direct-API rows (10 seeds x 3 samples per cell, three C0 "
            "regimes, E0/E1). Supports reliability and ranking-stability claims under the frozen "
            "protocol; not trading-profit or best-model advice."
        ),
    },
]

# Gap definitions. Each carries a `resolved` predicate evaluated against the
# public artifacts at build time, so the index reports the *current* state of
# the evidence rather than a hard-coded snapshot.


def _matrix_gap_resolved() -> bool:
    gate = _load_json(_resolve("docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json"))
    return bool(gate.get("headline_scientific_claim_ready")) and int(gate.get("main_threshold_group_count", 0)) > 0


def _pack_self_verification_passes() -> bool:
    """Whether the release pack verifies itself on a fresh unzip.

    This is a real and useful signal -- it catches a broken or incomplete
    pack -- but it is produced by the same party that built the pack, so it is
    not independent evidence of reproduction.
    """

    report = _load_json(_resolve("docs/results/v0_3_replication_pack_verification/replication_report.json"))
    verification = report.get("verification", {})
    return bool(verification.get("overall_pass")) and all(
        check.get("status") == "PASS" for check in verification.get("hard_checks", [])
    )


def _reproduction_gap_resolved() -> bool:
    """Only an accepted *independent* report closes the reproduction gap.

    An earlier amendment let the pack's own self-verification close it. That
    put this index in direct conflict with the project's external-reproduction
    intake gate, which rejects self-reports by design, and it let a headline
    claim be marked reproduction-ready on the strength of the authors checking
    their own artifact. Self-verification is still reported, under its own
    field, as what it is.
    """

    gate = _load_json(_resolve("docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.json"))
    return int(gate.get("accepted_report_count", 0)) >= 1


GAP_SPECS = [
    {
        "gap_id": "direct_api_model_matrix",
        "required_for": "scientific model reliability claims",
        "missing_evidence": "direct API model rows with at least 10 seeds and 3 samples per seed, or explicit pilot labeling",
        "current_status": (
            "plan/preflight and threshold gate exist; current public rows are fixture/pilot evidence and "
            "no non-fixture direct API group has run"
        ),
        "blocking_level": "headline-scientific-claim",
        "resolved": _matrix_gap_resolved,
    },
    {
        "gap_id": "external_reproduction_reports",
        "required_for": "reproduction criterion: at least one accepted independent external report",
        "missing_evidence": (
            "a passing pack self-verification report, or at least one accepted independent "
            "external reproduction report (intake gate remains open either way)"
        ),
        "current_status": "v0.3 intake gate exists; no accepted independent reports are present",
        "blocking_level": "external-validation-claim",
        "resolved": _reproduction_gap_resolved,
    },
]

REQUIRED_PROTOCOL_ARTIFACTS = {
    "direct-provider manifest schema or contract": "direct_api_pilot",
    "raw seed rows": "direct_api_pilot;execution_ladder;memory_contamination",
    "aggregate rows": "execution_ladder;memory_contamination",
    "significance table": "memory_contamination",
    "ranking-stability table": "execution_ladder",
    "contamination probe report": "memory_contamination",
    "contamination-control readiness audit": "contamination_control_audit",
    "execution-sensitivity report": "execution_ladder",
    "execution stress-grid report": "execution_stress_grid",
    "FinAudit pilot report": "finaudit_pilot",
    "FinAudit direct-model audit plan": "finaudit_direct_model_plan",
    "power curve or detectable effect note": "power_detectable_effect_note",
    "variance decomposition table": "variance_decomposition",
    "claim-boundary audit": "claim_boundary_audit",
    "direct API redaction and submission checklist": "direct_api_submission_checklist",
    "direct API model matrix plan": "direct_api_model_matrix_plan",
    "direct API call packet manifest": "direct_api_call_packets",
    "direct API model matrix gate": "direct_api_matrix_gate",
    "external reproduction report gate": "external_reproduction_gate",
    "external reproduction bundle": "replication_pack_verification",
    "direct API matrix results": "direct_api_matrix_results",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a v0.3 evidence index from generated artifacts.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_rows = [_artifact_row(spec) for spec in ARTIFACT_SPECS]
    coverage_rows = _coverage_rows(artifact_rows)
    gap_rows = _gap_rows()
    summary = _summary(artifact_rows, coverage_rows, gap_rows)

    _write_csv(output_dir / "v0_3_evidence_index.csv", artifact_rows, list(artifact_rows[0]))
    _write_csv(output_dir / "v0_3_claim_coverage.csv", coverage_rows, list(coverage_rows[0]))
    gap_fields = ["protocol_id", "gap_id", "required_for", "missing_evidence", "current_status", "blocking_level"]
    _write_csv(output_dir / "v0_3_open_gaps.csv", gap_rows, gap_fields)
    _write_json(output_dir / "v0_3_evidence_index.json", summary)
    (output_dir / "v0_3_evidence_index.md").write_text(
        _summary_markdown(summary, artifact_rows, coverage_rows, gap_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display(output_dir / 'v0_3_evidence_index.csv')}")
    print(f"Wrote {_display(output_dir / 'v0_3_claim_coverage.csv')}")
    print(f"Wrote {_display(output_dir / 'v0_3_open_gaps.csv')}")
    print(f"Wrote {_display(output_dir / 'v0_3_evidence_index.json')}")
    print(f"Wrote {_display(output_dir / 'v0_3_evidence_index.md')}")
    print(f"Artifacts indexed: {len(artifact_rows)}")
    print(f"Open gaps: {len(gap_rows)}")
    return 0


def _artifact_row(spec: dict[str, Any]) -> dict[str, Any]:
    summary_path = _resolve(spec["summary_path"])
    rows_path = _resolve(spec["primary_rows"])
    summary = _load_json(summary_path)
    missing = [path for path in (summary_path, rows_path) if not path.exists()]
    row_count = summary.get("row_count", summary.get("task_count", summary.get("score_row_count", "")))
    return {
        "protocol_id": PROTOCOL_ID,
        "artifact_id": spec["artifact_id"],
        "claim_area": spec["claim_area"],
        "claim_class": spec["claim_class"],
        "evidence_stage": spec["evidence_stage"],
        "supports_headline_claim": str(bool(spec["supports_headline_claim"])).lower(),
        "summary_path": _display(summary_path),
        "primary_rows": _display(rows_path),
        "summary_schema": summary.get("schema", ""),
        "row_count": row_count,
        "statistical_methods": ";".join(spec["statistical_methods"]),
        "claim_boundary": spec["claim_boundary"],
        "artifact_sha256": _sha256_path(summary_path) if summary_path.exists() else "",
        "primary_rows_sha256": _sha256_path(rows_path) if rows_path.exists() else "",
        "status": "missing" if missing else "present",
        "missing_paths": ";".join(_display(path) for path in missing),
    }


def _coverage_rows(artifact_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_artifact = {row["artifact_id"]: row for row in artifact_rows}
    rows: list[dict[str, Any]] = []
    for required_artifact, evidence_ref in REQUIRED_PROTOCOL_ARTIFACTS.items():
        if evidence_ref.startswith("gap:"):
            rows.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "required_artifact": required_artifact,
                    "coverage_status": "open-gap",
                    "evidence_ref": evidence_ref,
                    "claim_boundary": "Required by protocol but not yet satisfied by public v0.3 artifacts.",
                }
            )
            continue
        refs = evidence_ref.split(";")
        present = [ref for ref in refs if by_artifact.get(ref, {}).get("status") == "present"]
        status = "missing"
        if present:
            stages = {str(by_artifact[ref].get("evidence_stage", "")) for ref in present}
            status = "covered-by-fixture" if "protocol-fixture" in stages else "covered-by-artifact"
        rows.append(
            {
                "protocol_id": PROTOCOL_ID,
                "required_artifact": required_artifact,
                "coverage_status": status,
                "evidence_ref": ";".join(present),
                "claim_boundary": (
                    "Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require "
                    "non-fixture direct API rows and scale thresholds."
                ),
            }
        )
    return rows


def _gap_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for gap in GAP_SPECS:
        if gap["resolved"]():
            continue
        row = {"protocol_id": PROTOCOL_ID, **gap}
        row.pop("resolved")
        rows.append(row)
    return rows


def _summary(
    artifact_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    gap_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    present = [row for row in artifact_rows if row["status"] == "present"]
    open_coverage = [row for row in coverage_rows if row["coverage_status"] == "open-gap"]
    return {
        "schema": "trellm_v0_3_evidence_index_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_count": len(artifact_rows),
        "present_artifact_count": len(present),
        "required_protocol_artifact_count": len(coverage_rows),
        "covered_artifact_count": sum(
            1 for row in coverage_rows if row["coverage_status"] in {"covered-by-fixture", "covered-by-artifact"}
        ),
        "covered_fixture_count": sum(1 for row in coverage_rows if row["coverage_status"] == "covered-by-fixture"),
        "open_gap_count": len(gap_rows),
        "open_protocol_coverage_count": len(open_coverage),
        "headline_scientific_claim_ready": not gap_rows,
        # Reported separately from gap closure: the pack verifying itself is
        # evidence that the pack is complete and self-consistent, not evidence
        # that anyone else reproduced it.
        "pack_self_verification_passes": _pack_self_verification_passes(),
        "independent_reproduction_accepted": _reproduction_gap_resolved(),
        "claim_boundary": (
            "This index maps public v0.3 artifacts to protocol claims. Gate-passing direct-API rows support "
            "reliability and ranking-stability claims within the frozen protocol; nothing here supports "
            "trading-profit or best-model advice."
            if not gap_rows
            else "This index maps public v0.3 artifacts to protocol claims. Current artifacts validate protocol "
            "plumbing and pilot mechanisms; they do not yet support headline scientific model-performance claims."
        ),
        "artifacts": [row["artifact_id"] for row in artifact_rows],
        "open_gaps": [row["gap_id"] for row in gap_rows],
    }


def _summary_markdown(
    summary: dict[str, Any],
    artifact_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    gap_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# TreLLM v0.3 Evidence Index",
        "",
        "This index maps generated public artifacts to the v0.3 protocol claims.",
        "It is deliberately conservative: fixture and pilot artifacts do not support headline scientific model-performance claims.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Present artifacts: `{summary['present_artifact_count']} / {summary['artifact_count']}`",
        f"- Public-artifact-covered protocol artifacts: `{summary['covered_artifact_count']} / {summary['required_protocol_artifact_count']}`",
        f"- Fixture-covered protocol artifacts: `{summary['covered_fixture_count']} / {summary['required_protocol_artifact_count']}`",
        f"- Open gaps: `{summary['open_gap_count']}`",
        f"- Headline scientific claim ready: `{summary['headline_scientific_claim_ready']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Artifact Map",
        "",
        "| Artifact | Claim area | Stage | Methods | Supports headline claim | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in artifact_rows:
        lines.append(
            f"| {row['artifact_id']} | {row['claim_area']} | {row['evidence_stage']} | "
            f"{row['statistical_methods']} | {row['supports_headline_claim']} | {row['status']} |"
        )
    lines += [
        "",
        "## Protocol Coverage",
        "",
        "| Required artifact | Status | Evidence | Boundary |",
        "| --- | --- | --- | --- |",
    ]
    for row in coverage_rows:
        lines.append(
            f"| {row['required_artifact']} | {row['coverage_status']} | {row['evidence_ref']} | {row['claim_boundary']} |"
        )
    lines += [
        "",
        "## Open Gaps",
        "",
        "| Gap | Required for | Missing evidence | Current status |",
        "| --- | --- | --- | --- |",
    ]
    for row in gap_rows:
        lines.append(
            f"| {row['gap_id']} | {row['required_for']} | {row['missing_evidence']} | {row['current_status']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_path(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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
