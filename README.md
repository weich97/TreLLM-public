<p align="center">
  <img src="docs/assets/trellm_readme_audit_system_banner_v2.svg"
       alt="TreLLM trading audit system wordmark"
       width="780">
</p>

<p align="center">
  <strong>
    TreLLM is an LLM-driven trading audit and control system. TradeArena is
    its public leaderboard for ranking auditable agent runs.
  </strong>
</p>

<p align="center">
  <a href="https://github.com/weich97/TreLLM-public/actions/workflows/ci.yml">
    <img alt="CI status" src="https://github.com/weich97/TreLLM-public/actions/workflows/ci.yml/badge.svg">
  </a>
  <a href="https://pypi.org/project/tradearena-benchmark/">
    <img alt="PyPI version" src="https://img.shields.io/pypi/v/tradearena-benchmark">
  </a>
  <a href="https://pypi.org/project/tradearena-benchmark/">
    <img alt="Python versions" src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776ab?logo=python&logoColor=white">
  </a>
  <a href="https://arxiv.org/abs/2605.28850">
    <img alt="arXiv:2605.28850" src="https://img.shields.io/badge/arXiv-2605.28850-b31b1b.svg">
  </a>
  <a href="https://github.com/weich97/TreLLM-public/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/weich97/TreLLM-public">
  </a>
  <a href="https://github.com/weich97/TreLLM-public/actions/workflows/ci.yml">
    <img alt="Coverage generated in CI" src="https://img.shields.io/badge/coverage-CI%20XML-64748b">
  </a>
  <a href="docs/claim_boundaries.md">
    <img alt="Claim boundary" src="https://img.shields.io/badge/claims-engineering%20%7C%20benchmark%20%7C%20scientific-475569">
  </a>
</p>

<p align="center">
  <a href="docs/getting_started.md">Getting started</a> |
  <a href="https://pypi.org/project/tradearena-benchmark/">PyPI</a> |
  <a href="https://weich97.github.io/TreLLM-public/">Project site</a> |
  <a href="https://weich97.github.io/TreLLM-public/agent_autopsy_dashboard.html">Agent Autopsy</a> |
  <a href="https://weich97.github.io/TreLLM-public/benchmark-v0.2.html">Benchmark card</a> |
  <a href="https://weich97.github.io/TreLLM-public/community_registry.html">Leaderboard</a> |
  <a href="docs/benchmark_submissions.md">Redacted manifests</a> |
  <a href="docs/public_artifact_privacy.md">Artifact privacy</a> |
  <a href="docs/research_report.md">Technical report</a> |
  <a href="docs/evaluation_rigor.md">Rigor</a> |
  <a href="docs/claim_boundaries.md">Claims</a> |
  <a href="docs/claim_boundary_review_quickstart.md">Claim review</a> |
  <a href="docs/external_validation_quickstart.md">Validate</a> |
  <a href="docs/execution_calibration_quickstart.md">Execution calibration</a> |
  <a href="docs/live_trading_readiness.md">Live readiness</a> |
  <a href="docs/broker_adapter_contract.md">Broker contract</a> |
  <a href="docs/deterministic_baseline_submission_quickstart.md">Baseline rows</a> |
  <a href="docs/observability.md">Trace export</a> |
  <a href="docs/benchmark_v0_2_spec.md">v0.2 spec</a> |
  <a href="docs/plugin_development.md">Plugins</a> |
  <a href="docs/agent_skills.md">Agent skills</a> |
  <a href="docs/financial_audit_agent_benchmark.md">Audit-agent tasks</a> |
  <a href="docs/poe_skill_task_experiments.md">Skill model matrix</a> |
  <a href="docs/benchmark_maturity.md">Maturity track</a> |
  <a href="docs/community_tasks.md">First issues</a> |
  <a href="docs/contributor_roadmap.md">Roadmap</a> |
  <a href="docs/narrative_positioning.md">Positioning</a> |
  <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <a href="https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=weich97/TreLLM-public">
    <img alt="Open in GitHub Codespaces"
         src="https://img.shields.io/badge/Open%20in-Codespaces-181717?logo=github">
  </a>
  <a href="https://colab.research.google.com/github/weich97/TreLLM-public/blob/main/notebooks/tradearena_5min_colab.ipynb">
    <img alt="Open in Colab"
         src="https://colab.research.google.com/assets/colab-badge.svg">
  </a>
  <a href="https://mybinder.org/v2/gh/weich97/TreLLM-public/main?filepath=notebooks%2Ftradearena_5min_colab.ipynb">
    <img alt="Launch Binder"
         src="https://mybinder.org/badge_logo.svg">
  </a>
  <a href="https://nbviewer.org/github/weich97/TreLLM-public/blob/main/notebooks/tradearena_5min_colab.ipynb">
    <img alt="View notebook"
         src="https://img.shields.io/badge/View-nbviewer-f37626">
  </a>
</p>

# TreLLM

TreLLM is not investment advice or a promise of profitable trading. Its
default commands do not submit live orders. Its long-term direction is a
live-ready, human-gated control plane where financial-agent intent remains
auditable, reproducible, risk-checked, and explainable before any broker-facing
workflow can act.

TreLLM is an audit microscope for financial agents: it records what a model
wanted to do, how risk controls revised it, how execution frictions changed the
fill, and whether the result can be replayed, hashed, redacted, and compared.
TradeArena is its public leaderboard for ranking auditable agent runs.

