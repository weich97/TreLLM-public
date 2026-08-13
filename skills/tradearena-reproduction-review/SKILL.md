# TreLLM Reproduction Review Skill

## Purpose

Review a reproduction pack, benchmark row, or external validation report for
hash stability and artifact completeness.

## When To Use

Use this skill when a user asks to verify:

- a deterministic reproduction pack;
- a `hash-run` output;
- a replay command;
- a benchmark submission manifest;
- a fresh-environment run on macOS, Linux, Colab, Binder, or CI.

## Do Not Use This Skill For

- certifying live-provider determinism;
- claiming model profitability;
- accepting artifacts with missing commands or hashes.

## Required Inputs

Locate:

- commit or release tag;
- Python version and OS/platform;
- command log;
- trajectory reproducibility hash;
- file SHA-256 hashes;
- whether live APIs, downloaded data, private fills, or broker data were used;
- dashboard/report artifact paths.
- evidence labels attached to the benchmark row.

## Safety Boundary

Do not expose credentials, provider raw text, private holdings, or private fill
logs. Redact local paths when needed for public reports.

## Workflow

1. Check commit/tag and package version.
2. Check Python and platform metadata.
3. Verify command log and return codes.
4. Verify trajectory and artifact hashes.
5. Confirm whether live APIs or downloaded data were used.
6. Confirm that dashboard HTML and JSON artifacts exist and are non-empty.
7. Classify the reproduction status as match, mismatch, incomplete, or blocked.

## Output Contract

Return:

- Summary
- Environment
- Commands Checked
- Hashes Checked
- Artifact Completeness
- Live Or Private Inputs
- Reproduction Status
- Missing Evidence
- Recommended Next Command

## Validation Commands

```bash
python scripts/run_external_reproduction_pack.py --output-dir outputs/reproduction/v0_2_external
tradearena hash-run <trajectory.json>
tradearena replay <trajectory.json> --case <case> --step <step> --json
```
