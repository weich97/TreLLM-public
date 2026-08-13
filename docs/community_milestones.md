# Community Milestones

These milestones are the intended GitHub milestone structure for the public
repository. They are documented here so the roadmap stays visible even when a
contributor is reading the source tree rather than the GitHub Issues UI.

## v0.1.1: Reproducibility Polish

Goal: make the first public TreLLM audit release easier to cite, reproduce,
and review while keeping TradeArena benchmark rows comparable.

- Add a high-spread execution stress preset with CSV, JSON, and SVG artifacts.
- Reflow public Markdown files for readable diffs.
- Add benchmark provenance and limitations blocks.
- Keep `https://weich97.github.io/TreLLM/` as a stable root landing page.
- Smoke-check the Colab and Codespaces paths.
- Keep release-readiness checks in CI.

## v0.2.0: TradeArena Leaderboard Registry

Goal: let external users submit comparable, redacted benchmark rows.

- Finalize `schemas/benchmark_submission.schema.json`.
- Add one example redacted benchmark submission.
- Build a static registry page from submitted manifests.
- Add one external baseline or scenario.
- Document review rules for provider-sensitive model outputs.
- Add external validation and paper-gap issue templates.
- Track accepted non-maintainer validation reports separately from
  maintainer-authored examples.

Initial implementation paths:

- `examples/benchmark_submissions/example_redacted_submission.json`
- `scripts/validate_benchmark_submission.py`
- `scripts/build_benchmark_registry.py`
- `docs/results/community_registry.md`

## Discussion Calls To Action

- Execution simulation: comment with the market-friction assumption you think
  matters most.
- Redacted benchmarks: comment with fields you would be comfortable sharing.
- Teaching or project use: post the scenario you want students or teammates to
  reproduce.
- New adapters: link the data, broker, or model interface you want TreLLM to
  support.
- External validation: reproduce a documented command and file the validation
  report template with commit, environment, commands, and artifacts.
