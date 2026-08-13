from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_evidence_index_maps_artifacts_and_open_gaps(tmp_path: Path):
    output_dir = tmp_path / "evidence_index"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_evidence_index.py",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Artifacts indexed: 17" in result.stdout
    assert "Open gaps: 1" in result.stdout

    summary = json.loads((output_dir / "v0_3_evidence_index.json").read_text(encoding="utf-8"))
    artifacts = list(csv.DictReader((output_dir / "v0_3_evidence_index.csv").open(encoding="utf-8")))
    coverage = list(csv.DictReader((output_dir / "v0_3_claim_coverage.csv").open(encoding="utf-8")))
    gaps = list(csv.DictReader((output_dir / "v0_3_open_gaps.csv").open(encoding="utf-8")))
    markdown = (output_dir / "v0_3_evidence_index.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_evidence_index_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["present_artifact_count"] == 17
    assert summary["covered_artifact_count"] == 21
    assert summary["covered_fixture_count"] == 9
    assert summary["required_protocol_artifact_count"] == 21
    # The matrix gate passes (18/18 threshold groups), but the reproduction
    # gap stays open: only an accepted *independent* report closes it. An
    # earlier version let the pack's own self-verification close it, which put
    # this index in conflict with the external-reproduction intake gate and
    # let a headline claim read as reproduction-ready on the authors' own
    # check. Self-verification is still reported, under its own field.
    assert summary["headline_scientific_claim_ready"] is False
    assert summary["open_gaps"] == ["external_reproduction_reports"]
    assert summary["pack_self_verification_passes"] is True
    assert summary["independent_reproduction_accepted"] is False
    # With the reproduction gap open the boundary text takes its cautious
    # branch, which is the point of deriving the text from the gate state.
    assert "do not yet support" in summary["claim_boundary"]

    assert {row["artifact_id"] for row in artifacts} == {
        "direct_api_pilot",
        "direct_api_matrix_gate",
        "direct_api_model_matrix_plan",
        "direct_api_call_packets",
        "direct_api_submission_checklist",
        "claim_boundary_audit",
        "execution_ladder",
        "execution_stress_grid",
        "finaudit_pilot",
        "finaudit_direct_model_plan",
        "memory_contamination",
        "contamination_control_audit",
        "power_detectable_effect_note",
        "variance_decomposition",
        "external_reproduction_gate",
        "replication_pack_verification",
        "direct_api_matrix_results",
    }
    assert {row["status"] for row in artifacts} == {"present"}
    headline_supporters = {row["artifact_id"] for row in artifacts if row["supports_headline_claim"] == "true"}
    assert headline_supporters == {"direct_api_matrix_results"}
    assert all(row["artifact_sha256"].startswith("sha256:") for row in artifacts)
    assert any("BH-FDR" in row["statistical_methods"] for row in artifacts)
    assert any("kendall_tau" in row["statistical_methods"] for row in artifacts)
    assert any("execution_assumption_axis_sweep" in row["statistical_methods"] for row in artifacts)
    assert any("detectable_effect_grid" in row["statistical_methods"] for row in artifacts)
    assert any("between_within_seed_variance_components" in row["statistical_methods"] for row in artifacts)
    assert any("seed_sample_threshold_gate" in row["statistical_methods"] for row in artifacts)
    assert any("pre_registered_10x3_matrix_plan" in row["statistical_methods"] for row in artifacts)
    assert any("deterministic_call_packet_hashing" in row["statistical_methods"] for row in artifacts)
    assert any("redaction_submission_checklist" in row["statistical_methods"] for row in artifacts)
    assert any("claim_boundary_text_audit" in row["statistical_methods"] for row in artifacts)
    assert any("contamination_tier_readiness_audit" in row["statistical_methods"] for row in artifacts)
    assert any("independent_report_count_gate" in row["statistical_methods"] for row in artifacts)
    assert any("direct_model_auditor_plan" in row["statistical_methods"] for row in artifacts)
    assert any("frozen_expected_value_comparison" in row["statistical_methods"] for row in artifacts)

    external = next(row for row in coverage if row["required_artifact"] == "external reproduction bundle")
    assert external["coverage_status"] == "covered-by-artifact"
    assert external["evidence_ref"] == "replication_pack_verification"
    matrix_results = next(row for row in coverage if row["required_artifact"] == "direct API matrix results")
    assert matrix_results["coverage_status"] == "covered-by-artifact"
    assert matrix_results["evidence_ref"] == "direct_api_matrix_results"
    power_note = next(row for row in coverage if row["required_artifact"] == "power curve or detectable effect note")
    assert power_note["coverage_status"] == "covered-by-artifact"
    assert power_note["evidence_ref"] == "power_detectable_effect_note"
    variance = next(row for row in coverage if row["required_artifact"] == "variance decomposition table")
    assert variance["coverage_status"] == "covered-by-artifact"
    assert variance["evidence_ref"] == "variance_decomposition"
    matrix_gate = next(row for row in coverage if row["required_artifact"] == "direct API model matrix gate")
    assert matrix_gate["coverage_status"] == "covered-by-artifact"
    assert matrix_gate["evidence_ref"] == "direct_api_matrix_gate"
    matrix_plan = next(row for row in coverage if row["required_artifact"] == "direct API model matrix plan")
    assert matrix_plan["coverage_status"] == "covered-by-artifact"
    assert matrix_plan["evidence_ref"] == "direct_api_model_matrix_plan"
    call_packets = next(row for row in coverage if row["required_artifact"] == "direct API call packet manifest")
    assert call_packets["coverage_status"] == "covered-by-artifact"
    assert call_packets["evidence_ref"] == "direct_api_call_packets"
    submission_checklist = next(
        row for row in coverage if row["required_artifact"] == "direct API redaction and submission checklist"
    )
    assert submission_checklist["coverage_status"] == "covered-by-artifact"
    assert submission_checklist["evidence_ref"] == "direct_api_submission_checklist"
    claim_audit = next(row for row in coverage if row["required_artifact"] == "claim-boundary audit")
    assert claim_audit["coverage_status"] == "covered-by-artifact"
    assert claim_audit["evidence_ref"] == "claim_boundary_audit"
    contamination_audit = next(
        row for row in coverage if row["required_artifact"] == "contamination-control readiness audit"
    )
    assert contamination_audit["coverage_status"] == "covered-by-artifact"
    assert contamination_audit["evidence_ref"] == "contamination_control_audit"
    stress_grid = next(row for row in coverage if row["required_artifact"] == "execution stress-grid report")
    assert stress_grid["coverage_status"] == "covered-by-fixture"
    assert stress_grid["evidence_ref"] == "execution_stress_grid"
    finaudit_plan = next(row for row in coverage if row["required_artifact"] == "FinAudit direct-model audit plan")
    assert finaudit_plan["coverage_status"] == "covered-by-artifact"
    assert finaudit_plan["evidence_ref"] == "finaudit_direct_model_plan"
    reproduction_gate = next(row for row in coverage if row["required_artifact"] == "external reproduction report gate")
    assert reproduction_gate["coverage_status"] == "covered-by-artifact"
    assert reproduction_gate["evidence_ref"] == "external_reproduction_gate"
    assert sum(1 for row in coverage if row["coverage_status"] == "covered-by-fixture") == 9
    assert sum(1 for row in coverage if row["coverage_status"] == "covered-by-artifact") == 12
    assert not any(row["coverage_status"] == "open-gap" for row in coverage)

    assert [row["gap_id"] for row in gaps] == ["external_reproduction_reports"]
    assert "TreLLM v0.3 Evidence Index" in markdown
    assert "Headline scientific claim ready: `False`" in markdown
