# TreLLM Project Metadata

Use this page for repository setup, project listings, and quickstart links.
TreLLM's public positioning is:

> We audit how autonomous financial agents move from intent to risk-aware,
> execution-realistic actions.

## Repository Positioning

Use this one-liner in GitHub, package metadata, and project listings:

```text
TreLLM is an LLM-driven trading audit and live-readiness control system; TradeArena is its public leaderboard for replayable trajectories, risk gates, execution calibration, and reproducible agent evidence.
```

Longer description:

```text
TreLLM turns every financial-agent decision into a traceable trajectory:
observation -> signal -> intended allocation -> risk gate -> order ->
fill/rejection -> portfolio state -> diagnostic report. TradeArena is the
public leaderboard layer for ranking comparable, reproducible agent runs.
The repository ships demos for audit reports, execution realism, risk gates,
extension paths, A-share rules, retail planning, and leaderboard artifacts.
```

## GitHub Topics

Recommended topics:

```text
llm-agents
llm-trading
trading-agents
trading-audit
financial-ai
quantitative-finance
agent-audit
agent-evaluation
risk-management
execution-simulation
portfolio-optimization
auditability
reproducible-research
leaderboard
ai-agents
execution-calibration
risk-gates
trellm
live-readiness
paper-trading
```

## Repository Checklist

- Publish GitHub release `v0.2.0`.
- Prepare patch release candidate `v0.2.1` from
  [`release_candidate_v0.2.1.md`](release_candidate_v0.2.1.md) after CI passes.
- Add the topics above.
- Verify GitHub About metadata with
  `python scripts/check_repository_metadata.py weich97/TreLLM-public`.
- Enable GitHub Discussions.
- Verify the GitHub Pages site at `https://weich97.github.io/TreLLM-public/`.
- Create the issue backlog in `docs/launch/issue_backlog.md`.
- Verify the browser-playable 3-minute demo and link it from the README.
- Verify the v0.2 external reproduction pack with at least three independent
  reports: macOS/Python 3.10, Linux/Python 3.11, and Colab or Binder.
  readiness contract before framing TreLLM as an publication-level agent evaluation
  system.
- Attach the execution calibration stability report, market-rule fixture report,
  and external validation bundle to the patch release notes.

## Core Demo Command

```bash
python -m pip install -e ".[dev]"
python scripts/run_showcase.py
```

Open:

```text
outputs/examples/index.html
```

Watch in the browser:

```text
https://weich97.github.io/TreLLM-public/demo_video.html
```

## Suggested Repository Description

```text
TreLLM is an LLM-driven trading audit and live-readiness control system; TradeArena is its public leaderboard for replayable trajectories, risk gates, execution calibration, and reproducible agent evidence.
```
