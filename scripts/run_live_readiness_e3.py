"""E3: human-gating feasibility-frontier sweep for the live-readiness control plane.

Airlock live-readiness experiment E3 (frontier); results under docs/results/live_readiness_e3/.
Deterministic analytic sweep -- zero LLM, zero network, no randomness. It
answers: at which decision cadence x book size x human approval latency can a
single operator sustain hash-bound, expiring approvals without (a) approvals
expiring, (b) an unbounded review queue, or (c) blowing the weekly human
attention budget?

Model (one gated session per decision epoch covering the whole symbol book,
exactly like the deployed weekly orchestrator):

- attention_minutes(n)   = review_base_minutes + review_minutes_per_order * n
- effective_latency(n,L) = max(L, attention_minutes(n))   [cannot approve
                           faster than the review itself takes]
- session_wall_minutes   = chain_compute_p95_ms(n)/60000 + effective_latency
- criteria (all must hold):
    expiry_ok:  session_wall_minutes <= expiry_minutes (approval validity)
    backlog_ok: session_wall_minutes <= decision interval (queue depth <= 1;
                a slower operator falls behind and approvals eventually expire)
    budget_ok:  sessions_per_week * attention_minutes(n) <= weekly budget

The per-session compute cost comes from the measured E2 scaling arm
(docs/results/live_readiness_e2/e2_latency.csv, rows ``scaling_full_chain_n*``,
piecewise-linear interpolation over order count, clamped at the endpoints).
Approval-latency values are ASSUMED (to be replaced by the E4 empirical
distribution once the pre-registered deployment window closes); every
assumption is echoed into the CSV and the markdown report.

Usage:

  python scripts/run_live_readiness_e3.py \
    --e2-csv docs/results/live_readiness_e2/e2_latency.csv \
    --output-dir docs/results/live_readiness_e3
"""

from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_E2_CSV = ROOT / "docs" / "results" / "live_readiness_e2" / "e2_latency.csv"
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "results" / "live_readiness_e3"

# Decision cadences: (name, sessions per week, minutes between decisions).
FREQUENCIES: tuple[tuple[str, float, float], ...] = (
    ("weekly", 1.0, 10080.0),
    ("daily", 7.0, 1440.0),
    ("hourly", 168.0, 60.0),
    ("per-minute", 10080.0, 1.0),
)

CSV_FIELDS = (
    "frequency",
    "sessions_per_week",
    "decision_interval_minutes",
    "n_symbols",
    "approval_latency_minutes",
    "review_base_minutes",
    "review_minutes_per_order",
    "expiry_minutes",
    "weekly_budget_minutes",
    "chain_compute_p95_ms",
    "attention_minutes_per_session",
    "effective_latency_minutes",
    "session_wall_minutes",
    "weekly_attention_minutes",
    "expiry_ok",
    "backlog_ok",
    "budget_ok",
    "feasible",
    "binding_constraints",
    "session_of_first_expiry",
    "auto_approval_fraction_for_budget",
)


def load_chain_compute_points(e2_csv: Path) -> list[tuple[int, float]]:
    """Return sorted (order_count, full-chain P95 ms) points from the E2 CSV."""

    if not e2_csv.exists():
        raise FileNotFoundError(
            f"E2 latency CSV not found: {e2_csv}; run scripts/run_live_readiness_e2.py first "
            "or pass --chain-p95-ms to use a single explicit compute cost"
        )
    points: list[tuple[int, float]] = []
    fallback: tuple[int, float] | None = None
    with e2_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            layer = str(row.get("layer", ""))
            if layer.startswith("scaling_full_chain_n"):
                points.append((int(row["order_count"]), float(row["p95_ms"])))
            elif layer == "full_chain_session":
                fallback = (int(row["order_count"]), float(row["p95_ms"]))
    if not points and fallback is not None:
        points = [fallback]
    if not points:
        raise ValueError(f"E2 CSV has no scaling_full_chain_n* or full_chain_session rows: {e2_csv}")
    return sorted(points)


def chain_compute_p95_ms(points: list[tuple[int, float]], n_symbols: int) -> float:
    """Piecewise-linear interpolation of full-chain P95 over order count, clamped."""

    if n_symbols <= points[0][0]:
        return points[0][1]
    if n_symbols >= points[-1][0]:
        return points[-1][1]
    for (left_n, left_ms), (right_n, right_ms) in zip(points, points[1:]):
        if left_n <= n_symbols <= right_n:
            span = right_n - left_n
            weight = (n_symbols - left_n) / span
            return left_ms + weight * (right_ms - left_ms)
    return points[-1][1]


