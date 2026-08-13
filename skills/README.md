# TreLLM Agent Skills

TreLLM skills are workflow templates for humans, reviewers, and coding agents
working with TreLLM system artifacts and TradeArena leaderboard artifacts. They
are not benchmark-agent prompts, trading strategies, broker tools, or
investment-advice modules.

Use these skills to audit trajectories, review risk gates, classify claim
boundaries, reproduce benchmark rows, inspect execution calibration evidence,
and author narrow plugins.

## Boundary

- Skills must not be injected into a benchmarked LLM agent unless the skill
  content is recorded as part of the agent configuration and reproducibility
  manifest.
- Skills must not ask for API keys, broker credentials, account statements,
  private holdings, or raw provider logs.
- Skills must report missing evidence before making a benchmark or scientific
  conclusion.
- Skills should prefer existing TreLLM validation commands over ad hoc
  scripts.

## Included Skills

| Skill | Primary use |
| --- | --- |
| `tradearena-trajectory-audit` | Inspect intent-to-risk-to-execution trajectories |
| `tradearena-risk-gate-review` | Review risk budget edits, blocks, and violations |
| `tradearena-execution-calibration` | Classify stress, calibrated, quote-replay, and fill-replay evidence |
| `tradearena-claim-boundary-review` | Prevent engineering, benchmark, and scientific claim drift |
| `tradearena-reproduction-review` | Review reproduction packs, hashes, manifests, and artifacts |
| `tradearena-plugin-author` | Author or review narrow TreLLM plugins |

Run the contract checks:

```bash
python scripts/validate_skill_contract.py skills
python scripts/build_skill_index.py skills --output docs/agent_skills_index.md
python scripts/score_skill_task.py --tasks-dir examples/skill_tasks --validate-only
```

Small evaluation tasks live in `examples/skill_tasks/`. They check whether a
reviewer or coding agent can audit trajectories, respect claim boundaries, and
write plugins without turning the skill into a trading prompt.
