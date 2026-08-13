# Execution Model And Calibration

TreLLM's execution layer is a configurable paper-execution stress model. It
is designed to make execution assumptions explicit and replayable. It should not
be read as broker-grade transaction-cost analysis unless the parameters are
calibrated with venue quotes, broker fee schedules, order timestamps, and
realized fills.

## Mode Boundary

The repository separates stress simulation from calibrated or replayed execution
so benchmark readers can tell which claims are supported by the data.

| Mode | Class | Required market/execution data | Suitable use |
| --- | --- | --- | --- |
| Stress simulator | `RealisticOrderSimulator` | OHLCV bars plus explicit fee, spread, latency, participation, and impact assumptions | Compare agents under shared paper-execution stress |
| Calibrated simulator | `CalibratedOrderSimulator` | Externally fitted quote/fill calibration profile and documented parameter provenance | Reuse a broker- or venue-specific fit without hiding its source |
| Quote / Level-2 replay | `QuoteReplayOrderSimulator` | `MarketSnapshot.alt_data["quotes"]` for bid/ask and optionally `alt_data["level2"]` or `alt_data["order_book"]` for depth | Replay decisions under observed quoted spread and depth constraints |
| Real fill replay | `FillReplayOrderSimulator` | Private or licensed fill CSV, aligned by timestamp, symbol, and side | Audit whether submitted orders match realized fills in a historical execution log |

The default public benchmark uses the stress simulator. It is useful for
agent-reliability evaluation and execution sensitivity analysis, but it is not a
transaction-cost prediction engine. A credible transaction-cost result should
use calibrated or replayed inputs and report venue, broker, order type, symbol
universe, sample size, and date range.

For a shorter contributor workflow, see
[`execution_calibration_quickstart.md`](execution_calibration_quickstart.md).

## Simulator Equation

`RealisticOrderSimulator` delays orders by `latency_steps`, caps per-symbol
fills by `bar.volume * participation_rate`, enforces cash and inventory
constraints, and prices market orders with:

```text
slip_rate =
  spread_bps / 20000
  + base_slippage_bps / 10000
  + market_impact * (filled_quantity / volume)
  + 0.1 * ((high - low) / close)
```

For buys, `fill_price = close * (1 + slip_rate)`. For sells,
`fill_price = close * (1 - slip_rate)`. Commissions are charged as basis points
of traded notional.

This is a transparent stress equation, not a full limit-order-book simulator.
Its components are deliberately simple:

| Component | Formula | Rationale |
| --- | --- | --- |
| Spread crossing | `spread_bps / 2` | Marketable orders pay half the quoted bid-ask spread relative to mid/reference price. |
| Base slippage | `base_slippage_bps` | Residual shortfall not explained by spread, participation, or bar range. |
| Participation impact | `market_impact * (filled_quantity / volume) * 10000` | Linear market-impact proxy in the spirit of Kyle/Almgren-Chriss style impact terms. |
| Bar-range volatility | `0.1 * ((high - low) / close) * 10000` | OHLCV-observable volatility stress term when no quote path is available. |

The model intentionally uses a linear impact term for readability and
reproducibility. Market-impact literature often finds nonlinear or concave
relationships in real order-flow data, so any broker-grade study should fit the
impact term from fills rather than reuse the default coefficient.

## Parameter Provenance

| Parameter | Role in simulator | Default | What is needed for calibration | Current default status |
| --- | --- | ---: | --- | --- |
| `commission_bps` | Explicit fee on traded notional | `1.0` | Broker or exchange fee schedule | User assumption |
| `spread_bps` | Full quoted bid-ask spread; market order crosses half | `0.0` | Quote/NBBO or order-book snapshots | User-supplied; high-spread demos set it explicitly |
| `base_slippage_bps` | Residual shortfall before spread, impact, and bar volatility | `2.0` | Historical order/fill shortfall after spread adjustment | Stress assumption or OHLCV proxy |
| `participation_rate` | Maximum fillable fraction of bar volume | `0.05` | Execution policy or parent-order participation target | Policy cap |
| `latency_steps` | Number of bars before an order becomes eligible | `1` | Order submission and acknowledgement/fill timestamps | Scenario assumption |
| `market_impact` | Linear coefficient on participation | `0.15` | Regression of implementation shortfall on participation using fill logs | Conservative stress assumption |
| `(high-low)/close` | Intrabar volatility component | data-derived | OHLCV bars | Observable in historical bars |

The default parameters are intentionally conservative stress-test settings for
comparing agents under identical frictions. They are not claimed to be universal
market constants.

## Crypto Fee-Tier And Spread-Shock Preset

