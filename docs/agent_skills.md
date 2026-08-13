# TreLLM Agent Skills

TreLLM agent skills are repository workflow templates for audit,
reproduction, execution calibration, claim-boundary review, and plugin authoring.
They are deliberately outside `src/tradearena` so they do not become runtime
trading features.

## Positioning

Use skills to help a human reviewer or coding agent:

- inspect a trajectory from raw intent to risk-gated decision, order, fill, and
  portfolio effect;
- review risk-gate edits and violations;
- classify execution evidence as stress-only, calibrated, quote replay, or fill
  replay;
- weaken claims that outrun their evidence;
- verify reproduction packs, hashes, manifests, and dashboard artifacts;
- author or review narrow plugins.

Do not use skills as stock-picking prompts, profit-maximization systems, broker
connectors, or live-trading assistants.

## Benchmark Boundary

Skills should not be injected into a benchmarked LLM agent by default. If a
benchmark run uses a skill as part of the agent prompt or retrieval context,
record it in the reproducibility manifest, retrieved-document list, or prompt
version. Otherwise the benchmark row is not comparable to runs that did not use
the skill.

## Safety Boundary

Skills must not request or expose:

- API keys;
- broker credentials;
- account statements;
- private holdings;
- raw provider prompts or responses unless they are explicitly public;
- private fill logs unless the user says local analysis is permitted.

Every skill must report missing evidence before making benchmark or scientific
claims.

## Included Skills

The generated index is tracked in
[`docs/agent_skills_index.md`](agent_skills_index.md). The source directories
live under [`skills/`](../skills/).

| Skill | Use |
| --- | --- |
| `tradearena-trajectory-audit` | Audit a trajectory step by step |
| `tradearena-risk-gate-review` | Inspect risk budgets, edits, and violations |
| `tradearena-execution-calibration` | Review execution evidence and unsupported cost claims |
| `tradearena-claim-boundary-review` | Classify claims and recommend weaker wording |
| `tradearena-reproduction-review` | Review manifests, hashes, commands, and artifacts |
| `tradearena-plugin-author` | Author or review a narrow plugin with tests |

## Validation

Run:

```bash
python scripts/validate_skill_contract.py skills
python scripts/build_skill_index.py skills --output docs/agent_skills_index.md --check
python scripts/score_skill_task.py --tasks-dir examples/skill_tasks --validate-only
python scripts/score_skill_task.py --tasks-dir examples/skill_tasks --answers-dir examples/skill_task_answers/reference
```

The validator checks that every skill has a purpose, required inputs, safety
boundary, workflow, output contract, validation commands, resources, and
claim-boundary language.

## Skill Task Suite

Small evaluation tasks live in [`examples/skill_tasks/`](../examples/skill_tasks/).
They test whether a reviewer or coding agent can:

- find risk-gate and execution mismatches;
- classify execution evidence correctly;
- weaken unsupported claims;
- propose deterministic plugin tests;
- avoid trading advice.

The suite is described as a financial-audit agent benchmark in
[`docs/financial_audit_agent_benchmark.md`](financial_audit_agent_benchmark.md).
It intentionally asks whether LLMs can audit, reproduce, and bound claims, not
whether they can pick stocks.

The generated matrix is tracked in
[`docs/results/skill_task_matrix.md`](results/skill_task_matrix.md).
Provider-backed challenge matrices are tracked in
[`docs/results/poe_skill_task_matrix.md`](results/poe_skill_task_matrix.md) and
[`docs/results/poe_skill_challenge_matrix.md`](results/poe_skill_challenge_matrix.md).
The challenge suite under `examples/skill_tasks_challenge/` intentionally
stresses adversarial claim wording, public-artifact redaction, reproduction
honesty, and execution-calibration boundaries.

The task suite measures TreLLM-specific financial-audit ability rather than
trading ability:

| Ability | Measurable task | Scoring |
| --- | --- | --- |
| Audit accuracy | Find risk edits, rejected orders, and partial fills | Rubric match |
| Risk-gate understanding | Detect complete and missing risk-report fields | Checklist score |
| Execution-boundary awareness | Avoid calling stress simulation real transaction-cost evidence | Hard fail |
| Claim discipline | Label engineering, benchmark, and scientific claims | Label accuracy |
| Reproduction awareness | Report commit, hash, command, artifact path, and data-source flags | Field coverage |
| Plugin engineering | Write a narrow plugin plan with deterministic tests | Test/review score |
