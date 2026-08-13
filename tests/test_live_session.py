from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradearena.cli import main as cli_main
from tradearena.tools import (
    LiveSessionConfig,
    LiveSessionError,
    approve_session,
    execute_session,
    propose_session,
    reconcile_session,
    reject_session,
    review_session,
    session_status,
    verify_journal_chain,
)
from tradearena.tools.live_session import (
    APPROVAL_FILENAME,
    BUNDLE_FILENAME,
    JOURNAL_FILENAME,
    RESPONSE_FILENAME,
    SESSION_SUMMARY_FILENAME,
    STATE_FILENAME,
)

PROPOSE_NOW = "2026-07-02T10:00:00Z"
APPROVE_NOW = "2026-07-02T10:05:00Z"
EXECUTE_NOW = "2026-07-02T10:06:00Z"
RECONCILE_NOW = "2026-07-02T10:07:00Z"

UP_WEEK_PRICES = {
    "BTC-USD": {"close": 109250.5, "prev_close": 108000.0},
    "BTC=F": {"close": 109900.0, "prev_close": 110500.0},
    "GSPC": {"close": 6150.25, "prev_close": 6100.0},
}
DOWN_WEEK_PRICES = {
    "BTC-USD": {"close": 90.0, "prev_close": 100.0},
    "BTC=F": {"close": 90.0, "prev_close": 100.0},
    "GSPC": {"close": 90.0, "prev_close": 100.0},
}


def _write_prices(tmp_path: Path, prices: dict) -> Path:
    prices_path = tmp_path / "prices.json"
    prices_path.write_text(json.dumps(prices), encoding="utf-8")
    return prices_path


def _config(tmp_path: Path, session_id: str, **overrides) -> LiveSessionConfig:
    defaults = {
        "session_id": session_id,
        "root": tmp_path / "sessions",
        "prices_file": _write_prices(tmp_path, UP_WEEK_PRICES),
    }
    defaults.update(overrides)
    return LiveSessionConfig(**defaults)


def _run_full_session(tmp_path: Path, session_id: str = "w1", **config_overrides) -> Path:
    root = tmp_path / "sessions"
    propose_session(_config(tmp_path, session_id, **config_overrides), now=PROPOSE_NOW)
    approve_session(
        session_id, root=root, approved_by="operator-1", reason="weekly plan approved", now=APPROVE_NOW
    )
    execute_session(session_id, root=root, now=EXECUTE_NOW)
    reconcile_session(session_id, root=root, now=RECONCILE_NOW)
    return root / session_id


def test_full_dry_run_session_chain_passes_final_gate(tmp_path: Path, capsys):
    root = tmp_path / "sessions"
    proposed = propose_session(_config(tmp_path, "w1"), now=PROPOSE_NOW)

    assert proposed["status"] == "proposed"
    assert proposed["order_count"] == 2  # BTC=F momentum is negative and is skipped
    assert proposed["request_artifact_hash"].startswith("sha256:")

    review = review_session("w1", root=root)
    assert "hash_matches_proposed_state=True" in review
    assert "buy BTC-USD" in review
    assert "buy GSPC" in review

    approved = approve_session(
        "w1", root=root, approved_by="operator-1", reason="weekly plan approved", now=APPROVE_NOW
    )
    assert approved["status"] == "approved"
    assert approved["approval_latency_seconds"] == 300.0

    executed = execute_session("w1", root=root, now=EXECUTE_NOW)
    assert executed["status"] == "executed"
    assert executed["response_count"] == 2

    reconciled = reconcile_session("w1", root=root, now=RECONCILE_NOW)
    assert reconciled["status"] == "reconciled"
    assert reconciled["preflight_ready"] is True
    assert reconciled["preflight_error_count"] == 0

    session_dir = root / "w1"
    summary = json.loads((session_dir / SESSION_SUMMARY_FILENAME).read_text(encoding="utf-8"))
    assert summary["status"] == "reconciled"
    assert summary["approval_latency_seconds"] == 300.0
    assert summary["reconciliation"]["response_count"] == 2
    assert summary["reconciliation"]["missing_response_count"] == 0
    assert summary["reconciliation"]["unmatched_response_count"] == 0

    response = json.loads((session_dir / RESPONSE_FILENAME).read_text(encoding="utf-8"))
    assert response["request_artifact_hash"] == summary["request_artifact_hash"]
    assert response["live_submission"] is False
    assert response["account_mode"] == "paper"

    assert verify_journal_chain(root / JOURNAL_FILENAME) == []

    # The runbook's single final gate command must validate the sealed bundle.
    gate_exit = cli_main(
        ["validate-live-readiness", str(session_dir / BUNDLE_FILENAME), "--now", RECONCILE_NOW]
    )
    capsys.readouterr()
    assert gate_exit == 0


