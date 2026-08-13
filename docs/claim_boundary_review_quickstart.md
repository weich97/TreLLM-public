# Claim Boundary Review Quickstart

This track is for contributors who want to review whether a public TradeArena
claim is supported by the artifacts in the repository. It is useful for README
text, benchmark cards, leaderboard rows, release notes, blog posts, and paper
draft language.

The review goal is not to make the project sound smaller. The goal is to make
each statement easy to audit: what is proven by code, what is a benchmark result
under a frozen protocol, and what would need stronger evidence before becoming
a scientific claim.

## Pick A Claim

Good one-hour review targets:

| Target | Where to look | Useful question |
| --- | --- | --- |
| README summary claim | `README.md` | Does this describe an engineering feature, a benchmark result, or model skill? |
| Benchmark card caption | `docs/results/benchmark_v0_2.md` | Does the caption name execution mode and evidence labels? |
| Leaderboard row | `docs/results/community_registry.md` | Do tags match the row's `claim_scope` and `evidence_tier`? |
| Release or launch note | `docs/launch/` | Does it separate demo status from external validation? |
| Paper draft wording | linked paper artifact or issue text | Does the claim require independent replication or private fills? |

Start with one sentence or one table caption. A focused review is easier to
merge than a broad style critique.

## Claim Classes

Use the weakest class that still says something useful:

| Class | Supported when | Example wording |
| --- | --- | --- |
| Engineering | A command, artifact, schema, or hash proves the system can record or replay something. | "TreLLM records replayable trajectory artifacts with hashes; TradeArena can publish the resulting leaderboard evidence." |
| Benchmark | A frozen scenario, seeds or windows, baselines, risk settings, and execution assumptions support a comparison. | "Under the v0.2 stress protocol, risk gates and execution frictions change measured outcomes." |
| Scientific | Repeated runs, stable provider/version records, non-LLM baselines, confidence intervals, failure analysis, and independent replication support a model or agent-class conclusion. | "This model class is more reliable under financial decision stress." |

Scientific wording should be rare. Most public rows are engineering or
benchmark evidence until independent validation and stronger provider
provenance exist.

## Evidence Labels

Check the row or text for labels from [`evidence_labels.md`](evidence_labels.md).
Common weakening rules:

| Evidence label | Do not claim |
| --- | --- |
| `stress-only` | calibrated, broker-grade, or venue-wide transaction-cost prediction |
| `cached-provider` | live provider behavior unless the run says it was live |
| `redacted-prompt` | fully auditable model reasoning |
| `deterministic-baseline` | LLM model skill |
| missing `external-submitted` | community validation or independent adoption |
| missing `quote-calibrated` / `fill-replay-validated` | calibrated execution realism |

When labels conflict with wording, weaken the wording rather than upgrading the
claim.

## Review Checklist

For each reviewed claim, record:

- claim text or a short paraphrase;
- file path and line number when available;
- claim class: engineering, benchmark, or scientific;
- evidence labels attached to the artifact or row;
- command that reproduces or validates the evidence;
- artifact path, manifest path, or hash;
- missing evidence;
- recommended wording.

Useful commands:

```bash
python scripts/check_release_readiness.py
python scripts/validate_benchmark_spec.py benchmarks/v0.2/spec.json
python scripts/build_benchmark_registry.py examples/benchmark_submissions
```

For a specific benchmark submission, run:

```bash
tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json
```

## Recommended Issue Format

Open an external validation issue and choose **Benchmark claim-boundary
review**:

<https://github.com/weich97/TreLLM-public/issues/new?template=external_validation.yml>

Use this compact format:

```text
Claim:
File/path:
Claim class:
Evidence labels:
Current supporting evidence:
Runnable verification command or artifact path:
Missing evidence:
Recommended action: weaken, strengthen, or leave unchanged
Recommended wording:
```

## Examples Of Safe Weakening

| Original shape | Safer shape |
| --- | --- |
| "Model X is the best trading agent." | "Model X has the highest score in this cached, redacted benchmark row under the stated stress assumptions." |
| "The execution model is calibrated." | "The default row is stress-only; calibrated claims require quote/fill provenance." |
| "The benchmark is community validated." | "The repository has external validation pathways; community validation requires accepted non-maintainer reports." |
| "The result proves profitability." | "The result is a reliability and auditability measurement under the stated execution mode, not an investment claim." |

For the full policy, see [`claim_boundaries.md`](claim_boundaries.md).
