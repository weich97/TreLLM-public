from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest

from tradearena.core.domain import Order, OrderType, Side
from tradearena.factory import build_default_system, default_registry
from tradearena.planning import load_holdings_csv
from tradearena.tools import (
    AlpacaPaperExportAdapter,
    BrokerAdapter,
    BrokerAdapterContractError,
    BrokerAdapterMode,
    BrokerApproval,
    BrokerOrderStatus,
    BrokerResponse,
    BrokerSafetyConfig,
    DryRunBrokerAdapter,
    FuturesContractMetadata,
    FuturesRollRiskEngine,
    broker_approval_from_artifact,
    broker_handoff_artifact_hash,
    broker_safety_from_approval_artifact,
    build_broker_approval_artifact,
    reconcile_broker_responses,
    validate_broker_approval_artifact,
    validate_broker_approval_artifact_file,
    validate_broker_approval_request_binding,
    validate_broker_handoff_artifact,
    validate_broker_handoff_artifact_file,
    validate_broker_response_artifact,
    validate_broker_response_artifact_file,
    write_broker_response_artifact,
)

ROOT = Path(__file__).resolve().parents[1]


def test_alpaca_paper_export_adapter_requires_human_approval(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="unit")
    result = adapter.write([Order("AAPL", Side.BUY, 3.5, reason="unit test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))

    assert result["order_count"] == 1
    assert payload["schema"] == "tradearena_broker_handoff_artifact_v0.1"
    assert payload["adapter_mode"] == "offline_export"
    assert payload["account_mode"] == "none"
    assert payload["live_submission"] is False
    assert payload["manual_approval_required"] is True
    assert payload["orders"][0]["adapter_mode"] == "offline_export"
    assert payload["orders"][0]["approval_status"] == "requires_human_approval"
    assert validate_broker_handoff_artifact(payload) == []


def test_broker_handoff_artifact_validator_and_cli_reject_mode_mismatch(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-validate")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))

    subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-broker-handoff", str(artifact)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "scripts/validate_broker_handoff_artifact.py", str(artifact)],
        cwd=ROOT,
        check=True,
    )

    payload["orders"][0]["submit_live"] = True
    broken = tmp_path / "broken_alpaca_paper_orders.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    errors = validate_broker_handoff_artifact(payload)
    result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-broker-handoff", str(broken)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert "orders[0].submit_live must match live_human_approved mode" in errors
    assert result.returncode == 1
    assert "orders[0].submit_live must match live_human_approved mode" in result.stdout


def test_broker_handoff_artifact_rejects_order_account_mode_mismatch(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-account-mode")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["account_mode"] = "paper"
    payload["orders"][0]["account_mode"] = "live"

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[0].account_mode must match artifact account_mode" in errors


def test_broker_handoff_writer_rejects_live_account_for_non_live_mode(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="handoff-live-account-non-live",
        safety=BrokerSafetyConfig(account_mode="live", max_quantity=2.0, allowed_symbols=("AAPL",)),
    )

    try:
        adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "non-live handoff artifacts must not use account_mode live" in str(exc)
    else:
        raise AssertionError("expected non-live handoff account_mode live failure")


def test_broker_handoff_artifact_rejects_live_account_for_non_live_mode():
    payload = {
        "schema": "tradearena_broker_handoff_artifact_v0.1",
        "adapter": "dry-run-unit-adapter",
        "adapter_mode": "dry_run",
        "account_mode": "live",
        "paper_only": True,
        "live_submission": False,
        "manual_approval_required": True,
        "kill_switch": False,
        "orders": [],
    }

    assert "non-live handoff artifacts must not use account_mode live" in validate_broker_handoff_artifact(payload)


def test_broker_handoff_writer_rejects_unknown_account_mode(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="handoff-unknown-account",
        safety=BrokerSafetyConfig(account_mode="simulation", max_quantity=2.0, allowed_symbols=("AAPL",)),
    )

    try:
        adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "account_mode must be one of none, paper, live" in str(exc)
    else:
        raise AssertionError("expected unsupported handoff account_mode failure")


def test_broker_handoff_artifact_rejects_unknown_account_mode():
    payload = {
        "schema": "tradearena_broker_handoff_artifact_v0.1",
        "adapter": "dry-run-unit-adapter",
        "adapter_mode": "dry_run",
        "account_mode": "simulation",
        "paper_only": True,
        "live_submission": False,
        "manual_approval_required": True,
        "kill_switch": False,
        "orders": [],
    }

    assert "account_mode must be one of none, paper, live" in validate_broker_handoff_artifact(payload)


def test_paper_sandbox_adapter_skeleton_uses_mock_client_without_default_network(tmp_path):
    from tradearena.tools import PaperSandboxAdapterSkeleton

    class MockPaperClient:
        def __init__(self) -> None:
            self.calls = 0

        def submit_paper_orders(self, requests):
            self.calls += 1
            return [
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.ACCEPTED,
                    broker_order_id="mock-paper-accepted-1",
                    submitted_quantity=requests[0].quantity,
                    accepted_quantity=requests[0].quantity,
                    submitted_at="2026-05-31T16:00:00Z",
                    broker_timestamp="2026-05-31T16:00:01Z",
                    account_mode="paper",
                )
            ]

    factory_calls = 0
    client = MockPaperClient()

    def client_factory():
        nonlocal factory_calls
        factory_calls += 1
        return client

    adapter = PaperSandboxAdapterSkeleton(client_factory=client_factory, client_prefix="mock-paper")
    handoff = adapter.write([Order("AAPL", Side.BUY, 1.0, reason="paper skeleton")], tmp_path)
    handoff_payload, handoff_errors = validate_broker_handoff_artifact_file(handoff["json"])

    assert factory_calls == 0
    assert client.calls == 0
    assert handoff_errors == []
    assert handoff_payload["adapter_mode"] == BrokerAdapterMode.PAPER_SANDBOX.value
    assert handoff_payload["account_mode"] == "paper"
    assert handoff_payload["live_submission"] is False

    result = adapter.submit_paper([Order("AAPL", Side.BUY, 1.0, reason="paper skeleton")], tmp_path)
    response_payload, response_errors = validate_broker_response_artifact_file(result["response_artifact"])

    assert factory_calls == 1
    assert client.calls == 1
    assert response_errors == []
    assert response_payload["adapter_mode"] == BrokerAdapterMode.PAPER_SANDBOX.value
    assert response_payload["account_mode"] == "paper"
    assert response_payload["live_submission"] is False
    assert response_payload["responses"][0]["status"] == BrokerOrderStatus.ACCEPTED.value
    assert response_payload["reconciliation"]["accepted_count"] == 1


@pytest.mark.parametrize(
    ("field_path", "expected_error"),
    [
        (("adapter",), "adapter must be non-empty"),
        (("orders", 0, "client_order_id"), "orders[0].client_order_id must be non-empty"),
        (("orders", 0, "symbol"), "orders[0].symbol must be non-empty"),
        (("orders", 0, "reason"), "orders[0].reason must be non-empty"),
    ],
)
def test_broker_handoff_artifact_rejects_blank_text_fields(tmp_path, field_path, expected_error):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-blank-text")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = "   "

    assert expected_error in validate_broker_handoff_artifact(payload)


def test_broker_handoff_artifact_writer_rejects_adapter_name_whitespace(tmp_path):
    class WhitespaceAdapter(AlpacaPaperExportAdapter):
        name = "alpaca-paper-export-adapter "

    adapter = WhitespaceAdapter(client_prefix="handoff-writer-adapter-whitespace")

    try:
        adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "adapter must not contain whitespace" in str(exc)
    else:
        raise AssertionError("expected handoff adapter name whitespace to be rejected by writer")


def test_broker_handoff_artifact_rejects_adapter_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-adapter-whitespace")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["adapter"] = f"{payload['adapter']} "

    errors = validate_broker_handoff_artifact(payload)

    assert "adapter must not contain whitespace" in errors


def test_broker_handoff_artifact_rejects_duplicate_client_order_ids(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-duplicate-client-id")
    adapter.write(
        [
            Order("AAPL", Side.BUY, 1.0, reason="unit test"),
            Order("MSFT", Side.BUY, 1.0, reason="unit test"),
        ],
        tmp_path,
    )
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["orders"][1]["client_order_id"] = payload["orders"][0]["client_order_id"]

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[1].client_order_id duplicates an earlier order" in errors


def test_broker_handoff_artifact_rejects_client_order_id_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-client-id-whitespace")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["orders"][0]["client_order_id"] = f"{payload['orders'][0]['client_order_id']} "

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[0].client_order_id must not contain whitespace" in errors


def test_broker_handoff_artifact_rejects_symbol_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-symbol-whitespace")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["orders"][0]["symbol"] = "AAPL "

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[0].symbol must not contain whitespace" in errors


def test_broker_handoff_artifact_rejects_limit_order_without_limit_price(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-limit-price")
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="unit test")],
        tmp_path,
    )
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["orders"][0]["limit_price"] = None

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[0].limit orders require a positive limit_price" in errors


def test_broker_handoff_artifact_rejects_market_order_with_limit_price(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-market-price")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["orders"][0]["limit_price"] = 100.0

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[0].market orders must not include limit_price" in errors


def test_broker_handoff_artifact_rejects_unsupported_time_in_force(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-time-in-force")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["orders"][0]["time_in_force"] = "banana"

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[0].time_in_force must be one of cls, day, fok, gtc, ioc, opg" in errors


def test_broker_handoff_writer_rejects_unsupported_time_in_force(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-writer-tif", time_in_force="banana")

    try:
        adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "time_in_force must be one of cls, day, fok, gtc, ioc, opg" in str(exc)
    else:
        raise AssertionError("expected unsupported time_in_force to be rejected by writer")


def test_broker_handoff_writer_rejects_client_prefix_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff prefix")

    try:
        adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "client_prefix must not contain whitespace" in str(exc)
    else:
        raise AssertionError("expected whitespace client_prefix to be rejected by writer")


@pytest.mark.parametrize("adapter_cls", [AlpacaPaperExportAdapter, DryRunBrokerAdapter])
@pytest.mark.parametrize(
    ("client_prefix", "expected_error"),
    [
        ("", "client_prefix must be non-empty"),
        (123, "client_prefix must be non-empty"),
    ],
)
def test_broker_handoff_writer_rejects_non_text_client_prefix(tmp_path, adapter_cls, client_prefix, expected_error):
    adapter = adapter_cls(client_prefix=client_prefix)

    try:
        adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert expected_error in str(exc)
    else:
        raise AssertionError("expected non-text client_prefix to be rejected by writer")


def test_broker_handoff_artifact_rejects_nonfinite_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="handoff-nonfinite")
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    artifact = tmp_path / "alpaca_paper_orders.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["orders"][0]["quantity"] = float("nan")

    errors = validate_broker_handoff_artifact(payload)

    assert "orders[0].quantity must be a positive finite number" in errors


def test_broker_safety_config_blocks_disallowed_orders(tmp_path):
    adapter = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            allowed_symbols=("MSFT",),
            max_quantity=2.0,
        )
    )

    try:
        adapter.write([Order("AAPL", Side.BUY, 3.5, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "allow-list" in str(exc)
    else:
        raise AssertionError("expected broker adapter allow-list failure")


def test_broker_safety_config_requires_reference_price_for_market_notional_limit(tmp_path):
    adapter = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            account_mode="paper",
            max_notional=100.0,
            max_quantity=10.0,
        )
    )

    try:
        adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "reference_price" in str(exc)
    else:
        raise AssertionError("expected reference price failure for max_notional market order")


@pytest.mark.parametrize(
    ("field_name", "safety"),
    [
        ("max_quantity", BrokerSafetyConfig(account_mode="paper", max_quantity=0.0)),
        ("max_notional", BrokerSafetyConfig(account_mode="paper", max_notional=0.0, max_quantity=10.0)),
    ],
)
def test_broker_safety_config_rejects_nonpositive_limits(tmp_path, field_name, safety):
    adapter = AlpacaPaperExportAdapter(safety=safety)

    try:
        adapter.write(
            [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="unit test")],
            tmp_path,
        )
    except BrokerAdapterContractError as exc:
        assert f"{field_name} must be a positive finite number" in str(exc)
    else:
        raise AssertionError(f"expected nonpositive {field_name} safety limit failure")


def test_dry_run_broker_adapter_writes_validated_handoff_without_live_submission(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="dry-unit",
        safety=BrokerSafetyConfig(
            account_mode="paper",
            max_quantity=2.0,
            allowed_symbols=("AAPL",),
        ),
    )
    assert isinstance(adapter, BrokerAdapter)

    result = adapter.write([Order("AAPL", Side.BUY, 1.25, reason="dry run unit")], tmp_path)
    payload = json.loads((tmp_path / "dry_run_orders.json").read_text(encoding="utf-8"))

    assert result["order_count"] == 1
    assert result["adapter_mode"] == "dry_run"
    assert result["paper_only"] is True
    assert payload["adapter"] == "dry-run-broker-adapter"
    assert payload["adapter_mode"] == "dry_run"
    assert payload["live_submission"] is False
    assert payload["orders"][0]["submit_live"] is False
    assert validate_broker_handoff_artifact(payload) == []


def test_live_human_approved_mode_requires_approval_and_marks_live(tmp_path):
    missing_limits = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED)
    )
    try:
        missing_limits.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path / "limits")
    except BrokerAdapterContractError as exc:
        assert "max_notional and max_quantity" in str(exc)
    else:
        raise AssertionError("expected missing live limit failure")

    missing_approval = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            max_notional=1000.0,
            max_quantity=10.0,
        )
    )
    try:
        missing_approval.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path / "missing")
    except BrokerAdapterContractError as exc:
        assert "approved human approval record" in str(exc)
    else:
        raise AssertionError("expected missing approval failure")

    malformed_time_approval = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="not-a-timestamp",
                max_notional=1000.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )
    try:
        malformed_time_approval.write(
            [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
            tmp_path / "malformed-approval-time",
        )
    except BrokerAdapterContractError as exc:
        assert "approval approved_at must be an ISO timestamp with timezone" in str(exc)
    else:
        raise AssertionError("expected malformed live approval timestamp failure")

    non_string_time_approval = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at=123,
                max_notional=1000.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )
    try:
        non_string_time_approval.write(
            [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
            tmp_path / "non-string-approval-time",
        )
    except BrokerAdapterContractError as exc:
        assert "approval approved_at must be an ISO timestamp with timezone" in str(exc)
    else:
        raise AssertionError("expected non-string live approval timestamp failure")

    nonfinite_approval_notional = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=float("nan"),
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )
    try:
        nonfinite_approval_notional.write(
            [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
            tmp_path / "nonfinite-approval-notional",
        )
    except BrokerAdapterContractError as exc:
        assert "live_human_approved mode requires a positive finite approval max_notional" in str(exc)
    else:
        raise AssertionError("expected nonfinite approval max_notional failure")

    for allowed_symbols in ((), ("   ",)):
        unscoped_approval = AlpacaPaperExportAdapter(
            safety=BrokerSafetyConfig(
                mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
                account_mode="live",
                max_notional=1000.0,
                max_quantity=10.0,
                approval=BrokerApproval(
                    approval_status="approved",
                    approved_by="unit-operator",
                    approved_at="2026-05-31T12:00:00Z",
                    max_notional=1000.0,
                    allowed_symbols=allowed_symbols,
                    approval_reason="unit test approval",
                ),
            )
        )
        try:
            unscoped_approval.write(
                [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
                tmp_path / f"unscoped-approval-{len(allowed_symbols)}",
            )
        except BrokerAdapterContractError as exc:
            assert "approval allowed_symbols must be a non-empty list of symbols" in str(exc)
        else:
            raise AssertionError("expected unscoped live approval allowed_symbols failure")

    duplicate_symbol_approval = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=1000.0,
                allowed_symbols=("AAPL", "AAPL"),
                approval_reason="unit test approval",
            ),
        )
    )
    try:
        duplicate_symbol_approval.write(
            [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
            tmp_path / "duplicate-symbol-approval",
        )
    except BrokerAdapterContractError as exc:
        assert "approval allowed_symbols must not contain duplicates" in str(exc)
    else:
        raise AssertionError("expected duplicate live approval allowed_symbols failure")

    for field_name in ("approved_by", "approved_at", "approval_reason"):
        approval_kwargs = {
            "approval_status": "approved",
            "approved_by": "unit-operator",
            "approved_at": "2026-05-31T12:00:00Z",
            "max_notional": 1000.0,
            "allowed_symbols": ("AAPL",),
            "approval_reason": "unit test approval",
        }
        approval_kwargs[field_name] = "   "
        blank_approval = AlpacaPaperExportAdapter(
            safety=BrokerSafetyConfig(
                mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
                account_mode="live",
                max_notional=1000.0,
                max_quantity=10.0,
                approval=BrokerApproval(**approval_kwargs),
            )
        )
        try:
            blank_approval.write(
                [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
                tmp_path / f"blank-{field_name}",
            )
        except BrokerAdapterContractError as exc:
            assert "approved human approval record" in str(exc)
        else:
            raise AssertionError(f"expected blank approval {field_name} failure")

    unredacted_operator_approval = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="operator@example.com",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=100.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )
    try:
        unredacted_operator_approval.write(
            [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
            tmp_path / "unredacted-operator-approval",
        )
    except BrokerAdapterContractError as exc:
        assert "approved_by must be a redacted operator id, not an email address" in str(exc)
    else:
        raise AssertionError("expected unredacted live approval operator failure")

    approved = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=100.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )
    try:
        approved.write([Order("AAPL", Side.BUY, 1.0, reason="unit test")], tmp_path / "no-reference-price")
    except BrokerAdapterContractError as exc:
        assert "reference_price" in str(exc)
    else:
        raise AssertionError("expected live order reference price failure")

    too_large_for_approval = Order(
        "AAPL",
        Side.BUY,
        1.0,
        order_type=OrderType.LIMIT,
        limit_price=200.0,
        reason="unit test",
    )
    try:
        approved.write([too_large_for_approval], tmp_path / "approval-notional")
    except BrokerAdapterContractError as exc:
        assert "approval max_notional" in str(exc)
    else:
        raise AssertionError("expected approval max_notional failure")

    approved.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
        tmp_path / "approved",
    )
    payload = json.loads((tmp_path / "approved" / "alpaca_paper_orders.json").read_text(encoding="utf-8"))

    assert payload["adapter_mode"] == "live_human_approved"
    assert payload["account_mode"] == "live"
    assert payload["live_submission"] is True
    assert payload["manual_approval_required"] is False
    assert payload["orders"][0]["approval_status"] == "approved"