```json
{
  "step": 2,
  "intent": {"AAPL": 0.42},
  "risk_revision": {"AAPL": 0.35, "reason": "max_position_weight"},
  "execution": {"fill_ratio": 0.68, "slippage_bps": 14.2},
  "replay_hash": "sha256:9f4c..."
}
```

<p align="center">
  <img src="docs/assets/readme_audit_lifecycle.gif"
       alt="Animated TreLLM audit trace showing observation, plan, risk review, execution, and reflection records."
       width="920">
</p>

<p align="center">
  <img src="docs/assets/readme_pipeline_architecture.svg"
       alt="TreLLM runtime architecture: market inputs feed an agent observe-plan loop, a risk gate, an execution simulator, portfolio state, memory feedback, and replayable audit artifacts."
       width="980">
</p>

The current public path runs offline and paper/sandbox TreLLM experiments, with
TradeArena providing the comparable leaderboard and benchmark-card layer. The
system is still an early-stage research prototype, but it is intentionally
organized so future broker-facing adapters can inherit the same risk gates,
execution calibration, human approval records, reconciliation artifacts, and
audit logs. See [`docs/live_trading_readiness.md`](docs/live_trading_readiness.md).

## Name And Compatibility

TreLLM is the system name for the LLM-driven trading audit and control plane.
TradeArena names the leaderboard, benchmark cards, ranking tables, and public
comparison surfaces inside that system.
The `tradearena` command and package remain the compatibility surface for the
current public release, so existing notebooks, install commands, imports, and
GitHub Pages links keep working while the system identity moves beyond a
leaderboard-only framing.

## External Validators Wanted

TreLLM is looking for independent validation reports, calibration
mini-reports, and claim-boundary critiques. The most useful first contribution
is not a new model row; it is a small public artifact that another reader can
audit.

Start here: [`docs/external_validation_quickstart.md`](docs/external_validation_quickstart.md).

Good first validation paths:

