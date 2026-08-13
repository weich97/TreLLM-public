from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.domain import Order, OrderType, Side
from tradearena.core.serialization import write_json
from tradearena.tools import (
    BrokerAdapterContractError,
    BrokerApproval,
    BrokerSafetyConfig,
    DryRunBrokerAdapter,
    broker_handoff_artifact_hash,
    broker_safety_from_approval_artifact,
    build_broker_approval_artifact,
    validate_broker_approval_artifact,
    validate_broker_approval_request_binding,
)

OUTPUT_DIR = Path("outputs/examples/broker_approval_safety")
SUMMARY_PATH = OUTPUT_DIR / "summary.json"
HANDOFF_PATH = OUTPUT_DIR / "dry_run_orders.json"
APPROVAL_PATH = OUTPUT_DIR / "broker_approval_artifact.json"
DEMO_NOW = "2026-05-31T12:30:00Z"
VERIFICATION_COMMANDS = [
    f"python scripts/validate_broker_handoff_artifact.py {HANDOFF_PATH.as_posix()}",
    f"python scripts/hash_broker_handoff_artifact.py {HANDOFF_PATH.as_posix()}",
    f"python scripts/validate_broker_approval_artifact.py {APPROVAL_PATH.as_posix()} --now {DEMO_NOW}",
    (
        f"python scripts/validate_broker_approval_binding.py {APPROVAL_PATH.as_posix()} "
        f"{HANDOFF_PATH.as_posix()} --now {DEMO_NOW}"
    ),
]


def main() -> int:
    order = Order(
        "AAPL",
        Side.BUY,
        2.0,
        order_type=OrderType.LIMIT,
        limit_price=100.0,
        reason="approved demo order",
    )
    dry_run = DryRunBrokerAdapter(
        client_prefix="approval-demo",
        safety=BrokerSafetyConfig(
            account_mode="paper",
            max_quantity=5.0,
            allowed_symbols=("AAPL", "MSFT"),
            allowed_order_types=(OrderType.LIMIT,),
        ),
    )
    dry_run.write([order], OUTPUT_DIR)
    request_hash = broker_handoff_artifact_hash(HANDOFF_PATH)

    approval = BrokerApproval(
        approval_status="approved",
        approved_by="operator-demo-7",
        approved_at="2026-05-31T12:00:00Z",
        max_notional=250.0,
        allowed_symbols=("AAPL", "MSFT"),
        approval_reason="paper shadow checks passed for this bounded rebalance",
    )
    artifact = build_broker_approval_artifact(
        approval,
        approval_id="approval-demo-001",
        account_mode="live",
        max_quantity=5.0,
        allowed_order_types=(OrderType.LIMIT,),
        expires_at="2026-05-31T13:00:00Z",
        request_artifact_hash=request_hash,
    )
    validation_errors = validate_broker_approval_artifact(artifact, now=DEMO_NOW)
    binding_errors = validate_broker_approval_request_binding(artifact, HANDOFF_PATH, now=DEMO_NOW)
    safety = broker_safety_from_approval_artifact(artifact, now=DEMO_NOW, request_artifact=HANDOFF_PATH)

    approved_order_passed = False
    oversized_order_blocked = False
    blocked_reason = ""
    safety.validate_order(order, reference_price=100.0)
    approved_order_passed = True
    try:
        safety.validate_order(
            Order("AAPL", Side.BUY, 3.0, order_type=OrderType.LIMIT, limit_price=100.0, reason="oversized demo order"),
            reference_price=100.0,
        )
    except BrokerAdapterContractError as exc:
        oversized_order_blocked = True
        blocked_reason = str(exc)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    APPROVAL_PATH.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "approval_id": artifact["approval_id"],
        "approval_validated": not validation_errors,
        "request_hash_bound": not binding_errors,
        "approval_checked_at": DEMO_NOW,
        "request_artifact_hash": request_hash,
        "validation_errors": validation_errors,
        "binding_errors": binding_errors,
        "verification_commands": VERIFICATION_COMMANDS,
        "adapter_mode": safety.mode.value,
        "account_mode": safety.account_mode,
        "allowed_symbols": list(safety.allowed_symbols),
        "allowed_order_types": [order_type.value for order_type in safety.allowed_order_types],
        "max_notional": safety.max_notional,
        "max_quantity": safety.max_quantity,
        "approved_order_passed": approved_order_passed,
        "oversized_order_blocked": oversized_order_blocked,
        "blocked_reason": blocked_reason,
        "safety_note": "Approval artifact is redacted and local-only; no broker credentials are read and no orders are submitted.",
    }
    write_json(SUMMARY_PATH, summary)
    print("Broker approval safety demo")
    print(f"  approval_validated={summary['approval_validated']}")
    print(f"  request_hash_bound={summary['request_hash_bound']}")
    print(f"  approved_order_passed={approved_order_passed}")
    print(f"  oversized_order_blocked={oversized_order_blocked}")
    print(f"  wrote={APPROVAL_PATH}")
    return 0 if not validation_errors and not binding_errors and approved_order_passed and oversized_order_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
