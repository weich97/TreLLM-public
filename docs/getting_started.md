# Getting Started

TreLLM is easiest to evaluate as a sequence of explicit run modes. Treat it as
an early-stage reliability lab for financial AI agents: the first run checks the
runner, trajectory schema, risk gate, execution simulator, and metric stack. It
is not a live LLM call. LLM agent runs are opt-in once you configure a provider
key or a local cache. TradeArena remains the public leaderboard and ranking
surface for comparable benchmark artifacts.

## Five-Minute Path

If the package is already installed, one command writes a replayable trajectory:

```bash
mkdir -p outputs/examples
tradearena --benchmark tradearena-core --periods 30 --output outputs/examples/quickstart_trajectory.json
tradearena hash-run outputs/examples/quickstart_trajectory.json
tradearena replay outputs/examples/quickstart_trajectory.json --case risk_aware_realistic_agent --step 17
```

For the full local demo portal:

```bash
git clone https://github.com/weich97/TreLLM-public.git
cd TreLLM
python -m pip install -e ".[dev]"
python scripts/run_showcase.py
```

Open:

```text
outputs/examples/index.html
outputs/examples/agent_autopsy_dashboard.html
```

Use this page as the first quality check. Inspect the generated reports, charts,
trajectories, and demo pages before deciding whether to invest time in live LLM
keys, real-market downloads, AI portfolio-manager prototypes, multi-agent
finance systems, or broker-facing extensions.

The first-run path does not call DeepSeek, Poe, OpenAI, Hugging Face, AkShare,
or Yahoo Finance. It uses tracked data, deterministic synthetic markets, and
redacted metadata artifacts.

No local install yet? Use:

- [GitHub Codespaces][codespaces-quickstart]
- Colab notebook: [`notebooks/tradearena_5min_colab.ipynb`](../notebooks/tradearena_5min_colab.ipynb)
- [Binder][binder-quickstart]
- [nbviewer][nbviewer-quickstart]

Binder and Colab sessions should run the setup cell first; it installs the
editable checkout and creates `outputs/examples` before writing
`outputs/examples/notebook_trajectory.json`. Binder can take several minutes on
the first launch while the image builds. After a Colab runtime reset, rerun the
setup cell before running the benchmark and `hash-run` cells again.

## LLM Paths

Use the no-key manifest demo to inspect what prior LLM experiment coverage looks
like without shipping raw prompts or responses:

```bash
python examples/llm_cache_replay_demo.py
```

Run one live/cache-backed LLM analyst case through Poe:

```powershell
$env:POE_API_KEY="..."
tradearena --benchmark llm-smoke `
  --analysts poe-llm `
  --llm-model gpt-5.5 `
  --periods 3 `
  --symbols SYN,ALT `
  --llm-cache outputs/examples/poe_llm_smoke_cache.jsonl
```

Or run the same smoke test through DeepSeek:

```powershell
$env:DEEPSEEK_API_KEY="..."
tradearena --benchmark llm-smoke `
  --analysts deepseek-llm `
  --llm-model deepseek-v4-flash `
  --periods 3 `
  --symbols SYN,ALT `
  --llm-cache outputs/examples/deepseek_llm_smoke_cache.jsonl
```

Or point the OpenAI-compatible adapter at a local Ollama server. This path is
opt-in, does not require a cloud API key by default, and still writes a cache so
the same prompt can be replayed later without contacting the local endpoint:

```bash
export TRADEARENA_OLLAMA_BASE_URL="http://localhost:11434/v1"
tradearena --benchmark llm-smoke \
  --analysts ollama-llm \
  --llm-model llama3.2 \
  --periods 3 \
  --symbols SYN,ALT \
  --llm-cache outputs/examples/ollama_llm_smoke_cache.jsonl
```

If your Ollama-compatible gateway enforces authentication, set
`TRADEARENA_OLLAMA_API_KEY`; otherwise the local request is sent without an
Authorization header. Keep `outputs/examples/ollama_llm_smoke_cache.jsonl` out
of shared artifacts unless prompts and responses have been reviewed/redacted.

`llm-smoke` intentionally runs a single LLM analyst case. The default
`tradearena-core` benchmark remains deterministic unless you explicitly set
`--analysts deepseek-llm`, `--analysts poe-llm`, or `--analysts ollama-llm`.

Before running live model providers, market-data downloads, or broker-facing
exports, read the advanced integration checklist:
[`advanced_integrations_security.md`](advanced_integrations_security.md).
Live provider runs should use environment-variable secrets, ignored local caches,
and redacted manifests for shared artifacts.

## Fifteen-Minute Path

```bash
python examples/audit_trajectory_walkthrough.py
python scripts/render_audit_report.py
python examples/execution_realism_sweep_demo.py
python examples/portfolio_markowitz_demo.py
python examples/visual_tour_demo.py
python examples/custom_plugin_demo.py
python examples/extension_walkthrough_demo.py
python examples/retail_planner_demo.py
```

Useful files:

- `outputs/examples/audit_report.html`
- `outputs/examples/agent_autopsy_dashboard.html`
- `outputs/examples/benchmark-v0.2.html`
- `outputs/examples/showcase.html`
- `outputs/examples/execution_realism_sweep.svg`
- `outputs/examples/portfolio_markowitz.svg`
- `outputs/examples/visual_tour_index.html`
- `outputs/examples/custom_plugin.svg`
- `outputs/examples/extension_walkthrough.svg`
- `outputs/examples/retail_planning_report.html`
- `outputs/examples/audit_walkthrough_trajectory.json`

The execution realism sweep includes a `high_spread` preset. It keeps the same
agent and synthetic market but adds a quoted bid-ask spread so users can see
how crossing cost changes realized return and slippage even when fill rates do
not collapse.

## Extension Path

Start from a generated skeleton:

```bash
tradearena new-plugin --type risk --name max-drawdown-guard
```

Then compare with `examples/custom_plugin_demo.py`. It defines one local analyst
class and reuses the existing runner, risk manager, execution simulator, memory
store, and evaluators.

Then run `examples/extension_walkthrough_demo.py`. It shows the fuller
contributor path: a custom analyst, a custom risk manager, and a custom
evaluator plugged into the same runner while the data provider, strategy,
execution simulator, memory store, and trajectory logger remain unchanged.

For an investor-facing extension, run `examples/retail_planner_demo.py`. It
uses a separate planning layer with investor profiles, goals, suitability
checks, paper rebalance instructions, and futures margin estimates.

## Quality Check

```bash
python -m pytest tests -q
python scripts/run_showcase.py --reuse-existing
python scripts/check_release_readiness.py
```

[codespaces-quickstart]: https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=weich97/TreLLM-public
[binder-quickstart]: https://mybinder.org/v2/gh/weich97/TreLLM-public/main?filepath=notebooks%2Ftradearena_5min_colab.ipynb
[nbviewer-quickstart]: https://nbviewer.org/github/weich97/TreLLM-public/blob/main/notebooks/tradearena_5min_colab.ipynb