def test_cli_steps_are_resumable_across_invocations(tmp_path: Path, capsys):
    root = tmp_path / "sessions"
    prices = _write_prices(tmp_path, UP_WEEK_PRICES)
    steps = [
        ["live-session", "propose", "--session", "w2", "--root", str(root), "--now", PROPOSE_NOW,
         "--prices-file", str(prices)],
        ["live-session", "review", "--session", "w2", "--root", str(root)],
        ["live-session", "approve", "--session", "w2", "--root", str(root), "--now", APPROVE_NOW,
         "--approved-by", "operator-1", "--reason", "weekly plan approved"],
        ["live-session", "execute", "--session", "w2", "--root", str(root), "--now", EXECUTE_NOW],
        ["live-session", "reconcile", "--session", "w2", "--root", str(root), "--now", RECONCILE_NOW],
        ["live-session", "status", "--session", "w2", "--root", str(root)],
    ]
    # Each invocation reloads session state from disk, so the approval can
    # happen hours later or after an interpreter restart.
    for step in steps:
        assert cli_main(step) == 0, step
    capsys.readouterr()

    state = json.loads((root / "w2" / STATE_FILENAME).read_text(encoding="utf-8"))
    assert state["status"] == "reconciled"
    assert state["proposed_at"] == PROPOSE_NOW
    assert state["approved_at"] == APPROVE_NOW
    assert state["executed_at"] == EXECUTE_NOW
    assert state["reconciled_at"] == RECONCILE_NOW


def test_execute_refuses_tampered_handoff(tmp_path: Path):
    root = tmp_path / "sessions"
    propose_session(_config(tmp_path, "w3"), now=PROPOSE_NOW)
    approve_session(
        "w3", root=root, approved_by="operator-1", reason="weekly plan approved", now=APPROVE_NOW
    )

    handoff_path = root / "w3" / "dry_run_orders.json"
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    payload["orders"][0]["quantity"] = payload["orders"][0]["quantity"] * 10
    handoff_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    review = review_session("w3", root=root)
    assert "hash_matches_proposed_state=False" in review

    with pytest.raises(LiveSessionError, match="does not match"):
        execute_session("w3", root=root, now=EXECUTE_NOW)

    state = json.loads((root / "w3" / STATE_FILENAME).read_text(encoding="utf-8"))
    assert state["status"] == "approved"
    assert not (root / "w3" / RESPONSE_FILENAME).exists()


def test_execute_refuses_tampered_approval_artifact(tmp_path: Path):
    root = tmp_path / "sessions"
    propose_session(_config(tmp_path, "w3b"), now=PROPOSE_NOW)
    approve_session(
        "w3b", root=root, approved_by="operator-1", reason="weekly plan approved", now=APPROVE_NOW
    )

    approval_path = root / "w3b" / APPROVAL_FILENAME
    payload = json.loads(approval_path.read_text(encoding="utf-8"))
    payload["request_artifact_hash"] = "sha256:" + "0" * 64
    approval_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(LiveSessionError, match="execution is refused"):
        execute_session("w3b", root=root, now=EXECUTE_NOW)
    assert not (root / "w3b" / RESPONSE_FILENAME).exists()


def test_execute_refuses_expired_approval(tmp_path: Path):
    root = tmp_path / "sessions"
    propose_session(_config(tmp_path, "w4"), now=PROPOSE_NOW)
    approve_session(
        "w4",
        root=root,
        approved_by="operator-1",
        reason="weekly plan approved",
        now=APPROVE_NOW,
        valid_minutes=1,
    )

    with pytest.raises(LiveSessionError, match="expired"):
        execute_session("w4", root=root, now="2026-07-02T11:00:00Z")
    assert not (root / "w4" / RESPONSE_FILENAME).exists()


