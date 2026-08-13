# Retail Planning Sandbox

TreLLM includes an offline-friendly planning layer for educational, research, and
paper-trading workflows. It helps contributors build investor-facing tools
without bypassing suitability checks or turning the framework into an
unreviewed live-trading bot.

Run:

```bash
python examples/retail_planner_demo.py
```

Open:

```text
outputs/examples/retail_planning_report.html
```

The demo writes:

- `outputs/examples/retail_planning_report.html`
- `outputs/examples/retail_planning_summary.json`
- `outputs/examples/retail_planning_audit.json`
- `outputs/examples/retail_planning_allocation.svg`

## What It Demonstrates

The workflow models two profiles:

- an ordinary stock/ETF investor with futures disabled
- an experienced investor with a small index-futures overlay and margin enabled

The same planning stack handles both:

```text
InvestorProfile + FinancialGoal
  -> RetailPlanningAgent
  -> StrategicAllocationEngine
  -> SuitabilityGate
  -> PaperRebalanceBroker
  -> FuturesMarginModel
  -> PlanningReport
```

The ordinary profile receives stock/ETF paper-rebalance instructions and no
futures margin estimate. The experienced profile allows index futures, but the
suitability gate still blocks an unapproved commodity futures candidate and
requires human approval for all paper orders.

## Safety Boundary

This module is intentionally conservative:

- no live brokerage calls
- no automatic execution
- all orders are `paper_pending_human_approval`
- futures exposure requires both `allow_futures=True` and `allow_margin=True`
- futures margin is an estimate, not an exchange or broker guarantee
- reports include educational-use disclaimers

## Extension Points

Useful contribution targets:

- replace `StrategicAllocationEngine` with a tax-aware allocator
- add a local CSV or brokerage-account importer for current holdings
- add futures contract calendars, expiry, and roll rules
- add retirement-account constraints and contribution limits
- add a human-approval broker adapter that exports orders for review

The planning layer is separate from the trading-agent runner, but it uses the
same design philosophy: narrow interfaces, structured risk reports, and
reproducible artifacts.
