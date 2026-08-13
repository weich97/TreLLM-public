from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from tradearena.core.reproducibility import compute_reproducibility_hash, hash_trajectory_file
from tradearena.evaluation.evidence import evidence_payload
from tradearena.evaluation.submissions import (
    build_registry_rows,
    validate_submission,
    validate_submission_file,
    write_registry_html,
)

ROOT = Path(__file__).resolve().parents[1]
SUBPROCESS_ENV = {
    **os.environ,
    "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
}


def test_example_redacted_submission_validates_and_hash_matches():
    path = ROOT / "examples/benchmark_submissions/example_redacted_submission.json"
    payload, errors = validate_submission_file(path)

    assert errors == []
    assert payload["reproducibility_hash"] == compute_reproducibility_hash(payload)
    assert payload["redaction"]["raw_provider_text_removed"] is True
    assert payload["evidence"]["tags"] == ["stress-only", "deterministic-baseline"]


def test_example_llm_redacted_submission_includes_model_audit_fields():
    path = ROOT / "examples/benchmark_submissions/example_llm_redacted_submission.json"
    payload, errors = validate_submission_file(path)

    assert errors == []
    assert payload["agent"]["provider"] == "poe"
    assert payload["agent"]["prompt_mode"] == "rationale"
    assert payload["agent"]["risk_feedback_mode"] == "true"
    assert 0 <= payload["agent"]["parse_coverage"] <= 1
    assert payload["trajectory_manifest"]["artifact_hashes"]
    assert payload["evidence"]["tags"] == ["stress-only", "cached-provider", "redacted-prompt"]


def test_example_direct_api_redacted_submission_includes_provider_manifest_binding():
    path = ROOT / "examples/benchmark_submissions/example_direct_api_redacted_submission.json"
    payload, errors = validate_submission_file(path)

    assert errors == []
    assert payload["agent"]["provider"] == "fixture-direct-api"
    assert payload["agent"]["model_family"] == "fixture-llm-policy-v0"
    assert payload["trajectory_manifest"]["artifact_hashes"]["direct_provider_manifest"].startswith("sha256:")
    assert payload["evidence"]["tags"] == ["stress-only", "direct-api", "protocol-fixture", "redacted-prompt"]
    assert payload["evidence"]["claim_class"] == "engineering"
    assert payload["evidence"]["evidence_tier"] == "manifest-only"


def test_anonymous_redacted_submission_validates_and_uses_entry_id_boundary():
    path = ROOT / "examples/benchmark_submissions/anonymous_entry_redacted_submission.json"
    payload, errors = validate_submission_file(path)
    text = path.read_text(encoding="utf-8")

    assert errors == []
    assert payload["reproducibility_hash"] == compute_reproducibility_hash(payload)
    assert payload["agent"]["provider"] == "anonymous"
    assert payload["agent"]["model_identifier_redacted"] is True
    assert payload["agent"]["model_display_name"].startswith("entry-id:")
    assert payload["evidence"]["tags"] == ["stress-only", "external-submitted", "redacted-prompt"]
    assert payload["redaction"]["provider_secrets_removed"] is True
    assert payload["redaction"]["raw_provider_text_removed"] is True
    for forbidden in (
        "api_key",
        "password",
        "raw_prompt_text",
        "raw_response_text",
        "private_holdings",
        "broker_account",
    ):
        assert forbidden not in text.lower()


def test_validate_submission_file_reports_malformed_json(tmp_path: Path):
    submission = tmp_path / "broken_submission.json"
    submission.write_text('{"schema_version": ', encoding="utf-8")

    payload, errors = validate_submission_file(submission)

    assert payload == {}
    assert errors == ["benchmark submission file must contain valid JSON"]


