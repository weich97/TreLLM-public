# Related Work And Positioning

TreLLM is designed to complement, not replace, existing financial AI and agent
frameworks. Its niche is auditability, realistic execution, risk gates, and
replayable artifacts for financial-agent reliability: LLM trading agents, AI
portfolio-manager prototypes, and multi-agent finance systems. TradeArena is
the leaderboard and benchmark layer inside TreLLM.

## Trading-Agent Frameworks

### TradingAgents

TradingAgents focuses on multi-agent LLM trading workflows.

TreLLM is complementary: it focuses on replayable trajectories, risk-gate
intervention logs, execution realism, and benchmark artifacts.

### FinRobot

FinRobot focuses on financial analysis and equity-research agents.

TreLLM is a simulation, audit, and evaluation layer for decision traces
rather than an analyst-only assistant.

## Financial AI And Quant Platforms

### FinRL / FinRL-Meta

FinRL and FinRL-Meta focus on financial reinforcement learning environments and
benchmarks.

TreLLM can host quant or RL-style baselines, but centers LLM decision
chains, tool traces, risk reports, and realistic order simulation.

### FinGPT

FinGPT focuses on financial LLM data and adaptation.

TreLLM evaluates how model-backed agents behave under market constraints,
risk feedback, and execution friction.

### Qlib

Qlib focuses on quantitative investment research workflows.

TreLLM is lighter-weight and agent-native, with emphasis on reproducible
audit logs and execution-aware evaluation.

## Backtesting And Data Tooling

### Backtrader / Zipline

Backtrader and Zipline are classic backtesting engines.

TreLLM adds agent traces, risk lifecycle reports, memory state, and
LLM-specific replay metadata.

### Nautilus Trader / QuantConnect LEAN

Nautilus Trader and QuantConnect LEAN are mature trading and backtesting
systems with richer execution, brokerage, and venue abstractions than
TreLLM's current prototype. TreLLM's execution layer should therefore
be read as an auditable stress model unless its parameters are calibrated
against quote and fill logs.

### Execution And Market-Impact Literature

TreLLM's spread, participation, slippage, and impact surfaces are aligned
with standard market-microstructure calibration questions: Kyle-style order-flow
impact, Almgren-Chriss optimal execution, direct estimation of equity market
impact from fills, and empirical studies of how markets absorb supply and
demand. The project does not claim that its default parameters reproduce those
models; they are explicit stress assumptions until a fill-log comparison is
provided.

### OpenBB

OpenBB focuses on financial data and research tooling.

TreLLM can consume market data adapters, but its core contribution is the audit
protocol. The TradeArena leaderboard layer keeps the evaluation traceable.

## General Agent Orchestration

### LangGraph / AutoGen / CrewAI

These systems focus on general agent orchestration.

TreLLM provides finance-specific schemas, risk gates, execution simulators,
and trading-agent metrics.

## Why This Distinction Matters

Many trading-agent demos report a return curve. That is not enough for LLM
agents because the result depends on prompt version, retrieved context, tool
outputs, memory state, model version, market timestamp, risk constraints,
portfolio state, execution simulator state, and random seed.

TreLLM asks a different question:

> Can the agent's decision be replayed, audited, risk-checked, and compared
> under realistic execution assumptions?

This makes TreLLM useful alongside stronger forecasting, research, and
RL systems. Those systems can plug into TreLLM as analysts, strategies, risk
modules, or baselines while the TradeArena leaderboard layer keeps the
evaluation traceable.