The no-key crypto microstructure demo compares two execution presets over the
same synthetic symbols, seed, and market path:

```bash
python examples/crypto_microstructure_stress_demo.py
```

The `baseline_fee_tier` preset uses a low explicit fee tier and narrow quoted
spread assumption. The `fee_tier_spread_shock` preset raises `commission_bps`,
widens `spread_bps`, lowers participation, and increases latency/impact while
leaving the generated orders and market inputs reproducible. The summary
artifact reports fill rate, slippage cost, commissions, rejected orders, partial
fills, and the last pending-order count for each preset.

This preset is an execution-stress diagnostic. It should not be described as a
venue-calibrated crypto transaction-cost model unless the fee tier comes from a
broker/exchange schedule and the spread, depth, latency, and residual slippage
terms are fitted from quote/order-book and fill records.

## Optional Almgren-Chriss Impact Stress

`AlmgrenChrissImpactStress` is an opt-in, paper-only helper for fixture-level
impact analysis. It does not replace the default simulator. Instead, it reports
modeled shortfall for a proposed order from explicit fixture fields:
`symbol`, `side`, `quantity`, `price`, and `volume`.

```bash
python examples/almgren_chriss_stress_demo.py
```

The demo compares the default stress baseline with a linear impact proxy and a
concave temporary-impact proxy. Linear impact is easier to audit and matches the
default simulator's participation term. Concave impact is useful as a liquidity
stress assumption because smaller visible volume can produce a larger shortfall
response. Both are stress proxies. They become calibration claims only after
`eta`, `gamma`, and the exponent are fitted from venue quote/order-book data and
realized fills.

## What OHLCV Can And Cannot Identify

The tracked Yahoo Finance daily and hourly files provide open, high, low, close,
and volume. They can support diagnostics such as median range, tail range, dollar
volume, and whether a participation cap is plausible for a proposed order size.
They do not contain:

- quoted bid and ask;
- queue depth or order-book imbalance;
- broker/exchange fee tier;
- order submission, acknowledgement, cancellation, or fill timestamps;
- realized execution shortfall for a real order.

As a result, OHLCV-based calibration can only produce a bar-level diagnostic. A
proper transaction-cost calibration should use quote and fill logs, then fit the
spread, residual slippage, latency, and impact terms against realized shortfall.

## Historical Fill Comparison

A real calibration comparison requires historical order/fill data. The public
repository does **not** ship broker fills, account statements, or exchange
execution logs, so the default public artifacts should be described as
execution-stress diagnostics rather than realized execution calibration.

If you have private or licensed fills, keep them under an ignored path such as
`data/private/` or `data/broker/`, then run:

```bash
python scripts/compare_execution_to_fills.py \
  --fills data/private/historical_fills.csv \
  --base-slippage-bps 2.0 \
  --market-impact 0.15 \
  --default-spread-bps 4.0 \
  --output docs/results/execution_fill_comparison.json \
  --markdown-output docs/results/execution_fill_comparison.md
```

Required CSV columns:

| Column | Meaning |
| --- | --- |
| `symbol` | Instrument identifier |
| `side` | `buy` or `sell` |
| `quantity` | Filled quantity |
| `reference_price` | Arrival mid, decision close, or other documented benchmark price |
| `fill_price` | Realized fill price |

Optional columns improve the comparison:

| Column | Meaning |
| --- | --- |
| `commission` | Realized commission or explicit fee |
| `spread_bps` | Full quoted spread at arrival or fill time |
| `bar_volume` | Volume over the bar used by the simulator |
| `bar_high`, `bar_low`, `bar_close` | Bar range used for the volatility component |
| `submitted_at`, `filled_at` | Timestamps for latency analysis |

The comparison computes:

```text
observed_shortfall_bps =
  +10000 * (fill_price - reference_price) / reference_price   for buys
  +10000 * (reference_price - fill_price) / reference_price   for sells

modeled_shortfall_bps =
  spread_bps / 2
  + base_slippage_bps
  + market_impact * (quantity / bar_volume) * 10000
  + 0.1 * ((bar_high - bar_low) / bar_close) * 10000
  + commission_bps

residual_bps = observed_shortfall_bps - modeled_shortfall_bps
```

Large positive residuals mean the simulator underestimates execution cost for
the supplied fills. Large negative residuals mean the stress settings are too
conservative for those fills. Report residual mean, residual MAE, sample size,
asset universe, venue, broker, order type, and date range before making any
claim that the simulator is calibrated.

## Quote/Fill Fit

The strongest public calibration path is a quote/fill fit. It uses top-of-book
bid/ask observations and realized fills to estimate median spread, latency,
base slippage, participation, and a linear market-impact coefficient.