def test_live_human_approved_mode_validates_safety_even_without_orders(tmp_path):
    adapter = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED)
    )

    try:
        adapter.write([], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "live_human_approved mode requires max_notional and max_quantity limits" in str(exc)
    else:
        raise AssertionError("expected empty live handoff to validate live safety")


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_error"),
    [
        ("max_notional", float("nan"), "max_notional must be a positive finite number"),
        ("max_quantity", 0.0, "max_quantity must be a positive finite number"),
    ],
)
def test_live_human_approved_mode_rejects_invalid_limits_without_orders(
    tmp_path,
    field_name,
    field_value,
    expected_error,
):
    safety_kwargs = {
        "mode": BrokerAdapterMode.LIVE_HUMAN_APPROVED,
        "account_mode": "live",
        "max_notional": 1000.0,
        "max_quantity": 10.0,
        "approval": BrokerApproval(
            approval_status="approved",
            approved_by="unit-operator",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=1000.0,
            allowed_symbols=("AAPL",),
            approval_reason="unit test approval",
        ),
    }
    safety_kwargs[field_name] = field_value
    adapter = AlpacaPaperExportAdapter(safety=BrokerSafetyConfig(**safety_kwargs))

    try:
        adapter.write([], tmp_path / field_name)
    except BrokerAdapterContractError as exc:
        assert expected_error in str(exc)
    else:
        raise AssertionError(f"expected empty live handoff to reject invalid {field_name}")


@pytest.mark.parametrize(
    ("allowed_order_types", "expected_error"),
    [
        ((), "allowed_order_types must contain market or limit"),
        (([OrderType.MARKET],), "allowed_order_types must contain market or limit"),
        ((OrderType.MARKET, OrderType.MARKET), "allowed_order_types must not contain duplicates"),
    ],
)
def test_live_human_approved_mode_rejects_invalid_order_type_scope_without_orders(
    tmp_path,
    allowed_order_types,
    expected_error,
):
    adapter = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            allowed_order_types=allowed_order_types,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=1000.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )

    try:
        adapter.write([], tmp_path / "invalid-order-type-scope")
    except BrokerAdapterContractError as exc:
        assert expected_error in str(exc)
    else:
        raise AssertionError("expected empty live handoff to reject invalid allowed_order_types")


def test_live_human_approved_mode_rejects_kill_switch_without_orders(tmp_path):
    adapter = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            kill_switch=True,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=1000.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )

    try:
        adapter.write([], tmp_path)
    except BrokerAdapterContractError as exc:
        assert "broker adapter kill switch is enabled" in str(exc)
    else:
        raise AssertionError("expected kill switch to block empty live handoff")


def test_live_human_approved_handoff_requires_live_account_mode(tmp_path):
    adapter = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="paper",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=1000.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )

    try:
        adapter.write(
            [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=50.0, reason="unit test")],
            tmp_path,
        )
    except BrokerAdapterContractError as exc:
        assert "live_human_approved mode requires account_mode live" in str(exc)
    else:
        raise AssertionError("expected live account_mode failure")

    payload = {
        "schema": "tradearena_broker_handoff_artifact_v0.1",
        "adapter": "live-unit-adapter",
        "adapter_mode": "live_human_approved",
        "account_mode": "paper",
        "paper_only": False,
        "live_submission": True,
        "manual_approval_required": False,
        "kill_switch": False,
        "orders": [],
    }

    assert "account_mode must be live for live_human_approved broker handoff artifacts" in validate_broker_handoff_artifact(
        payload
    )


def test_live_human_approved_handoff_rejects_kill_switch_artifact(tmp_path):
    adapter = AlpacaPaperExportAdapter(
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="unit-operator",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=1000.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        )
    )
    adapter.write([], tmp_path)
    payload = json.loads((tmp_path / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    payload["kill_switch"] = True

    assert "live_human_approved handoff artifacts must not set kill_switch" in validate_broker_handoff_artifact(payload)


def test_broker_response_artifact_summarizes_reconciliation(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="recon")
    requests = adapter.convert(
        [
            Order("AAPL", Side.BUY, 2.0, reason="unit test"),
            Order("MSFT", Side.SELL, 1.0, reason="unit test"),
        ]
    )
    responses = [
        BrokerResponse(
            client_order_id=requests[0].client_order_id,
            status=BrokerOrderStatus.PARTIALLY_FILLED,
            broker_order_id="paper-1",
            submitted_quantity=2.0,
            accepted_quantity=2.0,
            fill_quantity=1.0,
            fill_price=190.0,
            fees=0.02,
            account_mode="paper",
        ),
        BrokerResponse(
            client_order_id="unknown-order",
            status=BrokerOrderStatus.REJECTED,
            submitted_quantity=1.0,
            rejection_reason="symbol not enabled",
            account_mode="paper",
        ),
    ]

    summary = reconcile_broker_responses(requests, responses)
    assert summary.response_count == 2
    assert summary.partial_fill_count == 1
    assert summary.rejected_count == 1
    assert summary.unmatched_response_count == 1
    assert summary.missing_response_count == 1
    assert summary.fill_ratio_mean == 0.5

    artifact = tmp_path / "broker_response.json"
    result = write_broker_response_artifact(
        requests=requests,
        responses=responses,
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))

    assert result["response_count"] == 2
    assert payload["schema"] == "tradearena_broker_response_artifact_v0.1"
    assert payload["live_submission"] is False
    assert payload["reconciliation"]["missing_response_count"] == 1
    assert payload["responses"][0]["status"] == "partially_filled"


def test_broker_response_artifact_writer_emits_validator_clean_defaults(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="writer-defaults")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"

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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))

    assert validate_broker_response_artifact(payload) == []


