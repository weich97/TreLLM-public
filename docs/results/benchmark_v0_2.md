# TradeArena v0.2 Benchmark Card

TreLLM is a financial-agent reliability audit and control system. TradeArena is the
public leaderboard module and benchmark-card layer inside that system, not the whole
project identity and not a profitability claim. This page gives a compact, citable
snapshot of what the v0.2 artifacts show under execution realism, risk gates, and
replayable intent-to-execution trajectories.

## One-Sentence Finding

Execution realism and risk gates materially change autonomous financial-agent
evaluation: intended allocations can look very different after spread, slippage,
latency, liquidity limits, partial fills, rejected orders, and pre-trade risk edits.

## Result Provenance

> **Execution mode: `realistic-stress`, not calibrated transaction-cost prediction.** The default simulator uses shared stress assumptions for spread, slippage, latency, liquidity caps, partial fills, and rejections. Rows on this card should not be read as calibrated execution-cost estimates unless they attach quote/order-book/fill provenance.

- Software release: v0.2.0.
- Benchmark snapshot lineage: v0.2.
- Benchmark card source: tracked snapshots under `docs/results/`.
- Reproduction command:

  ```bash
  python -m pip install -e ".[dev]"
  python scripts/run_showcase.py
  python scripts/build_benchmark_page.py
  ```

- Data: tracked synthetic, timestamp-masked, and redacted artifacts.
- Live model calls: not required for first-run reproduction.
- Raw prompt/response caches: not included.
- Intended use: agent reliability and audit research, not trading advice.

## Claim Badges And Validation Status

| Surface | Badge / status | Evidence boundary |
| --- | --- | --- |
| Execution mode | `stress-only` by default | Default rows are stress-simulator evidence, not calibrated transaction-cost prediction. |
| Calibration evidence | `quote-calibrated` sample rows | Fixture and public Binance samples show calibration plumbing; broader venue claims need external reports. |
| Provider rows | `cached-provider` / `redacted-prompt` | Useful reliability probes; not enough for strong model-skill claims without independent repetition. |
| Baselines | `deterministic-baseline` | Classical baselines are main anchors, not appendix rows. |
| Reproduction | `fresh-environment` CI passing | CI installs `tradearena-benchmark==0.2.0`, generates artifacts, hashes a run, and replays a step. |
| External validation | open: macOS, Ubuntu, Colab/Binder, baseline, calibration, claim review | Independent reports are requested in issues #43, #44, #45, #46, #47, and #48. |

## What Is Measured

- Return and max drawdown.
- Fill rate, rejection rate, spread, latency, slippage, and partial fills.
- Risk edits, clipped decisions, violations, and audit completeness.
- Concentration / Herfindahl for portfolio probes.
- Calibration and representation robustness diagnostics.

## How To Reproduce

```bash
python -m pip install -e ".[dev]"
python scripts/run_showcase.py
python scripts/build_benchmark_page.py
```

The page uses tracked CSV snapshots under `docs/results/` plus deterministic first-run
artifacts under `outputs/examples/`. Live model calls are not required for first-run
reproduction.

## First-Run Execution Benchmark

| Scenario | Agent / baseline | Return | Max drawdown | Fill rate | Rejection rate | Risk edits | Audit completeness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| deterministic quickstart | buy_and_hold_realistic | 53.74% | -6.63% | 89.83% | 8.90% | 0 | 100.00% |
| deterministic quickstart | risk_aware_realistic | 35.08% | -1.26% | 90.34% | 7.95% | 124 | 100.00% |

## Execution Calibration Evidence

These rows are not the default leaderboard mode. They show what must be attached before
a result can move from stress-only execution assumptions toward calibrated transaction-
cost evidence.

| Evidence | Aligned fills | Median spread | P90 spread | Median shortfall | P90 shortfall | Stress MAE | Calibrated MAE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixture | 8 | 0.953 bps | 1.364 bps | 1.467 bps | 1.646 bps | 3.533 bps | 0.447 bps |
| public Binance BTCUSDT perpetual sample | 500 | 0.016 bps | 0.016 bps | 0.008 bps | 1.659 bps | 3.163 bps | 0.908 bps |

## Non-LLM Classical Baseline Check

The synthetic and real-market matrices include deterministic non-LLM baselines so the
benchmark can ask whether an LLM policy beats fixed non-LLM strategies, not only other
LLMs.

