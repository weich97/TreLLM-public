# TreLLM Trajectory Audit Skill

## Purpose

Audit a TreLLM trajectory from agent intent to risk-gated decision, order,
fill, portfolio state, and post-trade attribution.

## When To Use

Use this skill when the user provides or references:

- a trajectory JSON;
- a benchmark artifact;
- an audit report;
- an agent autopsy dashboard;
- a question about risk edits, rejected orders, partial fills, latency,
  slippage, or reproducibility.

## Do Not Use This Skill For

- live trading;
- buy or sell advice;
- alpha generation;
- model profitability claims from one run;
- broker-specific execution claims without quote/fill evidence.

## Required Inputs

Locate or ask for:

- trajectory path;
- commit or release tag;
- command that generated the trajectory;
- case name when the file is a multi-case artifact;
- evidence labels and execution mode.

## Safety Boundary

Do not request credentials, account statements, private holdings, raw provider
logs, or private fills. Do not recommend real trades. Treat the skill as an
audit workflow, not as a trading assistant.

## Workflow

1. Record trajectory path, commit/tag, command, and hash when available.
2. Inspect each step in this order: observation, signals, raw decisions,
   approved decisions, orders, fills, risk reports, execution report, portfolio,
   memory events, reproducibility state, and agent trace.
3. Compare raw decisions with approved decisions.
4. Flag low-confidence bets, target-weight clipping, gross-exposure scaling,
   drawdown kill switch activation, turnover warnings, rejected orders,
   partial fills, pending orders, slippage or latency violations, and
   rationale/decision mismatch.
5. Classify the supported claim as engineering, benchmark, or scientific.
6. State what evidence is missing before making conclusions.

## Output Contract

Return these sections:

- Summary
- Artifact And Reproducibility
- Decision-To-Risk Diff
- Risk Findings
- Execution Findings
- Portfolio Impact
- Claim Boundary
- Missing Evidence
- Recommended Next Command

## Validation Commands

```bash
tradearena hash-run <trajectory.json>
tradearena replay <trajectory.json> --case <case> --step <step> --json
python scripts/run_failure_autopsy.py --trajectory <trajectory.json>
```
