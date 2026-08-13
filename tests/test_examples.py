from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import tradearena.tools.broker_capability as broker_capability_validator
from tradearena.tools.broker_capability import validate_broker_adapter_capability
from tradearena.tools.live_readiness import validate_live_readiness_preflight_bundle_file

ROOT = Path(__file__).resolve().parents[1]


def test_examples_readme_section_numbers_are_sequential():
    text = (ROOT / "examples/README.md").read_text(encoding="utf-8")
    numbers = [int(match) for match in re.findall(r"^## (\d+)\.", text, flags=re.MULTILINE)]

    assert numbers == list(range(1, len(numbers) + 1))


def test_ashare_market_rules_demo_outputs_rule_events():
    _run_example("examples/ashare_market_rules_demo.py")
    summary = _read_json("outputs/examples/ashare_market_rules_summary.json")

    assert summary["summary"]["proposals"] == 5
    assert summary["summary"]["blocked"] >= 3
    assert summary["summary"]["clipped"] == 1
    assert (ROOT / "outputs/examples/ashare_market_rules.svg").exists()


def test_crisis_snapshot_demo_builds_gallery_from_tracked_artifacts():
    _run_example("examples/crisis_snapshot_demo.py")
    summary = _read_json("outputs/examples/crisis_snapshot_summary.json")

    assert summary["rows"] >= 20
    assert "deepseek-v4-pro" in summary["models"]
    assert "gpt-5.5" in summary["models"]
    assert (ROOT / "outputs/examples/crisis_snapshot_gallery.html").exists()


def test_akshare_csv_reuse_demo_uses_standard_csv_provider():
    _run_example("examples/akshare_csv_reuse_demo.py")
    summary = _read_json("outputs/examples/akshare_csv_reuse_summary.json")

    assert summary["provider_reused"] == "CsvMarketDataProvider"
    assert summary["symbols"] == ["600519.SS", "300750.SZ"]
    assert summary["steps"] == 10
    assert (ROOT / "outputs/examples/akshare_csv_reuse.svg").exists()


def test_llm_cache_replay_demo_summarizes_cached_frontier_rows():
    _run_example("examples/llm_cache_replay_demo.py")
    summary = _read_json("outputs/examples/llm_cache_replay_summary.json")

    assert summary["rows"] >= 100
    assert summary["timestamp_masked_rows"] == summary["rows"]
    assert summary["parsed_response_rate"] > 0.9
    assert summary["raw_cache_tracked_in_repo"] is False
    assert summary["redaction"]["raw_prompts_included"] is False
    assert "poe:gpt-5.5" in summary["provider_model_counts"]


def test_paper_design_demo_suite_builds_advanced_artifacts():
    subprocess.run([sys.executable, "scripts/run_paper_design_demos.py"], cwd=ROOT, check=True)

    assert (ROOT / "outputs/examples/experiment_design_index.html").exists()
    assert (ROOT / "outputs/examples/paper_design_index.html").exists()
    assert (ROOT / "outputs/examples/execution_realism_sweep.svg").exists()
    assert (ROOT / "outputs/examples/portfolio_markowitz.svg").exists()
    assert (ROOT / "outputs/examples/representation_signature.svg").exists()
    assert (ROOT / "outputs/examples/custom_plugin.svg").exists()


def test_execution_realism_sweep_includes_high_spread_preset():
    _run_example("examples/execution_realism_sweep_demo.py")
    summary = _read_json("outputs/examples/execution_realism_sweep_summary.json")
    rows = {row["case"]: row for row in summary["rows"]}

    assert "high_spread" in rows
    assert rows["high_spread"]["spread_bps"] > 0
    assert rows["high_spread"]["fill_rate"] >= 0.75
    assert rows["high_spread"]["slippage_cost"] > rows["realistic_default"]["slippage_cost"]
    assert "bid-ask spread" in summary["interpretation"]["high_spread"]
    assert (ROOT / "outputs/examples/execution_realism_sweep.csv").exists()
    assert (ROOT / "outputs/examples/execution_realism_sweep.svg").exists()


def test_visual_tour_demo_generates_animated_artifacts():
    _run_example("examples/visual_tour_demo.py")
    summary = _read_json("outputs/examples/visual_tour_summary.json")

    assert summary["api_free"] is True
    assert summary["requires_live_market_data"] is False
    assert (ROOT / "outputs/examples/visual_tour_index.html").exists()

    for filename in (
        "visual_tour_audit_lifecycle.gif",
        "visual_tour_execution_realism.gif",
        "visual_tour_diagnostics_loop.gif",
    ):
        path = ROOT / "outputs/examples" / filename
        assert path.exists()
        assert 0 < path.stat().st_size < 1_500_000


