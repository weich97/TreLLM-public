# E3: Human-Gating Feasibility Frontier (Live-Readiness Control Plane)

Deterministic analytic sweep over decision cadence x book size x human approval latency (live-readiness E3). Zero LLM calls, zero network, no randomness. A combination is feasible when a single sequential operator can gate every session without approvals expiring, without a growing review queue, and within the weekly attention budget.

- Generated: 2026-07-04T09:46:41+00:00
- Command: `python scripts/run_live_readiness_e3.py`

## Assumptions (all explicit; nothing else is baked into the model)

| Assumption | Value | Status |
| --- | --- | --- |
| Approval latency grid (propose -> approval issued) | 1 min, 5 min, 15 min, 60 min | **assumed**, to be replaced by the E4 empirical distribution |
| Operator attention per session | 2 min base + 0.2 min per order row | **assumed** |
| Effective response latency | max(approval latency, attention) -- an approval cannot be issued faster than the review itself takes | modeling rule |
| Approval expiry (SLA) | 1440 min (24 h) | orchestrator default (`approve --valid-for-minutes 1440`) |
| Weekly human ops budget | 60 min of attention per week | **assumed** (experiment plan: ~1 h/week single operator) |
| Per-session compute cost | full-chain P95 from the measured E2 scaling arm (`docs/results/live_readiness_e2/e2_latency.csv`), piecewise-linear in order count | **measured** |
| Service discipline | one operator, sequential, deterministic arrivals | modeling rule |
| Session shape | one gated session per decision epoch covering the whole symbol book (one handoff, one approval), as deployed | modeling rule |

Measured E2 full-chain compute points (order count -> P95 ms): 1 -> 139.3, 2 -> 138.2, 5 -> 145.2, 10 -> 148.8, 25 -> 158.0, 50 -> 155.2

## Feasibility criteria

1. `expiry_ok`: session wall clock (compute + effective latency) <= approval expiry.
2. `backlog_ok`: session wall clock <= decision interval (queue depth <= 1; otherwise the
   queue grows every epoch and approvals eventually expire -- the CSV reports the session
   index at which the first approval would expire).
3. `budget_ok`: sessions/week x attention/session <= weekly attention budget.

## Frontier: max feasible book size (symbols out of 50) per cadence x approval latency

| Cadence (sessions/wk) | 1 min | 5 min | 15 min | 60 min |
| --- | ---: | ---: | ---: | ---: |
| weekly (1) | 50 (all) | 50 (all) | 50 (all) | 50 (all) |
| daily (7) | 32 | 32 | 32 | 32 |
| hourly (168) | 0 (infeasible) | 0 (infeasible) | 0 (infeasible) | 0 (infeasible) |
| per-minute (10080) | 0 (infeasible) | 0 (infeasible) | 0 (infeasible) | 0 (infeasible) |

## Reading the frontier

- **weekly**: feasible for the full 1-50 book at every tested approval latency (worst-case weekly attention 12 min).
- **daily**: <= 1 min latency: up to 32 symbols (next constraint: budget); <= 5 min latency: up to 32 symbols (next constraint: budget); <= 15 min latency: up to 32 symbols (next constraint: budget); <= 60 min latency: up to 32 symbols (next constraint: budget).
- **hourly**: infeasible at every tested latency and book size (binding: budget; even a 1-symbol book needs 369.6 min/week of attention vs the 60-min budget). At the deployed 3-symbol book, 86% of sessions would need rule-based auto-approval to fit the budget.
- **per-minute**: infeasible at every tested latency and book size (binding: budget, backlog; even a 1-symbol book needs 22176 min/week of attention vs the 60-min budget, and the 1-min interval is shorter than one review). At the deployed 3-symbol book, 100% of sessions would need rule-based auto-approval to fit the budget.

Grid: 4 cadences x 50 book sizes x 4 latencies = 800 combinations, of which 328 are feasible.

Compute cost never binds anywhere on this grid: the measured full-chain P95 stays below 0.16 s even at 50 orders, i.e. under 0.26% of even the shortest assumed approval latency. The frontier is set entirely by the human: response latency against the decision interval, and attention against the weekly budget.

