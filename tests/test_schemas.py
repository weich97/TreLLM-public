from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

import scripts.validate_reproduction_report as reproduction_validator
from tradearena.core.domain import Order, OrderType, Side
from tradearena.core.trajectory import StepRecord, Trajectory
from tradearena.evaluation.submissions import validate_submission_file
from tradearena.tools import (
    AlpacaPaperExportAdapter,
    BrokerAdapterMode,
    BrokerApproval,
    BrokerOrderStatus,
    BrokerResponse,
    BrokerSafetyConfig,
    build_broker_approval_artifact,
    validate_broker_approval_artifact,
    write_broker_response_artifact,
)
from tradearena.tools.calibration import summarize_execution_calibration, summarize_quote_fill_calibration

ROOT = Path(__file__).resolve().parents[1]


def test_trajectory_schema_validates_serialized_trace():
    trajectory = Trajectory(experiment_name="schema-smoke", seed=1)
    trajectory.append(
        StepRecord(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            observation={"prices": {"SYN": 100.0}},
            signals=[],
            decisions=[],
            approved_decisions=[],
            orders=[],
            fills=[],
            portfolio={"cash": 100_000.0, "positions": {}, "equity": 100_000.0},
        )
    )
    payload = _json_round_trip(trajectory.to_dict())

    _validator("trajectory.schema.json").validate(payload)


def test_calibration_profile_schema_validates_ohlcv_diagnostic(tmp_path: Path):
    csv_path = tmp_path / "SYN_Daily.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-01-01,100,102,99,101,1000",
                "2026-01-02,101,104,100,103,1200",
            ]
        ),
        encoding="utf-8",
    )
    summary = summarize_execution_calibration([csv_path])

    _validator("calibration_profile.schema.json").validate(summary)


def test_calibration_profile_schema_validates_quote_fill_profile():
    summary = summarize_quote_fill_calibration(
        ROOT / "data/public/microstructure_sample/quotes.csv",
        ROOT / "data/public/microstructure_sample/fills.csv",
    )

    _validator("calibration_profile.schema.json").validate(summary)


def test_benchmark_submission_schema_has_explicit_version_contract():
    schema = _load_schema("benchmark_submission.schema.json")

    assert schema["properties"]["schema_version"]["const"] == "0.1"
    Draft202012Validator.check_schema(schema)


def test_schema_titles_keep_trellm_system_and_tradearena_leaderboard_roles_separate():
    expected_titles = {
        "benchmark_submission.schema.json": "TradeArena Benchmark Submission",
        "broker_adapter_capability.schema.json": "TreLLM Broker Adapter Capability Manifest",
        "calibration_profile.schema.json": "TreLLM execution calibration profile",
        "demo_artifact_contract.schema.json": "TreLLM Demo Artifact Contract",
        "direct_provider_manifest.schema.json": "TreLLM Direct Provider Manifest",
        "live_readiness_preflight.schema.json": "TreLLM Live Readiness Preflight Bundle",
        "reproduction_report.schema.json": "TreLLM External Reproduction Report",
        "skill_answer_set.schema.json": "TreLLM skill task answer set",
        "skill_task_rubric.schema.json": "TreLLM skill task rubric",
        "operator_runbook_artifact.schema.json": "TreLLM Operator Runbook Artifact",
        "trajectory.schema.json": "TreLLM trajectory",
    }

    for schema_name, expected_title in expected_titles.items():
        schema = _load_schema(schema_name)
        assert schema["title"] == expected_title


def test_direct_provider_manifest_schema_validates_example_contract():
    payload = json.loads((ROOT / "examples/provider_manifests/direct_openai_example.json").read_text(encoding="utf-8"))

    _validator("direct_provider_manifest.schema.json").validate(payload)
    assert payload["schema"] == "trellm_direct_provider_manifest_v0.1"
    assert payload["provider_route"] == "direct-api"
    assert payload["redaction"]["raw_prompt_public"] is False
    assert payload["redaction"]["raw_response_public"] is False


