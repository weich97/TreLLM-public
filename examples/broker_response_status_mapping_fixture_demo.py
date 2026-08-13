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
    AlpacaPaperExportAdapter,
    BrokerAdapterMode,
    BrokerOrderStatus,
    BrokerResponse,
    BrokerSafetyConfig,
    broker_handoff_artifact_hash,
    write_broker_response_artifact,
)

OUTPUT_DIR = Path("outputs/examples/broker_response_artifact")


def main() -> int:
    orders = [
        Order("AAPL", Side.BUY, 1.0, order_type=OrderType.LIMIT, limit_price=190.0, reason="accepted mapping"),
        Order("MSFT", Side.SELL, 1.0, order_type=OrderType.LIMIT, limit_price=421.0, reason="rejected mapping"),
        Order("NVDA", Side.BUY, 2.0, order_type=OrderType.LIMIT, limit_price=950.0, reason="partial mapping"),
        Order("TSLA", Side.BUY, 0.5, order_type=OrderType.LIMIT, limit_price=180.0, reason="cancel mapping"),
        Order("GOOG", Side.BUY, 0.25, order_type=OrderType.LIMIT, limit_price=170.0, reason="unknown mapping"),
    ]
    adapter = AlpacaPaperExportAdapter(
        client_prefix="status-map",
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
            max_quantity=5.0,
            allowed_symbols=("AAPL", "MSFT", "NVDA", "TSLA", "GOOG"),
        ),
    )
    request_export = adapter.write(orders, OUTPUT_DIR)
    requests = adapter.convert(orders)
    request_artifact = OUTPUT_DIR / "alpaca_paper_orders.json"
    responses = [
        BrokerResponse(
            client_order_id=requests[0].client_order_id,
            status=BrokerOrderStatus.ACCEPTED,
            broker_order_id="paper-status-accepted-1",
            submitted_quantity=requests[0].quantity,
            accepted_quantity=requests[0].quantity,
            submitted_at="2026-05-31T15:00:00Z",
            broker_timestamp="2026-05-31T15:00:01Z",
            account_mode="paper",
        ),
        BrokerResponse(
            client_order_id=requests[1].client_order_id,
            status=BrokerOrderStatus.REJECTED,
            submitted_quantity=requests[1].quantity,
            rejection_reason="paper sandbox rejected by symbol-level risk rule",
            submitted_at="2026-05-31T15:00:00Z",
            broker_timestamp="2026-05-31T15:00:02Z",
            account_mode="paper",
        ),
        BrokerResponse(
            client_order_id=requests[2].client_order_id,
            status=BrokerOrderStatus.PARTIALLY_FILLED,
            broker_order_id="paper-status-partial-3",
            submitted_quantity=requests[2].quantity,
            accepted_quantity=requests[2].quantity,
            fill_quantity=0.5,
            fill_price=950.25,
            fees=0.02,
            submitted_at="2026-05-31T15:00:00Z",
            broker_timestamp="2026-05-31T15:00:03Z",
            account_mode="paper",
        ),
        BrokerResponse(
            client_order_id=requests[3].client_order_id,
            status=BrokerOrderStatus.CANCELED,
            broker_order_id="paper-status-canceled-4",
            submitted_quantity=requests[3].quantity,
            accepted_quantity=requests[3].quantity,
            rejection_reason="operator canceled synthetic paper order before fill",
            submitted_at="2026-05-31T15:00:00Z",
            broker_timestamp="2026-05-31T15:00:04Z",
            account_mode="paper",
        ),
        BrokerResponse(
            client_order_id=requests[4].client_order_id,
            status=BrokerOrderStatus.UNKNOWN,
            submitted_quantity=requests[4].quantity,
            rejection_reason="paper sandbox raw status could not be mapped",
            submitted_at="2026-05-31T15:00:00Z",
            broker_timestamp="2026-05-31T15:00:05Z",
            account_mode="paper",
        ),
    ]
    response_artifact = OUTPUT_DIR / "response_artifact.json"
    response_export = write_broker_response_artifact(
        requests=requests,
        responses=responses,
        output=response_artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
        request_artifact_hash=broker_handoff_artifact_hash(request_artifact),
    )
    payload = json.loads(response_artifact.read_text(encoding="utf-8"))
    summary = {
        "request_export": request_export,
        "response_export": response_export,
        "reconciliation": payload["reconciliation"],
        "statuses": [response["status"] for response in payload["responses"]],
        "live_submission": False,
        "safety_note": "Synthetic paper status-mapping fixture only; no broker credentials are read and no live orders are submitted.",
        "verification_commands": [
            "python scripts/validate_broker_handoff_artifact.py outputs/examples/broker_response_artifact/alpaca_paper_orders.json",
            "python scripts/validate_broker_response_artifact.py outputs/examples/broker_response_artifact/response_artifact.json",
        ],
    }
    write_json(OUTPUT_DIR / "summary.json", summary)
    print("Broker response status-mapping fixture")
    print(f"  statuses={', '.join(summary['statuses'])}")
    print(f"  wrote={response_artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
