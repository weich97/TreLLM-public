from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json
from tradearena.tools import (
    AlpacaPaperOrder,
    BrokerAdapterMode,
    BrokerOrderStatus,
    BrokerResponse,
    broker_handoff_artifact_hash,
    validate_live_readiness_preflight_bundle_file,
    write_broker_response_artifact,
)

OUTPUT_DIR = Path("outputs/examples/live_readiness_preflight")
BUNDLE_PATH = OUTPUT_DIR / "preflight_bundle.json"
RESPONSE_PATH = OUTPUT_DIR / "preflight_response_artifact.json"
SUMMARY_PATH = OUTPUT_DIR / "preflight_summary.json"
DEMO_NOW = "2026-05-31T12:30:00Z"


def main() -> int:
    for command in (
        [sys.executable, "examples/broker_capability_manifest_demo.py"],
        [sys.executable, "examples/broker_approval_safety_demo.py"],
        [sys.executable, "examples/operator_runbook_demo.py"],
    ):
        subprocess.run(command, cwd=ROOT, check=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_bound_response_artifact()
    bundle = {
        "schema": "trellm_live_readiness_preflight_v0.1",
        "capability_manifest": "outputs/examples/broker_capability_manifest/capability_manifest.json",
        "handoff_artifact": "outputs/examples/broker_approval_safety/dry_run_orders.json",
        "approval_artifact": "outputs/examples/broker_approval_safety/broker_approval_artifact.json",
        "response_artifact": "outputs/examples/live_readiness_preflight/preflight_response_artifact.json",
        "operator_runbook_artifact": "outputs/examples/operator_runbook/summary.json",
        "approval_checked_at": DEMO_NOW,
        "safety_note": (
            "This preflight bundle links offline and paper artifacts for review. "
            "It performs no broker API calls and does not authorize live submission."
        ),
    }
    write_json(BUNDLE_PATH, bundle)
    summary, errors = validate_live_readiness_preflight_bundle_file(BUNDLE_PATH, now=DEMO_NOW)
    write_json(SUMMARY_PATH, summary)
    print("Live-readiness preflight demo")
    print(f"  ready={summary['ready']}")
    print(f"  error_count={summary['error_count']}")
    print(f"  wrote={BUNDLE_PATH}")
    return 0 if not errors else 1


def _write_bound_response_artifact() -> None:
    handoff_path = ROOT / "outputs/examples/broker_approval_safety/dry_run_orders.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    request_hash = broker_handoff_artifact_hash(handoff)
    requests = [_handoff_order_to_request(row) for row in handoff["orders"]]
    responses = [
        BrokerResponse(
            client_order_id=request.client_order_id,
            status=BrokerOrderStatus.REJECTED,
            submitted_quantity=request.quantity,
            rejection_reason="dry-run preflight response; no broker API call was made",
            submitted_at="2026-05-31T12:30:00Z",
            broker_timestamp="2026-05-31T12:30:01Z",
            account_mode=request.account_mode,
        )
        for request in requests
    ]
    write_broker_response_artifact(
        requests=requests,
        responses=responses,
        output=RESPONSE_PATH,
        adapter=str(handoff["adapter"]),
        adapter_mode=BrokerAdapterMode.DRY_RUN,
        account_mode=str(handoff["account_mode"]),
        request_artifact_hash=request_hash,
    )


def _handoff_order_to_request(row: dict[str, object]) -> AlpacaPaperOrder:
    limit_price = row.get("limit_price")
    max_notional = row.get("max_notional")
    return AlpacaPaperOrder(
        client_order_id=str(row["client_order_id"]),
        adapter_mode=str(row["adapter_mode"]),
        account_mode=str(row["account_mode"]),
        symbol=str(row["symbol"]),
        side=str(row["side"]),
        order_type=str(row["order_type"]),
        quantity=float(row["quantity"]),
        time_in_force=str(row["time_in_force"]),
        limit_price=None if limit_price is None else float(limit_price),
        submit_live=bool(row["submit_live"]),
        approval_status=str(row["approval_status"]),
        max_notional=None if max_notional is None else float(max_notional),
        reason=str(row["reason"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
