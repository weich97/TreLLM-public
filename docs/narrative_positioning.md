# Narrative Positioning

TreLLM should be described as an early-stage live-ready audit and control system
for agent reliability in financial decision systems, not only as a trading
benchmark. TradeArena should be described as the public leaderboard module and
benchmark-card surface. Trading remains the main experimental domain because it
exposes a compact chain from observation to intent, risk control, execution,
broker handoff, reconciliation, and realized state.

## Core Narrative

Use three phrases consistently:

- Agent Reliability: whether autonomous financial agents remain stable,
  calibrated, and inspectable under stress.
- Risk-aware AI Systems: whether structured risk reports can act as external
  constraints and feedback for model behavior.
- Intent-to-Execution Audit: how proposed actions change as they pass through
  risk gates, order conversion, execution frictions, broker review, fills, and
  portfolio state.
- Live-Ready Control Plane: how the same audit trail can support offline
  research, paper sandboxes, human approval, and future supervised live
  adapters without making live submission the default path.

## Scope

TreLLM currently implements offline and paper/sandbox financial-agent
experiments, plus an export-only broker review surface. It can support:

- LLM-assisted financial-agent evaluation;
- AI portfolio-manager prototypes;
- multi-agent finance systems that aggregate analyst, planner, memory, and
  execution modules;
- broker-review and paper-sandbox workflows that preserve risk and approval
  evidence;
- deterministic and classical baselines used as controls.

It should not be described as an unattended live trading bot, a profitability
engine, or a broker-grade simulator. Claims should stay tied to reproducible
trajectories, redacted manifests, explicit execution assumptions, and the
current integration stage from [`live_trading_readiness.md`](live_trading_readiness.md).

## Preferred One-Liner

TreLLM is an early-stage live-ready audit and control system for moving autonomous
financial-agent intent through risk controls, execution evidence, broker
review, and reproducible accountability. TradeArena is the public leaderboard
for comparing auditable runs from that system.
