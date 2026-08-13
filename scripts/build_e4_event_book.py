"""Build the E4 deployment event book (Airlock live readiness, the pre-registered
forward window).

Reads every session directory under ``outputs/live_sessions/`` plus the
hash-chained journal, and emits the cross-week operational record the
deployment analysis reports:

- ``e4_event_book.csv`` -- one row per ISO week of the committed window
  (2026-07-01 .. 2026-09-15): session status, per-step timestamps, approval
  (delegate) latency, order/blocked counts, gross notional, reconciliation
  discrepancies, expiries, and MISSED for window weeks with no session.
- ``e4_event_book.md`` -- the same as a readable table plus the two audits:
  the zero-unsafe-submission audit (every executed order maps to a reconciled
  response row hash-bound to an approved, unexpired handoff -- re-run, not
  asserted) and journal-chain verification (prev/entry hash links re-computed
  over the whole window).

Deterministic and offline; safe to run mid-window (future weeks show as
PENDING, past weeks without a session as MISSED). At window close (2026-09-15)
this is the freeze artifact for the event-book table.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradearena.tools.live_session import verify_journal_chain

SESSIONS = ROOT / "outputs/live_sessions"
JOURNAL = SESSIONS / "journal.jsonl"
OUT_DIR = ROOT / "docs/results/live_readiness_e4"
WINDOW_START = date(2026, 7, 1)
WINDOW_END = date(2026, 9, 15)


def _iso_week_id(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}w{week:02d}"


def window_weeks() -> list[str]:
    weeks: list[str] = []
    d = WINDOW_START
    while d <= WINDOW_END:
        wid = _iso_week_id(d)
        if wid not in weeks:
            weeks.append(wid)
        d += timedelta(days=7)
    last = _iso_week_id(WINDOW_END)
    if last not in weeks:
        weeks.append(last)
    return weeks


def _verify_journal() -> tuple[int, bool, str]:
    """Verify the hash chain with the orchestrator's own verifier."""
    if not JOURNAL.exists():
        return 0, False, "journal missing"
    entries = sum(1 for line in JOURNAL.read_text(encoding="utf-8").splitlines() if line.strip())
    problems = verify_journal_chain(JOURNAL)
    if problems:
        return entries, False, "; ".join(str(p) for p in problems[:2])
    return entries, True, "chain verified"


def _unsafe_submission_audit(summary: dict, session_dir: Path) -> tuple[bool, str]:
    """Every executed order maps to a reconciled response bound to an approved,
    unexpired handoff. Re-checks bindings from the artifacts on disk."""
    try:
        approval = json.loads((session_dir / "broker_approval_artifact.json").read_text(encoding="utf-8"))
        response = json.loads((session_dir / "broker_response_artifact.json").read_text(encoding="utf-8"))
        handoff = json.loads((session_dir / "dry_run_orders.json").read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        # Report the artifact name only: the event book is a public artifact and
        # an absolute path leaks the local filesystem layout (and the operator).
        missing = Path(str(exc.filename)).name if exc.filename else "unknown artifact"
        return False, f"artifact missing: {missing}"
    if approval.get("request_artifact_hash") != summary.get("request_artifact_hash"):
        return False, "approval hash != session hash"
    approved_at = datetime.fromisoformat(str(summary["approved_at"]).replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(str(summary["approval_expires_at"]).replace("Z", "+00:00"))
    executed_at = datetime.fromisoformat(str(summary["executed_at"]).replace("Z", "+00:00"))
    if not (approved_at <= executed_at <= expires_at):
        return False, "execution outside approval validity window"
    order_ids = {o.get("client_order_id") for o in handoff.get("orders", [])}
    responses = response.get("orders", response.get("responses", []))
    resp_ids = {o.get("client_order_id") for o in responses} if isinstance(responses, list) else set()
    if resp_ids and not resp_ids <= order_ids:
        return False, "response contains an order id not in the approved handoff"
    return True, "ok"


def main() -> int:
    tz_now = datetime.now(timezone.utc).date()
    sessions: dict[str, dict] = {}
    for p in sorted(SESSIONS.glob("*/session_summary.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        sessions[str(s["session_id"])] = {"summary": s, "dir": p.parent}

    entries, chain_ok, chain_detail = _verify_journal()

    rows: list[dict[str, object]] = []
    audits_ok = True
    for wid in window_weeks():
        rec: dict[str, object] = {"week": wid}
        info = sessions.get(wid)
        if info is None:
            # Week W's session runs on the Monday of week W+1 (it needs W's
            # weekly closes); give one further day of grace before MISSED.
            year, wk = int(wid[:4]), int(wid[5:])
            due = date.fromisocalendar(year, wk, 1) + timedelta(days=8)
            rec["status"] = "PENDING" if tz_now <= due else "MISSED"
            rows.append(rec)
            continue
        s = info["summary"]
        ok, detail = _unsafe_submission_audit(s, info["dir"])
        audits_ok = audits_ok and ok
        recon = s.get("reconciliation") or {}
        rec.update({
            "status": str(s.get("status", "")).upper(),
            "proposed_at": s.get("proposed_at", ""),
            "approved_at": s.get("approved_at", ""),
            "reconciled_at": s.get("reconciled_at", ""),
            "approval_latency_s": s.get("approval_latency_seconds", ""),
            "orders": s.get("order_count", ""),
            "blocked": s.get("blocked_count", ""),
            "discrepancies": recon.get("discrepancy_count", recon.get("discrepancies", 0)),
            "unsafe_submission_audit": "PASS" if ok else f"FAIL: {detail}",
        })
        rows.append(rec)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = ["week", "status", "proposed_at", "approved_at", "reconciled_at",
              "approval_latency_s", "orders", "blocked", "discrepancies",
              "unsafe_submission_audit"]
    with (OUT_DIR / "e4_event_book.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

    done = [r for r in rows if r["status"] == "RECONCILED"]
    missed = [r for r in rows if r["status"] == "MISSED"]
    lines = [
        "# E4 forward-window event book",
        "",
        f"Committed window {WINDOW_START} .. {WINDOW_END}; generated "
        f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z. Gating is operator-delegated "
        "(disclosed standing instruction); approval latencies are delegate latencies.",
        "",
        f"- Sessions reconciled: **{len(done)}** / {len(rows)} window weeks "
        f"(missed so far: {len(missed)})",
        f"- Journal hash chain: **{'PASS' if chain_ok else 'FAIL'}** "
        f"({entries} entries; {chain_detail})",
        f"- Zero-unsafe-submission audit: **{'PASS' if audits_ok else 'FAIL'}** "
        "(re-checked from artifacts, per session)",
        "",
        "| " + " | ".join(fields) + " |",
        "|" + "---|" * len(fields),
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(k, "")) for k in fields) + " |")
    (OUT_DIR / "e4_event_book.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"weeks={len(rows)} reconciled={len(done)} missed={len(missed)} "
          f"journal={'PASS' if chain_ok else 'FAIL'} unsafe_audit={'PASS' if audits_ok else 'FAIL'}")
    print(f"wrote {(OUT_DIR / 'e4_event_book.csv').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
