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
from tradearena.tools import BrokerSafetyConfig, DryRunBrokerAdapter, validate_broker_handoff_artifact

OUTPUT_DIR = Path("outputs/examples/dry_run_broker_adapter")


def main() -> int:
    orders = [
        Order("AAPL", Side.BUY, 1.25, order_type=OrderType.MARKET, reason="dry-run rebalance review"),
        Order("MSFT", Side.SELL, 0.75, order_type=OrderType.LIMIT, limit_price=420.0, reason="dry-run trim review"),
    ]
    adapter = DryRunBrokerAdapter(
        client_prefix="dry-demo",
        safety=BrokerSafetyConfig(
            account_mode="paper",
            max_quantity=2.0,
            allowed_symbols=("AAPL", "MSFT"),
        ),
    )
    result = adapter.write(orders, OUTPUT_DIR)
    artifact = Path(result["json"])
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    validation_errors = validate_broker_handoff_artifact(payload)
    summary = {
        "adapter": adapter.name,
        "adapter_mode": result["adapter_mode"],
        "account_mode": result["account_mode"],
        "order_count": result["order_count"],
        "paper_only": result["paper_only"],
        "live_submission": payload["live_submission"],
        "validated": not validation_errors,
        "validation_errors": validation_errors,
        "safety_note": "Dry-run request-shape validation only; no broker credentials are read and no API calls are made.",
    }
    write_json(OUTPUT_DIR / "summary.json", summary)
    print("Dry-run broker adapter demo")
    print(f"  orders={summary['order_count']} mode={summary['adapter_mode']}")
    print(f"  validated={summary['validated']}")
    print(f"  wrote={artifact}")
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
