# Crisis-Scene Experiments

This add-on suite turns two real historical stress periods into visual, audit-friendly probes:

- `tech_rates_2022`: 51 liquid U.S. equities during the 2022 technology/rates drawdown.
- `svb_2023`: banks, regional-bank ETFs, broad equity, and crypto proxies during the March 2023 SVB/regional-bank shock.

The goal is not to claim live trading profitability. The goal is to make LLM decision geometry, correlation blindness, risk feedback, and execution friction visible on real market paths.

## Rebuild

Download the daily panel:

```bash
python scripts/download_yahoo_daily.py --start 2021-01-01 --end 2023-12-31 --output-dir data/real/yahoo_daily_2021_2026_51 --tickers "AAPL,MSFT,NVDA,AMZN,META,GOOGL,GOOG,TSLA,AVGO,JPM,V,MA,UNH,XOM,COST,WMT,HD,PG,JNJ,ABBV,BAC,KO,PEP,CRM,NFLX,ORCL,AMD,CSCO,MRK,CVX,TMO,ACN,LIN,MCD,IBM,GE,CAT,DIS,QCOM,INTU,AMAT,TXN,NOW,ISRG,PM,NEE,RTX,SPGI,GS,HON,LOW,SCHW,C,WFC,MS,USB,PNC,TFC,KRE,XLF,^GSPC,BTC-USD,ETH-USD"
```

Run the live LLM crisis probe:

```bash
python scripts/run_crisis_scene_experiments.py \
  --output-dir outputs/tradearena_crisis \
  --data-dir data/real/yahoo_daily_2021_2026_51 \
  --cache data/llm_cache/crisis_scene_llm.jsonl \
  --scenes tech_rates_2022,svb_2023 \
  --models poe:gpt-5.5,poe:gemini-3.1-pro,poe:claude-opus-4.7,deepseek:deepseek-v4-pro \
  --feedback true,placebo,hidden \
  --max-symbols 51 \
  --max-periods 12
```

Build charts from raw trajectories already present, or copy the tracked snapshot when raw trajectories are absent:

```bash
python scripts/run_crisis_scene_experiments.py \
  --output-dir outputs/tradearena_crisis \
  --data-dir data/real/yahoo_daily_2021_2026_51 \
  --collect-existing
```

The LLM prompts mask calendar dates as relative steps (`T+0`, `T+1`, ...), so the crisis probe tests response to the recorded OHLCV path rather than explicit historical-date recall.

## Current Tracked Visuals

The repository tracks compact rendered copies under `docs/assets/crisis/`:

- `crisis_representation_trajectory.svg`: two-dimensional plan-embedding trajectory map.
- `crisis_correlation_intent_heatmap.svg`: market correlation versus LLM intent co-exposure.
- `crisis_feedback_learning_curves.svg`: rolling calibration score under true/placebo/hidden feedback.
- `crisis_exposure_waterfall.svg`: intended exposure versus risk-approved versus realized exposure.
- `crisis_microstructure_waterfall.svg`: realized exposure gap under slippage, latency, and partial fills.

The matching table snapshots live under `docs/results/crisis/`.

## Provider Notes

Poe and DeepSeek live calls are cache-first. A provider-side billing or availability failure for one model does not invalidate already cached trajectories; the runner logs the failed case and continues. The current tracked artifact includes the completed true/placebo/hidden matrix for GPT-5.5, Gemini 3.1 Pro, Claude Opus 4.7, and DeepSeek V4 Pro across both crisis scenes.

Raw prompt/response JSONL caches are local artifacts and are ignored by Git.
The repository tracks crisis tables, figures, and redacted cache manifests
instead. If you keep local caches on a second machine, rebuild the public
manifest with:

```bash
python scripts/build_llm_cache_manifest.py --cache data/llm_cache/crisis_scene_llm.jsonl
```

Large raw trajectory JSON files are intentionally not committed. They can exceed hundreds of megabytes because they contain full per-step decision objects for 51-symbol prompts. The tracked CSV summaries, compact charts, input data, redacted cache manifests, and script are sufficient for review and cross-machine reuse without bloating the repository.
