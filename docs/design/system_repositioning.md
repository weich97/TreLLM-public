# TreLLM System Repositioning Design

## Decision

The repository will use **TreLLM** as the external system identity for the
LLM-driven trading audit and control system. **TradeArena** will remain as the
name of the public leaderboard, benchmark, and ranking surface. The Python
package, import path, and CLI command remain `tradearena` during this migration
so existing installs, notebooks, GitHub Pages links, and paper references keep
working.

This is a phase-2 repositioning, not a full package rename.

## Problem

The current repository presents too much of the project as a benchmark arena.
That is useful for ranking auditable agent runs, but it understates the system
work: LLM-agent trace capture, risk gates, execution calibration, broker-review
handoffs, approval artifacts, response reconciliation, redaction, provenance,
and live-readiness controls. The public name should make the system function
clear before a reader sees the leaderboard.

## Naming Model

- **TreLLM**: the system. It is an LLM-driven trading audit and control system.
- **TradeArena**: the leaderboard and benchmark surface inside TreLLM.
- **tradearena**: the compatibility package, CLI, and import path for the
  current public release.

Canonical first-use wording:

> TreLLM is an LLM-driven trading audit and control system. TradeArena is its
> public leaderboard for ranking auditable agent runs.

Short-form wording:

> TreLLM records model intent, risk edits, execution effects, broker handoffs,
> approvals, and replayable audit evidence.

## Migration Scope

Phase 1 should update public-facing narrative without breaking APIs:

- README title area, first paragraphs, badge labels, and documentation map.
- `pyproject.toml` description and project URLs text, while keeping package
  name `tradearena-benchmark`.
- GitHub repository description text where it is controlled by tracked files.
- Documentation pages that currently frame the whole project as a benchmark.
- Generated site copy where source files live in the repository.
- Tests that protect the new identity split.

Phase 1 should not rename:

- GitHub repository URL `weich97/TreLLM-public`.
- Python package name `tradearena-benchmark`.
- Python import package `tradearena`.
- CLI command `tradearena`.
- Existing artifact schemas that already use `tradearena_*`.
- Published arXiv or historical benchmark result identifiers.

## README Structure

The README should present this order:

1. TreLLM system identity and one-sentence value proposition.
2. Safety boundary: not investment advice, no default live order submission.
3. System lifecycle: observe, plan, risk review, execution, audit, broker
   review, reconciliation.
4. TradeArena leaderboard as one module, not the whole product identity.
5. Contributor paths: validation reports, calibration mini-reports, broker
   safety contracts, and claim reviews.

The phrase "benchmark" remains valid only when describing a benchmark card,
leaderboard, registry row, or frozen comparison protocol. It should not be the
primary description of TreLLM.

## Documentation Rules

New or edited docs should follow these rules:

- Use "TreLLM" for system-level architecture, safety, live-readiness, and audit
  workflows.
- Use "TradeArena leaderboard" or "TradeArena benchmark" for ranking and
  benchmark outputs.
- Use `tradearena` only for commands, package installation, imports, schema IDs,
  and compatibility notes.
- Avoid implying that benchmark rank proves profitable trading ability.
- Keep all broker-facing copy tied to human approval, account mode, redaction,
  bounded scope, and response reconciliation.

## Compatibility Strategy

The public command remains:

```bash
tradearena --benchmark tradearena-core
```

Docs should explain that the command name is retained for release
compatibility. A future major release may add an alias after the TreLLM identity
settles, but this phase does not introduce a new CLI command.

## Tests And Gates

Add or update tests that prove:

- README includes the TreLLM system identity.
- README describes TradeArena as the public leaderboard/ranking surface.
- README still documents the `tradearena` compatibility command.
- README and docs do not describe the whole project only as a benchmark.
- Existing demo artifacts, release-readiness checks, and benchmark registries
  still validate.

Every implementation batch should run:

```bash
git -c safe.directory=D:/TreadeArena diff --check
python -m ruff check src scripts examples tests
python -m mypy
python -m compileall src scripts examples tests -q
python scripts/validate_demo_artifacts.py
python scripts/check_release_readiness.py
python -m pytest tests -q --cov=tradearena --cov-report=xml --cov-report=term-missing
```

For documentation-only batches, targeted README/doc tests may run first, but a
full verification pass is still required before pushing to `main`.

## First Implementation Batch

The first implementation batch should be intentionally narrow:

- Update README first-screen identity from TradeArena-as-project to
  TreLLM-as-system.
- Add a short "Name And Compatibility" section explaining the TreLLM,
  TradeArena, and `tradearena` split.
- Add README tests for that identity split.
- Update `pyproject.toml` description only if release-readiness checks stay
  green.

Broader docs can follow after the README establishes the new public identity.
