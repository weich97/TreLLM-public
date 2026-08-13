# TreLLM Skill Template

## Purpose

Use this skill to help a human or coding agent perform one narrow TreLLM
task: audit a trajectory, review a risk policy, reproduce a benchmark row,
calibrate execution assumptions, classify a claim, or author a small plugin.

This skill is not a trading strategy, investment advisor, broker connector, or
live-order execution tool.

## When To Use

Use this skill when the user asks to:

- inspect a TreLLM trajectory JSON;
- explain risk-gate edits, blocks, or violations;
- classify a benchmark claim;
- reproduce a deterministic benchmark artifact;
- compare stress, calibrated, quote-replay, or fill-replay execution
  assumptions;
- create or review a narrow TreLLM plugin.

## Do Not Use This Skill For

Do not use this skill to recommend buying, selling, shorting, or sizing real
positions.

## Required Inputs

Ask for or locate:

- repository commit or release tag;
- command used to generate the artifact;
- trajectory JSON, manifest, benchmark row, calibration report, or plugin diff;
- execution mode;
- evidence labels;
- whether live APIs, downloaded market data, private fills, or broker data were
  used.

## Safety Boundary

Never request or expose:

- API keys;
- broker credentials;
- account statements;
- private holdings;
- raw provider prompts or responses unless the user explicitly says they are
  public;
- private fill logs unless the user says they may be analyzed locally.

Never claim that a model can trade profitably from a single run.

## Workflow

1. Identify the artifact type.
2. Check reproducibility metadata.
3. Check claim class: engineering, benchmark, or scientific.
4. Inspect risk, execution, and audit fields.
5. Report missing evidence before making conclusions.
6. Provide exact commands that reproduce or validate the finding.

## Output Contract

Return:

- summary;
- evidence inspected;
- risk or execution findings;
- reproducibility status;
- claim-boundary status;
- missing evidence;
- recommended next command or patch.

## Validation Commands

Prefer existing TreLLM commands before inventing new scripts:

```bash
tradearena hash-run <trajectory.json>
tradearena replay <trajectory.json> --case <case> --step <step> --json
python scripts/run_external_reproduction_pack.py --output-dir outputs/reproduction/v0_2_external
python scripts/check_release_readiness.py
python scripts/validate_skill_contract.py
```