def test_broker_response_artifact_writer_records_request_artifact_hash(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-request-hash")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"

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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))

    assert payload["request_artifact_hash"] == "sha256:" + "1" * 64
    assert validate_broker_response_artifact(payload) == []


def test_broker_response_artifact_writer_rejects_malformed_request_artifact_hash(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-bad-request-hash")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    with pytest.raises(BrokerAdapterContractError, match="request_artifact_hash must be sha256"):
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
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
            request_artifact_hash="sha256:not-a-real-hash",
        )


def test_broker_response_artifact_writer_rejects_non_string_request_artifact_hash(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-non-string-request-hash")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    with pytest.raises(BrokerAdapterContractError, match="request_artifact_hash must be sha256"):
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
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
            request_artifact_hash=123,
        )


def test_broker_response_artifact_writer_rejects_submitted_quantity_mismatch(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-request-quantity")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=2.0,
                    rejection_reason="broker reported a different submitted quantity",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "submitted_quantity 2.0 does not match request quantity 1.0" in str(exc)
    else:
        raise AssertionError("expected submitted quantity mismatch failure")


def test_broker_response_artifact_writer_rejects_duplicate_request_ids(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-request-duplicate")
    requests = adapter.convert(
        [
            Order("AAPL", Side.BUY, 1.0, reason="unit test"),
            Order("MSFT", Side.SELL, 2.0, reason="unit test"),
        ]
    )
    duplicate_requests = [requests[0], replace(requests[1], client_order_id=requests[0].client_order_id)]

    try:
        write_broker_response_artifact(
            requests=duplicate_requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="duplicate request id should be rejected",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "requests[1].client_order_id duplicates an earlier request" in str(exc)
    else:
        raise AssertionError("expected duplicate request id failure")


def test_broker_response_artifact_writer_rejects_unknown_live_response_id(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-live-unknown-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id="external-live-order",
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="not from this reviewed live request",
                    account_mode="live",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].client_order_id external-live-order is not present in live request set" in str(exc)
    else:
        raise AssertionError("expected unknown live response client_order_id failure")


def test_broker_response_artifact_writer_rejects_account_mode_mismatch(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-account-binding")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="broker account mismatch",
                    account_mode="live",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].account_mode live does not match artifact account_mode paper" in str(exc)
    else:
        raise AssertionError("expected response account_mode mismatch failure")


def test_broker_response_artifact_writer_requires_live_account_for_live_mode(tmp_path):
    try:
        write_broker_response_artifact(
            requests=[],
            responses=[],
            output=tmp_path / "broker_response.json",
            adapter="live-writer-unit",
            adapter_mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "live_human_approved response artifacts require account_mode live" in str(exc)
    else:
        raise AssertionError("expected live response account_mode failure")


def test_broker_response_artifact_writer_rejects_live_account_for_non_live_mode(tmp_path):
    try:
        write_broker_response_artifact(
            requests=[],
            responses=[],
            output=tmp_path / "broker_response.json",
            adapter="paper-writer-unit",
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="live",
        )
    except BrokerAdapterContractError as exc:
        assert "non-live response artifacts must not use account_mode live" in str(exc)
    else:
        raise AssertionError("expected non-live response account_mode live failure")


def test_broker_response_artifact_writer_rejects_unknown_account_mode(tmp_path):
    try:
        write_broker_response_artifact(
            requests=[],
            responses=[],
            output=tmp_path / "broker_response.json",
            adapter="response-unknown-account",
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="simulation",
        )
    except BrokerAdapterContractError as exc:
        assert "account_mode must be one of none, paper, live" in str(exc)
    else:
        raise AssertionError("expected unsupported response account_mode failure")


def test_broker_response_artifact_writer_rejects_duplicate_client_order_ids(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-duplicate")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="first broker response",
                    account_mode="paper",
                ),
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="duplicate broker response",
                    account_mode="paper",
                ),
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[1].client_order_id duplicates an earlier response" in str(exc)
    else:
        raise AssertionError("expected duplicate client_order_id failure")


def test_broker_response_artifact_writer_rejects_duplicate_broker_order_ids(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-broker-duplicate")
    requests = adapter.convert(
        [
            Order("AAPL", Side.BUY, 1.0, reason="unit test"),
            Order("MSFT", Side.BUY, 1.0, reason="unit test"),
        ]
    )

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.ACCEPTED,
                    broker_order_id="paper-duplicate-broker",
                    submitted_quantity=1.0,
                    accepted_quantity=1.0,
                    account_mode="paper",
                ),
                BrokerResponse(
                    client_order_id=requests[1].client_order_id,
                    status=BrokerOrderStatus.ACCEPTED,
                    broker_order_id="paper-duplicate-broker",
                    submitted_quantity=1.0,
                    accepted_quantity=1.0,
                    account_mode="paper",
                ),
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[1].broker_order_id duplicates an earlier response" in str(exc)
    else:
        raise AssertionError("expected duplicate broker_order_id failure")


def test_broker_response_artifact_writer_requires_broker_order_id_for_accepted_responses(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-broker-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.ACCEPTED,
                    broker_order_id=None,
                    submitted_quantity=1.0,
                    accepted_quantity=1.0,
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].broker_order_id must be non-empty for accepted broker responses" in str(exc)
    else:
        raise AssertionError("expected missing broker_order_id failure")


def test_broker_response_artifact_writer_requires_rejection_reason_for_rejected_responses(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-rejection-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason=None,
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].rejection_reason must be non-empty for rejected responses" in str(exc)
    else:
        raise AssertionError("expected missing rejection_reason failure")


def test_broker_response_artifact_validator_and_cli_reject_count_mismatch(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="validate-recon")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.FILLED,
                broker_order_id="paper-filled-count-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=1.0,
                fill_price=190.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )

    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert validate_broker_response_artifact(payload) == []
    subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-broker-response", str(artifact)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "scripts/validate_broker_response_artifact.py", str(artifact)],
        cwd=ROOT,
        check=True,
    )

    payload["reconciliation"]["filled_count"] = 0
    broken = tmp_path / "broken_broker_response.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    errors = validate_broker_response_artifact(payload)
    result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-broker-response", str(broken)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert "reconciliation.filled_count must be 1; got 0" in errors
    assert result.returncode == 1
    assert "reconciliation.filled_count must be 1; got 0" in result.stdout


def test_broker_response_artifact_rejects_bad_fill_ratio_mean(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-ratio")
    requests = adapter.convert([Order("AAPL", Side.BUY, 2.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.PARTIALLY_FILLED,
                broker_order_id="paper-ratio-1",
                submitted_quantity=2.0,
                accepted_quantity=2.0,
                fill_quantity=1.0,
                fill_price=190.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )

    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["reconciliation"]["fill_ratio_mean"] = 0.25

    assert "reconciliation.fill_ratio_mean must be 0.5; got 0.25" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_impossible_unmatched_response_count(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-unmatched")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id="external-order",
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="not from this request",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )

    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["reconciliation"]["unmatched_response_count"] = 2

    assert (
        "reconciliation.unmatched_response_count cannot exceed response_count 1"
        in validate_broker_response_artifact(payload)
    )


def test_broker_response_artifact_rejects_impossible_fill_quantities(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-quantity")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.PARTIALLY_FILLED,
                broker_order_id="paper-impossible-fill-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=0.5,
                fill_price=190.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 2.0

    assert "responses[0].fill_quantity cannot exceed submitted_quantity" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_impossible_accepted_quantities(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-accepted-quantity")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-impossible-accepted-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["accepted_quantity"] = 2.0

    assert "responses[0].accepted_quantity cannot exceed submitted_quantity" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_rejects_fill_exceeding_accepted_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-fill-vs-accepted")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.PARTIALLY_FILLED,
                broker_order_id="paper-fill-vs-accepted-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=0.5,
                fill_price=190.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["accepted_quantity"] = 0.5
    payload["responses"][0]["fill_quantity"] = 1.0

    assert "responses[0].fill_quantity cannot exceed accepted_quantity" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_rejection_without_reason(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-rejection-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                rejection_reason="paper account symbol permission mismatch",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["rejection_reason"] = None

    assert "responses[0].rejection_reason must be non-empty for rejected responses" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_rejects_partial_fill_with_full_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-partial-full")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.PARTIALLY_FILLED,
                broker_order_id="paper-partial-full-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=0.5,
                fill_price=190.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 1.0

    assert "responses[0].partial fill_quantity must be less than submitted_quantity" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_rejects_filled_without_fill_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-filled-quantity")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.FILLED,
                broker_order_id="paper-filled-missing-quantity-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=1.0,
                fill_price=190.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = None

    assert "responses[0].filled responses require a positive fill_quantity" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_rejects_filled_with_partial_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-filled-partial")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.FILLED,
                broker_order_id="paper-filled-partial-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=1.0,
                fill_price=190.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 0.5

    assert "responses[0].filled fill_quantity must equal submitted_quantity" in validate_broker_response_artifact(
        payload
    )


@pytest.mark.parametrize(
    "status",
    [BrokerOrderStatus.PARTIALLY_FILLED, BrokerOrderStatus.FILLED],
)
def test_broker_response_artifact_rejects_fills_without_fill_price(tmp_path, status):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-{status.value}-price")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=f"paper-{status.value}-missing-price-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=0.5 if status is BrokerOrderStatus.PARTIALLY_FILLED else 1.0,
                fill_price=190.0,
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_price"] = None

    assert "responses[0].filled or partially_filled responses require a positive fill_price" in (
        validate_broker_response_artifact(payload)
    )


@pytest.mark.parametrize(
    ("status", "accepted_quantity", "fill_quantity", "expected_message"),
    [
        (
            BrokerOrderStatus.ACCEPTED,
            2.0,
            None,
            "responses[0].accepted_quantity cannot exceed submitted_quantity",
        ),
        (
            BrokerOrderStatus.PARTIALLY_FILLED,
            1.0,
            2.0,
            "responses[0].fill_quantity cannot exceed submitted_quantity",
        ),
        (
            BrokerOrderStatus.PARTIALLY_FILLED,
            0.5,
            1.0,
            "responses[0].fill_quantity cannot exceed accepted_quantity",
        ),
        (
            BrokerOrderStatus.PARTIALLY_FILLED,
            1.0,
            1.0,
            "responses[0].partial fill_quantity must be less than submitted_quantity",
        ),
        (
            BrokerOrderStatus.FILLED,
            1.0,
            0.5,
            "responses[0].filled fill_quantity must equal submitted_quantity",
        ),
    ],
)
def test_broker_response_artifact_writer_rejects_impossible_response_quantities(
    tmp_path,
    status,
    accepted_quantity,
    fill_quantity,
    expected_message,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-{status.value}-quantity")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=status,
                    broker_order_id=f"paper-writer-{status.value}-quantity-1",
                    submitted_quantity=1.0,
                    accepted_quantity=accepted_quantity,
                    fill_quantity=fill_quantity,
                    fill_price=190.0 if fill_quantity is not None else None,
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert expected_message in str(exc)
    else:
        raise AssertionError(f"expected {status.value} impossible quantity to be rejected by writer")


@pytest.mark.parametrize("status", [BrokerOrderStatus.PARTIALLY_FILLED, BrokerOrderStatus.FILLED])
@pytest.mark.parametrize("field_name", ["fill_quantity", "fill_price"])
@pytest.mark.parametrize("field_value", [None, 0.0])
def test_broker_response_artifact_writer_rejects_fills_without_positive_fill_fields(
    tmp_path,
    status,
    field_name,
    field_value,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-{status.value}-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": status,
        "broker_order_id": f"paper-writer-{status.value}-{field_name}-1",
        "submitted_quantity": 1.0,
        "accepted_quantity": 1.0,
        "fill_quantity": 0.5 if status is BrokerOrderStatus.PARTIALLY_FILLED else 1.0,
        "fill_price": 190.0,
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
        field_name: field_value,
    }

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        if field_name == "fill_quantity" and status is BrokerOrderStatus.FILLED:
            assert "responses[0].filled responses require a positive fill_quantity" in str(exc)
        elif field_name == "fill_quantity":
            assert "responses[0].partial fill_quantity must be positive" in str(exc)
        else:
            assert "responses[0].filled or partially_filled responses require a positive fill_price" in str(exc)
    else:
        raise AssertionError(f"expected {status.value} response {field_name} to be rejected by writer")


@pytest.mark.parametrize("field_name", ["submitted_at", "broker_timestamp"])
def test_broker_response_artifact_rejects_malformed_timestamps(tmp_path, field_name):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response = BrokerResponse(
        client_order_id=requests[0].client_order_id,
        status=BrokerOrderStatus.ACCEPTED,
        broker_order_id="paper-malformed-time-1",
        submitted_quantity=1.0,
        accepted_quantity=1.0,
        submitted_at="2026-06-02T09:30:00Z",
        broker_timestamp="2026-06-02T09:30:01Z",
        account_mode="paper",
    )
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[response],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0][field_name] = "June 2, 2026"

    assert f"responses[0].{field_name} must be an ISO timestamp with timezone" in (
        validate_broker_response_artifact(payload)
    )


@pytest.mark.parametrize("field_name", ["submitted_at", "broker_timestamp"])
def test_broker_response_artifact_writer_rejects_malformed_timestamps(tmp_path, field_name):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": BrokerOrderStatus.ACCEPTED,
        "broker_order_id": "paper-writer-malformed-time-1",
        "submitted_quantity": 1.0,
        "accepted_quantity": 1.0,
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
        field_name: "June 2, 2026",
    }

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].{field_name} must be an ISO timestamp with timezone" in str(exc)
    else:
        raise AssertionError(f"expected malformed {field_name} to be rejected by writer")


def test_broker_response_artifact_writer_rejects_broker_timestamp_before_submission(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-time-order")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.ACCEPTED,
                    broker_order_id="paper-writer-time-order-1",
                    submitted_quantity=1.0,
                    accepted_quantity=1.0,
                    submitted_at="2026-06-02T09:30:01Z",
                    broker_timestamp="2026-06-02T09:30:00Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].broker_timestamp must be at or after submitted_at" in str(exc)
    else:
        raise AssertionError("expected broker_timestamp before submitted_at to be rejected by writer")


def test_broker_response_artifact_rejects_duplicate_client_order_ids(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-duplicate-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-duplicate-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            ),
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    duplicate = dict(payload["responses"][0])
    duplicate["broker_order_id"] = "paper-duplicate-2"
    duplicate["submitted_at"] = "2026-06-02T09:30:02Z"
    duplicate["broker_timestamp"] = "2026-06-02T09:30:03Z"
    payload["responses"].append(duplicate)

    assert "responses[1].client_order_id duplicates an earlier response" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_requires_broker_order_id_for_accepted_responses(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-broker-order-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-broker-order-id-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["broker_order_id"] = None

    assert "responses[0].broker_order_id must be non-empty for accepted broker responses" in (
        validate_broker_response_artifact(payload)
    )


def test_broker_response_artifact_rejects_duplicate_broker_order_ids(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-duplicate-broker-id")
    requests = adapter.convert(
        [
            Order("AAPL", Side.BUY, 1.0, reason="unit test"),
            Order("MSFT", Side.BUY, 1.0, reason="unit test"),
        ]
    )
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-duplicate-broker-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            ),
            BrokerResponse(
                client_order_id=requests[1].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-duplicate-broker-2",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:02Z",
                broker_timestamp="2026-06-02T09:30:03Z",
                account_mode="paper",
            ),
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][1]["broker_order_id"] = payload["responses"][0]["broker_order_id"]

    assert "responses[1].broker_order_id duplicates an earlier response" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_row_account_mode_mismatch(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-account-mode")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-account-mode-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["account_mode"] = "live"

    assert "responses[0].account_mode must match artifact account_mode" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_broker_timestamp_before_submission(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-time-order")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-time-order-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["submitted_at"] = "2026-06-02T09:30:01Z"
    payload["responses"][0]["broker_timestamp"] = "2026-06-02T09:30:00Z"

    assert "responses[0].broker_timestamp must be at or after submitted_at" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_rejects_filled_without_accepted_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-filled-accepted")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.FILLED,
                broker_order_id="paper-filled-accepted-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=1.0,
                fill_price=190.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["accepted_quantity"] = None

    assert "responses[0].filled responses require a positive accepted_quantity" in validate_broker_response_artifact(
        payload
    )


@pytest.mark.parametrize(
    "status",
    [BrokerOrderStatus.ACCEPTED, BrokerOrderStatus.PARTIALLY_FILLED],
)
def test_broker_response_artifact_rejects_active_status_without_accepted_quantity(tmp_path, status):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-{status.value}-accepted")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=f"paper-{status.value}-accepted-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=0.5 if status is BrokerOrderStatus.PARTIALLY_FILLED else None,
                fill_price=190.0 if status is BrokerOrderStatus.PARTIALLY_FILLED else None,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["accepted_quantity"] = None

    assert f"responses[0].{status.value} responses require a positive accepted_quantity" in (
        validate_broker_response_artifact(payload)
    )


@pytest.mark.parametrize(
    "status",
    [BrokerOrderStatus.ACCEPTED, BrokerOrderStatus.PARTIALLY_FILLED, BrokerOrderStatus.FILLED],
)
@pytest.mark.parametrize("accepted_quantity", [None, 0.0])
def test_broker_response_artifact_writer_rejects_active_status_without_positive_accepted_quantity(
    tmp_path,
    status,
    accepted_quantity,
):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-{status.value}-accepted")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": status,
        "broker_order_id": f"paper-writer-{status.value}-accepted-1",
        "submitted_quantity": 1.0,
        "accepted_quantity": accepted_quantity,
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
    }
    if status is BrokerOrderStatus.PARTIALLY_FILLED:
        response_kwargs.update({"fill_quantity": 0.5, "fill_price": 190.0})
    if status is BrokerOrderStatus.FILLED:
        response_kwargs.update({"fill_quantity": 1.0, "fill_price": 190.0})

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].{status.value} responses require a positive accepted_quantity" in str(exc)
    else:
        raise AssertionError(f"expected {status.value} response accepted_quantity to be rejected by writer")


@pytest.mark.parametrize("status", [BrokerOrderStatus.CANCELED, BrokerOrderStatus.EXPIRED])
@pytest.mark.parametrize("field_name", ["fill_quantity", "fill_price"])
def test_broker_response_artifact_rejects_terminal_status_with_fill_fields(tmp_path, status, field_name):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-{status.value}-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                broker_order_id=f"paper-{status.value}-{field_name}-1",
                submitted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0][field_name] = 1.0

    assert f"responses[0].{status.value} responses must not report {field_name}" in validate_broker_response_artifact(
        payload
    )


@pytest.mark.parametrize("status", [BrokerOrderStatus.CANCELED, BrokerOrderStatus.EXPIRED])
@pytest.mark.parametrize("field_name", ["fill_quantity", "fill_price"])
def test_broker_response_artifact_writer_rejects_terminal_status_with_fill_fields(tmp_path, status, field_name):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-{status.value}-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": status,
        "broker_order_id": f"paper-writer-{status.value}-{field_name}-1",
        "submitted_quantity": 1.0,
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
        field_name: 1.0,
    }

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].{status.value} responses must not report {field_name}" in str(exc)
    else:
        raise AssertionError(f"expected {status.value} response {field_name} to be rejected by writer")


def test_broker_response_artifact_rejects_rejected_status_with_accepted_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-rejected-with-accepted")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.REJECTED,
                submitted_quantity=1.0,
                accepted_quantity=None,
                rejection_reason="broker rejected order",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["accepted_quantity"] = 1.0

    assert "responses[0].rejected responses must not report accepted_quantity" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_writer_rejects_rejected_status_with_accepted_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-rejected-accepted")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    accepted_quantity=1.0,
                    rejection_reason="broker rejected order",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].rejected responses must not report accepted_quantity" in str(exc)
    else:
        raise AssertionError("expected rejected accepted_quantity failure")


def test_broker_response_artifact_rejects_accepted_status_with_fill_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-accepted-with-fill")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-accepted-fill-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=None,
                fill_price=None,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 0.5

    assert "responses[0].accepted responses must not report fill_quantity" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_rejects_accepted_status_with_fill_price(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-accepted-with-price")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-accepted-price-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                fill_quantity=None,
                fill_price=None,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_price"] = 190.0

    assert "responses[0].accepted responses must not report fill_price" in validate_broker_response_artifact(payload)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [("fill_quantity", 0.5), ("fill_price", 190.0)],
)
def test_broker_response_artifact_writer_rejects_accepted_response_fills(tmp_path, field_name, field_value):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-accepted-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": BrokerOrderStatus.ACCEPTED,
        "broker_order_id": f"paper-accepted-{field_name}-1",
        "submitted_quantity": 1.0,
        "accepted_quantity": 1.0,
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
        field_name: field_value,
    }

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].accepted responses must not report {field_name}" in str(exc)
    else:
        raise AssertionError(f"expected accepted response {field_name} to be rejected by writer")


