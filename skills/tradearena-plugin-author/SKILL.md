# TreLLM Plugin Author Skill

## Purpose

Help a coding agent author or review one narrow TreLLM plugin without
changing runner orchestration.

## When To Use

Use this skill when the user asks for:

- a data, analyst, strategy, risk, execution, simulator, memory, or evaluator
  plugin;
- a plugin review;
- a deterministic plugin test;
- a plugin README or example.

Plugin output may support an engineering claim about extension behavior, but it
does not support a benchmark or scientific claim without reproducible evidence.

## Do Not Use This Skill For

- live trading features;
- broad runner rewrites;
- hidden global state;
- plugins that require secrets by default.

## Required Inputs

Locate:

- plugin type;
- protocol method names;
- minimal input and output examples;
- deterministic fixture or mock;
- expected test command.
- evidence labels if the plugin is used in a benchmark row.
- reproducibility metadata when the plugin changes benchmark behavior.

## Safety Boundary

Do not add live API calls as the default path. Do not commit raw prompts,
provider responses, broker credentials, private holdings, or private account
data. Keep plugins narrow and deterministic by default.

## Workflow

1. Identify plugin type: data, analyst, strategy, risk, execution, simulator,
   memory, or evaluator.
2. Read `docs/plugin_development.md` and `src/tradearena/core/interfaces.py`.
3. Implement only the required protocol boundary.
4. Add one deterministic test.
5. Add a README that states data/provider/security assumptions.
6. Run focused tests before broader quality gates.

## Output Contract

Return:

- Plugin Type
- Files Changed
- Protocol Implemented
- Determinism And Data Boundary
- Tests Added
- Security Notes
- Recommended Next Command

## Validation Commands

```bash
tradearena new-plugin --type risk --name max-drawdown-guard
python -m pytest tests/test_plugin_scaffold.py -q
python -m ruff check src scripts examples tests
```