def test_extension_walkthrough_demo_shows_modular_contribution_path():
    _run_example("examples/extension_walkthrough_demo.py")
    summary = _read_json("outputs/examples/extension_walkthrough_summary.json")

    assert summary["custom_modules"] == {
        "analyst": "GapVolumeAnalyst",
        "risk_manager": "VolatilityCircuitBreakerRisk",
        "evaluator": "ExtensionCoverageEvaluator",
    }
    assert summary["reused_core_modules"]["order_simulator"] == "realistic-order-simulator"
    assert summary["metrics"]["extension_custom_signal_count"] > 0
    assert summary["metrics"]["extension_circuit_breaker_blocks"] > 0
    assert summary["metrics"]["risk_lifecycle_coverage"] == 1.0
    assert (ROOT / "outputs/examples/extension_walkthrough.svg").exists()


def test_retail_planner_demo_builds_paper_planning_report():
    _run_example("examples/retail_planner_demo.py")
    summary = _read_json("outputs/examples/retail_planning_summary.json")

    assert summary["api_free"] is True
    assert summary["live_trading"] is False
    assert summary["manual_approval_required"] is True
    assert summary["scenarios"]["ordinary_stock_etf_plan"]["futures_margin_estimates"] == 0
    assert summary["scenarios"]["experienced_futures_overlay"]["futures_margin_estimates"] == 1
    assert "MCL" in summary["scenarios"]["experienced_futures_overlay"]["blocked_symbols"]
    assert (ROOT / "outputs/examples/retail_planning_report.html").exists()
    assert (ROOT / "outputs/examples/retail_planning_allocation.svg").exists()