def test_broker_response_artifact_rejects_rejected_status_with_fill_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-rejected-with-fill")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 0.5

    assert "responses[0].rejected responses must not report fill_quantity" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_rejected_status_with_fill_price(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-rejected-with-price")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_price"] = 190.0

    assert "responses[0].rejected responses must not report fill_price" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_rejected_status_with_fees(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-rejected-with-fees")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fees"] = 0.01

    assert "responses[0].rejected responses must not report fees" in validate_broker_response_artifact(payload)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [("fill_quantity", 0.5), ("fill_price", 190.0)],
)
def test_broker_response_artifact_writer_rejects_rejected_response_fills(tmp_path, field_name, field_value):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-rejected-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": BrokerOrderStatus.REJECTED,
        "submitted_quantity": 1.0,
        "rejection_reason": "paper account symbol permission mismatch",
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
        field_name: field_value,
    }

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].rejected responses must not report {field_name}" in str(exc)
    else:
        raise AssertionError(f"expected rejected response {field_name} to be rejected by writer")


def test_broker_response_artifact_writer_rejects_rejected_response_fees(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-rejected-fees")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    fees=0.01,
                    rejection_reason="paper account symbol permission mismatch",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].rejected responses must not report fees" in str(exc)
    else:
        raise AssertionError("expected rejected response fees to be rejected by writer")


@pytest.mark.parametrize("submitted_quantity", [None, 0.0])
def test_broker_response_artifact_rejects_missing_or_zero_submitted_quantity(tmp_path, submitted_quantity):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-submitted-quantity")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["submitted_quantity"] = submitted_quantity

    assert "responses[0].submitted_quantity must be a positive number" in validate_broker_response_artifact(payload)


@pytest.mark.parametrize("submitted_quantity", [None, 0.0])
def test_broker_response_artifact_writer_rejects_missing_or_zero_submitted_quantity(
    tmp_path,
    submitted_quantity,
):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-submitted-quantity")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=submitted_quantity,
                    rejection_reason="paper account symbol permission mismatch",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].submitted_quantity must be a positive number" in str(exc)
    else:
        raise AssertionError("expected missing or zero submitted_quantity to be rejected by writer")


@pytest.mark.parametrize("field_name", ["accepted_quantity", "fill_quantity", "fill_price", "fees"])
def test_broker_response_artifact_writer_rejects_negative_optional_numeric_fields(tmp_path, field_name):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-negative-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": BrokerOrderStatus.REJECTED,
        "submitted_quantity": 1.0,
        "rejection_reason": "paper account symbol permission mismatch",
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
        field_name: -0.01,
    }

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].{field_name} must be a non-negative number or null" in str(exc)
    else:
        raise AssertionError(f"expected negative {field_name} to be rejected by writer")


