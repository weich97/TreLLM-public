"""Evaluate and tabulate the C2 forward-frozen window (v0.3 benchmark).

The C2 commitment (``docs/results/forward_window_commitment_2026q3.json``) was
hash-frozen and git-timestamped on 2026-06-11, before the window opened; it
pins the window, symbols, weekly cadence, E1 (realistic-stress) execution,
max-position risk, and the Sharpe metric -- but NOT a model set (the
anti-memorization guarantee is about the future *data*, so the current
headline models are a valid choice). This script is the one-command
window-close deliverable:

1. **Verify** the frozen commitment: recompute the declaration hash and confirm
   the commitment's git-history date precedes ``window_start`` (refuses to
   proceed otherwise -- a tampered or post-dated commitment is not C2 evidence).
2. **Fetch** real daily OHLCV for the committed symbols over the window into a
   dedicated data dir, with a provenance record (source, fetch UTC, row counts,
   data hash). Before window close it fetches only the elapsed portion.
3. **Run** the committed protocol on that data via the tested real-market
   leaderboard machinery (``run_real_market_leaderboard.py``, ``c2_window``
   scenario). ``--mode dry-run`` (default) runs deterministic baselines only,
   proving the whole pipeline with zero LLM spend; ``--mode final`` (window
   close) runs the direct headline models.
4. **Tabulate** into ``tables/c2_window.tex`` (per-model
   Sharpe / total return / max drawdown / rank) plus a C2 provenance JSON.

Usage before window close (proves the plumbing today):
    python scripts/build_v03_c2_window.py --fetch --mode dry-run
At window close (2026-09-15):
    python scripts/build_v03_c2_window.py --fetch --mode final
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

COMMITMENT = ROOT / "docs/results/forward_window_commitment_2026q3.json"
DATA_DIR = ROOT / "data/real/c2_window_2026q3"
OUT_DIR = ROOT / "docs/results/v0_3_c2_window"
LEADERBOARD_OUT = ROOT / "docs/results/v0_3_c2_window/leaderboard"
TABLE = ROOT / "tables/c2_window.tex"
SCENARIO_KEY = "leaderboard_c2_forward_window_2026q3_weekly_v0_3"

# Direct headline models for the final run (routed models are appendix-only).
FINAL_MODELS = [
    "deepseek:deepseek-v4-pro", "deepseek:deepseek-v4-flash",
    "glm:glm-5", "glm:glm-5-turbo", "glm:glm-5.2",
]
DRY_RUN_MODELS = ["baseline:always-hold", "baseline:random"]
MODEL_DISPLAY = {
    "deepseek:deepseek-v4-pro": "deepseek-v4-pro",
    "deepseek:deepseek-v4-flash": "deepseek-v4-flash",
    "glm:glm-5": "glm-5",
    "glm:glm-5-turbo": "glm-5-turbo",
    "glm:glm-5.2": "glm-5.2",
    "baseline:always-hold": "always-hold (dry-run)",
    "baseline:random": "seeded random (dry-run)",
}


def _verify_commitment() -> dict:
    """Recompute the declaration hash and confirm the git date precedes the window."""
    result = subprocess.run(
        [sys.executable, "scripts/freeze_forward_window.py", "--verify", str(COMMITMENT)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"C2 commitment hash verification FAILED:\n{result.stderr.strip()}")
    commitment = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    # git-history date of the commitment file must precede window_start.
    git_date = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", str(COMMITMENT.relative_to(ROOT))],
        cwd=str(ROOT), capture_output=True, text=True,
    ).stdout.strip()
    if git_date:
        committed = datetime.fromisoformat(git_date).date()
        window_start = date.fromisoformat(commitment["window_start"])
        if committed >= window_start:
            raise SystemExit(
                f"C2 integrity FAILED: commitment git date {committed} is not before "
                f"window_start {window_start}; this is not forward-frozen evidence."
            )
        commitment["_git_committed_date"] = str(committed)
    else:
        commitment["_git_committed_date"] = "unknown (not yet committed)"
    print(f"C2 commitment verified: hash OK, committed {commitment['_git_committed_date']} "
          f"< window_start {commitment['window_start']}")
    return commitment


def _fetch_symbol(symbol: str, start: date, end: date) -> int:
    """Fetch daily back-adjusted OHLCV into the C2 data dir; returns row count.

    The committed/internal symbol name (e.g. ``GSPC``) is kept as the CSV file
    name, but the Yahoo ticker for an index carries a caret (``^GSPC``).
    """
    ticker = {"GSPC": "^GSPC"}.get(symbol, symbol)
    p1 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(end.year, end.month, end.day, 23, 59, tzinfo=timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}"
           f"?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]
    ts = data["timestamp"]
    q = data["indicators"]["quote"][0]
    adj = data["indicators"]["adjclose"][0]["adjclose"]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{symbol}_Daily_2021_2026.csv"
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        fh.write("Date,Open,High,Low,Close,Volume\n")
        for i in range(len(ts)):
            o, h, low, c, a = q["open"][i], q["high"][i], q["low"][i], q["close"][i], adj[i]
            if None in (o, h, low, c, a) or c in (0, None):
                continue
            f = a / c
            d = datetime.fromtimestamp(ts[i], timezone.utc).date().isoformat()
            fh.write(f"{d},{o*f:.6f},{h*f:.6f},{low*f:.6f},{a:.6f},{q['volume'][i] or 0}\n")
            n += 1
    return n


def _fetch_window(commitment: dict) -> dict:
    start = date.fromisoformat(commitment["window_start"])
    end = date.fromisoformat(commitment["window_end"])
    today = datetime.now(timezone.utc).date()
    effective_end = min(end, today)
    counts = {sym: _fetch_symbol(sym, start, effective_end) for sym in commitment["symbols"]}
    hasher = hashlib.sha256()
    for sym in sorted(commitment["symbols"]):
        hasher.update((DATA_DIR / f"{sym}_Daily_2021_2026.csv").read_bytes())
    provenance = {
        "source": "Yahoo Finance v8 chart API (daily, back-adjusted close)",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "window_start": str(start),
        "window_end": str(end),
        "effective_end": str(effective_end),
        "complete": effective_end >= end,
        "symbol_row_counts": counts,
        "data_sha256": "sha256:" + hasher.hexdigest(),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched window {start}..{effective_end} "
          f"({'COMPLETE' if provenance['complete'] else 'PARTIAL'}): {counts}")
    return provenance


def _run_leaderboard(models: list[str], weeks: int) -> None:
    LEADERBOARD_OUT.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "scripts/run_real_market_leaderboard.py",
        "--models", ",".join(models),
        "--scenarios", "c2_window",
        "--data-dir", str(DATA_DIR.relative_to(ROOT)),
        "--symbols", "GSPC,BTC-USD,BTC=F",
        "--frequency", "weekly",
        "--max-periods", str(max(2, weeks)),
        "--seeds", "0",
        "--output-dir", str(LEADERBOARD_OUT.relative_to(ROOT)),
        "--submission-dir", "examples/benchmark_submissions/c2_window",
        "--cache-dir", "outputs/llm_cache/c2_window",
    ]
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit("C2 leaderboard run failed; see output above.")


def _tabulate(commitment: dict, provenance: dict, mode: str) -> None:
    matrix = LEADERBOARD_OUT / "real_market_model_matrix.csv"
    rows = [r for r in csv.DictReader(matrix.open(encoding="utf-8"))
            if r.get("scenario_key", "") == "c2_window"]
    per_model: dict[str, dict[str, float]] = {}
    for r in rows:
        key = f"{r['provider']}:{r['model']}"
        per_model[key] = {
            "sharpe": float(r["sharpe"]), "total_return": float(r["total_return"]),
            "max_drawdown": float(r["max_drawdown"]),
        }
    order = [m for m in (FINAL_MODELS if mode == "final" else DRY_RUN_MODELS) if m in per_model]
    order.sort(key=lambda m: -per_model[m]["sharpe"])

    lines = ["\\begin{tabular}{lcccc}", "\\toprule",
             "Model & Sharpe & total return & max drawdown & rank \\\\", "\\midrule"]
    for rank, m in enumerate(order, start=1):
        d = per_model[m]
        lines.append(f"{MODEL_DISPLAY.get(m, m)} & {d['sharpe']:.2f} & "
                     f"{d['total_return']:.4f} & {d['max_drawdown']:.4f} & {rank} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "trellm_v0_3_c2_window_v0.1",
        "mode": mode,
        "commitment": {k: commitment[k] for k in commitment if not k.startswith("_")},
        "commitment_git_date": commitment.get("_git_committed_date"),
        "hash_verified": True,
        "data_provenance": provenance,
        "window_complete": provenance["complete"],
        "models_evaluated": order,
        "claim_boundary": (
            "The commitment pins the window, symbols, cadence, execution, risk, and metric, "
            "not a model set; models are evaluated on future data they could not have memorized. "
            "Dry-run rows are deterministic baselines proving the pipeline, not C2 evidence."
        ),
    }
    (OUT_DIR / "c2_window_summary.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {TABLE.relative_to(ROOT)} ({len(order)} rows, mode={mode}) "
          f"and {(OUT_DIR / 'c2_window_summary.json').relative_to(ROOT)}")
    if mode == "dry-run":
        print("NOTE: dry-run baselines only; re-run with --mode final after window close.")
    elif not provenance["complete"]:
        print("WARNING: --mode final but window data is PARTIAL; re-run after 2026-09-15 for the real table.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate and tabulate the C2 forward-frozen window.")
    parser.add_argument("--mode", choices=["dry-run", "final"], default="dry-run")
    parser.add_argument("--fetch", action="store_true", help="Fetch window OHLCV from Yahoo before running.")
    args = parser.parse_args(argv)

    commitment = _verify_commitment()
    if args.fetch:
        provenance = _fetch_window(commitment)
    else:
        prov_path = DATA_DIR / "provenance.json"
        if not prov_path.exists():
            raise SystemExit("No window data present; run with --fetch first.")
        provenance = json.loads(prov_path.read_text(encoding="utf-8"))

    start = date.fromisoformat(provenance["window_start"])
    eff_end = date.fromisoformat(provenance["effective_end"])
    weeks = max(2, (eff_end - start).days // 7)
    models = FINAL_MODELS if args.mode == "final" else DRY_RUN_MODELS
    _run_leaderboard(models, weeks)
    _tabulate(commitment, provenance, args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
