# Market Rules And Stress Presets

TreLLM's default simulator is market-agnostic. Market-specific realism
should be added as explicit rule plugins or scenario presets so reviewers can
see which assumptions are active.

## Market Rule Packages

| Market | Rules to encode | Why it matters |
| --- | --- | --- |
| US equities | regular-hours calendar, corporate actions, short-sale assumptions, NBBO-derived spread calibration | avoids mixing daily OHLCV backtests with undocumented execution assumptions |
| A-share | T+1 sale constraint, board-specific price limits, trading halts, lot sizes | many strategies that pass US-style assumptions become infeasible |
| Hong Kong equities | board lots, trading sessions, lunch break, stamp duty, short-sale eligibility | portfolio weights must translate into tradable quantities |
| Crypto | 24/7 sessions, venue fee tiers, funding or borrow costs, spread shocks | liquidity and fees can change faster than daily bars show |
| Futures | contract rolls, expiry, margin, tick size, session breaks | continuous prices can hide roll and margin risk |

TreLLM now exposes these as testable rule-package helpers in
[`src/tradearena/tools/market_rules.py`](../src/tradearena/tools/market_rules.py).
They are intentionally separate from the default simulator so a benchmark row
can state exactly which venue rule layer was active.

| Helper | Encoded checks |
| --- | --- |
| `ashare_rule_package()` | T+1 sellability, 100-share board lots, limit-up buy block, limit-down sell block |
| `hong_kong_rule_package()` | board-lot rounding and stamp-duty cost estimate |
| `crypto_rule_package()` | fee tier, funding cost, and participation-limited liquidity |
| `futures_rule_package()` | initial margin requirement and roll-window flag |
| `liquidity_halt_rule_package()` | participation clipping and Almgren-Chriss-style temporary impact estimate |

Minimal usage:

```python
from tradearena.core.domain import Side
from tradearena.tools import MarketRuleState, ashare_rule_package, review_market_rule_order

decision = review_market_rule_order(
    symbol="600519.SS",
    side=Side.SELL,
    quantity=200,
    state=MarketRuleState(
        price=100.0,
        previous_close=99.0,
        settled_position=100,
        same_day_buy_quantity=100,
    ),
    package=ashare_rule_package(),
)
assert decision.blocked
```

The output is a `MarketRuleDecision` with `status`, `reasons`, approved
quantity, fee/funding estimates, margin requirement, and market-impact
estimate. This makes market infeasibility auditable instead of hiding it inside
portfolio PnL.

For Hong Kong equities, target weights must first be converted into share
quantities before board-lot rounding and stamp-duty estimates can be reviewed.
The deterministic paper-only demo states its regular-session assumptions and
does not download exchange calendars or market data:

```bash
python examples/hk_market_rules_demo.py
```

It writes `outputs/examples/hk_market_rules_summary.json`,
`outputs/examples/hk_market_rules_orders.csv`, and
`outputs/examples/hk_market_rules.svg`.

## Plugin Boundary

Market rules are exchange-level feasibility plugins. They sit after a strategy
or risk manager proposes an order and before the simulator decides whether and
how it fills. A rule plugin may block or resize a proposed order; it must not
simulate fills, mutate portfolio accounting, call LLM/data providers, place live
orders, or change runner orchestration.

The structural contract is:

| Method or field | Purpose |
| --- | --- |
| `name: str` | Stable identifier recorded in manifests, reports, or benchmark configs. |
| `validate_order(symbol, side, quantity, state)` | Return one `MarketRuleDecision` for one proposed order. |
| `explain_block(decision)` | Explain a block or clip without making return/profit claims. |

Existing helpers can be adapted into the plugin protocol:

```python
from tradearena.core.domain import Side
from tradearena.tools import MarketRuleState, ashare_rule_package, market_rule_from_package

rule = market_rule_from_package(ashare_rule_package())
decision = rule.validate_order(
    symbol="600519.SS",
    side=Side.SELL,
    quantity=200,
    state=MarketRuleState(
        price=100.0,
        previous_close=99.0,
        settled_position=100,
        same_day_buy_quantity=100,
    ),
)
explanation = rule.explain_block(decision)
```

Third-party plugins should pass `validate_market_rule_plugin(plugin)` before
they are used in a scenario preset. That check is intentionally structural so
plugins can live outside the TradeArena package.

## Risk Preset Ideas

| Preset | Checks |
| --- | --- |
| retail | max single-name weight, cash-only buys, no shorting, turnover cap |
| hedge-fund style | gross/net exposure, leverage, VaR proxy, sector concentration |
| regulatory stress | drawdown stop, participation cap, liquidity halt, price-limit block |
| crisis | widening spread, low volume, delayed fills, rejected orders |

Risk presets should emit normal `RiskReport` records so they remain comparable
with the default `MaxPositionRiskManager`.

The built-in max-drawdown preset is a compact extension example for this
contract. It reuses the standard risk-report schema while making the drawdown
intervention explicit as either a block or a clip:

```python
from tradearena.agents import max_drawdown_risk_preset

risk = max_drawdown_risk_preset(
    max_drawdown=0.05,
    de_risk_weight=0.10,
    drawdown_lookback=3,
)
approved_decisions = risk.approve(snapshot, decisions, portfolio, memory)
assert risk.last_report is not None
```

For a deterministic blocked-and-clipped fixture, run:

```bash
python examples/max_drawdown_risk_preset_demo.py
```

This writes `docs/results/max_drawdown_risk_preset.json` and
`docs/results/max_drawdown_risk_preset.md`.

## Adversarial Scenarios

Adversarial tests are useful for LLM agents because the failure is often in
their stated plan, not only in the realized return.

Examples:

- false risk report that claims a healthy portfolio violated limits;
- sudden liquidity drought with pending orders already queued;
- flash crash followed by partial rebound;
- halt or limit-up/limit-down period where target weights cannot be reached;
- correlated selloff where single-name narratives hide portfolio exposure.

The liquidity-halt stress fixture makes the pending-order case concrete:

```bash
python examples/liquidity_halt_demo.py
```

It writes a replayable trajectory plus summary artifacts under
`outputs/examples/liquidity_halt/`, including a pre-halt pending order, a thin
liquidity partial fill, a rejected delayed order, and a circuit-halt risk block.

Each scenario should publish:

- the market path or fixture generator;
- execution and risk settings;
- expected qualitative behavior;
- metrics that detect unsafe behavior;
- one command to reproduce the artifact.

## Calibration Boundary

OHLCV data can support range, volume, and participation diagnostics. It cannot
identify quoted spread, queue position, broker latency, or realized shortfall by
itself. Use
[`docs/execution_model_boundaries.md`](execution_model_boundaries.md) before
claiming a simulator preset is calibrated to real execution.