def test_broker_response_artifact_writer_rejects_empty_adapter_name(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-empty-adapter")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
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
            output=tmp_path / "broker_response.json",
            adapter="",
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "adapter must be non-empty" in str(exc)
    else:
        raise AssertionError("expected empty response artifact adapter name to be rejected by writer")


def test_broker_response_artifact_writer_rejects_blank_adapter_name(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-blank-adapter")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
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
            output=tmp_path / "broker_response.json",
            adapter="   ",
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "adapter must be non-empty" in str(exc)
    else:
        raise AssertionError("expected blank response artifact adapter name to be rejected by writer")


def test_broker_response_artifact_writer_rejects_adapter_name_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-adapter-whitespace")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
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
            output=tmp_path / "broker_response.json",
            adapter=f"{adapter.name} ",
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "adapter must not contain whitespace" in str(exc)
    else:
        raise AssertionError("expected response artifact adapter name whitespace to be rejected by writer")


def test_broker_response_artifact_writer_rejects_empty_artifact_account_mode(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-empty-account")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
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
                    account_mode="",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="",
        )
    except BrokerAdapterContractError as exc:
        assert "account_mode must be non-empty" in str(exc)
    else:
        raise AssertionError("expected empty response artifact account_mode to be rejected by writer")


def test_broker_response_artifact_writer_rejects_empty_client_order_id(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-empty-client-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id="",
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="paper account symbol permission mismatch",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].client_order_id must be non-empty" in str(exc)
    else:
        raise AssertionError("expected empty response client_order_id to be rejected by writer")


def test_broker_response_artifact_writer_rejects_blank_client_order_id(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-blank-client-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id="   ",
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="paper account symbol permission mismatch",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].client_order_id must be non-empty" in str(exc)
    else:
        raise AssertionError("expected blank response client_order_id to be rejected by writer")


def test_broker_response_artifact_writer_rejects_client_order_id_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-client-id-whitespace")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=f"{requests[0].client_order_id} ",
                    status=BrokerOrderStatus.REJECTED,
                    submitted_quantity=1.0,
                    rejection_reason="paper account symbol permission mismatch",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].client_order_id must not contain whitespace" in str(exc)
    else:
        raise AssertionError("expected response client_order_id whitespace to be rejected by writer")


def test_broker_response_artifact_writer_rejects_blank_broker_order_id_for_accepted_responses(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-blank-broker-id")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.ACCEPTED,
                    broker_order_id="   ",
                    submitted_quantity=1.0,
                    accepted_quantity=1.0,
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].broker_order_id must be non-empty for accepted broker responses" in str(exc)
    else:
        raise AssertionError("expected accepted response with blank broker_order_id to be rejected by writer")


def test_broker_response_artifact_writer_rejects_broker_order_id_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-broker-id-whitespace")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.ACCEPTED,
                    broker_order_id="paper-broker-1 ",
                    submitted_quantity=1.0,
                    accepted_quantity=1.0,
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].broker_order_id must not contain whitespace" in str(exc)
    else:
        raise AssertionError("expected response broker_order_id whitespace to be rejected by writer")


@pytest.mark.parametrize("status", [BrokerOrderStatus.REJECTED, BrokerOrderStatus.UNKNOWN])
def test_broker_response_artifact_writer_rejects_blank_reason_for_terminal_responses(tmp_path, status):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-blank-{status.value}-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=status,
                    submitted_quantity=1.0,
                    rejection_reason="   ",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].rejection_reason must be non-empty for {status.value} responses" in str(exc)
    else:
        raise AssertionError(f"expected {status.value} response with blank reason to be rejected by writer")


def test_broker_response_artifact_rejects_unknown_status_without_reason(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-unknown-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["rejection_reason"] = None

    assert "responses[0].rejection_reason must be non-empty for unknown responses" in validate_broker_response_artifact(
        payload
    )


@pytest.mark.parametrize(
    ("field_name", "expected_error"),
    [
        ("adapter", "adapter must be non-empty"),
        ("client_order_id", "responses[0].client_order_id must be non-empty"),
        (
            "broker_order_id",
            "responses[0].broker_order_id must be non-empty for accepted broker responses",
        ),
    ],
)
def test_broker_response_artifact_validator_rejects_blank_response_text(tmp_path, field_name, expected_error):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-validator-blank-text")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id="paper-validator-blank-text-1",
                submitted_quantity=1.0,
                accepted_quantity=1.0,
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    if field_name == "adapter":
        payload["adapter"] = "   "
    else:
        payload["responses"][0][field_name] = "   "

    assert expected_error in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_adapter_whitespace(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-validator-adapter-whitespace")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["adapter"] = f"{payload['adapter']} "

    assert "adapter must not contain whitespace" in validate_broker_response_artifact(payload)


@pytest.mark.parametrize("status", [BrokerOrderStatus.REJECTED, BrokerOrderStatus.UNKNOWN])
def test_broker_response_artifact_validator_rejects_blank_reason(tmp_path, status):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-validator-blank-{status.value}-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=status,
                submitted_quantity=1.0,
                rejection_reason=f"{status.value} response reason",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["rejection_reason"] = "   "

    assert f"responses[0].rejection_reason must be non-empty for {status.value} responses" in (
        validate_broker_response_artifact(payload)
    )


def test_broker_response_artifact_writer_requires_reason_for_unknown_responses(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-unknown-reason")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.UNKNOWN,
                    submitted_quantity=1.0,
                    rejection_reason=None,
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].rejection_reason must be non-empty for unknown responses" in str(exc)
    else:
        raise AssertionError("expected unknown response without reason to be rejected by writer")


def test_broker_response_artifact_rejects_unknown_status_with_fill_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-unknown-fill")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
    write_broker_response_artifact(
        requests=requests,
        responses=[
            BrokerResponse(
                client_order_id=requests[0].client_order_id,
                status=BrokerOrderStatus.UNKNOWN,
                submitted_quantity=1.0,
                fill_quantity=None,
                rejection_reason="broker response status could not be mapped",
                submitted_at="2026-06-02T09:30:00Z",
                broker_timestamp="2026-06-02T09:30:01Z",
                account_mode="paper",
            )
        ],
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0]["fill_quantity"] = 0.5

    assert "responses[0].unknown responses must not report fill_quantity" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_writer_rejects_unknown_status_with_fill_quantity(tmp_path):
    adapter = AlpacaPaperExportAdapter(client_prefix="response-writer-unknown-fill")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[
                BrokerResponse(
                    client_order_id=requests[0].client_order_id,
                    status=BrokerOrderStatus.UNKNOWN,
                    submitted_quantity=1.0,
                    fill_quantity=0.5,
                    rejection_reason="broker response status could not be mapped",
                    submitted_at="2026-06-02T09:30:00Z",
                    broker_timestamp="2026-06-02T09:30:01Z",
                    account_mode="paper",
                )
            ],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert "responses[0].unknown responses must not report fill_quantity" in str(exc)
    else:
        raise AssertionError("expected unknown response fill_quantity to be rejected by writer")


@pytest.mark.parametrize("field_name", ["accepted_quantity", "fill_price", "fees"])
def test_broker_response_artifact_rejects_unknown_status_with_execution_fields(tmp_path, field_name):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-unknown-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    artifact = tmp_path / "broker_response.json"
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
        output=artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["responses"][0][field_name] = 1.0

    assert f"responses[0].unknown responses must not report {field_name}" in validate_broker_response_artifact(
        payload
    )


@pytest.mark.parametrize("field_name", ["accepted_quantity", "fill_price", "fees"])
def test_broker_response_artifact_writer_rejects_unknown_status_with_execution_fields(tmp_path, field_name):
    adapter = AlpacaPaperExportAdapter(client_prefix=f"response-writer-unknown-{field_name}")
    requests = adapter.convert([Order("AAPL", Side.BUY, 1.0, reason="unit test")])
    response_kwargs = {
        "client_order_id": requests[0].client_order_id,
        "status": BrokerOrderStatus.UNKNOWN,
        "submitted_quantity": 1.0,
        "rejection_reason": "broker response status could not be mapped",
        "submitted_at": "2026-06-02T09:30:00Z",
        "broker_timestamp": "2026-06-02T09:30:01Z",
        "account_mode": "paper",
        field_name: 1.0,
    }

    try:
        write_broker_response_artifact(
            requests=requests,
            responses=[BrokerResponse(**response_kwargs)],
            output=tmp_path / "broker_response.json",
            adapter=adapter.name,
            adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
        )
    except BrokerAdapterContractError as exc:
        assert f"responses[0].unknown responses must not report {field_name}" in str(exc)
    else:
        raise AssertionError(f"expected unknown response {field_name} to be rejected by writer")


def test_broker_response_artifact_rejects_live_mode_with_paper_account():
    payload = {
        "schema": "tradearena_broker_response_artifact_v0.1",
        "adapter": "live-unit-adapter",
        "adapter_mode": "live_human_approved",
        "account_mode": "paper",
        "live_submission": True,
        "reconciliation": {
            "response_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "partial_fill_count": 0,
            "filled_count": 0,
            "canceled_count": 0,
            "expired_count": 0,
            "unknown_count": 0,
            "unmatched_response_count": 0,
            "missing_response_count": 0,
            "fill_ratio_mean": None,
        },
        "responses": [],
    }

    assert "account_mode must be live for live_human_approved broker response artifacts" in validate_broker_response_artifact(
        payload
    )


def test_broker_response_artifact_rejects_non_live_mode_with_live_account():
    payload = {
        "schema": "tradearena_broker_response_artifact_v0.1",
        "adapter": "paper-unit-adapter",
        "adapter_mode": "paper_sandbox",
        "account_mode": "live",
        "live_submission": False,
        "reconciliation": {
            "response_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "partial_fill_count": 0,
            "filled_count": 0,
            "canceled_count": 0,
            "expired_count": 0,
            "unknown_count": 0,
            "unmatched_response_count": 0,
            "missing_response_count": 0,
            "fill_ratio_mean": None,
        },
        "responses": [],
    }

    assert "non-live response artifacts must not use account_mode live" in validate_broker_response_artifact(payload)


def test_broker_response_artifact_rejects_unknown_account_mode():
    payload = {
        "schema": "tradearena_broker_response_artifact_v0.1",
        "adapter": "paper-unit-adapter",
        "adapter_mode": "paper_sandbox",
        "account_mode": "simulation",
        "live_submission": False,
        "reconciliation": {
            "response_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "partial_fill_count": 0,
            "filled_count": 0,
            "canceled_count": 0,
            "expired_count": 0,
            "unknown_count": 0,
            "unmatched_response_count": 0,
            "missing_response_count": 0,
            "fill_ratio_mean": None,
        },
        "responses": [],
    }

    assert "account_mode must be one of none, paper, live" in validate_broker_response_artifact(payload)


def test_broker_approval_artifact_validator_and_cli_reject_unredacted_operator(tmp_path):
    approval = BrokerApproval(
        approval_status="approved",
        approved_by="operator-7",
        approved_at="2026-05-31T12:00:00Z",
        max_notional=2500.0,
        allowed_symbols=("AAPL", "MSFT"),
        approval_reason="paper shadow checks passed",
    )
    payload = build_broker_approval_artifact(
        approval,
        approval_id="approval-unit-001",
        account_mode="live",
        max_quantity=5.0,
        allowed_order_types=(OrderType.MARKET, OrderType.LIMIT),
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    artifact = tmp_path / "broker_approval.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    assert validate_broker_approval_artifact(payload) == []
    subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-broker-approval", str(artifact)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "scripts/validate_broker_approval_artifact.py", str(artifact)],
        cwd=ROOT,
        check=True,
    )

    payload["approved_by"] = "operator@example.com"
    broken = tmp_path / "broken_broker_approval.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    errors = validate_broker_approval_artifact(payload)
    result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "validate-broker-approval", str(broken)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert "approved_by must be a redacted operator id, not an email address" in errors
    assert result.returncode == 1
    assert "approved_by must be a redacted operator id, not an email address" in result.stdout


def test_broker_approval_artifact_requires_live_account_mode():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-paper-account-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["account_mode"] = "paper"

    assert "account_mode must be live for broker approval artifacts" in validate_broker_approval_artifact(payload)


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_error"),
    [
        ("approval_id", "   ", "approval_id must be non-empty"),
        ("approved_by", "   ", "approved_by must be non-empty"),
        ("approval_reason", "   ", "approval_reason must be non-empty"),
        ("allowed_symbols", ["   "], "allowed_symbols must be a non-empty list of symbols"),
    ],
)
def test_broker_approval_artifact_rejects_blank_text_fields(field_name, field_value, expected_error):
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-blank-text-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload[field_name] = field_value

    assert expected_error in validate_broker_approval_artifact(payload)


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_error"),
    [
        ("allowed_symbols", ["AAPL", "AAPL"], "allowed_symbols must not contain duplicates"),
        ("allowed_order_types", ["market", "market"], "allowed_order_types must not contain duplicates"),
    ],
)
def test_broker_approval_artifact_rejects_duplicate_scopes(field_name, field_value, expected_error):
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-duplicate-scope-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload[field_name] = field_value

    assert expected_error in validate_broker_approval_artifact(payload)