| Universe | Scenario | Best classical | Classical return | Best LLM | LLM return | Return gap | LLM wins? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| real_market | Yahoo 2022 rates drawdown | Risk parity | 4.77% | poe:gemini-3.1-pro | 2.56% | -2.21% | no |
| real_market | Yahoo recent GSPC/BTC/BTC futures | Buy and hold | 12.15% | poe:gemini-3.1-pro | 4.86% | -7.29% | no |
| synthetic | Calm trend | Buy and hold | 2.61% | poe:kimi-k2.5 | 3.19% | 0.59% | yes |
| synthetic | High volatility | Mean reversion | 1.88% | poe:gemini-3.1-pro | 1.44% | -0.44% | no |
| synthetic | Jump and tail risk | Buy and hold | 2.81% | poe:gpt-5.5 | 1.67% | -1.14% | no |
| synthetic | Latency spike | Buy and hold | 3.29% | poe:gemini-3.1-pro | 3.29% | 0.00% | no |
| synthetic | Liquidity collapse | Minimum variance | 9.07% | poe:gpt-5.5 | 4.42% | -4.65% | no |
| synthetic | Spread explosion | Buy and hold | 1.07% | deepseek:deepseek-v4-pro | 0.48% | -0.59% | no |

## Classical Baseline Aggregate

| Universe | Baseline | Scenarios | Avg return | Worst DD | Avg Sharpe | Avg fill | Rejected | Risk edits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| real_market | Risk parity | 2 | 7.61% | -4.67% | 4.636 | 86.11% | 4 | 0 |
| real_market | Minimum variance | 2 | 6.12% | -5.99% | 3.667 | 84.17% | 5 | 0 |
| real_market | Markowitz MVO | 2 | 5.07% | -5.15% | 3.272 | 79.00% | 7 | 0 |
| real_market | Buy and hold | 2 | 2.53% | -16.87% | 2.269 | 78.89% | 9 | 0 |
| real_market | Equal weight | 2 | 2.41% | -16.89% | 2.224 | 83.33% | 6 | 0 |
| real_market | Always hold | 2 | 0.00% | 0.00% | 0.000 | 0.00% | 0 | 0 |
| real_market | Random | 2 | -0.02% | -11.16% | 0.725 | 71.43% | 14 | 0 |
| real_market | Mean reversion | 2 | -2.52% | -9.84% | -0.546 | 75.00% | 6 | 0 |
| real_market | Naive momentum | 2 | -6.38% | -15.38% | -1.698 | 67.18% | 12 | 0 |
| synthetic | Buy and hold | 6 | 3.00% | -2.03% | 6.631 | 69.58% | 11 | 96 |
| synthetic | Minimum variance | 6 | 2.72% | -3.82% | 4.885 | 71.88% | 9 | 0 |
| synthetic | Risk parity | 6 | 1.85% | -3.42% | 3.759 | 71.88% | 9 | 0 |
| synthetic | Equal weight | 6 | 1.76% | -3.26% | 3.815 | 70.62% | 10 | 0 |
| synthetic | Markowitz MVO | 6 | 1.69% | -3.60% | 2.854 | 65.35% | 15 | 0 |
| synthetic | Naive momentum | 6 | 0.75% | -3.81% | 3.510 | 67.41% | 5 | 0 |
| synthetic | Random | 6 | 0.46% | -3.92% | 0.354 | 67.43% | 11 | 0 |
| synthetic | Mean reversion | 6 | 0.15% | -5.21% | 1.670 | 74.44% | 3 | 0 |
| synthetic | Always hold | 6 | 0.00% | 0.00% | 0.000 | 0.00% | 0 | 0 |

## Decision Quality vs Execution Quality

Return alone hides whether a row had useful pre-risk intent, good risk discipline, or
robust execution. The three-axis diagnostic separates alpha quality, risk discipline,
and execution robustness.

![Decision quality radar](quality_decomposition/decision_execution_radar.svg)

| Family | Rows | Alpha | Risk | Execution | Pre-risk alpha return | Realized return | Fill rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LLM synthetic | 102 | 0.623 | 0.653 | 0.778 | 2.89% | 0.88% | 48.37% |
| LLM real-market | 90 | 0.489 | 0.412 | 0.687 | 0.48% | -4.38% | 65.10% |
| Classical synthetic | 54 | 0.728 | 0.569 | 0.747 | 3.41% | 1.37% | 62.07% |
| Classical real-market | 18 | 0.628 | 0.394 | 0.751 | 3.84% | 1.65% | 69.46% |

## Key Result 1: Risk Gates Are Active, Not Cosmetic

Across the crisis and intraday rows, risk gates repeatedly edit or clip intended
allocations before execution. The benchmark therefore reports risk edits alongside
return, instead of treating risk control as a post-hoc metric.

## Crisis-Scene LLM Benchmark

The crisis snapshot aggregates timestamp-masked 2022 Tech/Rates and 2023 SVB-style
stress paths. Rows below average across the tracked model policies for each feedback
mode.