def test_direct_provider_manifest_schema_rejects_routed_provider_as_headline_evidence():
    payload = json.loads((ROOT / "examples/provider_manifests/direct_openai_example.json").read_text(encoding="utf-8"))
    payload["provider_route"] = "poe"

    errors = sorted(_validator("direct_provider_manifest.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("'direct-api' was expected" in error.message for error in errors)


def test_direct_provider_manifest_cli_rejects_missing_response_hash(tmp_path: Path):
    payload = json.loads((ROOT / "examples/provider_manifests/direct_openai_example.json").read_text(encoding="utf-8"))
    del payload["response"]["response_sha256"]
    manifest = tmp_path / "missing_response_hash.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_direct_provider_manifest.py", str(manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid direct provider manifest" in result.stdout
    assert "'response_sha256' is a required property" in result.stdout
    assert "Traceback" not in result.stderr


def test_operator_runbook_artifact_schema_validates_demo_output():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))

    _validator("operator_runbook_artifact.schema.json").validate(payload)


def test_operator_runbook_artifact_schema_rejects_live_submission():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))
    payload["live_submission"] = True

    errors = sorted(_validator("operator_runbook_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("False was expected" in error.message for error in errors)


def test_operator_runbook_artifact_schema_requires_live_readiness_command():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))
    payload["verification_commands"] = [
        command for command in payload["verification_commands"] if "validate-live-readiness" not in command
    ]

    errors = sorted(_validator("operator_runbook_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("does not contain items matching the given schema" in error.message for error in errors)


def test_operator_runbook_artifact_schema_requires_each_critical_checklist_id():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))
    payload["checklist"] = [
        item for item in payload["checklist"] if item["id"] != "reconciliation"
    ]
    payload["checklist"].append(
        {
            "id": "mode-boundary",
            "owner": "operator",
            "evidence": "duplicate placeholder",
            "pass_condition": "does not replace reconciliation evidence",
        }
    )

    errors = sorted(_validator("operator_runbook_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("does not contain items matching the given schema" in error.message for error in errors)


def test_operator_runbook_artifact_schema_rejects_duplicate_critical_checklist_id():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))
    duplicate = dict(payload["checklist"][0])
    duplicate["id"] = "reconciliation"
    payload["checklist"].append(duplicate)

    errors = sorted(_validator("operator_runbook_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("Too many items match the given schema" in error.message for error in errors)


def test_operator_runbook_artifact_schema_rejects_retention_path_parent_traversal():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))
    payload["incident_response_drill"]["artifact_retention_path"] = (
        "outputs/examples/operator_runbook/../private_logs/"
    )

    errors = sorted(_validator("operator_runbook_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("should not be valid" in error.message for error in errors)


def test_operator_runbook_artifact_schema_rejects_owner_whitespace():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))
    payload["incident_response_drill"]["rollback_owner"] = "operator "
    payload["checklist"][0]["owner"] = "operator "

    errors = sorted(_validator("operator_runbook_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("incident_response_drill", "rollback_owner") in paths
    assert ("checklist", 0, "owner") in paths


def test_operator_runbook_artifact_schema_rejects_affected_symbol_whitespace():
    subprocess.run([sys.executable, "examples/operator_runbook_demo.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "outputs/examples/operator_runbook/summary.json").read_text(encoding="utf-8"))
    payload["incident_response_drill"]["affected_symbols"] = ["AAPL "]

    errors = sorted(_validator("operator_runbook_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("incident_response_drill", "affected_symbols", 0) in paths


def test_broker_adapter_capability_schema_validates_demo_output():
    subprocess.run([sys.executable, "examples/broker_capability_manifest_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.json").read_text(encoding="utf-8")
    )

    _validator("broker_adapter_capability.schema.json").validate(payload)


def test_broker_adapter_capability_schema_rejects_adapter_id_whitespace():
    subprocess.run([sys.executable, "examples/broker_capability_manifest_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.json").read_text(encoding="utf-8")
    )
    payload["adapter_id"] = f"{payload['adapter_id']} "

    errors = sorted(_validator("broker_adapter_capability.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("adapter_id",) in paths


def test_broker_adapter_capability_schema_rejects_default_live_submission():
    subprocess.run([sys.executable, "examples/broker_capability_manifest_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.json").read_text(encoding="utf-8")
    )
    payload["live_submission_default"] = True

    errors = sorted(_validator("broker_adapter_capability.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("False was expected" in error.message for error in errors)


def test_broker_adapter_capability_schema_rejects_live_without_live_network_access():
    subprocess.run([sys.executable, "examples/broker_capability_manifest_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.json").read_text(encoding="utf-8")
    )
    payload["supports_live_submission"] = True
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["requires_credentials"] = True
    payload["credential_policy"]["env_vars"] = ["BROKER_API_KEY"]

    errors = sorted(_validator("broker_adapter_capability.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any("'required_for_live' was expected" in error.message for error in errors)


def test_broker_adapter_capability_schema_rejects_credential_env_var_whitespace():
    subprocess.run([sys.executable, "examples/broker_capability_manifest_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.json").read_text(encoding="utf-8")
    )
    payload["supports_live_submission"] = True
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["network_access"] = "required_for_live"
    payload["adapter_kind"] = "live_capable"
    payload["requires_credentials"] = True
    payload["credential_policy"]["env_vars"] = ["BROKER_API_KEY "]

    errors = sorted(_validator("broker_adapter_capability.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("credential_policy", "env_vars", 0) in paths


def test_broker_adapter_capability_schema_rejects_live_adapter_kind_mismatch():
    subprocess.run([sys.executable, "examples/broker_capability_manifest_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.json").read_text(encoding="utf-8")
    )
    live_support = deepcopy(payload)
    live_support["supports_live_submission"] = True
    live_support["supported_modes"].append("live_human_approved")
    live_support["account_modes"].append("live")
    live_support["network_access"] = "required_for_live"
    live_support["requires_credentials"] = True
    live_support["credential_policy"]["env_vars"] = ["BROKER_API_KEY"]

    live_kind = deepcopy(payload)
    live_kind["adapter_kind"] = "live_capable"

    validator = _validator("broker_adapter_capability.schema.json")
    for invalid_payload in (live_support, live_kind):
        errors = list(validator.iter_errors(invalid_payload))
        assert errors


def test_broker_adapter_capability_schema_rejects_live_without_required_live_controls():
    subprocess.run([sys.executable, "examples/broker_capability_manifest_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.json").read_text(encoding="utf-8")
    )
    payload["supports_live_submission"] = True
    payload["network_access"] = "required_for_live"
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["requires_credentials"] = True
    payload["credential_policy"]["env_vars"] = ["BROKER_API_KEY"]

    missing_mode = deepcopy(payload)
    missing_mode["supported_modes"].remove("live_human_approved")
    missing_account = deepcopy(payload)
    missing_account["account_modes"].remove("live")
    no_credentials = deepcopy(payload)
    no_credentials["requires_credentials"] = False
    missing_env_vars = deepcopy(payload)
    missing_env_vars["credential_policy"]["env_vars"] = []
    weak_safety = deepcopy(payload)
    weak_safety["safety_controls"]["kill_switch_required"] = False

    validator = _validator("broker_adapter_capability.schema.json")
    for invalid_payload in (missing_mode, missing_account, no_credentials, missing_env_vars, weak_safety):
        errors = list(validator.iter_errors(invalid_payload))
        assert errors


def test_live_readiness_preflight_schema_validates_demo_output():
    subprocess.run([sys.executable, "examples/live_readiness_preflight_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/live_readiness_preflight/preflight_bundle.json").read_text(encoding="utf-8")
    )

    _validator("live_readiness_preflight.schema.json").validate(payload)


def test_live_readiness_preflight_schema_documents_checked_at_runtime_binding():
    schema = _load_schema("live_readiness_preflight.schema.json")

    description = schema["properties"]["approval_checked_at"]["description"]

    assert "same timestamp passed to `validate-live-readiness --now`" in description
    assert "approval-expiry checks" in description


def test_operator_runbook_schema_documents_current_preflight_command_binding():
    schema = _load_schema("operator_runbook_artifact.schema.json")

    description = schema["properties"]["verification_commands"]["description"]

    assert "current preflight bundle being validated" in description
    assert "portable relative path" in description
    assert "`validate-live-readiness --now` timestamp" in description


@pytest.mark.parametrize(
    ("field", "bad_path"),
    [
        ("capability_manifest", "/tmp/capability_manifest.json"),
        ("handoff_artifact", "C:handoff_artifact.json"),
        ("approval_artifact", "outputs/../approval_artifact.json"),
        ("response_artifact", r"outputs\response_artifact.json"),
    ],
)
def test_live_readiness_preflight_schema_rejects_nonportable_component_paths(field: str, bad_path: str):
    subprocess.run([sys.executable, "examples/live_readiness_preflight_demo.py"], cwd=ROOT, check=True)
    payload = json.loads(
        (ROOT / "outputs/examples/live_readiness_preflight/preflight_bundle.json").read_text(encoding="utf-8")
    )
    payload[field] = bad_path

    errors = sorted(_validator("live_readiness_preflight.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert any(field in str(error.path) and "does not match" in error.message for error in errors)


def test_broker_response_artifact_schema_validates_writer_output(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.FILLED,
                broker_order_id="paper-schema-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=1.0,
                fill_price=100.0,
                fees=0.01,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
        request_artifact_hash="sha256:" + "1" * 64,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["request_artifact_hash"] == "sha256:" + "1" * 64
    _validator("broker_response_artifact.schema.json").validate(payload)


def test_broker_response_artifact_schema_rejects_adapter_whitespace(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-response-adapter-whitespace")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper account symbol permission mismatch",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["adapter"] = f"{payload['adapter']} "

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("adapter",) in paths


def test_broker_response_artifact_schema_rejects_malformed_request_hash(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-request-hash")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper account symbol permission mismatch",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
        request_artifact_hash="sha256:" + "2" * 64,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["request_artifact_hash"] = "sha256:not-a-real-hash"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert ("request_artifact_hash",) in {tuple(error.path) for error in errors}


def test_broker_response_artifact_schema_rejects_client_order_id_whitespace(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-response-client-id-whitespace")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper sandbox rejected order",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["client_order_id"] = f"{requests[0].client_order_id} "

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "client_order_id") in paths


def test_broker_response_artifact_schema_rejects_malformed_timestamps(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-time")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-schema-time-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["broker_timestamp"] = "June 2, 2026"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "broker_timestamp") in paths


def test_broker_response_artifact_schema_rejects_nonpositive_submitted_quantity(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-submitted")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper account symbol permission mismatch",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["submitted_quantity"] = 0.0

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "submitted_quantity") in paths


@pytest.mark.parametrize(
    ("status", "fill_quantity", "fill_price"),
    [
        (BrokerOrderStatus.ACCEPTED, None, None),
        (BrokerOrderStatus.PARTIALLY_FILLED, 0.5, 100.0),
        (BrokerOrderStatus.FILLED, 1.0, 100.0),
    ],
)
def test_broker_response_artifact_schema_rejects_nonpositive_accepted_quantity_for_active_statuses(
    tmp_path: Path,
    status: BrokerOrderStatus,
    fill_quantity: float | None,
    fill_price: float | None,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"schema-recon-accepted-{status.value}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=f"paper-schema-accepted-{status.value}",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=fill_quantity,
                fill_price=fill_price,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["accepted_quantity"] = 0.0

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "accepted_quantity") in paths


def test_broker_response_artifact_schema_rejects_empty_rejection_reason_for_rejected_status(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-rejected-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper account symbol permission mismatch",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["rejection_reason"] = ""

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "rejection_reason") in paths


def test_broker_response_artifact_schema_rejects_blank_rejection_reason_for_rejected_status(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-rejected-blank-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper account symbol permission mismatch",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["rejection_reason"] = "   "

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "rejection_reason") in paths


def test_broker_response_artifact_schema_rejects_empty_reason_for_unknown_status(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-unknown-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.UNKNOWN,
                submitted_quantity=1.0,
                rejection_reason="broker response status could not be mapped",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["rejection_reason"] = ""

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "rejection_reason") in paths


def test_broker_response_artifact_schema_rejects_blank_reason_for_unknown_status(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-unknown-blank-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.UNKNOWN,
                submitted_quantity=1.0,
                rejection_reason="broker response status could not be mapped",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["rejection_reason"] = "   "

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "rejection_reason") in paths


@pytest.mark.parametrize(
    ("status", "accepted_quantity", "fill_quantity", "fill_price"),
    [
        (BrokerOrderStatus.ACCEPTED, 1.0, None, None),
        (BrokerOrderStatus.PARTIALLY_FILLED, 1.0, 0.5, 100.0),
        (BrokerOrderStatus.FILLED, 1.0, 1.0, 100.0),
        (BrokerOrderStatus.CANCELED, None, None, None),
        (BrokerOrderStatus.EXPIRED, None, None, None),
    ],
)
def test_broker_response_artifact_schema_rejects_empty_broker_order_id_for_broker_statuses(
    tmp_path: Path,
    status: BrokerOrderStatus,
    accepted_quantity: float | None,
    fill_quantity: float | None,
    fill_price: float | None,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"schema-recon-broker-id-{status.value}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=f"paper-schema-broker-id-{status.value}",
                submitted_quantity=1.0,
                accepted_quantity=accepted_quantity,
                fill_quantity=fill_quantity,
                fill_price=fill_price,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["broker_order_id"] = ""

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "broker_order_id") in paths


def test_broker_response_artifact_schema_rejects_blank_broker_order_id_for_broker_status(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-blank-broker-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-schema-broker-id-blank",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["broker_order_id"] = "   "

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "broker_order_id") in paths


def test_broker_response_artifact_schema_rejects_broker_order_id_whitespace(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-response-broker-id-whitespace")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-schema-broker-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["broker_order_id"] = "paper-schema-broker-1 "

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "broker_order_id") in paths


@pytest.mark.parametrize(
    ("status", "fill_quantity"),
    [
        (BrokerOrderStatus.PARTIALLY_FILLED, 0.5),
        (BrokerOrderStatus.FILLED, 1.0),
    ],
)
def test_broker_response_artifact_schema_rejects_nonpositive_fill_quantity_for_fill_statuses(
    tmp_path: Path,
    status: BrokerOrderStatus,
    fill_quantity: float,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"schema-recon-fill-qty-{status.value}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=f"paper-schema-fill-qty-{status.value}",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=fill_quantity,
                fill_price=100.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 0.0

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "fill_quantity") in paths


@pytest.mark.parametrize(
    ("status", "fill_quantity"),
    [
        (BrokerOrderStatus.PARTIALLY_FILLED, 0.5),
        (BrokerOrderStatus.FILLED, 1.0),
    ],
)
def test_broker_response_artifact_schema_rejects_nonpositive_fill_price_for_fill_statuses(
    tmp_path: Path,
    status: BrokerOrderStatus,
    fill_quantity: float,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"schema-recon-fill-price-{status.value}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=f"paper-schema-fill-price-{status.value}",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=fill_quantity,
                fill_price=100.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_price"] = 0.0

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "fill_price") in paths


@pytest.mark.parametrize(
    ("status", "broker_order_id", "accepted_quantity", "rejection_reason"),
    [
        (BrokerOrderStatus.ACCEPTED, "paper-schema-no-fill-accepted", 1.0, None),
        (
            BrokerOrderStatus.REJECTED,
            None,
            None,
            "paper account symbol permission mismatch",
        ),
    ],
)
def test_broker_response_artifact_schema_rejects_fill_quantity_for_nonfill_statuses(
    tmp_path: Path,
    status: BrokerOrderStatus,
    broker_order_id: str | None,
    accepted_quantity: float | None,
    rejection_reason: str | None,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"schema-recon-no-fill-qty-{status.value}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=broker_order_id,
                submitted_quantity=1.0,
                accepted_quantity=accepted_quantity,
                fill_quantity=None,
                fill_price=None,
                rejection_reason=rejection_reason,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 0.5

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "fill_quantity") in paths


@pytest.mark.parametrize(
    ("status", "broker_order_id", "accepted_quantity", "rejection_reason"),
    [
        (BrokerOrderStatus.ACCEPTED, "paper-schema-no-price-accepted", 1.0, None),
        (
            BrokerOrderStatus.REJECTED,
            None,
            None,
            "paper account symbol permission mismatch",
        ),
    ],
)
def test_broker_response_artifact_schema_rejects_fill_price_for_nonfill_statuses(
    tmp_path: Path,
    status: BrokerOrderStatus,
    broker_order_id: str | None,
    accepted_quantity: float | None,
    rejection_reason: str | None,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"schema-recon-no-fill-price-{status.value}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=broker_order_id,
                submitted_quantity=1.0,
                accepted_quantity=accepted_quantity,
                fill_quantity=None,
                fill_price=None,
                rejection_reason=rejection_reason,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_price"] = 100.0

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "fill_price") in paths


@pytest.mark.parametrize(
    ("status", "field_name", "field_value", "broker_order_id", "rejection_reason"),
    [
        (BrokerOrderStatus.REJECTED, "accepted_quantity", 1.0, None, "broker rejected order"),
        (BrokerOrderStatus.REJECTED, "fees", 0.01, None, "broker rejected order"),
        (BrokerOrderStatus.UNKNOWN, "accepted_quantity", 1.0, None, "unmapped broker status"),
        (BrokerOrderStatus.UNKNOWN, "fill_quantity", 0.5, None, "unmapped broker status"),
        (BrokerOrderStatus.UNKNOWN, "fill_price", 100.0, None, "unmapped broker status"),
        (BrokerOrderStatus.UNKNOWN, "fees", 0.01, None, "unmapped broker status"),
        (BrokerOrderStatus.CANCELED, "fill_quantity", 0.5, "paper-canceled-schema", None),
        (BrokerOrderStatus.CANCELED, "fill_price", 100.0, "paper-canceled-schema", None),
        (BrokerOrderStatus.EXPIRED, "fill_quantity", 0.5, "paper-expired-schema", None),
        (BrokerOrderStatus.EXPIRED, "fill_price", 100.0, "paper-expired-schema", None),
    ],
)
def test_broker_response_artifact_schema_rejects_status_forbidden_positive_fields(
    tmp_path: Path,
    status: BrokerOrderStatus,
    field_name: str,
    field_value: float,
    broker_order_id: str | None,
    rejection_reason: str | None,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"schema-response-forbidden-{status.value}-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=broker_order_id,
                submitted_quantity=1.0,
                accepted_quantity=None,
                fill_quantity=None,
                fill_price=None,
                fees=None,
                rejection_reason=rejection_reason,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0][field_name] = field_value

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, field_name) in paths


def test_broker_response_artifact_schema_rejects_live_flag_mismatch(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-mismatch")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["live_submission"] = True

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("live_submission",) in paths


def test_broker_response_artifact_schema_requires_live_account_for_live_mode(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-recon-live-account")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
        account_mode="live",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["account_mode"] = "paper"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("account_mode",) in paths


def test_broker_response_artifact_schema_rejects_live_account_for_non_live_mode(tmp_path: Path):
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=[],
        responses=[],
        output=output,
        adapter="schema-paper-live-account",
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["account_mode"] = "live"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("account_mode",) in paths


def test_broker_response_artifact_schema_rejects_unknown_account_mode(tmp_path: Path):
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=[],
        responses=[],
        output=output,
        adapter="schema-response-unknown-account",
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["account_mode"] = "simulation"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("account_mode",) in paths


def test_broker_response_artifact_schema_rejects_row_account_mode_mismatch(tmp_path: Path):
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=[],
        responses=[
            BrokerResponse(
                client_order_id="schema-response-row-account-mode",
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-schema-row-account-mode-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=None,
                fill_price=None,
                fees=0.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=output,
        adapter="schema-response-row-account-mode",
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["account_mode"] = "none"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "account_mode") in paths


def test_broker_response_artifact_schema_rejects_live_response_account_for_non_live_mode(tmp_path: Path):
    output = tmp_path / "broker_response_artifact.json"
    write_broker_response_artifact(
        requests=[],
        responses=[
            BrokerResponse(
                client_order_id="paper-response-account-1",
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper row in paper artifact",
                account_mode="paper",
            )
        ],
        output=output,
        adapter="schema-paper-response-account",
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["account_mode"] = "live"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "account_mode") in paths


def test_broker_response_artifact_schema_requires_live_response_accounts_for_live_mode(tmp_path: Path):
    output = tmp_path / "broker_response_artifact.json"
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-live-response-account")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="schema test")])
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper row in live artifact",
                account_mode="live",
            )
        ],
        output=output,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
        account_mode="live",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["responses"][0]["account_mode"] = "paper"

    errors = sorted(_validator("broker_response_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("responses", 0, "account_mode") in paths


def test_broker_handoff_artifact_schema_validates_writer_output(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))

    _validator("broker_handoff_artifact.schema.json").validate(payload)


def test_broker_handoff_artifact_schema_rejects_mode_flag_mismatch(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-mismatch")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["live_submission"] = True
    payload["orders"][0]["submit_live"] = True

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("live_submission",) in paths
    assert ("orders", 0, "submit_live") in paths


def test_broker_handoff_artifact_schema_rejects_order_adapter_mode_mismatch(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-order-mode")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["orders"][0]["adapter_mode"] = "live_human_approved"
    payload["orders"][0]["account_mode"] = "live"
    payload["orders"][0]["submit_live"] = True
    payload["orders"][0]["approval_status"] = "approved"

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("orders", 0, "adapter_mode") in paths


def test_broker_handoff_artifact_schema_rejects_limit_order_without_limit_price(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-limit-price")
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="schema test")],
        tmp_path,
    )
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["orders"][0]["limit_price"] = None

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("orders", 0, "limit_price") in paths


def test_broker_handoff_artifact_schema_rejects_market_order_with_limit_price(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-market-price")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["orders"][0]["limit_price"] = 100.0

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("orders", 0, "limit_price") in paths


def test_broker_handoff_artifact_schema_rejects_unsupported_time_in_force(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-tif")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["orders"][0]["time_in_force"] = "banana"

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("orders", 0, "time_in_force") in paths


def test_broker_handoff_artifact_schema_rejects_symbol_whitespace(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-symbol-whitespace")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["orders"][0]["symbol"] = "AAPL "

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("orders", 0, "symbol") in paths


def test_broker_handoff_artifact_schema_rejects_client_order_id_whitespace(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-client-id-whitespace")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["orders"][0]["client_order_id"] = f"{payload['orders'][0]['client_order_id']} "

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("orders", 0, "client_order_id") in paths


def test_broker_handoff_artifact_schema_requires_live_account_for_live_mode(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-live-handoff-account")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["adapter_mode"] = "live_human_approved"
    payload["account_mode"] = "paper"
    payload["paper_only"] = False
    payload["live_submission"] = True
    payload["manual_approval_required"] = False
    payload["orders"][0]["adapter_mode"] = "live_human_approved"
    payload["orders"][0]["account_mode"] = "paper"
    payload["orders"][0]["submit_live"] = True
    payload["orders"][0]["approval_status"] = "approved"

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("account_mode",) in paths
    assert ("orders", 0, "account_mode") in paths


def test_broker_handoff_artifact_schema_rejects_live_account_for_non_live_mode(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-paper-live-account")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["account_mode"] = "live"
    payload["orders"][0]["account_mode"] = "live"

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("account_mode",) in paths
    assert ("orders", 0, "account_mode") in paths


def test_broker_handoff_artifact_schema_rejects_unknown_account_mode(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-unknown-account")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["account_mode"] = "simulation"

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("account_mode",) in paths


@pytest.mark.parametrize(
    ("field_path", "expected_path"),
    [
        (("adapter",), ("adapter",)),
        (("orders", 0, "client_order_id"), ("orders", 0, "client_order_id")),
        (("orders", 0, "symbol"), ("orders", 0, "symbol")),
        (("orders", 0, "reason"), ("orders", 0, "reason")),
    ],
)
def test_broker_handoff_artifact_schema_rejects_blank_text_fields(
    tmp_path: Path, field_path: tuple[object, ...], expected_path: tuple[object, ...]
):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-blank-text")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = "   "

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert expected_path in paths


def test_broker_handoff_artifact_schema_rejects_adapter_whitespace(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-handoff-adapter-whitespace")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["adapter"] = f"{payload['adapter']} "

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("adapter",) in paths


def test_broker_handoff_artifact_schema_rejects_order_account_mode_mismatch(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(
        client_prefix="schema-handoff-row-account-mode",
        safety=BrokerSafetyConfig(account_mode="paper"),
    )
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["orders"][0]["account_mode"] = "none"

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("orders", 0, "account_mode") in paths


def test_broker_handoff_artifact_schema_rejects_live_kill_switch(tmp_path: Path):
    adapter = AlpacaPaperExportAdapter(client_prefix="schema-live-kill-switch")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="schema test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["adapter_mode"] = "live_human_approved"
    payload["account_mode"] = "live"
    payload["paper_only"] = False
    payload["live_submission"] = True
    payload["manual_approval_required"] = False
    payload["kill_switch"] = True
    payload["orders"][0]["adapter_mode"] = "live_human_approved"
    payload["orders"][0]["account_mode"] = "live"
    payload["orders"][0]["submit_live"] = True
    payload["orders"][0]["approval_status"] = "approved"

    errors = sorted(_validator("broker_handoff_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("kill_switch",) in paths


def test_broker_approval_artifact_schema_validates_writer_output():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )

    _validator("broker_approval_artifact.schema.json").validate(payload)


def test_broker_approval_validator_rejects_now_without_timezone():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-runtime-naive-now-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )

    errors = validate_broker_approval_artifact(payload, now="2026-05-31T12:30:00")

    assert "now must be an ISO timestamp with timezone" in errors


def test_broker_approval_artifact_schema_requires_request_hash_binding():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-unbound-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["request_artifact_hash"] = None

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("request_artifact_hash",) in paths


def test_broker_approval_artifact_schema_rejects_malformed_request_hash():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-bad-hash-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["request_artifact_hash"] = "sha256:demo-redacted-request-hash"

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert errors
    assert list(errors[0].path) == ["request_artifact_hash"]


def test_broker_approval_artifact_schema_rejects_malformed_timestamps():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-bad-time-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["approved_at"] = "May 31, noon"
    payload["expires_at"] = "tomorrow"

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("approved_at",) in paths
    assert ("expires_at",) in paths


def test_broker_approval_artifact_schema_requires_expiry():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-null-expiry-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["expires_at"] = None

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("expires_at",) in paths


def test_broker_approval_artifact_schema_requires_live_account_mode():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-paper-account-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["account_mode"] = "paper"

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)

    assert errors
    assert list(errors[0].path) == ["account_mode"]


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_path"),
    [
        ("approval_id", "   ", ("approval_id",)),
        ("approved_by", "   ", ("approved_by",)),
        ("approval_reason", "   ", ("approval_reason",)),
        ("allowed_symbols", ["   "], ("allowed_symbols", 0)),
        ("allowed_symbols", ["AAPL "], ("allowed_symbols", 0)),
    ],
)
def test_broker_approval_artifact_schema_rejects_blank_text_fields(
    field_name: str, field_value: object, expected_path: tuple[object, ...]
):
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-blank-text-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload[field_name] = field_value

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert expected_path in paths


def test_broker_approval_artifact_schema_rejects_approval_id_whitespace():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-id-whitespace",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["approval_id"] = "approval-schema-id-whitespace "

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("approval_id",) in paths


def test_broker_approval_artifact_schema_rejects_approved_by_whitespace():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-operator-id-whitespace",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["approved_by"] = "operator-7 "

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert ("approved_by",) in paths


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("allowed_symbols", ["AAPL", "AAPL"]),
        ("allowed_order_types", ["market", "market"]),
    ],
)
def test_broker_approval_artifact_schema_rejects_duplicate_scopes(field_name: str, field_value: list[str]):
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=2500.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-schema-duplicate-scope-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload[field_name] = field_value

    errors = sorted(_validator("broker_approval_artifact.schema.json").iter_errors(payload), key=lambda err: err.path)
    paths = {tuple(error.path) for error in errors}

    assert (field_name,) in paths


def test_all_example_benchmark_submissions_match_schema_and_runtime_validator():
    validator = _validator("benchmark_submission.schema.json")

    for path in sorted((ROOT / "examples/benchmark_submissions").rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validator.validate(payload)
        _, errors = validate_submission_file(path)

        assert errors == [], path


def test_reproduction_report_validator_rejects_failed_required_commands(tmp_path: Path):
    payload = _minimal_reproduction_report()
    payload["commands"][0]["returncode"] = 2
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = reproduction_validator.validate_reproduction_report(payload)
    result = subprocess.run(
        [sys.executable, "scripts/validate_reproduction_report.py", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert "command trajectory returned 2" in errors
    assert result.returncode == 1
    assert "command trajectory returned 2" in result.stdout


def test_reproduction_report_validator_accepts_complete_manifest(tmp_path: Path):
    payload = _minimal_reproduction_report()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert reproduction_validator.validate_reproduction_report(payload) == []

    result = subprocess.run(
        [sys.executable, "scripts/validate_reproduction_report.py", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Valid reproduction report" in result.stdout


def test_reproduction_report_validator_reports_malformed_json(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text('{"schema": ', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_reproduction_report.py", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid reproduction report" in result.stdout
    assert "reproduction report must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def test_reproduction_report_validator_has_no_dependency_fallback(monkeypatch):
    payload = _minimal_reproduction_report()
    monkeypatch.setattr(reproduction_validator, "Draft202012Validator", None)

    assert reproduction_validator.validate_reproduction_report(payload) == []

    broken = dict(payload)
    del broken["commands"]
    errors = reproduction_validator.validate_reproduction_report(broken)

    assert "missing required fields: commands" in errors

    malformed = _minimal_reproduction_report()
    malformed["commands"][0] = {"id": "trajectory"}
    errors = reproduction_validator.validate_reproduction_report(malformed)

    assert "commands[0] missing required fields: argv" in errors


def _validator(schema_name: str) -> Draft202012Validator:
    schema = _load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _load_schema(schema_name: str) -> dict[str, Any]:
    return json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))


def _json_round_trip(value: object) -> Any:
    return json.loads(json.dumps(value, default=_json_default))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _minimal_reproduction_report() -> dict[str, Any]:
    return {
        "schema": "tradearena_external_reproduction_pack_v1",
        "created_at": "2026-05-23T00:00:00+00:00",
        "repository": "https://github.com/weich97/TreLLM-public",
        "commit_or_tag": "v0.2.0",
        "git_status_short": "",
        "python": {
            "version": "3.12.0",
            "implementation": "CPython",
            "executable": "python",
            "platform": "test",
        },
        "commands": [
            {
                "id": "trajectory",
                "description": "Generate trajectory",
                "argv": ["python", "examples/audit_trajectory_walkthrough.py"],
                "returncode": 0,
            }
        ],
        "artifacts": [
            {
                "path": "outputs/examples/audit_walkthrough_trajectory.json",
                "exists": True,
                "bytes": 100,
                "sha256": "sha256:" + "0" * 64,
            }
        ],
        "trajectory_hash": {
            "path": "outputs/examples/audit_walkthrough_trajectory.json",
            "file_sha256": "sha256:" + "1" * 64,
            "scenario_id": "audit_walkthrough",
            "reproducibility_hash": "sha256:" + "2" * 64,
        },
        "live_api_used": False,
        "market_data_used": "deterministic synthetic data",
        "private_fills_used": False,
    }