def test_validate_submission_cli_reports_malformed_json(tmp_path: Path):
    submission = tmp_path / "broken_submission.json"
    submission.write_text('{"schema_version": ', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-submission", str(submission)],
        cwd=ROOT,
        env=SUBPROCESS_ENV,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "benchmark submission file must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def test_registry_build_reports_malformed_submission_json(tmp_path: Path):
    submission_dir = tmp_path / "submissions"
    submission_dir.mkdir()
    (submission_dir / "broken_submission.json").write_text('{"schema_version": ', encoding="utf-8")

    rows, errors = build_registry_rows(submission_dir)

    assert rows == []
    assert len(errors) == 1
    assert "benchmark submission file must contain valid JSON" in errors[0]


def test_evidence_payload_adds_claim_and_tier_layers():
    evidence = evidence_payload(["stress-only", "cached-provider", "redacted-prompt"])

    assert evidence["claim_class"] == "benchmark"
    assert evidence["evidence_tier"] == "stress-benchmark"
    assert "Do not read this row as calibrated transaction-cost prediction." in evidence["boundary_notes"]


def test_submission_rejects_stress_only_calibrated_execution_overclaim():
    path = ROOT / "examples/benchmark_submissions/example_redacted_submission.json"
    payload, errors = validate_submission_file(path)
    assert errors == []

    overclaim = deepcopy(payload)
    overclaim["evidence"]["claim_scope"] = "broker-grade calibrated transaction-cost prediction"

    assert "stress-only evidence cannot claim calibrated or broker-grade transaction-cost validity" in validate_submission(
        overclaim,
        verify_hash=False,
    )


def test_submission_rejects_mismatched_claim_layers():
    path = ROOT / "examples/benchmark_submissions/example_redacted_submission.json"
    payload, errors = validate_submission_file(path)
    assert errors == []

    mismatched = deepcopy(payload)
    mismatched["evidence"]["claim_class"] = "scientific"
    mismatched["evidence"]["evidence_tier"] = "fill-replay-validated"

    validation_errors = validate_submission(mismatched, verify_hash=False)

    assert "evidence.claim_class must be 'benchmark' for tags stress-only;deterministic-baseline" in validation_errors
    assert "evidence.evidence_tier must be 'stress-benchmark' for tags stress-only;deterministic-baseline" in validation_errors


def test_submission_rejects_routed_provider_with_direct_api_tag():
    path = ROOT / "examples/benchmark_submissions/example_direct_api_redacted_submission.json"
    payload, errors = validate_submission_file(path)
    assert errors == []

    routed = deepcopy(payload)
    routed["agent"]["provider"] = "poe"

    assert "direct-api evidence cannot use routed provider: poe" in validate_submission(routed, verify_hash=False)


def test_submission_allows_quote_calibrated_boundary():
    path = ROOT / "examples/benchmark_submissions/example_redacted_submission.json"
    payload, errors = validate_submission_file(path)
    assert errors == []

    calibrated = deepcopy(payload)
    calibrated["evidence"] = evidence_payload(["quote-calibrated", "deterministic-baseline", "fully-auditable"])
    calibrated["evidence"]["claim_scope"] = "quote-calibrated execution evidence for a deterministic baseline"

    assert validate_submission(calibrated, verify_hash=False) == []


def test_submission_allows_scientific_class_only_with_strong_evidence():
    path = ROOT / "examples/benchmark_submissions/example_redacted_submission.json"
    payload, errors = validate_submission_file(path)
    assert errors == []

    scientific = deepcopy(payload)
    scientific["evidence"] = evidence_payload(["external-submitted", "fully-auditable", "fill-replay-validated"])
    scientific["evidence"]["claim_scope"] = "scientific model skill claim with independent fill replay evidence"

    assert scientific["evidence"]["claim_class"] == "scientific"
    assert validate_submission(scientific, verify_hash=False) == []


def test_cli_submission_registry_and_hash_run(tmp_path: Path):
    submission = ROOT / "examples/benchmark_submissions/example_redacted_submission.json"
    registry = tmp_path / "registry.md"
    csv_path = tmp_path / "registry.csv"
    html_path = tmp_path / "registry.html"

    subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-submission", str(submission)],
        cwd=ROOT,
        env=SUBPROCESS_ENV,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "build-registry",
            str(submission.parent),
            "--output",
            str(registry),
            "--csv-output",
            str(csv_path),
            "--html-output",
            str(html_path),
        ],
        cwd=ROOT,
        env=SUBPROCESS_ENV,
        check=True,
    )

    assert "quickstart_core_synthetic_v0_1" in registry.read_text(encoding="utf-8")
    assert "`stress-only`" in registry.read_text(encoding="utf-8")
    assert "`direct-api`" in registry.read_text(encoding="utf-8")
    assert "stress-benchmark" in registry.read_text(encoding="utf-8")
    assert "evidence_tags" in csv_path.read_text(encoding="utf-8")
    assert "evidence_tier" in csv_path.read_text(encoding="utf-8")
    assert "TradeArena Leaderboard Registry" in html_path.read_text(encoding="utf-8")
    assert "Community Benchmark Registry" not in html_path.read_text(encoding="utf-8")
    assert "stress-only" in html_path.read_text(encoding="utf-8")
    assert "deterministic-baseline" in html_path.read_text(encoding="utf-8")
    assert "Reproducible" in html_path.read_text(encoding="utf-8")
    assert "Redacted" in html_path.read_text(encoding="utf-8")
    assert "<details>" in html_path.read_text(encoding="utf-8")