Run the reproducible fixture:

```bash
python scripts/calibrate_quote_fill_model.py
```

This writes:

- `docs/results/execution_quote_fill_calibration_sample.json`
- `docs/results/execution_quote_fill_calibration_sample.md`

The checked-in fixture under `data/public/microstructure_sample/` is only a
pipeline test. Replace it with public exchange quote/order-book data, licensed
data, or broker fills before making a calibrated transaction-cost claim.

Run the public Binance futures sample:

```bash
python scripts/download_binance_microstructure_sample.py
python scripts/calibrate_quote_fill_model.py \
  --quotes data/public/binance_btcusdt_perp_2024_03_01_sample/quotes.csv \
  --fills data/public/binance_btcusdt_perp_2024_03_01_sample/fills.csv \
  --output docs/results/execution_quote_fill_calibration_binance_sample.json \
  --markdown-output docs/results/execution_quote_fill_calibration_binance_sample.md \
  --commission-bps-default 0
```

This sample uses public Binance USD-M futures `bookTicker`, `trades`, and
`klines` files. Public trades are treated as realized market fills for replay
calibration, not as broker-specific fills or private queue-position evidence.

## Quote And Fill Replay Inputs

`QuoteReplayOrderSimulator` reads quote data from `MarketSnapshot.alt_data`.
Accepted shapes are intentionally simple:

```python
snapshot.alt_data["quotes"] = {
    "AAPL": {"bid": 189.98, "ask": 190.02}
}
snapshot.alt_data["level2"] = {
    "AAPL": {"bids": [[189.98, 500]], "asks": [[190.02, 400]]}
}
```

When quotes are present, marketable buys cross the observed ask and sells cross
the observed bid before residual slippage and impact terms. When Level-2 depth
is present, fillable quantity is capped by both bar participation and observed
book depth.

`FillReplayOrderSimulator` is stricter: it only fills an order if the replay log
contains a matching `timestamp`, `symbol`, and `side`. Missing replay rows are
counted as rejected orders because a replay pipeline should not fabricate fills.
The CSV loader accepts `timestamp` or `filled_at`, `symbol`, `side`, `quantity`,
`fill_price`, and optional `commission`, `reference_price`, `requested_quantity`,
`latency_steps`, and `fill_ratio`.

## Reference Anchors

The current implementation is closer to a compact transaction-cost stress proxy
than to Nautilus Trader, Backtrader, or QuantConnect LEAN. The following
references explain why spread, participation, impact, volume, and realized fills
are the right calibration surfaces:

- Kyle, A. S. (1985). "Continuous Auctions and Insider Trading." Econometrica
  53(6), 1315-1335. DOI: [`10.2307/1913210`](https://doi.org/10.2307/1913210).
- Almgren, R. and Chriss, N. (2001). "Optimal Execution of Portfolio
  Transactions." Journal of Risk 3, 5-39. DOI:
  [`10.21314/JOR.2001.041`](https://doi.org/10.21314/JOR.2001.041).
- Almgren, R., Thum, C., Hauptmann, E., and Li, H. (2005). "Direct Estimation
  of Equity Market Impact." This is the model class most relevant to replacing
  TreLLM's default `market_impact` coefficient with a fill-log estimate;
  see the Risk article summary:
  [`Equity market impact`](https://www.risk.net/derivatives/structured-products/1500270/equity-market-impact).
- Bouchaud, J.-P., Farmer, J. D., and Lillo, F. (2009). "How Markets Slowly
  Digest Changes in Supply and Demand." Handbook of Financial Markets:
  Dynamics and Evolution, 57-160. Preprint:
  [`arXiv:0809.0822`](https://arxiv.org/abs/0809.0822).

## Reproducible Diagnostic

Run:

```bash
python scripts/calibrate_execution_model.py \
  --data-dir data/real/yahoo_intraday_1h_50 \
  --output docs/results/execution_calibration_intraday_1h.json \
  --markdown-output docs/results/execution_calibration_intraday_1h.md
```

The generated report records the data coverage, OHLCV-derived range and volume
statistics, the explicit assumptions, and the model-implied slippage components.
If `--spread-bps` is omitted, the report marks spread as unobserved rather than
pretending it was estimated from OHLCV data.

## Interpretation Boundary

Use the default execution model to compare agents under the same transparent
frictions, to stress-test risk gates, and to measure how decisions change after
partial fills or rejections. Use calibrated quote/fill parameters before making
claims about live venue execution quality, expected alpha after costs, or
broker-specific implementation shortfall. Use quote or fill replay before
claiming that TreLLM explains realized transaction costs for a specific
market, broker, or order-routing setup.
