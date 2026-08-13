from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.domain import Order, Side
from tradearena.core.serialization import write_json
from tradearena.tools import AlpacaPaperOrder, BrokerOrderStatus, BrokerResponse, PaperSandboxAdapterSkeleton

OUTPUT_DIR = Path("outputs/examples/mock_paper_sandbox_client")
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


class MockPaperSandboxClient:
    """Deterministic paper client fixture with no broker SDK or network call."""

    def __init__(self) -> None:
        self.calls = 0

    def submit_paper_orders(self, requests: Sequence[AlpacaPaperOrder]) -> list[BrokerResponse]:
        self.calls += 1
        return [
            BrokerResponse(
                client_order_id=request.client_order_id,
                status=BrokerOrderStatus.ACCEPTED,
                broker_order_id=f"mock-paper-{idx:04d}",
                submitted_quantity=request.quantity,
                accepted_quantity=request.quantity,
                submitted_at="2026-05-31T16:00:00Z",
                broker_timestamp=f"2026-05-31T16:00:0{idx}Z",
                account_mode="paper",
            )
            for idx, request in enumerate(requests, start=1)
        ]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = MockPaperSandboxClient()
    adapter = PaperSandboxAdapterSkeleton(client=client, client_prefix="mock-paper")
    orders = [
        Order("AAPL", Side.BUY, 1.0, reason="mock paper sandbox allocation"),
        Order("MSFT", Side.BUY, 0.5, reason="mock paper sandbox allocation"),
    ]
    result = adapter.submit_paper(orders, OUTPUT_DIR)
    summary = {
        "schema": "trellm_mock_paper_sandbox_client_demo_v0.1",
        "adapter": adapter.name,
        "adapter_mode": "paper_sandbox",
        "account_mode": "paper",
        "live_submission": result["live_submission"],
        "default_network_call": False,
        "mock_client_calls": client.calls,
        "request_artifact": "outputs/examples/mock_paper_sandbox_client/alpaca_paper_orders.json",
        "response_artifact": "outputs/examples/mock_paper_sandbox_client/paper_sandbox_response_artifact.json",
        "response_count": result["response_count"],
        "missing_response_count": result["missing_response_count"],
        "unmatched_response_count": result["unmatched_response_count"],
        "safety_note": (
            "Mock injected paper client only; no broker credentials are read and no live or network submission occurs."
        ),
    }
    write_json(SUMMARY_PATH, summary)
    print("Mock paper sandbox client demo")
    print(f"  adapter_mode={summary['adapter_mode']}")
    print(f"  mock_client_calls={summary['mock_client_calls']}")
    print(f"  wrote={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
