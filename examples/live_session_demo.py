from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.cli import main as cli_main
from tradearena.tools import (
    LiveSessionConfig,
    approve_session,
    execute_session,
    propose_session,
    reconcile_session,
    review_session,
    verify_journal_chain,
)

OUTPUT_ROOT = ROOT / "outputs" / "examples" / "live_session_demo"
SESSION_ID = "demo-2026w27"
PRICES_PATH = OUTPUT_ROOT / "weekly_prices.json"
PROPOSE_NOW = "2026-07-02T09:00:00Z"
APPROVE_NOW = "2026-07-02T09:05:00Z"
EXECUTE_NOW = "2026-07-02T09:06:00Z"
RECONCILE_NOW = "2026-07-02T09:07:00Z"

# Deterministic operator-style weekly prices: BTC=F momentum is negative, so
# the rule-based decision source stays in cash for that symbol.
WEEKLY_PRICES = {
    "BTC-USD": {"close": 109250.5, "prev_close": 108000.0},
    "BTC=F": {"close": 109900.0, "prev_close": 110500.0},
    "GSPC": {"close": 6150.25, "prev_close": 6100.0},
}


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PRICES_PATH.write_text(json.dumps(WEEKLY_PRICES, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    config = LiveSessionConfig(
        session_id=SESSION_ID,
        root=OUTPUT_ROOT,
        prices_file=PRICES_PATH,
    )
    proposed = propose_session(config, now=PROPOSE_NOW)
    print("Live session demo: propose")
    print(f"  status={proposed['status']} orders={proposed['order_count']} blocked={proposed['blocked_count']}")
    print(f"  request_artifact_hash={proposed['request_artifact_hash']}")
    print()
    print(review_session(SESSION_ID, root=OUTPUT_ROOT))
    print()

    approved = approve_session(
        SESSION_ID,
        root=OUTPUT_ROOT,
        approved_by="operator-demo-7",
        reason="paper shadow checks passed for this bounded weekly rebalance",
        now=APPROVE_NOW,
    )
    print("Live session demo: approve")
    print(f"  approval_id={approved['approval_id']} expires_at={approved['expires_at']}")
    print(f"  approval_latency_seconds={approved['approval_latency_seconds']}")

    executed = execute_session(SESSION_ID, root=OUTPUT_ROOT, now=EXECUTE_NOW)
    print("Live session demo: execute")
    print(f"  response_count={executed['response_count']}")

    reconciled = reconcile_session(SESSION_ID, root=OUTPUT_ROOT, now=RECONCILE_NOW)
    print("Live session demo: reconcile")
    print(f"  preflight_ready={reconciled['preflight_ready']}")
    print(f"  session_summary={reconciled['session_summary']}")
    print(f"  final_gate_command={reconciled['final_gate_command']}")

    bundle_path = OUTPUT_ROOT / SESSION_ID / "preflight_bundle.json"
    gate_exit = cli_main(["validate-live-readiness", str(bundle_path), "--now", RECONCILE_NOW])
    journal_errors = verify_journal_chain(OUTPUT_ROOT / "journal.jsonl")
    print("Live session demo: final gate")
    print(f"  validate_live_readiness_exit={gate_exit}")
    print(f"  journal_chain_valid={not journal_errors}")

    print()
    print("Weekly command sequence (real session under outputs/live_sessions):")
    print("  1. python -m tradearena.cli live-session propose --session 2026w27 --prices-file <weekly_prices.json>")
    print("  2. python -m tradearena.cli live-session review --session 2026w27")
    print('  3. python -m tradearena.cli live-session approve --session 2026w27 --approved-by <operator-id> --reason "<why>"')
    print("     (or) python -m tradearena.cli live-session reject --session 2026w27 --rejected-by <operator-id> --reason \"<why>\"")
    print("  4. python -m tradearena.cli live-session execute --session 2026w27")
    print("  5. python -m tradearena.cli live-session reconcile --session 2026w27")
    print("  6. run the printed final_gate_command to re-verify the sealed preflight bundle")

    success = (
        proposed["status"] == "proposed"
        and reconciled["preflight_ready"] is True
        and gate_exit == 0
        and not journal_errors
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
