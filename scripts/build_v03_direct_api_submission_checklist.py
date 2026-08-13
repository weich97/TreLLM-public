from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "benchmarks" / "v0.3" / "protocol.json"
DIRECT_PROVIDER_SCHEMA_PATH = ROOT / "schemas" / "direct_provider_manifest.schema.json"
BENCHMARK_SUBMISSION_SCHEMA_PATH = ROOT / "schemas" / "benchmark_submission.schema.json"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_direct_api_submission_checklist"
PROTOCOL_MANIFEST_FIELD_PATHS = {
    "provider": "provider",
    "model_id": "model_id",
    "model_version_or_release": "model_version_or_release",
    "api_endpoint_family": "api_endpoint_family",
    "temperature": "sampling.temperature",
    "top_p": "sampling.top_p",
    "max_tokens": "sampling.max_tokens",
    "call_started_at": "call_window.call_started_at",
    "call_completed_at": "call_window.call_completed_at",
    "prompt_template_id": "prompt.prompt_template_id",
    "prompt_sha256": "prompt.prompt_sha256",
    "response_sha256": "response.response_sha256",
    "redaction_policy": "redaction.redaction_policy",
    "retry_count": "call_window.retry_count",
    "parse_status": "response.parse_status",
    "cache_status": "cache.cache_status",
}
CHECKLIST_FIELDS = [
    "phase",
    "item_id",
    "blocking_level",
    "requirement",
    "verification",
    "evidence_path",
    "source",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the TreLLM v0.3 direct API redaction and submission checklist."
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol = _load_json(PROTOCOL_PATH)
    direct_schema = _load_json(DIRECT_PROVIDER_SCHEMA_PATH)
    submission_schema = _load_json(BENCHMARK_SUBMISSION_SCHEMA_PATH)
    rows = _checklist_rows()
    summary = _summary(protocol, direct_schema, submission_schema, rows)

    _write_csv(output_dir / "direct_api_submission_checklist_items.csv", rows)
    _write_json(output_dir / "direct_api_submission_checklist_summary.json", summary)
    (output_dir / "direct_api_submission_checklist.md").write_text(
        _summary_markdown(summary, rows),
        encoding="utf-8",
    )

    print(f"Wrote {_display(output_dir / 'direct_api_submission_checklist_items.csv')}")
    print(f"Wrote {_display(output_dir / 'direct_api_submission_checklist_summary.json')}")
    print(f"Wrote {_display(output_dir / 'direct_api_submission_checklist.md')}")
    print(f"Checklist items: {len(rows)}")
    print(f"Protocol manifest fields covered: {summary['protocol_manifest_fields_covered']}")
    return 0


def _checklist_rows() -> list[dict[str, str]]:
    return [
        _row(
            "planning",
            "plan-row-bound",
            "headline-scientific-claim",
            "Each direct API row is present in the pre-registered matrix plan before the provider call is made.",
            "Run scripts/build_v03_direct_api_matrix_plan.py and match provider, model, scenario, tier, execution level, seed, and sample index.",
            "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv",
            "benchmarks/v0.3/protocol.json",
        ),
        _row(
            "manifest",
            "direct-provider-route",
            "headline-scientific-claim",
            "Provider manifests use provider_route=direct-api; routed-provider rows remain appendix or historical evidence.",
            "Validate each manifest with scripts/validate_direct_provider_manifest.py.",
            "schemas/direct_provider_manifest.schema.json",
            "provider_protocol.headline_results",
        ),
        _row(
            "manifest",
            "model-version-endpoint",
            "headline-scientific-claim",
            "Provider, model_id, model_version_or_release, and api_endpoint_family are recorded without ambiguity.",
            "Check direct provider manifest fields provider, model_id, model_version_or_release, and api_endpoint_family.",
            "schemas/direct_provider_manifest.schema.json",
            "provider_protocol.required_manifest_fields",
        ),
        _row(
            "manifest",
            "call-window-failure-accounting",
            "headline-scientific-claim",
            "Call start, completion, request-id redaction, retry_count, parse_status, and cache_status are explicit.",
            "Check call_window, response.parse_status, and cache fields; failed/partial rows must not be silently dropped.",
            "schemas/direct_provider_manifest.schema.json",
            "provider_protocol.failure_accounting",
        ),
        _row(
            "manifest",
            "sampling-parameters",
            "headline-scientific-claim",
            "Temperature, top_p, and max_tokens are recorded for every direct provider call.",
            "Check sampling.temperature, sampling.top_p, and sampling.max_tokens in the manifest.",
            "schemas/direct_provider_manifest.schema.json",
            "provider_protocol.required_manifest_fields",
        ),
        _row(
            "redaction",
            "hash-only-prompt-response",
            "public-artifact-safety",
            "Public artifacts expose prompt_sha256 and response_sha256, not raw provider prompt or response text.",
            "Require prompt.raw_prompt_public=false, response.raw_response_public=false, and public privacy scan success.",
            "schemas/direct_provider_manifest.schema.json",
            "docs/advanced_integrations_security.md",
        ),
        _row(
            "redaction",
            "secret-and-account-data-removed",
            "public-artifact-safety",
            "Provider secrets and private account data are removed before any public submission.",
            "Require redaction.provider_secrets_removed=true and redaction.private_account_data_removed=true.",
            "schemas/direct_provider_manifest.schema.json",
            "docs/advanced_integrations_security.md",
        ),
        _row(
            "binding",
            "run-binding",
            "headline-scientific-claim",
            "Scenario, contamination tier, execution level, seed, sample index, and trajectory manifest hash bind the provider call to a replayable run.",
            "Check run_binding fields in the direct provider manifest.",
            "schemas/direct_provider_manifest.schema.json",
            "benchmarks/v0.3/protocol.json",
        ),
        _row(
            "submission",
            "submission-manifest-hash",
            "public-artifact-safety",
            "Benchmark submissions include the direct_provider_manifest hash and exclude raw prompt/response payloads.",
            "Check trajectory_manifest.artifact_hashes.direct_provider_manifest plus raw_prompts_included=false and raw_responses_included=false.",
            "schemas/benchmark_submission.schema.json",
            "examples/benchmark_submissions/example_direct_api_redacted_submission.json",
        ),
        _row(
            "submission",
            "evidence-tags-and-claim-class",
            "headline-scientific-claim",
            "Direct rows use evidence tags and claim_scope to prevent over-reading pilot, fixture, cached, or redacted evidence.",
            "Check evidence.tags, evidence.claim_scope, claim_class, evidence_tier, and boundary_notes.",
            "schemas/benchmark_submission.schema.json",
            "docs/claim_boundaries.md",
        ),
        _row(
            "submission",
            "execution-contamination-labels",
            "headline-scientific-claim",
            "Result rows label execution_level and contamination_tier before they can enter v0.3 main comparisons.",
            "Cross-check direct provider run_binding with benchmark submission execution_config and scenario metadata.",
            "benchmarks/v0.3/protocol.json",
            "docs/benchmark_v0_3_protocol.md",
        ),
        _row(
            "validation",
            "matrix-gate",
            "headline-scientific-claim",
            "Direct rows pass the matrix gate or remain explicitly labeled as pilot/incomplete evidence.",
            "Run scripts/build_v03_direct_api_matrix_gate.py against submission and provider manifest directories.",
            "docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json",
            "scripts/build_v03_direct_api_matrix_gate.py",
        ),
        _row(
            "validation",
            "privacy-scan",
            "public-artifact-safety",
            "Generated public artifacts pass the public artifact privacy scanner before publication.",
            "Run scripts/scan_public_artifacts.py on generated outputs, docs/results, and benchmark submissions.",
            "scripts/scan_public_artifacts.py",
            "scripts/check_release_readiness.py",
        ),
        _row(
            "claim-boundary",
            "no-profitability-claim",
            "paper-claim-boundary",
            "Direct API rows do not support trading-profitability claims unless separately backed by live, regulated, and externally audited evidence.",
            "Check claim_scope and report text for evaluation reliability language rather than investment advice or profitability claims.",
            "docs/claim_boundaries.md",
            "docs/benchmark_v0_3_protocol.md",
        ),
    ]


def _summary(
    protocol: dict[str, Any],
    direct_schema: dict[str, Any],
    submission_schema: dict[str, Any],
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    protocol_fields = protocol.get("provider_protocol", {}).get("required_manifest_fields", [])
    schema_paths = _schema_paths(direct_schema)
    covered_fields = [
        field
        for field in protocol_fields
        if PROTOCOL_MANIFEST_FIELD_PATHS.get(str(field), str(field)) in schema_paths
    ]
    missing_fields = [field for field in protocol_fields if field not in covered_fields]
    return {
        "schema": "trellm_v0_3_direct_api_submission_checklist_v0.1",
        "protocol_id": protocol.get("protocol_id"),
        "artifact_id": "direct_api_submission_checklist",
        "checklist_item_count": len(rows),
        "blocking_item_count": sum(1 for row in rows if row["blocking_level"]),
        "phases": sorted({row["phase"] for row in rows}),
        "protocol_manifest_field_count": len(protocol_fields),
        "covered_protocol_manifest_fields": covered_fields,
        "missing_protocol_manifest_fields": missing_fields,
        "protocol_manifest_fields_covered": not missing_fields,
        "direct_provider_schema_required": direct_schema.get("required", []),
        "benchmark_submission_schema_required": submission_schema.get("required", []),
        "claim_boundary": (
            "This checklist constrains public direct API submissions, redaction, and claim boundaries. "
            "It is not provider-performance evidence and does not close the direct_api_model_matrix gap."
        ),
        "artifacts": [
            "direct_api_submission_checklist_items.csv",
            "direct_api_submission_checklist_summary.json",
            "direct_api_submission_checklist.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], rows: list[dict[str, str]]) -> str:
    lines = [
        "# TreLLM v0.3 Direct API Submission Checklist",
        "",
        "This checklist is for contributors preparing public direct API rows for TreLLM v0.3.",
        "It focuses on redaction, manifest binding, matrix-gate readiness, and claim boundaries.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Checklist items: `{summary['checklist_item_count']}`",
        f"- Protocol manifest fields covered by schema: `{summary['protocol_manifest_fields_covered']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Items",
        "",
        "| Phase | Item | Blocking level | Requirement | Verification | Evidence path |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['phase']} | {row['item_id']} | {row['blocking_level']} | "
            f"{row['requirement']} | {row['verification']} | `{row['evidence_path']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _row(
    phase: str,
    item_id: str,
    blocking_level: str,
    requirement: str,
    verification: str,
    evidence_path: str,
    source: str,
) -> dict[str, str]:
    return {
        "phase": phase,
        "item_id": item_id,
        "blocking_level": blocking_level,
        "requirement": requirement,
        "verification": verification,
        "evidence_path": evidence_path,
        "source": source,
    }


def _schema_paths(schema: dict[str, Any]) -> set[str]:
    paths: set[str] = set()

    def visit(node: dict[str, Any], prefix: str = "") -> None:
        properties = node.get("properties", {})
        if not isinstance(properties, dict):
            return
        for name, child in properties.items():
            path = f"{prefix}.{name}" if prefix else str(name)
            paths.add(path)
            if isinstance(child, dict):
                visit(child, path)

    visit(schema)
    return paths


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{_display(path)} must contain a JSON object")
    return payload


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHECKLIST_FIELDS)
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