def test_broker_approval_artifact_rejects_symbol_whitespace():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-symbol-whitespace-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["allowed_symbols"] = ["AAPL "]

    assert "allowed_symbols must not contain whitespace" in validate_broker_approval_artifact(payload)


def test_broker_approval_artifact_rejects_approval_id_whitespace():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-validator-id-whitespace",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["approval_id"] = "approval-validator-id-whitespace "

    assert "approval_id must not contain whitespace" in validate_broker_approval_artifact(payload)


def test_broker_approval_artifact_rejects_approved_by_whitespace():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-validator-operator-id-whitespace",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["approved_by"] = "operator-7 "

    assert "approved_by must not contain whitespace" in validate_broker_approval_artifact(payload)


@pytest.mark.parametrize(
    ("allowed_symbols", "allowed_order_types", "expected_error"),
    [
        (("AAPL", "AAPL"), (OrderType.MARKET,), "allowed_symbols must not contain duplicates"),
        (("AAPL",), (OrderType.MARKET, OrderType.MARKET), "allowed_order_types must not contain duplicates"),
        (("AAPL ",), (OrderType.MARKET,), "allowed_symbols must not contain whitespace"),
    ],
)
def test_broker_approval_artifact_builder_rejects_duplicate_scopes(
    allowed_symbols, allowed_order_types, expected_error
):
    with pytest.raises(BrokerAdapterContractError, match=expected_error):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=allowed_symbols,
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-builder-duplicate-scope-001",
            account_mode="live",
            max_quantity=5.0,
            expires_at="2026-05-31T13:00:00Z",
            request_artifact_hash="sha256:" + "1" * 64,
            allowed_order_types=allowed_order_types,
        )


def test_broker_approval_artifact_builder_rejects_approval_id_whitespace():
    with pytest.raises(BrokerAdapterContractError, match="approval_id must not contain whitespace"):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-builder-id-whitespace ",
            account_mode="live",
            max_quantity=5.0,
            expires_at="2026-05-31T13:00:00Z",
            request_artifact_hash="sha256:" + "1" * 64,
            allowed_order_types=(OrderType.MARKET,),
        )


def test_broker_approval_artifact_builder_rejects_approved_by_whitespace():
    with pytest.raises(BrokerAdapterContractError, match="approved_by must not contain whitespace"):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7 ",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-builder-operator-id-whitespace",
            account_mode="live",
            max_quantity=5.0,
            expires_at="2026-05-31T13:00:00Z",
            request_artifact_hash="sha256:" + "1" * 64,
            allowed_order_types=(OrderType.MARKET,),
        )


@pytest.mark.parametrize(
    ("approval", "max_quantity", "expected_error"),
    [
        (
            BrokerApproval(
                approval_status="pending",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            5.0,
            "approval_status must be approved",
        ),
        (
            BrokerApproval(
                approval_status="approved",
                approved_by="   ",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            5.0,
            "approved_by must be non-empty",
        ),
        (
            BrokerApproval(
                approval_status="approved",
                approved_by="operator@example.com",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            5.0,
            "approved_by must be a redacted operator id, not an email address",
        ),
        (
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="May 31, noon",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            5.0,
            "approved_at must be an ISO timestamp with timezone",
        ),
        (
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=0.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            5.0,
            "max_notional must be a positive number",
        ),
        (
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="   ",
            ),
            5.0,
            "approval_reason must be non-empty",
        ),
        (
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            0.0,
            "max_quantity must be a positive number",
        ),
    ],
)
def test_broker_approval_artifact_builder_rejects_invalid_approval_fields(
    approval: BrokerApproval, max_quantity: float, expected_error: str
):
    with pytest.raises(BrokerAdapterContractError, match=expected_error):
        build_broker_approval_artifact(
            approval,
            approval_id="approval-builder-invalid-fields-001",
            account_mode="live",
            max_quantity=max_quantity,
            expires_at="2026-05-31T13:00:00Z",
            request_artifact_hash="sha256:" + "1" * 64,
        )


@pytest.mark.parametrize(
    ("approval_id", "account_mode", "allowed_symbols", "allowed_order_types", "expected_error"),
    [
        ("   ", "live", ("AAPL",), (OrderType.MARKET,), "approval_id must be non-empty"),
        (
            "approval-builder-paper-account-001",
            "paper",
            ("AAPL",),
            (OrderType.MARKET,),
            "account_mode must be live for broker approval artifacts",
        ),
        (
            "approval-builder-empty-symbols-001",
            "live",
            (),
            (OrderType.MARKET,),
            "allowed_symbols must be a non-empty list of symbols",
        ),
        (
            "approval-builder-blank-symbol-001",
            "live",
            ("   ",),
            (OrderType.MARKET,),
            "allowed_symbols must be a non-empty list of symbols",
        ),
        (
            "approval-builder-empty-order-types-001",
            "live",
            ("AAPL",),
            (),
            "allowed_order_types must contain market or limit",
        ),
        (
            "approval-builder-unsupported-order-types-001",
            "live",
            ("AAPL",),
            ("stop",),
            "allowed_order_types must contain market or limit",
        ),
    ],
)
def test_broker_approval_artifact_builder_rejects_invalid_artifact_scope_fields(
    approval_id: str,
    account_mode: str,
    allowed_symbols: tuple[str, ...],
    allowed_order_types: tuple[OrderType, ...],
    expected_error: str,
):
    with pytest.raises(BrokerAdapterContractError, match=expected_error):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=allowed_symbols,
                approval_reason="paper shadow checks passed",
            ),
            approval_id=approval_id,
            account_mode=account_mode,
            max_quantity=5.0,
            allowed_order_types=allowed_order_types,
            expires_at="2026-05-31T13:00:00Z",
            request_artifact_hash="sha256:" + "1" * 64,
        )


def test_broker_approval_artifact_builds_live_safety_config(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-safety",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL", "MSFT")),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 2.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="approved")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL", "MSFT"),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-safety-001",
        account_mode="live",
        max_quantity=5.0,
        allowed_order_types=(OrderType.LIMIT,),
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )

    approval = broker_approval_from_artifact(payload)
    safety = broker_safety_from_approval_artifact(payload, request_artifact=request_path)

    assert approval.allowed_symbols == ("AAPL", "MSFT")
    assert safety.mode == BrokerAdapterMode.LIVE_HUMAN_APPROVED
    assert safety.account_mode == "live"
    assert safety.max_notional == 250.0
    assert safety.max_quantity == 5.0
    assert safety.allowed_order_types == (OrderType.LIMIT,)
    safety.validate_order(
        Order("AAPL", Side.BUY, 2.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="approved"),
        reference_price=100.0,
    )

    try:
        safety.validate_order(
            Order("AAPL", Side.BUY, 3.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="too large"),
            reference_price=100.0,
        )
    except BrokerAdapterContractError as exc:
        assert (
            "does not match an approved broker handoff order" in str(exc)
            or "approved broker handoff order count 0" in str(exc)
        )
    else:
        raise AssertionError("expected unreviewed-order failure from approval artifact safety")


def test_broker_safety_from_approval_artifact_requires_reviewed_request_artifact():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-unbound-safety-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )

    try:
        broker_safety_from_approval_artifact(payload)
    except BrokerAdapterContractError as exc:
        assert "request_artifact is required to build live safety from a broker approval artifact" in str(exc)
    else:
        raise AssertionError("expected unbound live safety creation to be rejected")


def test_broker_approval_artifact_builder_requires_request_hash_binding():
    with pytest.raises(
        BrokerAdapterContractError,
        match="request_artifact_hash is required to bind approval to a broker handoff artifact",
    ):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-unbound-artifact-001",
            account_mode="live",
            max_quantity=5.0,
            expires_at="2026-05-31T13:00:00Z",
            request_artifact_hash="",
        )


def test_broker_approval_artifact_builder_rejects_non_string_request_hash():
    with pytest.raises(BrokerAdapterContractError, match="request_artifact_hash must be sha256"):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-non-string-request-hash-001",
            account_mode="live",
            max_quantity=5.0,
            expires_at="2026-05-31T13:00:00Z",
            request_artifact_hash=123,
        )


def test_broker_approval_artifact_builder_requires_expiry():
    with pytest.raises(BrokerAdapterContractError, match="expires_at is required for broker approval artifacts"):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-no-expiry-001",
            account_mode="live",
            max_quantity=5.0,
            expires_at="",
            request_artifact_hash="sha256:" + "1" * 64,
        )


def test_broker_approval_artifact_builder_rejects_non_string_expiry():
    with pytest.raises(BrokerAdapterContractError, match="expires_at must be an ISO timestamp with timezone"):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-non-string-expiry-001",
            account_mode="live",
            max_quantity=5.0,
            expires_at=123,
            request_artifact_hash="sha256:" + "1" * 64,
        )


@pytest.mark.parametrize(
    ("approved_at", "expires_at", "expected_error"),
    [
        ("2026-05-31T12:00:00Z", "tomorrow", "expires_at must be an ISO timestamp with timezone"),
        ("2026-05-31T12:00:00Z", "2026-05-31T12:00:00Z", "expires_at must be after approved_at"),
        ("2026-05-31T12:00:00Z", "2026-05-31T11:59:59Z", "expires_at must be after approved_at"),
    ],
)
def test_broker_approval_artifact_builder_rejects_invalid_expiry_window(
    approved_at: str, expires_at: str, expected_error: str
):
    with pytest.raises(BrokerAdapterContractError, match=expected_error):
        build_broker_approval_artifact(
            BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at=approved_at,
                max_notional=250.0,
                allowed_symbols=("AAPL",),
                approval_reason="paper shadow checks passed",
            ),
            approval_id="approval-bad-expiry-window-001",
            account_mode="live",
            max_quantity=5.0,
            expires_at=expires_at,
            request_artifact_hash="sha256:" + "1" * 64,
        )


def test_broker_approval_artifact_rejects_null_expiry():
    payload = {
        "schema": "tradearena_broker_approval_artifact_v0.1",
        "approval_id": "approval-null-expiry-001",
        "approval_status": "approved",
        "approved_by": "operator-7",
        "approved_at": "2026-05-31T12:00:00Z",
        "expires_at": None,
        "account_mode": "live",
        "max_notional": 250.0,
        "max_quantity": 5.0,
        "allowed_symbols": ["AAPL"],
        "allowed_order_types": ["market"],
        "approval_reason": "paper shadow checks passed",
        "request_artifact_hash": "sha256:" + "1" * 64,
    }

    assert validate_broker_approval_artifact(payload) == ["expires_at is required for broker approval artifacts"]


def test_broker_approval_artifact_rejects_expired_approval():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-expired-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )

    errors = validate_broker_approval_artifact(payload, now="2026-05-31T14:00:00Z")
    assert "approval artifact is expired" in errors
    try:
        broker_safety_from_approval_artifact(payload, now="2026-05-31T14:00:00Z")
    except BrokerAdapterContractError as exc:
        assert "approval artifact is expired" in str(exc)
    else:
        raise AssertionError("expected expired approval artifact failure")


def test_broker_approval_validator_cli_and_script_reject_expired_approval_with_now(tmp_path):
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-expired-command-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    artifact = tmp_path / "broker_approval.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-broker-approval",
            str(artifact),
            "--now",
            "2026-05-31T14:00:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    script_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_broker_approval_artifact.py",
            str(artifact),
            "--now",
            "2026-05-31T14:00:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert script_result.returncode == 1
    assert "approval artifact is expired" in result.stdout
    assert "approval artifact is expired" in script_result.stdout


def test_broker_approval_validator_cli_rejects_malformed_now_even_without_expiry(tmp_path):
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-bad-now-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    artifact = tmp_path / "broker_approval.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-broker-approval",
            str(artifact),
            "--now",
            "not-a-time",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "now must be an ISO timestamp" in result.stdout


def test_broker_approval_artifact_rejects_malformed_timestamps():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-bad-time-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["approved_at"] = "May 31, noon"
    payload["expires_at"] = "tomorrow"

    errors = validate_broker_approval_artifact(payload)
    assert "approved_at must be an ISO timestamp with timezone" in errors
    assert "expires_at must be an ISO timestamp with timezone" in errors