def test_reject_blocks_execution_and_is_idempotent(tmp_path: Path):
    root = tmp_path / "sessions"
    propose_session(_config(tmp_path, "w5"), now=PROPOSE_NOW)
    rejected = reject_session(
        "w5", root=root, rejected_by="operator-1", reason="volatility too high this week", now=APPROVE_NOW
    )
    assert rejected["status"] == "rejected"
    assert rejected["approval_latency_seconds"] == 300.0
    assert (root / "w5" / "rejection_record.json").exists()

    again = reject_session(
        "w5", root=root, rejected_by="operator-1", reason="volatility too high this week", now=EXECUTE_NOW
    )
    assert again["already_rejected"] is True

    with pytest.raises(LiveSessionError, match="rejected"):
        execute_session("w5", root=root, now=EXECUTE_NOW)
    with pytest.raises(LiveSessionError, match="rejected"):
        approve_session("w5", root=root, approved_by="operator-1", reason="late change", now=EXECUTE_NOW)

    summary = json.loads((root / "w5" / SESSION_SUMMARY_FILENAME).read_text(encoding="utf-8"))
    assert summary["status"] == "rejected"


def test_no_trade_week_is_recorded(tmp_path: Path):
    root = tmp_path / "sessions"
    config = LiveSessionConfig(
        session_id="w6", root=root, prices_file=_write_prices(tmp_path, DOWN_WEEK_PRICES)
    )
    proposed = propose_session(config, now=PROPOSE_NOW)
    assert proposed["status"] == "no_trade"
    assert proposed["order_count"] == 0

    summary = json.loads((root / "w6" / SESSION_SUMMARY_FILENAME).read_text(encoding="utf-8"))
    assert summary["status"] == "no_trade"
    with pytest.raises(LiveSessionError, match="no-trade"):
        approve_session("w6", root=root, approved_by="operator-1", reason="nothing", now=APPROVE_NOW)

    reconciled = reconcile_session("w6", root=root, now=RECONCILE_NOW)
    assert reconciled["status"] == "no_trade"


def test_llm_decision_source_is_a_stub_without_any_call(tmp_path: Path):
    root = tmp_path / "sessions"
    config = _config(tmp_path, "w7", decision_source="llm")
    with pytest.raises(LiveSessionError, match="declared interface only"):
        propose_session(config, now=PROPOSE_NOW)
    assert not (root / "w7" / STATE_FILENAME).exists()


def test_propose_is_idempotent_and_deterministic(tmp_path: Path):
    first = propose_session(_config(tmp_path, "w8"), now=PROPOSE_NOW)
    handoff_path = tmp_path / "sessions" / "w8" / "dry_run_orders.json"
    original_bytes = handoff_path.read_bytes()

    again = propose_session(_config(tmp_path, "w8"), now="2026-07-02T18:00:00Z")
    assert again["already_exists"] is True
    assert handoff_path.read_bytes() == original_bytes

    other_root = tmp_path / "other"
    other = propose_session(
        LiveSessionConfig(
            session_id="w8", root=other_root / "sessions", prices_file=tmp_path / "prices.json"
        ),
        now=PROPOSE_NOW,
    )
    assert other["request_artifact_hash"] == first["request_artifact_hash"]


def test_paper_mock_engine_full_chain(tmp_path: Path):
    session_dir = _run_full_session(tmp_path, "pm1", engine="paper_mock")

    handoff = json.loads((session_dir / "alpaca_paper_orders.json").read_text(encoding="utf-8"))
    response = json.loads((session_dir / RESPONSE_FILENAME).read_text(encoding="utf-8"))
    assert handoff["adapter"] == "alpaca-paper-export-adapter"
    assert handoff["adapter_mode"] == "paper_sandbox"
    assert response["adapter"] == "alpaca-paper-export-adapter"
    assert response["adapter_mode"] == "paper_sandbox"
    assert response["live_submission"] is False

    preflight = json.loads((session_dir / "preflight_summary.json").read_text(encoding="utf-8"))
    assert preflight["ready"] is True


