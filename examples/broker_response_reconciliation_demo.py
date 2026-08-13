from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.domain import Order, Side
from tradearena.core.serialization import write_json
from tradearena.tools import (
    AlpacaPaperExportAdapter,
    BrokerAdapterMode,
    BrokerOrderStatus,
    BrokerResponse,
    BrokerSafetyConfig,
    write_broker_response_artifact,
)

OUTPUT_DIR = Path("outputs/examples/broker_response_reconciliation")


def main() -> int:
    orders = [
        Order("AAPL", Side.BUY, 2.0, reason="paper sandbox rebalance"),
        Order("MSFT", Side.SELL, 1.0, reason="paper sandbox concentration trim"),
        Order("NVDA", Side.BUY, 0.5, reason="paper sandbox model allocation"),
    ]
    adapter = AlpacaPaperExportAdapter(
        client_prefix="paper-recon",
        safety=BrokerSafetyConfig(
            mode=BrokerAdapterMode.PAPER_SANDBOX,
            account_mode="paper",
            max_quantity=5.0,
            allowed_symbols=("AAPL", "MSFT", "NVDA"),
        ),
    )
    request_export = adapter.write(orders, OUTPUT_DIR)
    requests = adapter.convert(orders)
    responses = [
        BrokerResponse(
            client_order_id=requests[0].client_order_id,
            status=BrokerOrderStatus.FILLED,
            broker_order_id="paper-filled-1",
            submitted_quantity=requests[0].quantity,
            accepted_quantity=requests[0].quantity,
            fill_quantity=requests[0].quantity,
            fill_price=190.25,
            fees=0.03,
            submitted_at="2026-05-31T14:30:00Z",
            broker_timestamp="2026-05-31T14:30:01Z",
            account_mode="paper",
        ),
        BrokerResponse(
            client_order_id=requests[1].client_order_id,
            status=BrokerOrderStatus.PARTIALLY_FILLED,
            broker_order_id="paper-partial-2",
            submitted_quantity=requests[1].quantity,
            accepted_quantity=requests[1].quantity,
            fill_quantity=0.4,
            fill_price=421.10,
            fees=0.01,
            submitted_at="2026-05-31T14:30:00Z",
            broker_timestamp="2026-05-31T14:30:04Z",
            account_mode="paper",
        ),
        BrokerResponse(
            client_order_id="paper-recon-unmatched-0000",
            status=BrokerOrderStatus.REJECTED,
            submitted_quantity=1.0,
            rejection_reason="paper account symbol permission mismatch",
            submitted_at="2026-05-31T14:30:00Z",
            broker_timestamp="2026-05-31T14:30:05Z",
            account_mode="paper",
        ),
    ]
    response_artifact = OUTPUT_DIR / "broker_response_artifact.json"
    reconciliation = write_broker_response_artifact(
        requests=requests,
        responses=responses,
        output=response_artifact,
        adapter=adapter.name,
        adapter_mode=BrokerAdapterMode.PAPER_SANDBOX,
        account_mode="paper",
    )
    payload = json.loads(response_artifact.read_text(encoding="utf-8"))
    summary = {
        "request_export": request_export,
        "response_artifact": reconciliation,
        "reconciliation": payload["reconciliation"],
        "live_submission": False,
        "safety_note": "Synthetic paper responses only; no broker credentials are read and no live orders are submitted.",
    }
    write_json(OUTPUT_DIR / "summary.json", summary)
    print("Broker response reconciliation demo")
    print(f"  requests={request_export['order_count']} responses={reconciliation['response_count']}")
    print(f"  missing={reconciliation['missing_response_count']} unmatched={reconciliation['unmatched_response_count']}")
    print(f"  wrote={response_artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
