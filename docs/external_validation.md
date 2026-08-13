# External Validation Protocol

External validation is the evidence that makes TreLLM more than a
maintainer-run demo. A validation report should let another reader reproduce
the same result or understand why the result diverged.

If you want the shortest path, start with
[`external_validation_quickstart.md`](external_validation_quickstart.md). This
protocol page explains the evidence rules in more detail.

## What Counts As External Validation?

External validation must come from a person or organization outside the
maintainer set. It can be:

- a deterministic smoke-test reproduction;
- a redacted LLM benchmark row for the TradeArena leaderboard;
- a historical-market replay using documented data sources;
- a quote/fill-log execution calibration report;
- a critique that finds a reproducibility, documentation, or methodology issue.

Owner-authored examples and internal paper artifacts do not count as external
validation.

## Minimal Reproduction

Run the no-key path first:

```bash
git clone https://github.com/weich97/TreLLM-public.git
cd TreLLM
python -m pip install -e ".[dev]"
tradearena --benchmark tradearena-core
python scripts/check_release_readiness.py
```

For the v0.2 no-key reproduction pack, run:

```bash
python scripts/run_external_reproduction_pack.py
```

This writes `outputs/reproduction/v0_2/manifest.json` with commit, Python
version, commands, output hashes, trajectory hash, and whether live APIs,
downloaded market data, or private fills were used.

For the v0.3-protocol no-key reproduction pack, run:

```bash
python scripts/run_v03_external_reproduction_pack.py \
  --environment-class linux
```

Use `windows_or_macos`, `linux`, or `colab_or_binder` for the environment
class. Independent reviewers who want the report to count toward the v0.3 gate
should add:

```bash
--report-author-type independent --independent-reviewer
```

This writes `outputs/reproduction/v0_3/manifest.json` with the v0.3
`protocol_id`, environment class, command logs, artifact hashes, and a
trajectory reproducibility hash. The gate still requires three accepted
independent reports across the required environment classes.

Validate the report before submitting it:

```bash
python scripts/validate_reproduction_report.py outputs/reproduction/v0_2/manifest.json
```

For v0.3 reports, validate:

```bash
python scripts/validate_reproduction_report.py outputs/reproduction/v0_3/manifest.json
python scripts/build_v03_external_reproduction_gate.py \
  --report-dirs outputs/reproduction/v0_3
```

Build an issue-ready summary bundle:

```bash
python scripts/build_external_validation_bundle.py \
  --manifest outputs/reproduction/v0_2/manifest.json \
  --markdown-output outputs/reproduction/v0_2/external_validation_bundle.md
```

This produces a compact environment, command, artifact-hash, and trajectory-hash
summary that can be pasted into issues #43-#45. The bundle is evidence for
reproducibility of the no-key path; it is not evidence that any model trades
profitably.

Report:

- commit hash or release tag;
- operating system and Python version;
- install command;
- exact commands;
- whether all checks passed;
- output paths and any deviations.

## Five Starter Validation Tasks

These are the preferred first external reports because each one is small,
reviewable, and directly improves the TreLLM evidence chain and TradeArena
leaderboard context.

| Task | Target time | Submit |
| --- | ---: | --- |
| [Run v0.2 reproduction pack on macOS](https://github.com/weich97/TreLLM-public/issues/43) | 1 hour | manifest, shell log, Python version, deviations |
| [Run v0.2 reproduction pack on Ubuntu](https://github.com/weich97/TreLLM-public/issues/44) | 1 hour | manifest, distro/Python/install notes, deviations |
| [Run v0.2 reproduction pack on Colab/Binder](https://github.com/weich97/TreLLM-public/issues/45) | 1 hour | notebook URL, runtime type, generated manifest, deviations |
| [Submit one deterministic baseline row](https://github.com/weich97/TreLLM-public/issues/46) | 1-2 hours | schema-valid manifest, registry diff, reproducibility hash |
| [Submit one quote/fill calibration mini-report](https://github.com/weich97/TreLLM-public/issues/47) | 2-3 hours | calibration JSON/Markdown, data source, venue, sample size, replay error |
| [Review one benchmark claim boundary](https://github.com/weich97/TreLLM-public/issues/48) | 1 hour | issue or PR mapping one claim to engineering, benchmark, or scientific evidence |

Do not summarize these as "community interest." They count only when the
commands, artifacts, and deviations are public enough for another reader to
audit.

## LLM Validation

For a live or cache-backed LLM row, submit a redacted benchmark manifest rather
than raw prompts or responses:

```bash
tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json
tradearena build-registry examples/benchmark_submissions
```

The manifest should include provider family, model display name, prompt mode,
risk-feedback mode, parse coverage, metrics, and a reproducibility hash. It
should not include raw provider text, API keys, private data, or account
information.

## Execution Calibration Validation

Execution realism needs quote/fill evidence. If you have private or licensed
fills, keep them outside Git and run:

```bash
python scripts/compare_execution_to_fills.py \
  --fills data/private/historical_fills.csv \
  --output docs/results/execution_fill_comparison.json \
  --markdown-output docs/results/execution_fill_comparison.md
```

A useful calibration report should name:

- asset universe and date range;
- venue or broker, if shareable;
- order type and reference price definition;
- sample size;
- residual mean, residual MAE, and residual max absolute bps;
- whether latency timestamps, spread observations, and bar volume were supplied;
- any reason the report cannot be made public.

## Submission Path

Open an issue using the external validation template or submit a pull request
with a redacted manifest under `examples/benchmark_submissions/`.

For reproduction reports, paste the output of
`outputs/reproduction/v0_2/external_validation_bundle.md` into the matching
issue. For benchmark rows or calibration reports, include the validating command
and attach only redacted artifacts.

Maintainers should review whether:

- the commands are reproducible;
- the artifact omits secrets and raw provider text;
- the data source and license are acceptable;
- the reported claim matches the evidence.

accepted validations can be linked from the TradeArena leaderboard registry or
release notes.