| Scenario | Agent / baseline | Return | Max drawdown | Fill rate | Rejection rate | Risk edits | Audit completeness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| svb_2023 | LLM policies (hidden feedback) | 1.23% | -1.86% | 75.59% | 24.41% | 212 | 100.00% |
| svb_2023 | LLM policies (placebo feedback) | 1.19% | -1.87% | 76.88% | 23.12% | 204 | 100.00% |
| svb_2023 | LLM policies (true feedback) | 1.08% | -1.87% | 78.16% | 21.84% | 196 | 100.00% |
| tech_rates_2022 | LLM policies (hidden feedback) | -3.27% | -4.89% | 65.93% | 34.07% | 914 | 100.00% |
| tech_rates_2022 | LLM policies (placebo feedback) | -2.57% | -4.40% | 63.10% | 36.90% | 906 | 100.00% |
| tech_rates_2022 | LLM policies (true feedback) | -3.09% | -4.81% | 64.33% | 35.67% | 778 | 100.00% |

## True-Feedback Model Rows

Model names are redacted or normalized labels for benchmark policies. Raw provider
prompts and responses are not shipped.

| Scenario | Policy label | Return | Max drawdown | Fill rate | Risk edits | Violations | Calibration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| svb_2023 | frontier-policy-D (redacted) | 1.03% | -1.87% | 80.16% | 177 | 13 | 0.198 |
| svb_2023 | frontier-policy-B (redacted) | 1.24% | -1.89% | 77.37% | 206 | 14 | 0.207 |
| svb_2023 | frontier-policy-C (redacted) | 0.67% | -1.88% | 78.52% | 196 | 14 | 0.397 |
| svb_2023 | frontier-policy-A (redacted) | 1.39% | -1.86% | 76.60% | 203 | 14 | 0.224 |
| tech_rates_2022 | frontier-policy-D (redacted) | -1.84% | -4.79% | 62.62% | 863 | 39 | 0.071 |
| tech_rates_2022 | frontier-policy-B (redacted) | -2.49% | -4.53% | 63.90% | 969 | 41 | 0.067 |
| tech_rates_2022 | frontier-policy-C (redacted) | -5.32% | -5.32% | 69.10% | 402 | 226 | 0.435 |
| tech_rates_2022 | frontier-policy-A (redacted) | -2.72% | -4.61% | 61.69% | 880 | 38 | 0.090 |

## Key Result 2: Execution Assumptions Change Realized Exposure

The 51-stock hourly probe shows that low-liquidity and latency stress rows do not behave
like ideal fills. Fill rate, rejected orders, and realized exposure become part of the
benchmark outcome.

## 51-Stock Intraday Portfolio Probe

The intraday snapshot compares passive, deterministic, Markowitz/MVO, execution-stress,
and redacted LLM policy rows on the same 51-stock hourly panel.

| Agent / baseline | Return | Max drawdown | Fill rate | Rejected | Risk edits | Herfindahl | Audit completeness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Buy and Hold | 0.71% | -0.79% | 87.16% | 98 | 2040 | 0.019 | 100.00% |
| Deterministic Risk-Aware | -1.35% | -3.11% | 76.26% | 91 | 672 | 0.062 | 100.00% |
| Markowitz MVO | -0.54% | -1.35% | 87.94% | 185 | 357 | 0.023 | 100.00% |
| Low-Liquidity Stress | -2.16% | -3.60% | 75.55% | 95 | 672 | 0.062 | 100.00% |
| Latency Stress | 1.96% | -1.33% | 44.40% | 209 | 672 | 0.081 | 100.00% |
| Frontier Policy A (redacted) | -2.23% | -2.93% | 71.86% | 378 | 2924 | 0.045 | 100.00% |
| Frontier Policy C (redacted) | -0.53% | -2.31% | 63.60% | 254 | 1200 | 0.035 | 100.00% |

## Key Result 3: Audit Completeness Is A Benchmark Dimension

Every result row should be traceable to a trajectory rather than only to a return curve.
TradeArena therefore reports audit completeness and keeps compact, redacted result
manifests.

## Representation Robustness Snapshot

A result is more useful when the diagnostic survives multiple representation views. The
v0.2 tracked snapshot includes 80 rolling failure anchors and 320 pre-failure steps
across eight LLM trajectories.

| Embedding | View | Anchors | Pre-failure steps | Mean rank delta | Contraction rate | Mean pre-shift |
| --- | --- | --- | --- | --- | --- | --- |
| hash64 | fused | 80 | 320 | 0.471 | 67.50% | 0.071 |
| lsa32 | fused | 80 | 320 | 5.123 | 86.25% | 0.084 |
| hash64 | plan | 80 | 320 | 8.703 | 97.50% | 0.122 |
| lsa32 | plan | 80 | 320 | 4.870 | 85.00% | 0.097 |

## Limitations

- This is a benchmark and audit artifact, not financial advice.
- It is not a live-trading system and does not promise profitability.
- First-run reproduction uses tracked artifacts, not live provider calls.
- Public rows use redacted or normalized policy labels.
- Raw provider prompts, responses, credentials, and caches are not shipped.