| Time | Contribution | Where to submit |
| ---: | --- | --- |
| 1 hour | Run the no-key reproduction pack on macOS, Ubuntu, Colab, or Binder | Issues [#43](https://github.com/weich97/TreLLM-public/issues/43), [#44](https://github.com/weich97/TreLLM-public/issues/44), [#45](https://github.com/weich97/TreLLM-public/issues/45) |
| 1-2 hours | Submit one deterministic baseline manifest row | [Baseline row quickstart](docs/deterministic_baseline_submission_quickstart.md), Issue [#46](https://github.com/weich97/TreLLM-public/issues/46) |
| 2-3 hours | Submit one quote/fill calibration mini-report | [Execution calibration quickstart](docs/execution_calibration_quickstart.md), Issue [#47](https://github.com/weich97/TreLLM-public/issues/47) |
| 1 hour | Review one benchmark or README claim boundary | [Claim review quickstart](docs/claim_boundary_review_quickstart.md), Issue [#48](https://github.com/weich97/TreLLM-public/issues/48) |

Accepted validation reports should name the commit, environment, commands,
artifact paths, hashes, deviations, and whether any live APIs or private data
were used. Screenshots and informal impressions are welcome context, but they
do not count as validation unless the command and artifact trail is public.

## Research Framing

TreLLM is best read as an agent-reliability substrate, not only as a trading
benchmark. Finance supplies a high-stakes testbed where autonomous agents must
turn uncertain observations into portfolio intent, survive explicit risk
constraints, and face execution frictions before their actions become realized
state.

The current narrative has three pillars:

- Agent Reliability: do autonomous or multi-agent policies remain stable,
  calibrated, and inspectable under market stress?
- Risk-aware AI Systems: can structured risk reports act as external
  constraints and feedback for model behavior?
- Intent-to-Execution Audit: where does performance change between proposed
  weights, risk-approved weights, orders, fills, and final portfolio state?

This makes the system relevant to LLM trading agents, AI portfolio managers,
multi-agent finance systems, and broader autonomous-agent evaluation. The
included tasks are research-oriented and default to offline, paper, sandbox, or
human-review workflows; they are not live trading recommendations.

The repository also includes a small skill task suite for evaluating LLMs as
financial-audit agents rather than stock pickers. Those tasks ask models to
audit trajectories, interpret risk feedback, attribute execution friction,
review reproduction evidence, and weaken claims that outrun the evidence.

The accompanying technical report is:

> Weicheng Xue. 2026. Representation Signatures and Risk-Feedback Alignment in
> LLM Trading Agents. arXiv:2605.28850.
> https://arxiv.org/abs/2605.28850

## Claim Boundary

The repo distinguishes three claims:

| Claim class | What the project can say | Evidence required |
| --- | --- | --- |
| Engineering | TreLLM records replayable trajectories, risk reports, fills, manifests, and hashes. | Runnable artifact, schema validation, and reproduction command. |
| Benchmark | Risk gates and paper-execution frictions change measured outcomes under a frozen protocol. | Shared scenarios, seeds or rolling windows, fixed baselines, confidence intervals, and execution assumptions. |
| Scientific | A model or agent class is more reliable for financial decisions. | Stable provider/version records, repeated runs, non-LLM baseline wins, failure autopsy, and independent replication. |

Model rows that mix redaction, provider drift, cache-first behavior, and live
calls should be read as benchmark evidence, not as broad claims that one model
is generally better at trading. See
[`docs/claim_boundaries.md`](docs/claim_boundaries.md) and
[`docs/evidence_labels.md`](docs/evidence_labels.md).
Current public LLM runs are deliberately labeled as protocol fixtures, pilot
evidence, routed-provider evidence, or redacted benchmark rows until direct API
model matrices and independent external reproduction reports satisfy the v0.3
protocol gates.

## Why TreLLM?

TreLLM is not a replacement for mature backtesting engines. It is a small
audit harness for asking what happened between an agent's stated intent, the
risk-aware action that was allowed, and the paper order that survived execution
stress.

| Tool | Best fit | TreLLM / TradeArena relationship |
| --- | --- | --- |
| Backtrader | Event-driven strategy backtests and broker-style order workflows | Use when the main object is a classical strategy backtest; TreLLM focuses on agent traces, risk edits, and redacted LLM manifests. |
| vectorbt | Fast vectorized research over many parameter settings | Use when large array sweeps matter most; TreLLM trades speed for step-level audit records and execution/risk reports. |
| FinRL | Reinforcement-learning market environments and policy training | Use for RL policy development; TreLLM can wrap learned or deterministic policies as agents and compare their risk/execution behavior. |
| TreLLM + TradeArena | Live-ready financial-agent audit, risk control, execution calibration, broker-review handoff, and public leaderboard artifacts | Use when prompts, decisions, risk gates, fills, memory, approvals, and benchmark manifests need to be inspected together. |

## How A Run Works

The runner in
[`src/tradearena/core/runner.py`](src/tradearena/core/runner.py) executes the
same loop at every market timestamp: read the market snapshot, collect analyst
signals, build target weights, apply the risk gate, simulate fills, update the
portfolio, and write the logs.

The default allocation logic is intentionally simple and inspectable. In
[`SignalWeightedStrategy`](src/tradearena/agents/strategy.py), analyst signals
are grouped by symbol, confidence-weighted, and converted into target weights:

```text
combined_score(symbol) =
  sum(signal.score * max(0.01, signal.confidence)) /
  sum(max(0.01, signal.confidence))

target_weight = clip(5 * combined_score, -max_short_weight, max_long_weight)
```

Small scores inside the deadband become `HOLD`. The optional
[`MemoryAwareSignalWeightedStrategy`](src/tradearena/agents/strategy.py) applies
a decayed memory overlay when recent memory contains drawdowns, rejected orders,
or risk violations. It records the configured `memory_decay_rate`, a weighted
`memory_pollution_ratio` for noisy or invalid memory events, and
`memory_driven_leverage_amplification`, the per-decision ratio between
memory-adjusted and base target exposure. Classical baselines are first-class
comparison rows: buy-and-hold, equal weight, naive momentum, mean reversion,
risk parity, minimum variance, Markowitz/MVO, random, and always-hold. LLM rows
should beat these anchors before any model-skill claim is made.

Execution is split into two stages. First,
[`TargetWeightExecutionAgent`](src/tradearena/agents/execution.py) translates
approved target weights into market orders by comparing current position value
with target portfolio value. Trades below `min_trade_value` are skipped to avoid
noise. Second,
[`RealisticOrderSimulator`](src/tradearena/execution/stress.py) applies a
configurable paper-execution stress model:

- submitted orders enter a pending queue and become eligible after
  `latency_steps`;
- per-symbol fill capacity is capped by `bar.volume * participation_rate`;
- buys cannot exceed available cash, and sells cannot exceed holdings unless
  shorting is enabled;
- market orders cross half the configured bid-ask spread;
- execution price includes base slippage, spread, market impact, and intrabar
  volatility:

```text
slip_rate =
  spread_bps / 20000
  + base_slippage_bps / 10000
  + market_impact * (filled_quantity / volume)
  + 0.1 * ((high - low) / close)
```

The simulator writes an `ExecutionReport` with quantities, fill ratio, latency,
available liquidity, fees, slippage cost, partial fills, pending orders, and
rejections. The defaults are stress-test settings. They are not broker-grade
transaction-cost calibration.

## Execution Assumptions

The simulator is deliberately simple. The important parameters are:

| Parameter | Default role | Calibration source needed |
| --- | --- | --- |
| `commission_bps` | explicit fee on traded notional | broker or exchange fee schedule |
| `spread_bps` | full quoted spread; market orders cross half | quote/NBBO or order-book snapshots |
| `base_slippage_bps` | residual shortfall before spread, impact, and bar volatility | historical order/fill logs |
| `participation_rate` | cap on fillable bar volume | execution policy or parent-order participation target |
| `latency_steps` | bar-delay before an order is eligible | submission, acknowledgement, and fill timestamps |
| `market_impact` | coefficient on participation | regression of implementation shortfall on participation |

The tracked Yahoo Finance OHLCV files are enough for bar ranges, rough volume
checks, and participation caps. They are not enough for quoted spread, queue
depth, fee tier, latency, or realized shortfall. Treat the included benchmark
numbers as stress comparisons under shared assumptions. For execution claims,
replace the defaults with parameters fitted from quotes and fills.

The default TradeArena benchmark is therefore **not** suitable as a transaction-cost prediction
engine in its default configuration. The execution layer is split into
`tradearena.execution.simple`, `tradearena.execution.stress`,
`tradearena.execution.fill_replay`, and `tradearena.execution.calibration` so
results cannot silently mix stress assumptions with calibrated claims:

| Mode | Input required | Appropriate claim |
| --- | --- | --- |
| `realistic` | OHLCV bars plus explicit stress parameters | Agent reliability under shared paper-execution stress |
| `calibrated` | External quote/fill calibration profile | Reuse of documented venue- or broker-specific fitted parameters |
| `quote-replay` / `level2-replay` | Top-of-book or Level-2 snapshots in `MarketSnapshot.alt_data` | Quote-aware replay with observed spread/depth constraints |
| `fill-replay` | Private or licensed realized fill log | Audit replay of orders against historical fills |

Only the replay and calibrated modes should be used for transaction-cost
validation, and even then the calibration data source, venue, broker, order
types, and date range should be reported with the result.

Run the diagnostic:

```bash
python scripts/calibrate_execution_model.py --data-dir data/real/yahoo_intraday_1h_50
```

This writes `docs/results/execution_calibration_intraday_1h.json` and
`docs/results/execution_calibration_intraday_1h.md`. Full details are in
[`docs/execution_model_boundaries.md`](docs/execution_model_boundaries.md), including the
`scripts/compare_execution_to_fills.py` workflow for comparing private or
licensed historical fills against the simulator equation.

For quote/fill calibration, run the reproducible microstructure fixture:

```bash
python scripts/calibrate_quote_fill_model.py
```

This writes `docs/results/execution_quote_fill_calibration_sample.json` and
`docs/results/execution_quote_fill_calibration_sample.md`. Treat the checked-in
fixture as a pipeline test; publishable calibrated claims should replace it with
public exchange quote/order-book data, licensed data, or broker fills.

For a public exchange quote/fill sample, run:

```bash
python scripts/download_binance_microstructure_sample.py
python scripts/calibrate_quote_fill_model.py \
  --quotes data/public/binance_btcusdt_perp_2024_03_01_sample/quotes.csv \
  --fills data/public/binance_btcusdt_perp_2024_03_01_sample/fills.csv \
  --output docs/results/execution_quote_fill_calibration_binance_sample.json \
  --markdown-output docs/results/execution_quote_fill_calibration_binance_sample.md \
  --commission-bps-default 0
```

The checked-in Binance sample covers BTCUSDT USD-M futures public
top-of-book updates and public trades for a short UTC window. It is a
calibration example, not a venue-wide transaction-cost claim.

To close the loop across the three execution modes on the same small order
tape, run:

```bash
python scripts/run_execution_replay_calibration_loop.py
```

This writes `docs/results/execution_replay_calibration_loop.json` and
`docs/results/execution_replay_calibration_loop.md`, comparing OHLCV stress,
quote replay, and fill replay on a hand-checkable BTCUSDT fixture plus a
short Binance BTCUSDT public sample.

To check calibration stability across short public fill windows, run:

```bash
python scripts/run_execution_calibration_stability.py
```

This writes `docs/results/execution_calibration_stability.json` and
`docs/results/execution_calibration_stability.md`.

Risk control runs before, during, and after simulated execution.
[`MaxPositionRiskManager`](src/tradearena/agents/risk.py) runs three checks:

- pre-trade approval clips per-symbol weights to `max_abs_weight`, blocks
  decisions below `min_confidence`, rescales gross exposure above
  `max_gross_exposure`, forces de-risking when the rolling drawdown kill switch
  breaches `max_drawdown`, and reports projected turnover above
  `max_single_step_turnover`;
- in-trade monitoring checks realized participation, latency, and slippage
  against `max_order_participation`, `max_latency_steps`, and
  `max_slippage_bps`;
- post-trade attribution reports realized PnL, commission, slippage cost, and
  final exposures.

Each intervention is saved as a `RiskReport` with `RiskCheck` and
`RiskViolation` records. That makes it possible to compare the model's original
intent with the order that actually reached the simulator. For deterministic
exchange-rule feasibility examples, run:

```bash
python examples/market_rules_fixture_demo.py
```

This writes `docs/results/market_rules_fixture.json` and
`docs/results/market_rules_fixture.md`, covering A-share T+1/price limits,
Hong Kong board-lot rounding, crypto fee/funding, and liquidity-halt clips.

## Quick Start: Deterministic Smoke Test

```bash
python -m pip install tradearena-benchmark
tradearena --benchmark tradearena-core
```

This command does **not** call an LLM. It is a no-key smoke test for the runner,
log schema, risk gate, execution simulator, and metrics. It uses deterministic
analysts so a fresh checkout can be tested before API keys or billing are
involved.

The PyPI distribution is `tradearena-benchmark` because `tradearena` is already
occupied on PyPI by an unrelated project. The import namespace and CLI remain
`tradearena`.

## 5 Minutes To A Result

One command writes a replayable trajectory JSON:

```bash
mkdir -p outputs/examples
tradearena --benchmark tradearena-core --periods 30 --output outputs/examples/quickstart_trajectory.json
```

Then verify the run identity:

```bash
tradearena hash-run outputs/examples/quickstart_trajectory.json
```

Replay one trajectory step in the terminal:

```bash
tradearena replay outputs/examples/quickstart_trajectory.json --case risk_aware_realistic_agent --step 17
```

The first artifact to inspect is
`outputs/examples/quickstart_trajectory.json`: it contains the decisions,
pre-trade risk reports, simulated fills, portfolio states, and metrics for each
case. For browser reports, run the local showcase below.

To run the local demo portal:

```bash
git clone https://github.com/weich97/TreLLM-public.git
cd TreLLM
python -m pip install -e ".[dev]"
python scripts/run_showcase.py
```

Then open:

```text
outputs/examples/index.html
outputs/examples/agent_autopsy_dashboard.html
```

If you are deciding whether the project is worth using, start with this command
and inspect the generated reports before setting up model keys, market-data
downloads, or broker-facing code.

The first-run path uses deterministic agents, tracked snapshots, and local demo
files. It does not call DeepSeek, Poe, OpenAI, Hugging Face, AkShare, Yahoo
Finance, or broker APIs unless you run the opt-in commands below.

## Contributor Entry Points

The most useful early contributions are not broad feature requests. They are
small external evidence tasks that show a non-maintainer can run, question, or
submit benchmark evidence:

| Task | Time | Evidence to submit |
| --- | ---: | --- |
| [Run the v0.2 reproduction pack on macOS](https://github.com/weich97/TreLLM-public/issues/43) | 1 hour | `outputs/reproduction/v0_2/manifest.json`, Python version, command log, deviations |
| [Run the v0.2 reproduction pack on Ubuntu](https://github.com/weich97/TreLLM-public/issues/44) | 1 hour | same manifest plus OS/package-manager notes |
| [Run the v0.2 reproduction pack on Colab/Binder](https://github.com/weich97/TreLLM-public/issues/45) | 1 hour | notebook URL, runtime type, generated manifest, deviations |
| [Submit one deterministic baseline row](https://github.com/weich97/TreLLM-public/issues/46) | 1-2 hours | one schema-valid manifest and rebuilt registry output |
| [Submit one quote/fill calibration mini-report](https://github.com/weich97/TreLLM-public/issues/47) | 2-3 hours | calibration JSON/Markdown with source, venue, date range, and replay error |
| [Review one benchmark claim boundary](https://github.com/weich97/TreLLM-public/issues/48) | 1 hour | one issue or PR mapping a README/result claim to engineering, benchmark, or scientific evidence |

The concrete commands, acceptance criteria, and issue labels are in
[`docs/community_tasks.md`](docs/community_tasks.md). For plugin work, use
`tradearena new-plugin --type risk --name max-drawdown-guard` and follow
[`docs/plugin_development.md`](docs/plugin_development.md). For reviewer or
coding-agent workflows, use [`docs/agent_skills.md`](docs/agent_skills.md);
these skills are audit and reproduction templates, not benchmark-agent prompts.
The companion task suite scores models as financial-audit agents: audit
accuracy, risk-gate understanding, execution-boundary awareness, claim
discipline, reproduction awareness, and narrow plugin engineering.
The tracked task matrix is in
[`docs/results/skill_task_matrix.md`](docs/results/skill_task_matrix.md).
Reference answers in `examples/skill_task_answers/reference/` provide a
maintainer baseline for the scoring harness.
Provider-hosted Poe model matrices are tracked separately as audit-agent
experiments, not trading leaderboards:
[`docs/results/poe_skill_task_matrix.md`](docs/results/poe_skill_task_matrix.md)
and
[`docs/results/poe_skill_challenge_matrix.md`](docs/results/poe_skill_challenge_matrix.md).
The challenge suite in `examples/skill_tasks_challenge/` stresses claim
discipline, privacy redaction, reproduction honesty, execution-boundary
awareness, and market-rule caution.
The tracked challenge run covers 5 Poe-hosted models, 8 adversarial audit tasks,
3 reviewer prompt variants, and 2 independent samples per variant.
Follow-up `r3` samples are tracked for selected high-value rows to expose
repeat-level variance rather than treating a single provider answer as stable.

## LLM Run Paths

Live provider calls are opt-in.

- `tradearena --benchmark tradearena-core` runs the deterministic smoke test.
- `python examples/llm_cache_replay_demo.py` shows a redacted manifest from
  prior LLM runs without storing raw prompts or responses.
- `tradearena --benchmark llm-smoke ...` runs one live or cache-backed LLM
  analyst case.
- `tradearena --paper-output ...` runs the larger experiment suite. LLM sections
  use cache-first behavior where configured.

One real provider-backed smoke baseline is tracked here:
[`docs/results/llm_live_baseline.md`](docs/results/llm_live_baseline.md).
It records a 2026-05-18 Poe-hosted `gpt-5.5` run with redacted cache manifests
and no raw prompt/response text in Git.

Minimal live LLM smoke test through Poe:

```powershell
$env:POE_API_KEY="..."
tradearena --benchmark llm-smoke `
  --analysts poe-llm `
  --llm-model gpt-5.5 `
  --periods 3 `
  --symbols SYN,ALT `
  --llm-cache outputs/examples/poe_llm_smoke_cache.jsonl
```

Minimal live LLM smoke test through DeepSeek:

```powershell
$env:DEEPSEEK_API_KEY="..."
tradearena --benchmark llm-smoke `
  --analysts deepseek-llm `
  --llm-model deepseek-v4-flash `
  --periods 3 `
  --symbols SYN,ALT `
  --llm-cache outputs/examples/deepseek_llm_smoke_cache.jsonl
```

These commands write cache entries locally. Git ignores the cache because raw
prompts and responses can contain provider, licensing, privacy, or portfolio
constraints.

## Advanced Integrations Safety

DeepSeek, Poe-hosted models, OpenAI-compatible chat endpoints, AkShare, Yahoo
Finance, and broker-facing workflows are opt-in advanced paths. They are not
part of the first-run command. Broker-facing work should follow a staged path:
offline export, dry run, paper sandbox, and only then human-approved live
submission.

- Keep provider keys in environment variables or an OS secret manager.
- Track metrics and redacted manifests, not raw prompt/response caches.
- For Yahoo Finance or AkShare downloads, record source, frequency, symbols,
  timestamp policy, and adjustment mode.
- Treat the execution model as a stress model unless quote/fill logs are used
  for calibration.
- Broker-facing examples must stay offline export, paper sandbox, dry run, or
  human-reviewed. The default examples do not submit live orders.
- Any adapter that can touch a broker must follow
  [`docs/broker_adapter_contract.md`](docs/broker_adapter_contract.md).

Do not commit `.env` files, provider JSONL caches, broker tokens, account
statements, or private holdings. If a run needs to be shared, publish a redacted
submission or cache manifest instead of raw provider text.

The full checklist is in
[`docs/advanced_integrations_security.md`](docs/advanced_integrations_security.md).
The long-term staged path is in
[`docs/live_trading_readiness.md`](docs/live_trading_readiness.md).

## Live Trading Safety Contract

Broker-facing contributions must preserve a human-gated path from reviewed
intent to broker-visible response. A live adapter may only use
`live_human_approved` after a pre-live broker-review request has been hashed,
approved, bound to that exact request, and revalidated before submission.

Before sharing a broker-facing PR, run the relevant checks:

```bash
tradearena validate-broker-capability outputs/examples/broker_capability_manifest/capability_manifest.json
tradearena validate-broker-handoff outputs/examples/broker_approval_safety/dry_run_orders.json
tradearena hash-broker-handoff outputs/examples/broker_approval_safety/dry_run_orders.json
tradearena validate-broker-approval outputs/examples/broker_approval_safety/broker_approval_artifact.json --now 2026-05-31T12:30:00Z
tradearena validate-broker-approval-binding outputs/examples/broker_approval_safety/broker_approval_artifact.json outputs/examples/broker_approval_safety/dry_run_orders.json --now 2026-05-31T12:30:00Z
tradearena validate-broker-response outputs/examples/broker_response_reconciliation/broker_response_artifact.json
tradearena validate-operator-runbook outputs/examples/operator_runbook/summary.json
tradearena validate-live-readiness outputs/examples/live_readiness_preflight/preflight_bundle.json --now 2026-05-31T12:30:00Z
```

The approval must contain a redacted operator ID, positive finite notional and
quantity limits, allowed symbols and order types, an expiry, and the exact
pre-live broker-review request hash. Response artifacts must stay separated by
account mode and explain rejected or unknown broker statuses with redacted
reasons.

## Install And Run

From a clone:

```bash
python -m pip install -e ".[dev]"
tradearena --benchmark tradearena-core
python -m tradearena.cli --benchmark tradearena-core
```

From GitHub without cloning first:

```bash
python -m pip install "git+https://github.com/weich97/TreLLM-public.git"
tradearena --benchmark tradearena-core
```

## TradeArena Result

The v0.2 TradeArena benchmark card makes one limited claim:

> Autonomous financial-agent results can change materially once risk gates and
> paper-execution costs are included.

The public leaderboard includes two model-comparison generators:

- a classical baseline matrix: buy-and-hold, equal weight, SMA crossover,
  naive momentum, mean reversion, risk parity, minimum variance, Markowitz/MVO,
  random, and always-hold across the same synthetic and real-market scenarios;
- a synthetic matrix: seven LLMs plus lower anchors across calm-trend,
  high-volatility, jump/tail, liquidity-collapse, spread-explosion, and
  latency-spike scenarios;
- a real-market matrix: the same model set across Yahoo Finance `^GSPC`,
  `BTC-USD`, and CME Bitcoin futures (`BTC=F`) rolling windows.

Models include Poe-hosted `gpt-5.5`, `gemini-3.1-pro`, `kimi-k2.5`, `glm-5`,
`claude-opus-4.7`, plus direct `deepseek-v4-flash` and `deepseek-v4-pro`.
The rows are redacted benchmark manifests; raw provider prompts and responses
remain in ignored local caches. These rows are suitable for reliability and
audit benchmarking; they should not be described as model-level trading-skill
claims unless the model also beats the fixed non-LLM baselines under the frozen
protocol.

Each leaderboard row is evidence-labeled. Typical provider rows carry
`stress-only`, `cached-provider`, and `redacted-prompt`; deterministic anchors
carry `stress-only` and `deterministic-baseline`; calibration reports use
`quote-calibrated` or `fill-replay-validated` only when quote/fill provenance is
attached. See [`docs/evidence_labels.md`](docs/evidence_labels.md).

The leaderboard scripts now default to five seeds per `(model, scenario)` and
write raw seed rows plus aggregate tables with mean, sample standard deviation,
95% bootstrap confidence intervals, paired bootstrap tests, and paired
sign-flip permutation tests against the `always-hold` and `random` anchors.
The real-market matrix also treats seeds as rolling window offsets and writes a
walk-forward provenance table so cache-backed runs and provider drift remain
auditable. Full live refreshes can be provider-costly; use a smaller `--models`,
`--scenarios`, or `--seeds` slice for smoke tests.

The frozen comparison contract for this benchmark card is
[`benchmarks/v0.2/spec.json`](benchmarks/v0.2/spec.json), with a human-readable
summary in [`docs/benchmark_v0_2_spec.md`](docs/benchmark_v0_2_spec.md). Validate
and hash it with:

```bash
python scripts/validate_benchmark_spec.py benchmarks/v0.2/spec.json
```

Open:

- Static page:
  [`weich97.github.io/TreLLM-public/benchmark-v0.2.html`](https://weich97.github.io/TreLLM-public/benchmark-v0.2.html)
- Leaderboard:
  [`weich97.github.io/TreLLM-public/community_registry.html`](https://weich97.github.io/TreLLM-public/community_registry.html)
- Markdown artifact:
  [`docs/results/benchmark_v0_2.md`](docs/results/benchmark_v0_2.md)
- Model matrix:
  [`docs/results/model_matrix/leaderboard_model_matrix.md`](docs/results/model_matrix/leaderboard_model_matrix.md)
- Real-market matrix:
  [`docs/results/real_market_matrix/real_market_model_matrix.md`](docs/results/real_market_matrix/real_market_model_matrix.md)
- Classical non-LLM baselines:
  [`docs/results/classical_baselines/classical_baselines.md`](docs/results/classical_baselines/classical_baselines.md)
- Decision/execution quality decomposition:
  [`docs/results/quality_decomposition/quality_decomposition.md`](docs/results/quality_decomposition/quality_decomposition.md)

Rebuild:

```bash
python scripts/build_benchmark_page.py
python scripts/run_leaderboard_model_matrix.py --seeds 7,11,17,23,31 --update-registry
python scripts/run_real_market_leaderboard.py --seeds 7,11,17,23,31 --update-registry
python scripts/run_classical_baseline_matrix.py
python scripts/build_quality_decomposition.py
```

The classical baseline matrix runs passive, random, trend-following,
contrarian, volatility-weighted, minimum-variance, and Markowitz/MVO policies on
the same synthetic and Yahoo Finance leaderboard scenarios. It is a main
benchmark surface, not an appendix, because LLM rows must be compared against
classical strategies before any scientific model claim is credible.
The quality decomposition separates pre-risk alpha quality, risk discipline,
and execution robustness in a three-axis radar chart.

## System And Leaderboard Maturity

Before calling TreLLM externally validated, or calling TradeArena a
community-backed leaderboard benchmark, three pieces still need to exist: a
stable academic report, independent validation reports, and non-maintainer
contributions that are reviewed in public.

- Maturity track: [`docs/benchmark_maturity.md`](docs/benchmark_maturity.md)
- External validation protocol: [`docs/external_validation.md`](docs/external_validation.md)
- Community participation rules:
  [`docs/community_participation.md`](docs/community_participation.md)

## Validate A Redacted Leaderboard Row

TradeArena can validate redacted leaderboard manifests. A manifest shares the
scenario, execution settings, risk settings, metrics, and reproducibility hash.
It should not expose raw provider prompts, raw responses, credentials, or
private portfolios. The format is for research exchange; one maintainer-authored
manifest is not community adoption.

```bash
tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json
tradearena hash-run outputs/examples/audit_walkthrough_trajectory.json
```

See [`docs/benchmark_submissions.md`](docs/benchmark_submissions.md).

## Visual Preview

<table>
  <tr>
    <th>Audit lifecycle</th>
    <th>Execution stress</th>
    <th>Diagnostic loop</th>
  </tr>
  <tr>
    <td>
      <img src="docs/assets/readme_audit_lifecycle.gif"
           alt="Animated observe-plan-risk-execute-reflect audit trace"
           width="280">
    </td>
    <td>
      <img src="docs/assets/readme_execution_realism.gif"
           alt="Animated execution comparison of ideal, realistic, high-spread,
                low-liquidity, and high-latency fills"
           width="280">
    </td>
    <td>
      <img src="docs/assets/readme_diagnostics_loop.gif"
           alt="Animated representation, risk-feedback, and concentration diagnostics"
           width="280">
    </td>
  </tr>
</table>

The browser-playable demo video is here:
[`weich97.github.io/TreLLM-public/demo_video.html`](https://weich97.github.io/TreLLM-public/demo_video.html).

## What Is In The Repo

- A runner that records market observations, agent decisions, risk reports,
  simulated fills, portfolio state, and metrics.
- A paper-execution simulator with fees, spread, slippage, latency, liquidity
  caps, partial fills, and rejections.
- A risk manager with pre-trade clipping/blocking, in-trade warnings, and
  post-trade attribution.
- Extension points for data providers, analysts, strategies, risk managers,
  simulators, memory stores, planners, and evaluators.
- A broker-review export surface that can turn approved orders into
  human-review files without submitting them.
- A schema for redacted benchmark manifests and a small registry builder.

## Extension Path

Start with one small plugin:

```bash
python examples/custom_plugin_demo.py
python examples/extension_walkthrough_demo.py
```

The walkthrough swaps in a custom analyst, risk manager, and evaluator while the
rest of the runner stays unchanged.

Useful entry points:

- [`examples/README.md`](examples/README.md)
- [`docs/demo_matrix.md`](docs/demo_matrix.md)
- [`docs/extension_walkthrough.md`](docs/extension_walkthrough.md)
- [`docs/plugin_development.md`](docs/plugin_development.md)
- [`plugins/README.md`](plugins/README.md)
- [`docs/contributor_roadmap.md`](docs/contributor_roadmap.md)

## Documentation Map

- Quickstart: [`docs/getting_started.md`](docs/getting_started.md)
- Advanced integration safety:
  [`docs/advanced_integrations_security.md`](docs/advanced_integrations_security.md)
- Live trading readiness:
  [`docs/live_trading_readiness.md`](docs/live_trading_readiness.md)
- Broker adapter contract:
  [`docs/broker_adapter_contract.md`](docs/broker_adapter_contract.md)
- Broker handoff validation:
  `tradearena validate-broker-handoff outputs/examples/alpaca_paper_export/alpaca_paper_orders.json`
- Broker adapter capability validation:
  `tradearena validate-broker-capability outputs/examples/broker_capability_manifest/capability_manifest.json`
- Broker response validation:
  `tradearena validate-broker-response outputs/examples/broker_response_reconciliation/broker_response_artifact.json`
- Live-readiness preflight validation:
  `tradearena validate-live-readiness outputs/examples/live_readiness_preflight/preflight_bundle.json --now 2026-05-31T12:30:00Z`
- Technical white paper: [`docs/technical_report.md`](docs/technical_report.md)
- Benchmark maturity:
  [`docs/benchmark_maturity.md`](docs/benchmark_maturity.md)
- v0.2 credibility audit:
  [`docs/v0_2_credibility_audit.md`](docs/v0_2_credibility_audit.md)
- Academic report plan:
- External validation:
  [`docs/external_validation.md`](docs/external_validation.md)
- Community participation:
  [`docs/community_participation.md`](docs/community_participation.md)
- Contributor tasks:
  [`docs/community_tasks.md`](docs/community_tasks.md)
- Plugin development:
  [`docs/plugin_development.md`](docs/plugin_development.md)
- Benchmark challenges:
  [`docs/benchmark_challenges.md`](docs/benchmark_challenges.md)
- Community operations:
  [`docs/community_operations.md`](docs/community_operations.md)
- Market rules and stress presets:
  [`docs/market_rules.md`](docs/market_rules.md)
- Observability:
  [`docs/observability.md`](docs/observability.md)
- Schemas: [`docs/schemas.md`](docs/schemas.md)
- Execution model: [`docs/execution_model_boundaries.md`](docs/execution_model_boundaries.md)
- Execution calibration quickstart:
  [`docs/execution_calibration_quickstart.md`](docs/execution_calibration_quickstart.md)
- Redacted leaderboard submissions: [`docs/benchmark_submissions.md`](docs/benchmark_submissions.md)
- Deterministic baseline row quickstart:
  [`docs/deterministic_baseline_submission_quickstart.md`](docs/deterministic_baseline_submission_quickstart.md)
- Evaluation rigor: [`docs/evaluation_rigor.md`](docs/evaluation_rigor.md)
- Claim review quickstart:
  [`docs/claim_boundary_review_quickstart.md`](docs/claim_boundary_review_quickstart.md)
- v0.2 benchmark spec: [`docs/benchmark_v0_2_spec.md`](docs/benchmark_v0_2_spec.md)
- Execution calibration priority:
  [`docs/execution_calibration_priority.md`](docs/execution_calibration_priority.md)
- External reproduction pack:
  [`docs/reproduction_pack_v0_2.md`](docs/reproduction_pack_v0_2.md)
- Related work: [`docs/related_work.md`](docs/related_work.md)
- Retail planning sandbox: [`docs/retail_planning.md`](docs/retail_planning.md)
- Research protocol: [`docs/research_protocol.md`](docs/research_protocol.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Governance: [`GOVERNANCE.md`](GOVERNANCE.md)

## Local Checks

Each checkout can use its own `.venv`, which helps if you keep public and
private copies of the project side by side:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_local.ps1
```

The script installs the checkout in editable mode, then runs compile checks,
Ruff, tests, release-readiness checks, submission validation, artifact-contract
validation, and JSON validation.

## Safety Boundary

TreLLM does not promise profitable trading, does not provide financial
advice, and does not execute live trades by default. Public examples are
offline, paper/sandbox, dry-run, or human-review oriented. Broker and provider
integrations must follow
[`docs/live_trading_readiness.md`](docs/live_trading_readiness.md),
[`docs/broker_adapter_contract.md`](docs/broker_adapter_contract.md),
[`docs/advanced_integrations_security.md`](docs/advanced_integrations_security.md),
[`SECURITY.md`](SECURITY.md), and [`GOVERNANCE.md`](GOVERNANCE.md).

## Cite

If you use TreLLM in research or cite TradeArena leaderboard artifacts, please cite the technical report:

```bibtex
@article{xue2026tradearena,
  title         = {Representation Signatures and Risk-Feedback Alignment in LLM Trading Agents},
  author        = {Xue, Weicheng},
  year          = {2026},
  journal       = {arXiv preprint arXiv:2605.28850},
  doi           = {10.48550/arXiv.2605.28850},
  url           = {https://arxiv.org/abs/2605.28850},
  eprint        = {2605.28850},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG}
}
```

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata. If
you use a specific software release, also cite the repository release you used.