def session_of_first_expiry(
    wall_minutes: float, interval_minutes: float, expiry_minutes: float
) -> int | None:
    """First session (1-based) whose approval issues after its expiry, or None.

    Deterministic arrivals every ``interval`` minutes, one operator serving
    sequentially with per-session wall clock ``wall``. The k-th session's
    approval issues ``wall + k * (wall - interval)`` minutes after its own
    proposal (k = 0, 1, ...), so once wall > interval the delay grows without
    bound and eventually crosses the expiry window.
    """

    if wall_minutes > expiry_minutes:
        return 1
    deficit = wall_minutes - interval_minutes
    if deficit <= 0:
        return None
    first_index = math.floor((expiry_minutes - wall_minutes) / deficit) + 1
    return first_index + 1


def build_grid(
    *,
    points: list[tuple[int, float]],
    approval_latencies: list[float],
    max_symbols: int,
    review_base_minutes: float,
    review_minutes_per_order: float,
    expiry_minutes: float,
    weekly_budget_minutes: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for frequency, sessions_per_week, interval_minutes in FREQUENCIES:
        for n_symbols in range(1, max_symbols + 1):
            compute_ms = chain_compute_p95_ms(points, n_symbols)
            attention = review_base_minutes + review_minutes_per_order * n_symbols
            for latency in approval_latencies:
                effective_latency = max(latency, attention)
                wall = compute_ms / 60000.0 + effective_latency
                weekly_attention = sessions_per_week * attention
                expiry_ok = wall <= expiry_minutes
                backlog_ok = wall <= interval_minutes
                budget_ok = weekly_attention <= weekly_budget_minutes
                feasible = expiry_ok and backlog_ok and budget_ok
                binding = [
                    name
                    for name, ok in (
                        ("budget", budget_ok),
                        ("backlog", backlog_ok),
                        ("expiry", expiry_ok),
                    )
                    if not ok
                ]
                first_expiry = None if backlog_ok else session_of_first_expiry(wall, interval_minutes, expiry_minutes)
                # Fraction of sessions that would have to bypass the human
                # (rule-based auto-approval) for the remainder to fit the
                # weekly attention budget.
                auto_fraction = 0.0 if weekly_attention <= 0 else max(0.0, 1.0 - weekly_budget_minutes / weekly_attention)
                rows.append(
                    {
                        "frequency": frequency,
                        "sessions_per_week": sessions_per_week,
                        "decision_interval_minutes": interval_minutes,
                        "n_symbols": n_symbols,
                        "approval_latency_minutes": latency,
                        "review_base_minutes": review_base_minutes,
                        "review_minutes_per_order": review_minutes_per_order,
                        "expiry_minutes": expiry_minutes,
                        "weekly_budget_minutes": weekly_budget_minutes,
                        "chain_compute_p95_ms": round(compute_ms, 4),
                        "attention_minutes_per_session": round(attention, 4),
                        "effective_latency_minutes": round(effective_latency, 4),
                        "session_wall_minutes": round(wall, 6),
                        "weekly_attention_minutes": round(weekly_attention, 4),
                        "expiry_ok": expiry_ok,
                        "backlog_ok": backlog_ok,
                        "budget_ok": budget_ok,
                        "feasible": feasible,
                        "binding_constraints": ";".join(binding),
                        "session_of_first_expiry": "" if first_expiry is None else first_expiry,
                        "auto_approval_fraction_for_budget": round(auto_fraction, 4),
                    }
                )
    return rows


def max_feasible_symbols(rows: list[dict[str, object]], frequency: str, latency: float) -> int:
    feasible_counts = [
        int(row["n_symbols"])
        for row in rows
        if row["frequency"] == frequency
        and float(row["approval_latency_minutes"]) == latency
        and row["feasible"] is True
    ]
    return max(feasible_counts, default=0)


def _first_binding(rows: list[dict[str, object]], frequency: str, latency: float, n_symbols: int) -> str:
    for row in rows:
        if (
            row["frequency"] == frequency
            and float(row["approval_latency_minutes"]) == latency
            and int(row["n_symbols"]) == n_symbols
        ):
            return str(row["binding_constraints"]) or "none"
    return "n/a"


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_markdown(
    path: Path,
    *,
    rows: list[dict[str, object]],
    points: list[tuple[int, float]],
    e2_csv: Path,
    approval_latencies: list[float],
    max_symbols: int,
    review_base_minutes: float,
    review_minutes_per_order: float,
    expiry_minutes: float,
    weekly_budget_minutes: float,
) -> None:
    lines: list[str] = []
    lines.append("# E3: Human-Gating Feasibility Frontier (Live-Readiness Control Plane)")
    lines.append("")
    lines.append(
        "Deterministic analytic sweep over decision cadence x book size x human approval "
        "latency (live-readiness E3). Zero LLM calls, zero network, no randomness. A combination is "
        "feasible when a single sequential operator can gate every session without approvals "
        "expiring, without a growing review queue, and within the weekly attention budget."
    )
    lines.append("")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append("- Command: `python scripts/run_live_readiness_e3.py`")
    lines.append("")
    lines.append("## Assumptions (all explicit; nothing else is baked into the model)")
    lines.append("")
    lines.append("| Assumption | Value | Status |")
    lines.append("| --- | --- | --- |")
    lines.append(
        f"| Approval latency grid (propose -> approval issued) | {', '.join(f'{v:g} min' for v in approval_latencies)} "
        "| **assumed**, to be replaced by the E4 empirical distribution |"
    )
    lines.append(
        f"| Operator attention per session | {review_base_minutes:g} min base + "
        f"{review_minutes_per_order:g} min per order row | **assumed** |"
    )
    lines.append(
        "| Effective response latency | max(approval latency, attention) -- an approval cannot "
        "be issued faster than the review itself takes | modeling rule |"
    )
    lines.append(
        f"| Approval expiry (SLA) | {expiry_minutes:g} min (24 h) | orchestrator default "
        "(`approve --valid-for-minutes 1440`) |"
    )
    lines.append(
        f"| Weekly human ops budget | {weekly_budget_minutes:g} min of attention per week | "
        "**assumed** (experiment plan: ~1 h/week single operator) |"
    )
    try:
        e2_ref = e2_csv.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        e2_ref = e2_csv.as_posix()
    lines.append(
        "| Per-session compute cost | full-chain P95 from the measured E2 scaling arm "
        f"(`{e2_ref}`), piecewise-linear in order count | **measured** |"
    )
    lines.append("| Service discipline | one operator, sequential, deterministic arrivals | modeling rule |")
    lines.append(
        "| Session shape | one gated session per decision epoch covering the whole symbol book "
        "(one handoff, one approval), as deployed | modeling rule |"
    )
    lines.append("")
    lines.append("Measured E2 full-chain compute points (order count -> P95 ms): "
                 + ", ".join(f"{n} -> {ms:.1f}" for n, ms in points))
    lines.append("")
    lines.append("## Feasibility criteria")
    lines.append("")
    lines.append("1. `expiry_ok`: session wall clock (compute + effective latency) <= approval expiry.")
    lines.append("2. `backlog_ok`: session wall clock <= decision interval (queue depth <= 1; otherwise the")
    lines.append("   queue grows every epoch and approvals eventually expire -- the CSV reports the session")
    lines.append("   index at which the first approval would expire).")
    lines.append("3. `budget_ok`: sessions/week x attention/session <= weekly attention budget.")
    lines.append("")
    lines.append("## Frontier: max feasible book size (symbols out of "
                 f"{max_symbols}) per cadence x approval latency")
    lines.append("")
    header = "| Cadence (sessions/wk) | " + " | ".join(f"{v:g} min" for v in approval_latencies) + " |"
    lines.append(header)
    lines.append("| --- |" + " ---: |" * len(approval_latencies))
    for frequency, sessions_per_week, _interval in FREQUENCIES:
        cells = []
        for latency in approval_latencies:
            best = max_feasible_symbols(rows, frequency, latency)
            cells.append("0 (infeasible)" if best == 0 else (f"{best} (all)" if best == max_symbols else str(best)))
        lines.append(f"| {frequency} ({sessions_per_week:g}) | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## Reading the frontier")
    lines.append("")
    for frequency, sessions_per_week, interval in FREQUENCIES:
        bests = {latency: max_feasible_symbols(rows, frequency, latency) for latency in approval_latencies}
        if all(best == max_symbols for best in bests.values()):
            lines.append(
                f"- **{frequency}**: feasible for the full 1-{max_symbols} book at every tested "
                f"approval latency (worst-case weekly attention "
                f"{sessions_per_week * (review_base_minutes + review_minutes_per_order * max_symbols):g} min)."
            )
        elif all(best == 0 for best in bests.values()):
            base_weekly = sessions_per_week * (review_base_minutes + review_minutes_per_order)
            binding = _first_binding(rows, frequency, approval_latencies[0], 1).replace(";", ", ")
            deployed_book = min(3, max_symbols)
            deployed_attention = review_base_minutes + review_minutes_per_order * deployed_book
            deployed_weekly = sessions_per_week * deployed_attention
            auto_fraction = max(0.0, 1.0 - weekly_budget_minutes / deployed_weekly) if deployed_weekly > 0 else 0.0
            lines.append(
                f"- **{frequency}**: infeasible at every tested latency and book size "
                f"(binding: {binding}; even a 1-symbol book needs {base_weekly:g} min/week of attention "
                f"vs the {weekly_budget_minutes:g}-min budget"
                + (
                    f", and the {interval:g}-min interval is shorter than one review"
                    if review_base_minutes + review_minutes_per_order > interval
                    else ""
                )
                + f"). At the deployed {deployed_book}-symbol book, {100.0 * auto_fraction:.0f}% of sessions "
                "would need rule-based auto-approval to fit the budget."
            )
        else:
            parts = []
            for latency in approval_latencies:
                best = bests[latency]
                cap = f"{best}" if best else "0"
                binding = _first_binding(rows, frequency, latency, min(best + 1, max_symbols))
                parts.append(f"<= {latency:g} min latency: up to {cap} symbols (next constraint: {binding})")
            lines.append(f"- **{frequency}**: " + "; ".join(parts) + ".")
    lines.append("")
    feasible_rows = sum(1 for row in rows if row["feasible"] is True)
    lines.append(
        f"Grid: {len(FREQUENCIES)} cadences x {max_symbols} book sizes x {len(approval_latencies)} latencies "
        f"= {len(rows)} combinations, of which {feasible_rows} are feasible."
    )
    lines.append("")
    lines.append(
        "Compute cost never binds anywhere on this grid: the measured full-chain P95 stays below "
        f"{max(ms for _n, ms in points) / 1000.0:.2f} s even at {points[-1][0]} orders, i.e. under "
        f"{100.0 * (max(ms for _n, ms in points) / 60000.0) / min(approval_latencies):.2f}% of even the shortest "
        "assumed approval latency. The frontier is set entirely by the human: response latency against the "
        "decision interval, and attention against the weekly budget."
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="E3 human-gating feasibility-frontier sweep (deterministic, zero LLM, zero network)."
    )
    parser.add_argument("--e2-csv", default=str(DEFAULT_E2_CSV), help="E2 latency CSV (compute-cost input).")
    parser.add_argument(
        "--chain-p95-ms",
        type=float,
        default=None,
        help="Override: single full-chain P95 in ms used for every book size (skips reading the E2 CSV).",
    )
    parser.add_argument(
        "--approval-latencies",
        default="1,5,15,60",
        help="Comma-separated assumed approval latencies in minutes (default 1,5,15,60).",
    )
    parser.add_argument("--max-symbols", type=int, default=50, help="Book sizes 1..N to scan (default 50).")
    parser.add_argument(
        "--review-base-minutes", type=float, default=2.0, help="Assumed attention floor per session (default 2.0)."
    )
    parser.add_argument(
        "--review-minutes-per-order",
        type=float,
        default=0.2,
        help="Assumed incremental attention per order row (default 0.2 = 12 s).",
    )
    parser.add_argument(
        "--expiry-minutes", type=float, default=1440.0, help="Approval validity window in minutes (default 1440)."
    )
    parser.add_argument(
        "--weekly-budget-minutes",
        type=float,
        default=60.0,
        help="Weekly human attention budget in minutes (default 60).",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for e3_frontier.csv/.md.")
    args = parser.parse_args(argv)

    approval_latencies = sorted({float(part) for part in str(args.approval_latencies).split(",") if part.strip()})
    if not approval_latencies or any(latency <= 0 for latency in approval_latencies):
        print("approval-latencies must be positive numbers")
        return 1
    if args.max_symbols < 1 or args.review_base_minutes < 0 or args.review_minutes_per_order < 0:
        print("max-symbols must be >= 1 and review times must be non-negative")
        return 1
    if args.expiry_minutes <= 0 or args.weekly_budget_minutes <= 0:
        print("expiry-minutes and weekly-budget-minutes must be positive")
        return 1

    e2_csv = Path(args.e2_csv)
    if args.chain_p95_ms is not None:
        points = [(1, float(args.chain_p95_ms))]
    else:
        points = load_chain_compute_points(e2_csv)

    rows = build_grid(
        points=points,
        approval_latencies=approval_latencies,
        max_symbols=args.max_symbols,
        review_base_minutes=args.review_base_minutes,
        review_minutes_per_order=args.review_minutes_per_order,
        expiry_minutes=args.expiry_minutes,
        weekly_budget_minutes=args.weekly_budget_minutes,
    )

    output_dir = Path(args.output_dir)
    csv_path = output_dir / "e3_frontier.csv"
    md_path = output_dir / "e3_frontier.md"
    _write_csv(csv_path, rows)
    _write_markdown(
        md_path,
        rows=rows,
        points=points,
        e2_csv=e2_csv,
        approval_latencies=approval_latencies,
        max_symbols=args.max_symbols,
        review_base_minutes=args.review_base_minutes,
        review_minutes_per_order=args.review_minutes_per_order,
        expiry_minutes=args.expiry_minutes,
        weekly_budget_minutes=args.weekly_budget_minutes,
    )

    for frequency, _sessions, _interval in FREQUENCIES:
        summary = ", ".join(
            f"{latency:g}min->{max_feasible_symbols(rows, frequency, latency)}" for latency in approval_latencies
        )
        print(f"E3 {frequency}: max feasible symbols by latency: {summary}")
    print(f"  wrote {csv_path}")
    print(f"  wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
