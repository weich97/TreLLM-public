# TreLLM Claim Boundary Review Skill

## Purpose

Review README text, papers, benchmark cards, leaderboard rows, and release notes
for claim overreach.

## When To Use

Use this skill when a user asks whether a TradeArena statement is supported by
the available artifacts or whether wording should be weakened.

## Do Not Use This Skill For

- promoting model profitability;
- turning benchmark results into investment advice;
- hiding missing evidence.

## Required Inputs

Locate:

- the claim text;
- benchmark row or artifact path;
- evidence labels;
- trajectory or manifest hash;
- reproducibility metadata;
- data source and execution mode;
- whether live APIs, cached providers, private fills, or redacted prompts were
  used.

## Safety Boundary

Do not upgrade a claim class without evidence. When evidence is missing, prefer
weaker wording over speculation.

## Workflow

1. Quote or summarize the claim.
2. Classify it as engineering, benchmark, or scientific.
3. List supporting evidence.
4. List missing evidence.
5. Assign evidence labels.
6. Recommend weaker wording when the claim is not fully supported.

## Output Contract

Return:

- Claim
- Claim Class
- Supported Evidence
- Missing Evidence
- Evidence Labels
- Required Weakening
- Recommended Wording
- Recommended Next Command

## Validation Commands

```bash
python scripts/validate_benchmark_spec.py
python scripts/build_benchmark_page.py
python scripts/check_release_readiness.py
```