def test_execution_is_idempotent_and_response_bytes_stable(tmp_path: Path):
    session_dir = _run_full_session(tmp_path, "w9")
    root = tmp_path / "sessions"
    response_bytes = (session_dir / RESPONSE_FILENAME).read_bytes()

    executed_again = execute_session("w9", root=root, now="2026-07-02T20:00:00Z")
    assert executed_again["already_executed"] is True
    reconciled_again = reconcile_session("w9", root=root, now="2026-07-02T20:00:00Z")
    assert reconciled_again["already_reconciled"] is True
    assert reconciled_again["preflight_ready"] is True
    assert (session_dir / RESPONSE_FILENAME).read_bytes() == response_bytes


def test_journal_chain_detects_tampering(tmp_path: Path):
    _run_full_session(tmp_path, "w10")
    journal_path = tmp_path / "sessions" / JOURNAL_FILENAME
    assert verify_journal_chain(journal_path) == []

    lines = journal_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["details"]["order_count"] = 99
    lines[0] = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    errors = verify_journal_chain(journal_path)
    assert any("entry_hash does not match" in error for error in errors)


def test_approve_requires_redacted_operator_id(tmp_path: Path):
    root = tmp_path / "sessions"
    propose_session(_config(tmp_path, "w11"), now=PROPOSE_NOW)
    with pytest.raises(LiveSessionError, match="@"):
        approve_session(
            "w11", root=root, approved_by="operator@example.com", reason="ok", now=APPROVE_NOW
        )
    with pytest.raises(LiveSessionError, match="whitespace"):
        approve_session("w11", root=root, approved_by="operator one", reason="ok", now=APPROVE_NOW)
    state = json.loads((root / "w11" / STATE_FILENAME).read_text(encoding="utf-8"))
    assert state["status"] == "proposed"


def test_session_status_lists_sessions(tmp_path: Path):
    _run_full_session(tmp_path, "w12")
    root = tmp_path / "sessions"
    listing = session_status(root=root)
    assert listing["session_count"] == 1
    assert listing["sessions"][0]["session_id"] == "w12"
    assert listing["sessions"][0]["status"] == "reconciled"

    single = session_status("w12", root=root)
    assert single["status"] == "reconciled"
    assert single["request_artifact_hash"].startswith("sha256:")


def test_cli_reports_errors_with_nonzero_exit(tmp_path: Path, capsys):
    root = tmp_path / "sessions"
    exit_code = cli_main(["live-session", "execute", "--session", "missing", "--root", str(root)])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "live-session error" in output


def test_signed_approval_passes_the_gate_it_authorizes(tmp_path: Path):
    """A signed approval must still execute, and its signature must verify.

    Signing previously bricked the session: the closed-world approval validator
    rejected the signature block as an undeclared field, so the very next step
    refused an approval that was strictly more trustworthy than an unsigned one.
    The unit tests for the signing module all passed while the integrated
    feature was broken, which is why this test drives approve -> execute ->
    reconcile end to end.
    """

    from tradearena.tools.approval_signing import (
        generate_approver_keypair,
        verify_approval_signature,
    )

    root = tmp_path / "sessions"
    key_path = tmp_path / "keys" / "approver.ed25519"
    trusted_public = generate_approver_keypair(key_path)

    propose_session(_config(tmp_path, "w1"), now=PROPOSE_NOW)
    approved = approve_session(
        "w1",
        root=root,
        approved_by="operator-1",
        reason="weekly plan approved",
        now=APPROVE_NOW,
        signing_key_path=key_path,
    )
    assert approved["status"] == "approved"

    artifact = json.loads(
        (root / "w1" / "broker_approval_artifact.json").read_text(encoding="utf-8")
    )
    assert verify_approval_signature(artifact, [trusted_public]) == []

    executed = execute_session("w1", root=root, now=EXECUTE_NOW)
    assert executed["status"] == "executed"
    reconciled = reconcile_session("w1", root=root, now=RECONCILE_NOW)
    assert reconciled["status"] == "reconciled"
    assert reconciled["preflight_error_count"] == 0
