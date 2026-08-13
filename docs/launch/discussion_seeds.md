# Discussion Seeds

Use these after enabling GitHub Discussions.

## General: What Should A Reproducible Financial-Agent Trajectory Include?

Prompt:

```text
TreLLM currently records observation, signals, proposed decisions, approved
decisions, risk reports, orders, fills, portfolio state, memory events,
execution simulator state, and random seed.

What fields would you add before trusting a financial-agent reliability benchmark?

Call to action:

Reply with one field you would require in a public leaderboard submission.
```

## Ideas: Execution Realism Presets

Prompt:

```text
Which execution assumptions matter most for financial-agent evaluation:
slippage, latency, order participation, partial fills, rejected orders, market
impact, spread, or something else?

Call to action:

If you work on execution simulation, comment with the assumption you think
most often changes the conclusion of a backtest.
```

## Q&A: Redacted Leaderboard Submissions

Prompt:

```text
We want community leaderboard submissions without exposing raw provider prompts or
responses. What should a redacted manifest include to be useful but safe?

Call to action:

Reply with the fields you would be comfortable sharing in a public leaderboard
row.
```

## Ideas: Planning vs Live Trading Boundary

Prompt:

```text
The retail planning sandbox is offline by default and requires human approval.
What is the safest extension path for planning, paper trading, broker-review
exports, and future supervised live adapters?

Call to action:

If you use TreLLM in a class, project, or internal evaluation, post the
scenario you want to reproduce.
```