def test_operator_runbook_demo_builds_live_ready_checklist():
    _run_example("examples/operator_runbook_demo.py")
    summary = _read_json("outputs/examples/operator_runbook/summary.json")
    runbook = (ROOT / "outputs/examples/operator_runbook/operator_runbook.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_operator_runbook_v0.1"
    assert summary["live_submission"] is False
    assert summary["default_mode"] == "offline_export"
    assert summary["manual_approval_required"] is True
    assert summary["kill_switch_required"] is True
    assert summary["approval_expiry_required"] is True
    assert summary["artifact_retention_required"] is True
    assert summary["incident_owner_required"] is True
    assert summary["incident_response_drill"] == {
        "kill_switch_action": "disable_broker_submission",
        "rollback_owner": "operator",
        "affected_account_mode": "paper",
        "affected_symbols": ["AAPL", "MSFT"],
        "artifact_retention_path": "outputs/examples/operator_runbook/incident_drill/",
        "reenable_approval_gate": "new approval artifact bound to a newly reviewed handoff hash",
    }
    assert {item["id"] for item in summary["checklist"]} >= {
        "mode-boundary",
        "approval-expiry",
        "kill-switch",
        "reconciliation",
        "rollback",
        "artifact-retention",
        "incident-owner",
    }
    assert any("validate-live-readiness" in command for command in summary["verification_commands"])
    assert "TreLLM Operator Runbook Checklist" in runbook
    assert "does not authorize live submission" in runbook
    assert "incident owner" in runbook
    assert "disable_broker_submission" in runbook
    assert "new approval artifact bound to a newly reviewed handoff hash" in runbook


def test_operator_runbook_validator_rejects_live_submission(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    artifact = tmp_path / "operator_runbook.json"
    payload["live_submission"] = True
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "False was expected" in result.stdout


def test_operator_runbook_validator_requires_live_readiness_preflight_command(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        command for command in payload["verification_commands"] if "validate-live-readiness" not in command
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "verification_commands must include validate-live-readiness" in result.stdout


def test_operator_runbook_validator_requires_incident_reenable_gate(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["incident_response_drill"].pop("reenable_approval_gate")
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "'reenable_approval_gate' is a required property" in result.stdout


def test_operator_runbook_validator_rejects_retention_path_parent_traversal(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["incident_response_drill"]["artifact_retention_path"] = (
        "outputs/examples/operator_runbook/../private_logs/"
    )
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "incident_response_drill.artifact_retention_path must stay under outputs/examples/operator_runbook/" in result.stdout


def test_operator_runbook_validator_rejects_owner_whitespace(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["incident_response_drill"]["rollback_owner"] = "operator "
    payload["checklist"][0]["owner"] = "operator "
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "'operator ' does not match" in result.stdout


def test_operator_runbook_validator_rejects_affected_symbol_whitespace(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["incident_response_drill"]["affected_symbols"] = ["AAPL "]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "'AAPL ' does not match" in result.stdout


def test_operator_runbook_validator_requires_each_critical_checklist_id(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
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
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "checklist missing required ids: reconciliation" in result.stdout


def test_operator_runbook_validator_rejects_placeholder_live_readiness_command(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = ["echo validate-live-readiness"]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert (
        "verification_commands must not include unsupported validate-live-readiness commands"
    ) in result.stdout


def test_operator_runbook_validator_rejects_invalid_live_readiness_now_timestamp(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now not-a-time"
        )
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert (
        "verification_commands validate-live-readiness --now value must be an ISO timestamp "
        "with timezone"
    ) in result.stdout


def test_operator_runbook_validator_rejects_unknown_live_readiness_args(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now 2026-05-31T12:30:00Z --dry-run"
        )
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert (
        "verification_commands validate-live-readiness command must only include "
        "the preflight bundle path, --now, and its timestamp"
    ) in result.stdout


def test_operator_runbook_validator_rejects_absolute_live_readiness_bundle_path(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "C:/Users/Administrator/preflight_bundle.json "
            "--now 2026-05-31T12:30:00Z"
        )
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert (
        "verification_commands validate-live-readiness preflight bundle path "
        "must be portable and relative"
    ) in result.stdout


def test_operator_runbook_validator_rejects_multiple_live_readiness_commands(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now 2026-05-31T12:30:00Z"
        ),
        (
            "python -m tradearena.cli validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now 2026-05-31T12:35:00Z"
        ),
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert (
        "verification_commands must include exactly one supported "
        "validate-live-readiness command"
    ) in result.stdout


def test_operator_runbook_validator_rejects_extra_placeholder_live_readiness_command(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now 2026-05-31T12:30:00Z"
        ),
        "echo validate-live-readiness",
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert (
        "verification_commands must not include unsupported validate-live-readiness commands"
    ) in result.stdout


def test_operator_runbook_validator_rejects_chained_live_readiness_command(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now 2026-05-31T12:30:00Z ; echo ok"
        )
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "verification_commands validate-live-readiness command must not contain shell chaining" in result.stdout


def test_operator_runbook_validator_rejects_windows_chained_live_readiness_command(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now 2026-05-31T12:30:00Z & echo ok"
        )
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "verification_commands validate-live-readiness command must not contain shell chaining" in result.stdout


def test_operator_runbook_validator_rejects_compact_windows_chained_live_readiness_command(tmp_path: Path):
    _run_example("examples/operator_runbook_demo.py")
    payload = _read_json("outputs/examples/operator_runbook/summary.json")
    payload["verification_commands"] = [
        (
            "tradearena validate-live-readiness "
            "outputs/examples/live_readiness_preflight/preflight_bundle.json "
            "--now 2026-05-31T12:30:00Z&echo ok"
        )
    ]
    artifact = tmp_path / "operator_runbook.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operator_runbook_artifact.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid operator runbook artifact" in result.stdout
    assert "verification_commands validate-live-readiness command must not contain shell chaining" in result.stdout


def test_operator_runbook_cli_validates_demo_artifact():
    _run_example("examples/operator_runbook_demo.py")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-operator-runbook",
            "outputs/examples/operator_runbook/summary.json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Valid operator runbook artifact" in result.stdout


def test_broker_capability_manifest_demo_builds_review_boundary():
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    report = (ROOT / "outputs/examples/broker_capability_manifest/capability_manifest.md").read_text(encoding="utf-8")

    assert payload["schema"] == "trellm_broker_adapter_capability_v0.1"
    assert payload["default_mode"] == "offline_export"
    assert payload["supports_live_submission"] is False
    assert payload["live_submission_default"] is False
    assert payload["credential_policy"]["no_credentials_in_repo"] is True
    assert payload["safety_controls"]["kill_switch_required"] is True
    assert "TreLLM Broker Adapter Capability Manifest" in report
    assert "not permission to submit live orders" in report


def test_broker_capability_validator_rejects_adapter_id_whitespace():
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload["adapter_id"] = f"{payload['adapter_id']} "

    assert "adapter_id must not contain whitespace" in validate_broker_adapter_capability(payload)


def test_broker_capability_validator_rejects_live_without_required_controls(tmp_path: Path):
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload["supports_live_submission"] = True
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["requires_credentials"] = True
    payload["safety_controls"]["kill_switch_required"] = False
    artifact = tmp_path / "broker_capability.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_broker_adapter_capability.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid broker adapter capability manifest" in result.stdout
    assert "live-capable adapters must set safety_controls.kill_switch_required to true" in result.stdout


def test_broker_capability_validator_rejects_live_without_live_network_access(tmp_path: Path):
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload["supports_live_submission"] = True
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["requires_credentials"] = True
    payload["credential_policy"]["env_vars"] = ["BROKER_API_KEY"]
    artifact = tmp_path / "broker_capability.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_broker_adapter_capability.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid broker adapter capability manifest" in result.stdout
    assert "live-capable adapters must set network_access to required_for_live" in result.stdout


def test_broker_capability_validator_rejects_credential_env_var_whitespace():
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload["supports_live_submission"] = True
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["network_access"] = "required_for_live"
    payload["adapter_kind"] = "live_capable"
    payload["requires_credentials"] = True
    payload["credential_policy"]["env_vars"] = ["BROKER_API_KEY "]

    assert "credential_policy.env_vars must not contain whitespace" in validate_broker_adapter_capability(payload)


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        (
            "supported_modes",
            ["offline_export "],
            "supported_modes must contain only supported broker adapter modes",
        ),
        ("account_modes", ["paper "], "account_modes must contain only none, paper, or live"),
        ("supported_order_types", ["market", "stop"], "supported_order_types must contain only market or limit"),
        (
            "supported_time_in_force",
            ["day", "gtd"],
            "supported_time_in_force must contain only cls, day, fok, gtc, ioc, or opg",
        ),
    ],
)
def test_broker_capability_fallback_rejects_invalid_scope_lists(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: list[str],
    expected_error: str,
):
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload[field] = value
    monkeypatch.setattr(broker_capability_validator, "Draft202012Validator", None)

    assert expected_error in broker_capability_validator.validate_broker_adapter_capability(payload)


def test_broker_capability_validator_rejects_live_support_without_live_adapter_kind(tmp_path: Path):
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload["supports_live_submission"] = True
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["network_access"] = "required_for_live"
    payload["requires_credentials"] = True
    payload["credential_policy"]["env_vars"] = ["BROKER_API_KEY"]
    artifact = tmp_path / "broker_capability.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_broker_adapter_capability.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid broker adapter capability manifest" in result.stdout
    assert "live-capable adapters must set adapter_kind to live_capable" in result.stdout


def test_broker_capability_validator_rejects_live_adapter_kind_without_live_support(tmp_path: Path):
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload["adapter_kind"] = "live_capable"
    artifact = tmp_path / "broker_capability.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_broker_adapter_capability.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid broker adapter capability manifest" in result.stdout
    assert "adapter_kind live_capable requires supports_live_submission true" in result.stdout


def test_broker_capability_validator_requires_env_vars_when_credentials_are_required(tmp_path: Path):
    _run_example("examples/broker_capability_manifest_demo.py")
    payload = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    payload["supports_live_submission"] = True
    payload["supported_modes"].append("live_human_approved")
    payload["account_modes"].append("live")
    payload["requires_credentials"] = True
    payload["network_access"] = "required_for_live"
    payload["credential_policy"]["env_vars"] = []
    artifact = tmp_path / "broker_capability.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_broker_adapter_capability.py", str(artifact)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid broker adapter capability manifest" in result.stdout
    assert "credential_policy.env_vars must list credential environment variables when credentials are required" in result.stdout


def test_broker_capability_cli_validates_demo_artifact():
    _run_example("examples/broker_capability_manifest_demo.py")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-broker-capability",
            "outputs/examples/broker_capability_manifest/capability_manifest.json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Valid broker adapter capability manifest" in result.stdout


def test_mock_paper_sandbox_client_demo_uses_injected_client_only():
    _run_example("examples/mock_paper_sandbox_client_demo.py")
    summary = _read_json("outputs/examples/mock_paper_sandbox_client/summary.json")
    response = _read_json("outputs/examples/mock_paper_sandbox_client/paper_sandbox_response_artifact.json")
    request = _read_json("outputs/examples/mock_paper_sandbox_client/alpaca_paper_orders.json")

    assert summary["adapter_mode"] == "paper_sandbox"
    assert summary["account_mode"] == "paper"
    assert summary["live_submission"] is False
    assert summary["default_network_call"] is False
    assert summary["mock_client_calls"] == 1
    assert summary["response_count"] == 2
    assert summary["missing_response_count"] == 0
    assert summary["unmatched_response_count"] == 0
    assert request["adapter_mode"] == "paper_sandbox"
    assert request["account_mode"] == "paper"
    assert response["adapter_mode"] == "paper_sandbox"
    assert response["account_mode"] == "paper"
    assert response["live_submission"] is False
    assert response["reconciliation"]["accepted_count"] == 2


def test_live_readiness_preflight_demo_links_broker_safety_artifacts():
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    summary = _read_json("outputs/examples/live_readiness_preflight/preflight_summary.json")

    assert bundle["schema"] == "trellm_live_readiness_preflight_v0.1"
    assert bundle["capability_manifest"] == "outputs/examples/broker_capability_manifest/capability_manifest.json"
    assert bundle["handoff_artifact"] == "outputs/examples/broker_approval_safety/dry_run_orders.json"
    assert bundle["response_artifact"] == "outputs/examples/live_readiness_preflight/preflight_response_artifact.json"
    assert summary["ready"] is True
    assert summary["components"]["capability_manifest"]["valid"] is True
    assert summary["components"]["approval_binding"]["valid"] is True


def test_live_readiness_preflight_rejects_parent_traversal_component_path(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    outside_capability_path = tmp_path.parent / f"{tmp_path.name}_capability_manifest.json"
    outside_capability_path.write_text(
        json.dumps(_read_json(bundle["capability_manifest"])),
        encoding="utf-8",
    )
    bundle["capability_manifest"] = f"../{outside_capability_path.name}"
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert "capability_manifest path must not contain parent traversal" in result.stdout


def test_live_readiness_preflight_rejects_absolute_component_path(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    capability_path = tmp_path / "capability_manifest.json"
    capability_path.write_text(json.dumps(_read_json(bundle["capability_manifest"])), encoding="utf-8")
    bundle["capability_manifest"] = str(capability_path)
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert "capability_manifest path must be relative" in result.stdout


def test_live_readiness_preflight_rejects_drive_qualified_component_path(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    bundle["capability_manifest"] = "C:capability_manifest.json"
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert "capability_manifest path must not be drive-qualified" in result.stdout


@pytest.mark.parametrize(
    ("component_path", "expected_error"),
    [
        ("nested\\capability_manifest.json", "capability_manifest path must use forward slashes"),
        ("capability manifest.json", "capability_manifest path must not contain whitespace"),
    ],
)
def test_live_readiness_preflight_rejects_nonportable_component_path_text(
    tmp_path: Path, component_path: str, expected_error: str
):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    destination = tmp_path / component_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(_read_json(bundle["capability_manifest"])), encoding="utf-8")
    bundle["capability_manifest"] = component_path
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert expected_error in result.stdout


def test_live_readiness_preflight_validator_rejects_mode_not_declared_by_capability(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    capability = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    capability["supported_modes"] = ["offline_export"]
    capability_path = tmp_path / "capability.json"
    capability_path.write_text(json.dumps(capability), encoding="utf-8")

    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    bundle["capability_manifest"] = capability_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert "handoff_artifact.adapter_mode dry_run is not declared" in result.stdout
    assert "response_artifact.adapter_mode dry_run is not declared" in result.stdout


def test_live_readiness_preflight_rejects_adapter_not_named_by_capability(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    capability = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    capability["adapter_id"] = "stale-paper-adapter"
    capability_path = tmp_path / "capability.json"
    capability_path.write_text(json.dumps(capability), encoding="utf-8")

    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    bundle["capability_manifest"] = capability_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    runbook = _read_json(bundle["operator_runbook_artifact"])
    runbook["verification_commands"] = [
        (
            f"tradearena validate-live-readiness {bundle_path.name} "
            "--now 2026-05-31T12:30:00Z"
        )
    ]
    runbook_path = tmp_path / "operator_runbook.json"
    runbook_path.write_text(json.dumps(runbook), encoding="utf-8")
    bundle["operator_runbook_artifact"] = runbook_path.name
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "handoff_artifact.adapter dry-run-broker-adapter does not match "
        "capability_manifest.adapter_id stale-paper-adapter"
    ) in result.stdout


def test_live_readiness_preflight_rejects_order_terms_not_declared_by_capability(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    capability = _read_json("outputs/examples/broker_capability_manifest/capability_manifest.json")
    capability["supported_order_types"] = ["market"]
    capability["supported_time_in_force"] = ["gtc"]
    capability_path = tmp_path / "capability.json"
    capability_path.write_text(json.dumps(capability), encoding="utf-8")

    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    bundle["capability_manifest"] = capability_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    runbook = _read_json(bundle["operator_runbook_artifact"])
    runbook["verification_commands"] = [
        (
            f"tradearena validate-live-readiness {bundle_path.name} "
            "--now 2026-05-31T12:30:00Z"
        )
    ]
    runbook_path = tmp_path / "operator_runbook.json"
    runbook_path.write_text(json.dumps(runbook), encoding="utf-8")
    bundle["operator_runbook_artifact"] = runbook_path.name
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "handoff_artifact.orders[0].order_type limit is not declared in "
        "capability_manifest.supported_order_types"
    ) in result.stdout
    assert (
        "handoff_artifact.orders[0].time_in_force day is not declared in "
        "capability_manifest.supported_time_in_force"
    ) in result.stdout


def test_live_readiness_preflight_rejects_runbook_default_mode_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    runbook = _read_json(bundle["operator_runbook_artifact"])
    runbook["default_mode"] = "dry_run"
    runbook_path = tmp_path / "operator_runbook.json"
    runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

    bundle["operator_runbook_artifact"] = runbook_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "operator_runbook_artifact.default_mode dry_run does not match "
        "capability_manifest.default_mode offline_export"
    ) in result.stdout


def test_live_readiness_preflight_rejects_safety_control_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    capability = _read_json(bundle["capability_manifest"])
    capability["safety_controls"]["kill_switch_required"] = False
    capability_path = tmp_path / "capability.json"
    capability_path.write_text(json.dumps(capability), encoding="utf-8")

    bundle["capability_manifest"] = capability_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "capability_manifest.safety_controls.kill_switch_required false does not satisfy "
        "operator_runbook_artifact.kill_switch_required true"
    ) in result.stdout


def test_live_readiness_preflight_rejects_reconciliation_control_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    capability = _read_json(bundle["capability_manifest"])
    capability["safety_controls"]["reconciliation_required"] = False
    capability_path = tmp_path / "capability.json"
    capability_path.write_text(json.dumps(capability), encoding="utf-8")

    bundle_path = tmp_path / "preflight_bundle.json"
    runbook = _read_json(bundle["operator_runbook_artifact"])
    runbook["verification_commands"] = [
        (
            f"tradearena validate-live-readiness {bundle_path.name} "
            "--now 2026-05-31T12:30:00Z"
        )
    ]
    runbook_path = tmp_path / "operator_runbook.json"
    runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

    bundle["capability_manifest"] = capability_path.name
    bundle["operator_runbook_artifact"] = runbook_path.name
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "capability_manifest.safety_controls.reconciliation_required false does not satisfy "
        "operator_runbook_artifact checklist id reconciliation"
    ) in result.stdout


def test_live_readiness_preflight_rejects_runbook_incident_drill_scope_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    runbook = _read_json(bundle["operator_runbook_artifact"])
    runbook["incident_response_drill"]["affected_account_mode"] = "live"
    runbook["incident_response_drill"]["affected_symbols"] = ["MSFT"]

    bundle_path = tmp_path / "preflight_bundle.json"
    runbook["verification_commands"] = [
        (
            f"tradearena validate-live-readiness {bundle_path.name} "
            "--now 2026-05-31T12:30:00Z"
        )
    ]
    runbook_path = tmp_path / "operator_runbook.json"
    runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

    bundle["operator_runbook_artifact"] = runbook_path.name
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "operator_runbook_artifact.incident_response_drill.affected_account_mode live "
        "does not cover handoff_artifact.account_mode paper"
    ) in result.stdout
    assert (
        "operator_runbook_artifact.incident_response_drill.affected_symbols missing "
        "handoff symbols: AAPL"
    ) in result.stdout


def test_live_readiness_preflight_rejects_response_account_mode_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response["account_mode"] = "none"
    for row in response["responses"]:
        row["account_mode"] = "none"
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert "response_artifact.account_mode none does not match handoff_artifact.account_mode paper" in result.stdout


def test_live_readiness_preflight_rejects_response_adapter_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response["adapter"] = "paper-sandbox-adapter"
    response["adapter_mode"] = "paper_sandbox"
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "response_artifact.adapter paper-sandbox-adapter does not match "
        "handoff_artifact.adapter dry-run-broker-adapter"
    ) in result.stdout
    assert (
        "response_artifact.adapter_mode paper_sandbox does not match "
        "handoff_artifact.adapter_mode dry_run"
    ) in result.stdout


def test_live_readiness_preflight_rejects_unreviewed_response_client_order_id(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response["responses"][0]["client_order_id"] = "unreviewed-response-0001"
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "response_artifact.responses[0].client_order_id unreviewed-response-0001 "
        "is not present in handoff_artifact.orders"
    ) in result.stdout


def test_live_readiness_preflight_requires_response_for_each_handoff_order(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response["responses"] = []
    response["reconciliation"] = {
        "response_count": 0,
        "accepted_count": 0,
        "filled_count": 0,
        "partial_fill_count": 0,
        "canceled_count": 0,
        "expired_count": 0,
        "rejected_count": 0,
        "unknown_count": 0,
        "missing_response_count": 0,
        "unmatched_response_count": 0,
        "fill_ratio_mean": None,
    }
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "handoff_artifact.orders[0].client_order_id approval-demo-0001-aapl "
        "is missing from response_artifact.responses"
    ) in result.stdout


def test_live_readiness_preflight_rejects_response_quantity_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response["responses"][0]["submitted_quantity"] = 3.0
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    summary, errors = validate_live_readiness_preflight_bundle_file(bundle_path, now="2026-05-31T12:30:00Z")

    assert summary["ready"] is False
    assert (
        "response_artifact.responses[0].submitted_quantity 3.0 does not match "
        "handoff_artifact.orders quantity 2.0 for client_order_id approval-demo-0001-aapl"
    ) in errors


def test_live_readiness_preflight_rejects_stale_response_reconciliation_counts(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response["reconciliation"]["missing_response_count"] = 1
    response["reconciliation"]["unmatched_response_count"] = 1
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "response_artifact.reconciliation.missing_response_count 1 does not match "
        "handoff/response linkage count 0"
    ) in result.stdout
    assert (
        "response_artifact.reconciliation.unmatched_response_count 1 does not match "
        "handoff/response linkage count 0"
    ) in result.stdout


def test_live_readiness_preflight_requires_response_request_hash(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response.pop("request_artifact_hash", None)
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert "response_artifact.request_artifact_hash is required for live-readiness preflight" in result.stdout


def test_live_readiness_preflight_rejects_response_request_hash_mismatch(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    response = _read_json(bundle["response_artifact"])
    response["request_artifact_hash"] = "sha256:" + "0" * 64
    response_path = tmp_path / "broker_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    bundle["response_artifact"] = response_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert "response_artifact.request_artifact_hash does not match handoff_artifact hash" in result.stdout


def test_live_readiness_preflight_requires_bundle_checked_at_to_match_cli_now(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    bundle["approval_checked_at"] = "2026-05-31T12:00:00Z"
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "approval_checked_at 2026-05-31T12:00:00Z does not match validation --now "
        "2026-05-31T12:30:00Z"
    ) in result.stdout


def test_live_readiness_preflight_requires_runbook_now_to_match_checked_at(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    runbook = _read_json(bundle["operator_runbook_artifact"])
    runbook["verification_commands"] = [
        command.replace("2026-05-31T12:30:00Z", "2026-05-31T12:00:00Z")
        for command in runbook["verification_commands"]
    ]
    runbook_path = tmp_path / "operator_runbook.json"
    runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

    bundle["operator_runbook_artifact"] = runbook_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "operator_runbook_artifact verification command --now 2026-05-31T12:00:00Z "
        "does not match preflight approval_checked_at 2026-05-31T12:30:00Z"
    ) in result.stdout


def test_live_readiness_preflight_requires_runbook_command_to_reference_current_bundle(tmp_path: Path):
    _run_example("examples/live_readiness_preflight_demo.py")
    bundle = _read_json("outputs/examples/live_readiness_preflight/preflight_bundle.json")
    runbook = _read_json(bundle["operator_runbook_artifact"])
    runbook["verification_commands"] = [
        command.replace(
            "outputs/examples/live_readiness_preflight/preflight_bundle.json",
            "outputs/examples/live_readiness_preflight/stale_preflight_bundle.json",
        )
        for command in runbook["verification_commands"]
    ]
    runbook_path = tmp_path / "operator_runbook.json"
    runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

    bundle["operator_runbook_artifact"] = runbook_path.name
    bundle_path = tmp_path / "preflight_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_readiness_preflight.py",
            str(bundle_path),
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid live-readiness preflight bundle" in result.stdout
    assert (
        "operator_runbook_artifact verification command bundle path "
        "outputs/examples/live_readiness_preflight/stale_preflight_bundle.json "
        "does not match current preflight bundle"
    ) in result.stdout


def test_live_readiness_preflight_cli_validates_demo_bundle():
    _run_example("examples/live_readiness_preflight_demo.py")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-live-readiness",
            "outputs/examples/live_readiness_preflight/preflight_bundle.json",
            "--now",
            "2026-05-31T12:30:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Valid live-readiness preflight bundle" in result.stdout


def test_showcase_index_can_be_built_from_existing_or_missing_artifacts():
    tracked_result_paths = (
        ROOT / "docs/results/benchmark_v0_2.md",
        ROOT / "docs/results/quality_decomposition/quality_decomposition_aggregate.csv",
    )
    tracked_results_before = {path: path.read_text(encoding="utf-8") for path in tracked_result_paths}

    subprocess.run([sys.executable, "scripts/run_showcase.py", "--reuse-existing"], cwd=ROOT, check=True)

    tracked_results_after = {path: path.read_text(encoding="utf-8") for path in tracked_result_paths}
    assert tracked_results_after == tracked_results_before

    html = (ROOT / "outputs/examples/showcase.html").read_text(encoding="utf-8")
    assert "TreLLM Showcase" in html
    assert "Experiment-design demos" in html
    assert "Animated visual tour" in html
    assert "Agent Autopsy Dashboard" in html
    assert "Custom plugin extension" in html
    assert "Contributor extension walkthrough" in html
    assert "Retail planning sandbox" in html
    assert "Dry-run broker adapter" in html
    assert "Broker capability manifest" in html
    assert "Broker approval safety" in html
    assert "Operator runbook checklist" in html
    assert "Live-readiness preflight bundle" in html


def test_demo_artifact_contract_runs_required_validators(tmp_path: Path):
    _run_example("examples/broker_response_reconciliation_demo.py")
    manifest = tmp_path / "demo_artifacts.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "test"',
                "artifacts:",
                "  - id: broker_recon_contract",
                "    command: python examples/broker_response_reconciliation_demo.py",
                "    required_outputs:",
                "      - outputs/examples/broker_response_reconciliation/alpaca_paper_orders.json",
                "    required_validators:",
                (
                    "      - python scripts/validate_broker_handoff_artifact.py "
                    "outputs/examples/broker_response_reconciliation/alpaca_paper_orders.json"
                ),
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "scripts/validate_demo_artifacts.py", "--manifest", str(manifest)],
        cwd=ROOT,
        check=True,
    )

    broken_manifest = tmp_path / "broken_demo_artifacts.yaml"
    broken_manifest.write_text(
        "\n".join(
            [
                'version: "test"',
                "artifacts:",
                "  - id: broker_recon_contract",
                "    command: python examples/broker_response_reconciliation_demo.py",
                "    required_outputs:",
                "      - outputs/examples/broker_response_reconciliation/alpaca_paper_orders.json",
                "    required_validators:",
                (
                    "      - python scripts/validate_broker_response_artifact.py "
                    "outputs/examples/broker_response_reconciliation/alpaca_paper_orders.json"
                ),
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "scripts/validate_demo_artifacts.py", "--manifest", str(broken_manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "validator failed" in result.stdout


def test_demo_artifact_contract_checks_summary_verification_commands(tmp_path: Path):
    _run_example("examples/broker_approval_safety_demo.py")
    manifest = tmp_path / "demo_artifacts.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "test"',
                "artifacts:",
                "  - id: broker_approval_contract",
                "    command: python examples/broker_approval_safety_demo.py",
                "    required_outputs:",
                "      - outputs/examples/broker_approval_safety/summary.json",
                "    required_json_fields:",
                "      - outputs/examples/broker_approval_safety/summary.json:verification_commands",
                "    required_validators:",
                "      - python scripts/validate_broker_handoff_artifact.py outputs/examples/broker_approval_safety/dry_run_orders.json",
                "      - python scripts/hash_broker_handoff_artifact.py outputs/examples/broker_approval_safety/dry_run_orders.json",
                (
                    "      - python scripts/validate_broker_approval_artifact.py "
                    "outputs/examples/broker_approval_safety/broker_approval_artifact.json "
                    "--now 2026-05-31T12:30:00Z"
                ),
                (
                    "      - python scripts/validate_broker_approval_binding.py "
                    "outputs/examples/broker_approval_safety/broker_approval_artifact.json "
                    "outputs/examples/broker_approval_safety/dry_run_orders.json "
                    "--now 2026-05-31T12:30:00Z"
                ),
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, "scripts/validate_demo_artifacts.py", "--manifest", str(manifest)],
        cwd=ROOT,
        check=True,
    )

    broken_manifest = tmp_path / "broken_demo_artifacts.yaml"
    broken_manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "python scripts/hash_broker_handoff_artifact.py",
            "python scripts/validate_broker_handoff_artifact.py",
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "scripts/validate_demo_artifacts.py", "--manifest", str(broken_manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "verification_commands do not match required_validators" in result.stdout


def test_demo_artifact_contract_reports_malformed_required_json(tmp_path: Path):
    broken_json = ROOT / "outputs/examples/demo_artifact_contract_malformed_test.json"
    manifest = tmp_path / "demo_artifacts.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "test"',
                "artifacts:",
                "  - id: malformed_json_contract",
                "    command: python examples/quickstart.py",
                "    required_outputs:",
                "      - outputs/examples/demo_artifact_contract_malformed_test.json",
                "    required_json_fields:",
                "      - outputs/examples/demo_artifact_contract_malformed_test.json:summary.status",
            ]
        ),
        encoding="utf-8",
    )
    broken_json.parent.mkdir(parents=True, exist_ok=True)
    broken_json.write_text('{"summary": ', encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/validate_demo_artifacts.py", "--manifest", str(manifest)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    finally:
        broken_json.unlink(missing_ok=True)

    assert result.returncode == 1
    assert "Demo artifact contract failed" in result.stdout
    assert "invalid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def _run_example(path: str) -> None:
    subprocess.run([sys.executable, path], cwd=ROOT, check=True)


def _read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))
