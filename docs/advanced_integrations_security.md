# Advanced Integration Safety

TreLLM supports optional model, market-data, paper-broker, and future
broker-facing integration paths. These paths are research and control-plane
utilities, not permission to run unattended live trading. The default repository
path remains offline and deterministic. TradeArena leaderboard artifacts should
stay reproducible from tracked metadata and redacted manifests.

## Integration Modes

| Mode | Network calls | Secrets | Live order path | Intended use |
| --- | --- | --- | --- | --- |
| Deterministic smoke test | No | No | No | CI, first run, reproducibility checks |
| Cache replay | No | No | No | Reuse prior model outputs through local caches or redacted manifests |
| Live LLM analyst | Yes | Provider API key | No | Measure model behavior, risk feedback, and parsing coverage |
| Market-data download | Yes | Usually no key for Yahoo/AkShare scripts | No | Build normalized OHLCV CSV inputs with source metadata |
| Broker review export | No broker submission | No broker key required | No | Create review files that a human can inspect outside TreLLM |
| Paper trading sandbox | Broker paper API only | Paper-account credentials | No | Test broker request/response and reconciliation without live capital |
| Human-approved live adapter | Broker live API | Broker credentials | Only after explicit approval | Future supervised execution track, outside benchmark claims |

## Secret Handling

- Prefer per-session environment variables or an operating-system secret manager.
  Do not commit keys, paste them into notebooks, or pass them as CLI arguments.
- On PowerShell, a per-session key is enough for one run:

```powershell
$env:POE_API_KEY = "..."
$env:DEEPSEEK_API_KEY = "..."
$env:OPENAI_API_KEY = "..."
```

- If you persist a key with `setx`, remember that it is stored in the user
  environment. Rotate it after shared-machine experiments and remove it with:

```powershell
[Environment]::SetEnvironmentVariable("POE_API_KEY", $null, "User")
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", $null, "User")
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $null, "User")
```

- Keep local secret files under ignored paths such as `.env`, `.secrets/`, or
  `data/private/`. Public TradeArena leaderboard artifacts should be
  reproducible from code, tracked metadata, and redacted manifests, not from
  private credentials.

## LLM Provider Rules

LLM analysts return signals or target weights. They do not submit orders. A live
provider run must record enough metadata for audit while avoiding credential or
private prompt leakage:

- provider and model label;
- prompt mode, risk-feedback mode, and output mode;
- cache path or redacted manifest path;
- parse coverage and failed-parse counts where available;
- whether timestamps were masked;
- whether raw prompts and responses are retained locally or omitted from public
  artifacts.

Raw JSONL caches may contain provider responses, prompt text, private portfolio
state, or provider-specific usage constraints. They are intentionally ignored by
Git. Publish redacted manifests with:

```bash
python scripts/build_llm_cache_manifest.py --cache data/llm_cache/deepseek_analyst.jsonl
```

## Market Data Rules

Yahoo Finance and AkShare scripts normalize downloaded rows into the same CSV
schema consumed by `CsvMarketDataProvider`. Treat downloaded market data as an
input artifact with provenance:

- source API or site;
- download date;
- symbol universe;
- frequency and timestamp policy;
- adjustment mode;
- missing-row and timezone handling.

OHLCV bars do not contain quotes, order-book depth, queue position, realized
fill timestamps, or broker fee tiers. Execution parameters calibrated only from
bars should be described as stress assumptions, not broker-grade execution
calibration.

## Broker Adapter Rules

The public repository currently ships export-only broker surfaces. A broker
adapter must default to one of these modes:

- offline export;
- dry run;
- paper trading sandbox;
- human-approved review;
- redacted manifest generation.

Any adapter that can submit live orders is outside the public TradeArena leaderboard path,
must be separate from default examples, and must satisfy
[`broker_adapter_contract.md`](broker_adapter_contract.md). At minimum it needs
explicit mode selection, sandbox configuration, human approval before live
submission, account isolation, order-size limits, credential redaction, a kill
switch, reconciliation artifacts, and tests that prove the default path cannot
place orders.

The included Alpaca example writes paper-review JSON/CSV files and sets
`submit_live=false`; it does not call Alpaca or any other broker API.

## Public Artifact Checklist

Before publishing benchmark results or examples, verify:

- no API keys, broker tokens, cookies, account numbers, or private holdings are
  present;
- raw prompt/response caches are local only or replaced by redacted manifests;
- data provenance and execution assumptions are stated;
- live provider calls are opt-in and clearly labeled;
- broker-facing outputs are offline export, dry run, paper sandbox, or
  human-review files;
- generated artifacts can be reproduced without private credentials whenever
  the command is advertised as a first-run path.

Run the release checks before pushing:

```bash
python scripts/check_release_readiness.py
python -m pytest -q
```

For the staged path from TreLLM audit research to supervised live execution, see
[`live_trading_readiness.md`](live_trading_readiness.md).
