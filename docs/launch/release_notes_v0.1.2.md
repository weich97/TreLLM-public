# v0.1.2: PyPI-Ready Benchmark Registry Release

TreLLM v0.1.2 is the first PyPI-ready release under the
`tradearena-benchmark` distribution name. The import namespace and CLI remain
`tradearena`.

## Highlights

- Prepared the installable PyPI distribution `tradearena-benchmark`.
- Promoted `tradearena` as the canonical module and CLI entrypoint.
- Added redacted benchmark submission validation and community registry
  generation.
- Added reproducibility hashes for benchmark and trajectory artifacts.
- Added demo artifact contracts so showcase claims are machine-checkable.
- Expanded CI to Python 3.10, 3.11, and 3.12 with Ruff, compile checks, tests,
  CodeQL, release packaging, and Pages smoke tests.
- Added security, governance, code-owner, and maintainer metadata for external
  contributors.

## Install

```bash
python -m pip install tradearena-benchmark
tradearena --benchmark tradearena-core
```

## Validate A Submission

```bash
tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json
tradearena build-registry examples/benchmark_submissions --output docs/results/community_registry.md
```

## Notes

The shorter `tradearena` distribution name is already occupied on PyPI by an
unrelated project. This repository therefore publishes as
`tradearena-benchmark` while keeping `import tradearena` and the `tradearena`
CLI.
