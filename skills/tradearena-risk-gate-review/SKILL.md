# TreLLM Risk Gate Review Skill

## Purpose

Review TreLLM risk-manager behavior without treating return as the primary
outcome.

## When To Use

Use this skill when the user asks about:

- risk-gate edits, blocks, clips, or violations;
- `MaxPositionRiskManager` configuration;
- drawdown kill switch behavior;
- in-trade participation, latency, or slippage monitoring;
- post-trade risk attribution.

## Do Not Use This Skill For

- live position sizing;
- investment recommendations;
- profitability claims from a single risk report.

## Required Inputs

Locate:

- `RiskBudget` or risk-manager config;
- raw and approved decisions;
- risk reports and violations;
- execution reports when reviewing in-trade monitoring;
- portfolio equity and memory events when reviewing drawdown behavior.
- evidence labels and reproducibility metadata when reviewing a benchmark row.

## Safety Boundary

Do not advise how to bypass a risk gate. Do not ask for private accounts or
broker data. If private fills are needed, analyze them only locally and report
redacted aggregate findings.

## Workflow

1. Identify the active risk manager and risk budget.
2. Check `max_abs_weight`, `min_confidence`, `max_gross_exposure`,
   `max_single_step_turnover`, `max_order_participation`,
   `max_latency_steps`, `max_slippage_bps`, `max_drawdown`,
   `drawdown_lookback`, and `drawdown_de_risk_weight`.
3. Compare raw decisions to approved decisions.
4. Record every block, clip, scale, warning, and violation.
5. Verify whether the report severity matches the observed behavior.
6. Classify whether the finding supports an engineering, benchmark, or
   scientific claim.

## Output Contract

Return:

- Summary
- Risk Budget Inspected
- Decision Edits
- Violations
- In-Trade Findings
- Attribution Notes
- Claim Boundary
- Missing Evidence
- Recommended Next Command

## Validation Commands

```bash
python -m pytest tests/test_components.py tests/test_simulator_invariants.py -q
tradearena replay <trajectory.json> --case <case> --step <step> --json
```
