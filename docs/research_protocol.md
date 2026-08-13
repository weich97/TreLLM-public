# TreLLM Research Protocol

TreLLM is meant to support system-style AI finance papers. A valid experiment
should preserve enough evidence to reconstruct what the agent observed, why it
acted, which risk constraints were triggered, how execution changed the
intended trade, and how the portfolio evolved afterward. TradeArena names the
leaderboard and benchmark layer for comparable public artifacts.

## Required Artifacts

- Experiment config, universe, seed, and task metadata.
- Component names and versions.
- Observation summaries with timestamped market/news/macro data.
- Analyst signals and rationales.
- Strategy decisions and target weights.
- Structured `RiskReport` objects.
- Orders, fills, pending orders, rejected orders, and partial fills.
- Portfolio states after each step.
- Memory events, theses, trade journal entries, and failure cases.
- Evaluation metrics and ablation labels.

## Challenge Coverage

1. Reproducibility:
   Record prompts, tool calls, data timestamps, memory state, decisions, and fills as a full trajectory.

2. Evaluation:
   Report performance, drawdown, volatility, turnover, cost sensitivity, behavioral stability, and reasoning consistency.

3. Execution realism:
   Compare realistic execution against ideal execution to estimate backtest over-optimism.

4. Risk control:
   Run with and without the risk gate, and report blocked/clipped decisions plus failed checks.

5. Extensibility:
   Replace one plugin at a time: data, analyst, strategy, memory, risk, execution, or evaluator.

6. Auditability:
   Use risk and execution reports to explain why a trade happened and what happened after submission.

7. Data leakage:
   Use `BenchmarkTask` and `DataLeakagePolicy` metadata to declare time splits, prompt freezing, and future-news restrictions.

8. Agent organization:
   Compare single-agent, committee, debate, hierarchy, and risk-manager architectures under the same task.

## Suggested Experiments

- LLM comparison: same task, same tools, different LLM analyst/strategy plugins.
- Organization comparison: single agent vs analyst committee vs analyst-strategy-risk hierarchy.
- Risk ablation: risk gate enabled vs disabled.
- Execution ablation: ideal fills vs realistic execution.
- Memory ablation: stateless vs episodic memory vs thesis tracking.
- Cost sensitivity: sweep commission, slippage, latency, and liquidity participation limits.
- Failure analysis: inspect worst drawdowns and risk violations from audit logs.

## Artifact Generation

Use:

```bash
python -m tradearena.cli --paper-output outputs/tradearena_paper --periods 120 --symbols SYN,ALT,DEF --paper-seeds 3,7,11
```

The output directory contains publication-oriented CSV/Markdown tables, SVG charts, raw per-case trajectories, execution event logs, risk event logs, and a machine-readable summary.
