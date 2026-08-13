# TreLLM Execution Calibration Skill

## Purpose

Classify execution evidence as stress-only, calibrated, quote replay, or fill
replay, and state which transaction-cost claims are supported.

## When To Use

Use this skill when the user provides:

- an `ExecutionReport`;
- a calibration JSON or Markdown report;
- quote, Level-2, or fill replay data;
- a benchmark row with execution evidence labels;
- a question about spread, latency, participation, slippage, or market impact.

## Do Not Use This Skill For

- broker-grade transaction-cost claims without quote/fill provenance;
- live-order routing;
- execution predictions from OHLCV-only data.

## Required Inputs

Locate:

- execution mode: stress, calibrated, quote replay, or fill replay;
- quote source, fill source, venue, symbol universe, and date range;
- fee schedule or commission assumption;
- fitted parameters and residuals;
- artifact hashes and commands.
- reproducibility metadata when the calibration is tied to a benchmark row.

## Safety Boundary

Do not request broker credentials or private fills. If private fills are used
locally, report only aggregate statistics and redacted provenance.

## Workflow

1. Identify the execution mode and assumption class.
2. Check whether quote, Level-2, or fill provenance is attached.
3. Inspect spread, latency, participation, slippage, and impact parameters.
4. Compare calibrated replay error against stress-only replay error when
   available.
5. Assign evidence labels such as `stress-only`, `quote-calibrated`, or
   `fill-replay-validated`.
6. State unsupported claims explicitly.

## Output Contract

Return:

- Summary
- Execution Mode
- Provenance Inspected
- Parameter Sources
- Replay Error Or Residuals
- Evidence Labels
- Supported Claims
- Unsupported Claims
- Recommended Next Command

## Validation Commands

```bash
python scripts/calibrate_quote_fill_model.py
python scripts/compare_execution_to_fills.py
python scripts/check_release_readiness.py
```