def test_script_submission_registry_entries_work_without_installed_package(tmp_path: Path):
    submission = ROOT / "examples/benchmark_submissions/example_redacted_submission.json"
    registry = tmp_path / "script_registry.md"
    csv_path = tmp_path / "script_registry.csv"
    html_path = tmp_path / "script_registry.html"

    subprocess.run(
        [sys.executable, "scripts/validate_benchmark_submission.py", str(submission)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/build_benchmark_registry.py",
            str(submission),
            "--output",
            str(registry),
            "--csv-output",
            str(csv_path),
            "--html-output",
            str(html_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "`stress-only`" in registry.read_text(encoding="utf-8")
    assert "evidence_tags" in csv_path.read_text(encoding="utf-8")
    assert "TradeArena Leaderboard Registry" in html_path.read_text(encoding="utf-8")
    assert "Community Benchmark Registry" not in html_path.read_text(encoding="utf-8")


def test_registry_entry_ids_and_empty_html_are_stable(tmp_path: Path):
    submission_dir = ROOT / "examples/benchmark_submissions"
    rows, errors = build_registry_rows(submission_dir)
    assert errors == []

    entry_ids = {row["reproducibility_hash"]: row["entry_id"] for row in rows}
    rows_again, errors_again = build_registry_rows(submission_dir)
    assert errors_again == []
    assert entry_ids == {row["reproducibility_hash"]: row["entry_id"] for row in rows_again}

    html_path = tmp_path / "empty_registry.html"
    write_registry_html([], html_path)
    html = html_path.read_text(encoding="utf-8")

    assert "No accepted submissions yet." in html
    assert "TradeArena Leaderboard Registry" in html
    assert "Community Benchmark Registry" not in html


def test_registry_html_preserves_badges_sorting_metadata_and_detail_panels(tmp_path: Path):
    submission_dir = ROOT / "examples/benchmark_submissions"
    rows, errors = build_registry_rows(submission_dir)
    assert errors == []

    html_path = tmp_path / "registry.html"
    write_registry_html(rows[:2], html_path)
    html = html_path.read_text(encoding="utf-8")

    for row in rows[:2]:
        assert row["entry_id"] in html
        assert row["reproducibility_status"] == "Reproducible"
        assert row["redaction_status"] == "Redacted"
        assert row["source_file"] in html
        assert row["claim_scope"] in html
        assert row["reproducibility_hash"] in html

    assert '<span class="badge">Reproducible</span>' in html
    assert '<span class="badge redacted">Redacted</span>' in html
    assert '<details><summary>Open</summary>' in html
    assert 'data-sort="num">Return</th>' in html
    assert 'data-sort="num">Audit</th>' in html
    assert 'data-provider="' in html
    assert 'data-search="' in html
    assert 'data-value="' in html


def test_empty_registry_html_preserves_filter_and_sort_shell(tmp_path: Path):
    html_path = tmp_path / "empty_registry.html"
    write_registry_html([], html_path)
    html = html_path.read_text(encoding="utf-8")

    assert "No accepted submissions yet." in html
    assert 'id="search"' in html
    assert 'id="provider"' in html
    assert '<table id="registry">' in html
    assert 'data-sort="text">Entry</th>' in html
    assert 'data-sort="num">Return</th>' in html
    assert "applyFilter()" in html


def test_hash_run_produces_stable_trajectory_fingerprint():
    trajectory = ROOT / "outputs/examples/audit_walkthrough_trajectory.json"
    if not trajectory.exists():
        subprocess.run([sys.executable, "examples/audit_trajectory_walkthrough.py"], cwd=ROOT, check=True)

    direct = hash_trajectory_file(trajectory)
    result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "hash-run", str(trajectory)],
        cwd=ROOT,
        env=SUBPROCESS_ENV,
        check=True,
        capture_output=True,
        text=True,
    )
    via_cli = json.loads(result.stdout)

    assert via_cli["file_sha256"] == direct["file_sha256"]
    assert via_cli["reproducibility_hash"] == direct["reproducibility_hash"]


def test_hash_run_reports_malformed_trajectory_json(tmp_path: Path):
    trajectory = tmp_path / "broken_trajectory.json"
    trajectory.write_text('{"steps": ', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "hash-run", str(trajectory)],
        cwd=ROOT,
        env=SUBPROCESS_ENV,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Trajectory file must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def test_tradearena_public_namespace_imports_core_modules():
    import tradearena
    import tradearena.core.domain

    assert tradearena.TradeArena.__name__ == "TradeArena"
    assert tradearena.core.domain.Bar.__name__ == "Bar"
