# External Validation Quickstart

TreLLM needs external evidence: reports from people who are not maintainers and
who can show exactly what they ran, what artifacts were produced, and where the
result diverged or matched. TradeArena leaderboard rows are one reviewable
submission path, but reproduction and calibration reports are equally
important. This page is the shortest path from a fresh clone to a useful
validation issue.

## Pick One Path

| Time | Best if you have... | Do this | Submit |
| ---: | --- | --- | --- |
| 1 hour | A fresh macOS, Ubuntu, Colab, or Binder environment | Run the no-key reproduction pack | Issues [#43](https://github.com/weich97/TreLLM-public/issues/43), [#44](https://github.com/weich97/TreLLM-public/issues/44), [#45](https://github.com/weich97/TreLLM-public/issues/45) |
| 1-2 hours | Basic Python comfort | Submit one deterministic baseline row | [Baseline row quickstart](deterministic_baseline_submission_quickstart.md), Issue [#46](https://github.com/weich97/TreLLM-public/issues/46) |
| 2-3 hours | Market microstructure or broker-fill context | Submit one quote/fill calibration mini-report | Issue [#47](https://github.com/weich97/TreLLM-public/issues/47) |
| 1 hour | A careful reviewer mindset | Review one public claim boundary | [Claim review quickstart](claim_boundary_review_quickstart.md), Issue [#48](https://github.com/weich97/TreLLM-public/issues/48) |

If you are unsure where to start, run the no-key reproduction pack. It requires
no model API keys, private market data, or broker credentials.

## No-Key Reproduction Pack

```bash
git clone https://github.com/weich97/TreLLM-public.git
cd TreLLM
python -m pip install -e ".[dev]"
python scripts/validate_benchmark_spec.py benchmarks/v0.2/spec.json
python scripts/run_external_reproduction_pack.py
python scripts/check_release_readiness.py
```

The main output is:

```text
outputs/reproduction/v0_2/manifest.json
```

Validate it:

```bash
python scripts/validate_reproduction_report.py outputs/reproduction/v0_2/manifest.json
```

Build a paste-ready issue summary:

```bash
python scripts/build_external_validation_bundle.py \
  --manifest outputs/reproduction/v0_2/manifest.json \
  --markdown-output outputs/reproduction/v0_2/external_validation_bundle.md
```

Paste the generated Markdown into the matching external reproduction issue.

## What To Report

Every useful validation report should include:

- commit hash or release tag;
- operating system, CPU architecture, and Python version;
- install command;
- exact commands run;
- whether the working tree was clean;
- output paths and hashes;
- whether live APIs, downloaded market data, private fills, or broker data were
  used;
- any failed command, traceback, warning, or deviation.

## What Counts

Counts as external validation:

- a reproducible no-key report with manifest and command log;
- a schema-valid redacted TradeArena leaderboard row;
- a quote/fill calibration report with data source, sample size, residuals, and
  replay error;
- a claim-boundary critique that maps one public claim to evidence and a
  verification command; use
  [`claim_boundary_review_quickstart.md`](claim_boundary_review_quickstart.md)
  for the review checklist.

Does not count by itself:

- screenshots without commands;
- "works for me" comments without manifest or hashes;
- raw LLM prompts or responses pasted into issues;
- private fills, holdings, or account data committed to Git;
- live-trading results or investment recommendations.

## Why This Matters

TreLLM should not claim community validation until people outside the
maintainer set have reproduced commands, submitted benchmark rows, calibrated
execution assumptions, or challenged public claims. External validation is how
the project separates engineering demos from benchmark evidence.

For the full protocol, see [`external_validation.md`](external_validation.md).