def test_broker_approval_artifact_rejects_expiry_before_approval_time():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-reversed-window-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["expires_at"] = "2026-05-31T11:59:59Z"

    assert "expires_at must be after approved_at" in validate_broker_approval_artifact(payload)


def test_broker_approval_artifact_rejects_malformed_request_hash():
    payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-bad-hash-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "1" * 64,
    )
    payload["request_artifact_hash"] = "sha256:demo-redacted-request-hash"

    assert validate_broker_approval_artifact(payload) == [
        "request_artifact_hash must be sha256:<64 lowercase hex chars>"
    ]


def test_broker_artifact_file_validators_report_malformed_json(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text('{"schema": ', encoding="utf-8")

    for validator in (
        validate_broker_handoff_artifact_file,
        validate_broker_approval_artifact_file,
        validate_broker_response_artifact_file,
    ):
        payload, errors = validator(broken)

        assert payload == {}
        assert errors == ["broker artifact file must contain valid JSON"]


def test_broker_artifact_file_validators_report_missing_paths(tmp_path):
    missing = tmp_path / "missing_broker_artifact.json"

    for validator in (
        validate_broker_handoff_artifact_file,
        validate_broker_approval_artifact_file,
        validate_broker_response_artifact_file,
    ):
        payload, errors = validator(missing)

        assert payload == {}
        assert errors == [f"broker artifact file does not exist: {missing}"]


def test_broker_artifact_file_validators_report_directory_paths(tmp_path):
    artifact_dir = tmp_path / "broker_artifact_dir"
    artifact_dir.mkdir()

    for validator in (
        validate_broker_handoff_artifact_file,
        validate_broker_approval_artifact_file,
        validate_broker_response_artifact_file,
    ):
        payload, errors = validator(artifact_dir)

        assert payload == {}
        assert errors == [f"broker artifact path is not a file: {artifact_dir}"]


def test_broker_artifact_validator_scripts_report_malformed_json(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text('{"schema": ', encoding="utf-8")

    for script in (
        "scripts/validate_broker_handoff_artifact.py",
        "scripts/validate_broker_approval_artifact.py",
        "scripts/validate_broker_response_artifact.py",
    ):
        result = subprocess.run(
            [sys.executable, script, str(broken)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "broker artifact file must contain valid JSON" in result.stdout
        assert "Traceback" not in result.stderr


def test_broker_artifact_validator_scripts_report_missing_paths(tmp_path):
    missing = tmp_path / "missing_broker_artifact.json"

    for script in (
        "scripts/validate_broker_handoff_artifact.py",
        "scripts/validate_broker_approval_artifact.py",
        "scripts/validate_broker_response_artifact.py",
    ):
        result = subprocess.run(
            [sys.executable, script, str(missing)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert f"broker artifact file does not exist: {missing}" in result.stdout
        assert "Traceback" not in result.stderr


def test_broker_artifact_validator_scripts_report_directory_paths(tmp_path):
    artifact_dir = tmp_path / "broker_artifact_dir"
    artifact_dir.mkdir()

    for script in (
        "scripts/validate_broker_handoff_artifact.py",
        "scripts/validate_broker_approval_artifact.py",
        "scripts/validate_broker_response_artifact.py",
    ):
        result = subprocess.run(
            [sys.executable, script, str(artifact_dir)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert f"broker artifact path is not a file: {artifact_dir}" in result.stdout
        assert "Traceback" not in result.stderr


def test_broker_handoff_hash_helper_reports_malformed_json_path(tmp_path):
    broken = tmp_path / "broken_handoff.json"
    broken.write_text('{"schema": ', encoding="utf-8")

    try:
        broker_handoff_artifact_hash(broken)
    except BrokerAdapterContractError as exc:
        assert str(exc) == "broker artifact file must contain valid JSON"
    else:
        raise AssertionError("malformed broker handoff JSON was hashed")


def test_broker_handoff_hash_helper_reports_missing_path(tmp_path):
    missing = tmp_path / "missing_handoff.json"

    try:
        broker_handoff_artifact_hash(missing)
    except BrokerAdapterContractError as exc:
        assert str(exc) == f"broker artifact file does not exist: {missing}"
    else:
        raise AssertionError("missing broker handoff JSON was hashed")


def test_broker_handoff_hash_helper_reports_directory_path(tmp_path):
    artifact_dir = tmp_path / "handoff_dir"
    artifact_dir.mkdir()

    try:
        broker_handoff_artifact_hash(artifact_dir)
    except BrokerAdapterContractError as exc:
        assert str(exc) == f"broker artifact path is not a file: {artifact_dir}"
    else:
        raise AssertionError("directory broker handoff path was hashed")


def test_broker_approval_artifact_binds_to_handoff_request_hash(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-bind",
        safety=BrokerSafetyConfig(
            account_mode="paper",
            max_quantity=5.0,
            allowed_symbols=("AAPL",),
        ),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 2.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="binding unit")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_hash = broker_handoff_artifact_hash(request_payload)
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-bound-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=request_hash,
    )

    assert request_hash.startswith("sha256:")
    assert validate_broker_approval_request_binding(approval_payload, request_payload) == []
    assert validate_broker_approval_request_binding(approval_payload, request_path) == []

    approval_payload["request_artifact_hash"] = "sha256:" + "0" * 64
    assert validate_broker_approval_request_binding(approval_payload, request_payload) == [
        "request_artifact_hash does not match broker handoff artifact"
    ]


def test_broker_approval_binding_rejects_approval_expiring_at_current_time(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-expiry-boundary",
        safety=BrokerSafetyConfig(
            account_mode="paper",
            max_quantity=5.0,
            allowed_symbols=("AAPL",),
        ),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 2.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="expiry boundary")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-expiry-boundary-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )

    assert validate_broker_approval_request_binding(
        approval_payload,
        request_path,
        now="2026-05-31T13:00:00Z",
    ) == ["approval artifact is expired"]


def test_broker_approval_binding_rejects_already_live_handoff_request(tmp_path):
    adapter = AlpacaPaperExportAdapter(
        client_prefix="approval-live-request",
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.LIVE_HUMAN_APPROVED,
            account_mode="live",
            max_notional=1000.0,
            max_quantity=10.0,
            approval=BrokerApproval(
                approval_status="approved",
                approved_by="operator-7",
                approved_at="2026-05-31T12:00:00Z",
                max_notional=1000.0,
                allowed_symbols=("AAPL",),
                approval_reason="unit test approval",
            ),
        ),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="already live")],
        tmp_path,
    )
    request_path = tmp_path / "alpaca_paper_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:05:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-live-request-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )

    assert validate_broker_approval_request_binding(approval_payload, request_path) == [
        "request artifact must be a pre-live broker-review handoff, not live_human_approved"
    ]


def test_broker_handoff_hash_cli_and_script_validate_before_printing_hash(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="hash-cli",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="hash cli")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    expected_hash = broker_handoff_artifact_hash(request_path)

    cli_result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "hash-broker-handoff", str(request_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    script_result = subprocess.run(
        [sys.executable, "scripts/hash_broker_handoff_artifact.py", str(request_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert cli_result.stdout.strip() == expected_hash
    assert script_result.stdout.strip() == expected_hash

    payload = json.loads(request_path.read_text(encoding="utf-8"))
    payload["orders"][0]["submit_live"] = True
    broken_path = tmp_path / "broken_dry_run_orders.json"
    broken_path.write_text(json.dumps(payload), encoding="utf-8")
    broken_result = subprocess.run(
        [sys.executable, "-m", "tradearena.cli", "hash-broker-handoff", str(broken_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert broken_result.returncode == 1
    assert "Invalid broker handoff artifact" in broken_result.stdout


def test_broker_handoff_hash_helper_rejects_invalid_artifacts(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="hash-helper",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="hash helper")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    payload["orders"][0]["submit_live"] = True

    try:
        broker_handoff_artifact_hash(payload)
    except BrokerAdapterContractError as exc:
        assert "orders[0].submit_live must match live_human_approved mode" in str(exc)
    else:
        raise AssertionError("invalid broker handoff artifact was hashed")


def test_broker_approval_binding_reports_invalid_handoff_without_raising(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-invalid-request",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="invalid request")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_hash = broker_handoff_artifact_hash(request_payload)
    request_payload["orders"][0]["submit_live"] = True
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=500.0,
            allowed_symbols=("AAPL",),
            approval_reason="unit test",
        ),
        approval_id="approval-invalid-request",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=request_hash,
    )

    errors = validate_broker_approval_request_binding(approval_payload, request_payload)

    assert "orders[0].submit_live must match live_human_approved mode" in errors


def test_broker_approval_request_binding_rejects_orders_outside_approval_scope(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-scope",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 2.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="scope unit")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=150.0,
            allowed_symbols=("MSFT",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-scope-001",
        account_mode="live",
        max_quantity=1.0,
        allowed_order_types=(OrderType.MARKET,),
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )

    errors = validate_broker_approval_request_binding(approval_payload, request_path)
    assert "orders[0].symbol AAPL is outside approval allowed_symbols" in errors
    assert "orders[0].order_type limit is outside approval allowed_order_types" in errors
    assert "orders[0].quantity 2.0 exceeds approval max_quantity 1.0" in errors
    assert "orders[0].notional 200.00 exceeds approval max_notional 150.00" in errors
    try:
        broker_safety_from_approval_artifact(approval_payload, request_artifact=request_path)
    except BrokerAdapterContractError as exc:
        assert "outside approval allowed_symbols" in str(exc)
    else:
        raise AssertionError("expected approval request scope failure before live safety creation")


def test_broker_approval_request_binding_requires_calculable_notional(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-unpriced",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write([Order("AAPL", Side.BUY, 1.0, reason="unpriced market order")], tmp_path)
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=150.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-unpriced-001",
        account_mode="live",
        max_quantity=5.0,
        allowed_order_types=(OrderType.MARKET,),
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )

    assert validate_broker_approval_request_binding(approval_payload, request_path) == [
        "orders[0].notional cannot be checked without a positive limit_price"
    ]


def test_broker_approval_request_binding_rejects_empty_reviewed_handoff(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-empty-request",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write([], tmp_path)
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-empty-request-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )

    assert validate_broker_approval_request_binding(approval_payload, request_path) == [
        "request artifact must contain at least one reviewed order"
    ]
    try:
        broker_safety_from_approval_artifact(approval_payload, request_artifact=request_path)
    except BrokerAdapterContractError as exc:
        assert "request artifact must contain at least one reviewed order" in str(exc)
    else:
        raise AssertionError("expected empty reviewed request to be rejected before live safety creation")


def test_broker_safety_from_approval_artifact_can_require_request_binding(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-safety-bind",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="safety bind")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-safety-bound-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )

    safety = broker_safety_from_approval_artifact(approval_payload, request_artifact=request_path)
    assert safety.mode == BrokerAdapterMode.LIVE_HUMAN_APPROVED

    approval_payload["request_artifact_hash"] = "sha256:" + "0" * 64
    try:
        broker_safety_from_approval_artifact(approval_payload, request_artifact=request_path)
    except BrokerAdapterContractError as exc:
        assert "request_artifact_hash does not match broker handoff artifact" in str(exc)
    else:
        raise AssertionError("expected request binding failure before live safety creation")


def test_broker_safety_from_bound_approval_rejects_unreviewed_order(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-runtime-bind",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="reviewed order")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-runtime-bound-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )
    safety = broker_safety_from_approval_artifact(approval_payload, request_artifact=request_path)
    live_adapter = AlpacaPaperExportAdapter(client_prefix="runtime-bound-live", safety=safety)

    live_adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="reviewed order")],
        tmp_path / "approved",
    )
    try:
        live_adapter.write(
            [Order("AAPL", Side.BUY, 2.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="unreviewed order")],
            tmp_path / "unreviewed",
        )
    except BrokerAdapterContractError as exc:
        assert (
            "does not match an approved broker handoff order" in str(exc)
            or "approved broker handoff order count 0" in str(exc)
        )
    else:
        raise AssertionError("expected unreviewed order to be rejected by bound live safety")


def test_broker_safety_from_bound_approval_rejects_duplicate_reviewed_order_reuse(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-duplicate-bind",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    reviewed_order = Order(
        "AAPL",
        Side.BUY,
        1.0,
        order_type=OrderType.LIMIT,
        limit_price=100.0,
        reason="reviewed order",
    )
    adapter.write([reviewed_order], tmp_path)
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-duplicate-bound-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )
    safety = broker_safety_from_approval_artifact(approval_payload, request_artifact=request_path)
    live_adapter = AlpacaPaperExportAdapter(client_prefix="duplicate-bound-live", safety=safety)

    try:
        live_adapter.write([reviewed_order, reviewed_order], tmp_path / "duplicate")
    except BrokerAdapterContractError as exc:
        assert "approved broker handoff order count" in str(exc)
    else:
        raise AssertionError("expected duplicate reuse of one reviewed order to be rejected")


def test_broker_safety_from_bound_approval_rejects_time_in_force_change(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-tif-bind",
        time_in_force="day",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    reviewed_order = Order(
        "AAPL",
        Side.BUY,
        1.0,
        order_type=OrderType.LIMIT,
        limit_price=100.0,
        reason="reviewed order",
    )
    adapter.write([reviewed_order], tmp_path)
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-tif-bound-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )
    safety = broker_safety_from_approval_artifact(approval_payload, request_artifact=request_path)
    live_adapter = AlpacaPaperExportAdapter(client_prefix="tif-bound-live", time_in_force="gtc", safety=safety)

    try:
        live_adapter.write([reviewed_order], tmp_path / "changed-tif")
    except BrokerAdapterContractError as exc:
        assert "time_in_force" in str(exc)
    else:
        raise AssertionError("expected changed time_in_force to be rejected by bound live safety")


def test_broker_approval_binding_cli_and_script_reject_hash_mismatch(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-bind-cli",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="binding cli")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-bound-cli-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )
    approval_path = tmp_path / "broker_approval.json"
    approval_path.write_text(json.dumps(approval_payload), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-broker-approval-binding",
            str(approval_path),
            str(request_path),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/validate_broker_approval_binding.py",
            str(approval_path),
            str(request_path),
        ],
        cwd=ROOT,
        check=True,
    )

    approval_payload["request_artifact_hash"] = "sha256:" + "0" * 64
    approval_path.write_text(json.dumps(approval_payload), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-broker-approval-binding",
            str(approval_path),
            str(request_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    script_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_broker_approval_binding.py",
            str(approval_path),
            str(request_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert script_result.returncode == 1
    assert "request_artifact_hash does not match broker handoff artifact" in result.stdout
    assert "request_artifact_hash does not match broker handoff artifact" in script_result.stdout


def test_broker_approval_binding_script_reports_malformed_request_json(tmp_path):
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=500.0,
            allowed_symbols=("AAPL",),
            approval_reason="unit test",
        ),
        approval_id="approval-malformed-request",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash="sha256:" + "0" * 64,
    )
    approval_path = tmp_path / "broker_approval.json"
    approval_path.write_text(json.dumps(approval_payload), encoding="utf-8")
    request_path = tmp_path / "broken_request.json"
    request_path.write_text('{"schema": ', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_broker_approval_binding.py",
            str(approval_path),
            str(request_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "broker artifact file must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def test_broker_approval_binding_cli_and_script_reject_expired_approval(tmp_path):
    adapter = DryRunBrokerAdapter(
        client_prefix="approval-expired-cli",
        safety=BrokerSafetyConfig(account_mode="paper", max_quantity=5.0, allowed_symbols=("AAPL",)),
    )
    adapter.write(
        [Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="expired binding")],
        tmp_path,
    )
    request_path = tmp_path / "dry_run_orders.json"
    approval_payload = build_broker_approval_artifact(
        BrokerApproval(
            approval_status="approved",
            approved_by="operator-7",
            approved_at="2026-05-31T12:00:00Z",
            max_notional=250.0,
            allowed_symbols=("AAPL",),
            approval_reason="paper shadow checks passed",
        ),
        approval_id="approval-expired-cli-001",
        account_mode="live",
        max_quantity=5.0,
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=broker_handoff_artifact_hash(request_path),
    )
    approval_path = tmp_path / "broker_approval.json"
    approval_path.write_text(json.dumps(approval_payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "validate-broker-approval-binding",
            str(approval_path),
            str(request_path),
            "--now",
            "2026-05-31T14:00:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    script_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_broker_approval_binding.py",
            str(approval_path),
            str(request_path),
            "--now",
            "2026-05-31T14:00:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert script_result.returncode == 1
    assert "approval artifact is expired" in result.stdout
    assert "approval artifact is expired" in script_result.stdout


def test_broker_approval_safety_demo_writes_valid_artifact():
    subprocess.run([sys.executable, "examples/broker_approval_safety_demo.py"], cwd=ROOT, check=True)
    artifact = ROOT / "outputs/examples/broker_approval_safety/broker_approval_artifact.json"
    summary = json.loads((ROOT / "outputs/examples/broker_approval_safety/summary.json").read_text(encoding="utf-8"))
    payload = json.loads(artifact.read_text(encoding="utf-8"))

    assert summary["approval_validated"] is True
    assert summary["request_hash_bound"] is True
    assert summary["adapter_mode"] == "live_human_approved"
    assert summary["approved_order_passed"] is True
    assert summary["oversized_order_blocked"] is True
    assert payload["request_artifact_hash"] == summary["request_artifact_hash"]
    assert validate_broker_approval_artifact(payload) == []
    assert summary["verification_commands"] == [
        "python scripts/validate_broker_handoff_artifact.py outputs/examples/broker_approval_safety/dry_run_orders.json",
        "python scripts/hash_broker_handoff_artifact.py outputs/examples/broker_approval_safety/dry_run_orders.json",
        (
            "python scripts/validate_broker_approval_artifact.py "
            "outputs/examples/broker_approval_safety/broker_approval_artifact.json "
            "--now 2026-05-31T12:30:00Z"
        ),
        (
            "python scripts/validate_broker_approval_binding.py "
            "outputs/examples/broker_approval_safety/broker_approval_artifact.json "
            "outputs/examples/broker_approval_safety/dry_run_orders.json "
            "--now 2026-05-31T12:30:00Z"
        ),
    ]


def test_broker_approval_safety_demo_contract_validates_with_fixed_now():
    manifest = (ROOT / "docs/demo_artifacts.yaml").read_text(encoding="utf-8")

    assert (
        "python scripts/validate_broker_approval_artifact.py "
        "outputs/examples/broker_approval_safety/broker_approval_artifact.json "
        "--now 2026-05-31T12:30:00Z"
    ) in manifest
    assert (
        "python scripts/validate_broker_approval_binding.py "
        "outputs/examples/broker_approval_safety/broker_approval_artifact.json "
        "outputs/examples/broker_approval_safety/dry_run_orders.json "
        "--now 2026-05-31T12:30:00Z"
    ) in manifest


def test_dry_run_broker_adapter_demo_writes_valid_handoff():
    subprocess.run([sys.executable, "examples/dry_run_broker_adapter_demo.py"], cwd=ROOT, check=True)
    artifact = ROOT / "outputs/examples/dry_run_broker_adapter/dry_run_orders.json"
    summary = json.loads((ROOT / "outputs/examples/dry_run_broker_adapter/summary.json").read_text(encoding="utf-8"))
    payload = json.loads(artifact.read_text(encoding="utf-8"))

    assert summary["adapter_mode"] == "dry_run"
    assert summary["live_submission"] is False
    assert summary["validated"] is True
    assert payload["adapter"] == "dry-run-broker-adapter"
    assert validate_broker_handoff_artifact(payload) == []


def test_holdings_csv_import_fixture_loads_retail_holdings():
    holdings = load_holdings_csv(ROOT / "examples/fixtures/retail_holdings.csv")

    assert len(holdings) == 4
    assert holdings[0].symbol == "CASH"
    assert sum(item.market_value for item in holdings) == 100000


def test_futures_roll_engine_flags_roll_window():
    report = FuturesRollRiskEngine().review(
        timestamp=datetime(2026, 6, 14),
        contracts=(
            FuturesContractMetadata(
                symbol="MESM26",
                root_symbol="MES",
                expiry=date(2026, 6, 19),
                roll_start=date(2026, 6, 12),
                roll_end=date(2026, 6, 17),
                contract_multiplier=5.0,
                initial_margin_rate=0.08,
            ),
        ),
        positions={"MESM26": 1.0},
    )

    assert any(item.constraint == "futures_roll_window" for item in report.violations)
    assert report.blocked_count == 0


def test_mock_rl_policy_baseline_reuses_standard_stack():
    registry = default_registry()
    assert "mock-rl-policy" in registry.names("strategy")

    system = build_default_system(
        symbols=("SYN", "ALT", "DEF"),
        periods=12,
        seed=5,
        analyst_names=(),
        strategy_name="mock-rl-policy",
        max_position_weight=0.2,
    )
    trajectory, metrics = system.run()

    assert metrics["steps"] == 12
    assert trajectory.steps[-1].decisions
    assert all(float(decision["target_weight"]) <= 0.2 for decision in trajectory.steps[-1].decisions)


def test_new_issue_examples_write_expected_artifacts():
    examples = (
        ("examples/alpaca_paper_export_demo.py", "outputs/examples/alpaca_paper_export/summary.json"),
        (
            "examples/broker_response_reconciliation_demo.py",
            "outputs/examples/broker_response_reconciliation/summary.json",
        ),
        ("examples/holdings_csv_import_demo.py", "outputs/examples/holdings_csv_import/summary.json"),
        ("examples/futures_roll_risk_demo.py", "outputs/examples/futures_roll_risk/summary.json"),
        ("examples/crypto_microstructure_stress_demo.py", "outputs/examples/crypto_microstructure_stress/summary.json"),
        ("examples/rl_policy_baseline_demo.py", "outputs/examples/rl_policy_baseline/summary.json"),
    )
    for script, artifact in examples:
        subprocess.run([sys.executable, script], cwd=ROOT, check=True)
        assert (ROOT / artifact).exists()

    crypto = json.loads(
        (ROOT / "outputs/examples/crypto_microstructure_stress/summary.json").read_text(encoding="utf-8")
    )
    assert crypto["rejected_order_count"] >= 0
    assert "total_slippage_cost" in crypto

    futures = json.loads((ROOT / "outputs/examples/futures_roll_risk/summary.json").read_text(encoding="utf-8"))
    assert futures["roll_flagged"] is True

    reconciliation = json.loads(
        (ROOT / "outputs/examples/broker_response_reconciliation/summary.json").read_text(encoding="utf-8")
    )
    assert reconciliation["live_submission"] is False
    assert reconciliation["reconciliation"]["partial_fill_count"] == 1
    assert reconciliation["reconciliation"]["missing_response_count"] == 1


def test_broker_response_status_mapping_fixture_writes_valid_artifact():
    subprocess.run([sys.executable, "examples/broker_response_status_mapping_fixture_demo.py"], cwd=ROOT, check=True)
    artifact = ROOT / "outputs/examples/broker_response_artifact/response_artifact.json"

    payload, errors = validate_broker_response_artifact_file(artifact)

    assert errors == []
    assert payload["adapter_mode"] == BrokerAdapterMode.PAPER_SANDBOX.value
    assert payload["account_mode"] == "paper"
    assert payload["live_submission"] is False
    assert [response["status"] for response in payload["responses"]] == [
        BrokerOrderStatus.ACCEPTED.value,
        BrokerOrderStatus.REJECTED.value,
        BrokerOrderStatus.PARTIALLY_FILLED.value,
        BrokerOrderStatus.CANCELED.value,
        BrokerOrderStatus.UNKNOWN.value,
    ]
    assert payload["reconciliation"] == {
        "response_count": 5,
        "accepted_count": 1,
        "rejected_count": 1,
        "partial_fill_count": 1,
        "filled_count": 0,
        "canceled_count": 1,
        "expired_count": 0,
        "unknown_count": 1,
        "unmatched_response_count": 0,
        "missing_response_count": 0,
        "fill_ratio_mean": 0.25,
    }

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_broker_response_artifact.py",
            str(artifact.relative_to(ROOT)),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
