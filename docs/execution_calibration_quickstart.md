# Execution Calibration Quickstart

This track is for contributors who want to strengthen TreLLM execution
evidence. The goal is not to prove that the default simulator predicts a venue
or broker. The goal is to attach quote, order-book, or fill evidence to a
paper-execution result so readers can see which claims are stress tests and
which claims are calibrated.

## Pick A Path

| Path | Time | Data needed | Output claim |
| --- | ---: | --- | --- |
| Fixture sanity check | 10-15 min | checked-in toy quotes and fills | pipeline works; no market claim |
| Public exchange mini-report | 30-60 min | public quotes and trades for one venue, symbol, and window | `quote-calibrated` sample for that window |
| Private or licensed fill audit | 2-3 hours | broker or licensed fills plus reference prices | `fill-replay-validated` audit for that source |
| Replay-loop study | 2-4 hours | shared order tape plus quotes and fills | stress, quote replay, and fill replay comparison |

Use the weakest honest label. If a report does not include quote/order-book/fill
provenance, label it `stress-only`.

## Fast Local Check

Run the hand-checkable fixture first:

```bash
python scripts/calibrate_quote_fill_model.py
```

This writes:

- `docs/results/execution_quote_fill_calibration_sample.json`
- `docs/results/execution_quote_fill_calibration_sample.md`

This verifies the calibration code path and report schema. It is not evidence
about a real venue.

## Public Exchange Mini-Report

For a reproducible public-data example, download the small BTCUSDT perpetual
sample and fit the quote/fill report:

```bash
python scripts/download_binance_microstructure_sample.py
python scripts/calibrate_quote_fill_model.py \
  --quotes data/public/binance_btcusdt_perp_2024_03_01_sample/quotes.csv \
  --fills data/public/binance_btcusdt_perp_2024_03_01_sample/fills.csv \
  --output docs/results/execution_quote_fill_calibration_binance_sample.json \
  --markdown-output docs/results/execution_quote_fill_calibration_binance_sample.md \
  --commission-bps-default 0
```

The resulting row can support a narrow statement: the TreLLM calibration
pipeline was run on this public BTCUSDT sample with observed top-of-book quotes
and public trades. It should not be described as a Binance-wide, broker-grade,
or all-market transaction-cost model.

## Private Or Licensed Fill Audit

If you have realized fills, keep raw files outside the public artifact path,
for example under `data/private/` or `data/broker/`, and submit only redacted
summary artifacts:

```bash
python scripts/compare_execution_to_fills.py \
  --fills data/private/historical_fills.csv \
  --base-slippage-bps 2.0 \
  --market-impact 0.15 \
  --default-spread-bps 4.0 \
  --output docs/results/execution_fill_comparison.json \
  --markdown-output docs/results/execution_fill_comparison.md
```

Do not publish account identifiers, broker credentials, holdings, counterparty
fields, or raw fills that you are not allowed to redistribute.

## Evidence Checklist

A useful calibration mini-report includes:

- commit or release tag;
- exact command;
- quote source and fill source;
- venue, symbol universe, and date range;
- order type and reference-price definition;
- fee or commission treatment;
- aligned quote/fill sample size;
- median and tail spread;
- fitted base slippage and market-impact coefficient;
- latency or timestamp-alignment summary when timestamps exist;
- residual mean, residual MAE, P90 absolute residual, and max absolute
  residual;
- output paths and hashes;
- a short limitation note that names what the data cannot prove.

## Submit The Result

Open an external validation issue and choose **Quote/fill calibration
mini-report** or **Execution fill calibration**:

<https://github.com/weich97/TreLLM-public/issues/new?template=external_validation.yml>

Attach the generated Markdown report, the generated JSON summary when it can be
shared, and a short note mapping the row to one of these labels:

| Label | Use when |
| --- | --- |
| `stress-only` | Parameters are assumptions or OHLCV diagnostics only. |
| `quote-calibrated` | The report uses observed bid/ask or order-book data plus realized public trades or fills. |
| `fill-replay-validated` | The report replays against broker, exchange, or licensed realized fills. |

Good reports are narrow, reproducible, and explicit about limits. A single
well-documented one-symbol window is more useful than a broad claim without
timestamps, residuals, or provenance.
