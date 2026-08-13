# System And Leaderboard Maturity Track

TreLLM should be presented as an early-stage research prototype until three
forms of evidence exist in public:

1. a stable academic report that states the scientific claim and limitations;
2. independent external validation against reproducible commands and artifacts;
3. real community participation through issues, replications, benchmark rows,
   reviews, or merged pull requests.

This document makes that bar explicit so the repository does not overstate its
current maturity.

## Current Status

| Track | Current repository support | What is still missing |
| --- | --- | --- |
| Academic report | Technical white paper, research protocol, benchmark card, live LLM smoke baseline | A peer-review-style report with frozen claims, external validation appendix, and stable tables/figures |
| External validation | Redacted benchmark schema, validation scripts, release-readiness checks, fill-comparison protocol | Independent reproduction reports from users who are not maintainers |
| Community participation | Contribution guide, issue templates, roadmap, TradeArena submission format | External issues/PRs/leaderboard rows that are reviewed and accepted |

Owner-maintained examples, generated demos, and internal paper artifacts are not
community adoption signals. They are useful scaffolding, but the project should
not call itself community-validated until external contributors submit
replicable evidence.

## Evidence Bar

TreLLM can credibly describe itself as externally validated, and TradeArena can
credibly describe its leaderboard module as a niche benchmark, only after the
following minimum evidence exists:

| Evidence | Minimum public bar |
| --- | --- |
| Academic report | Versioned PDF or preprint tied to a release tag, with experiment commands and limitations |
| External validation | At least three independent replication or calibration reports, each naming commit, environment, commands, and artifacts |
| Community participation | At least two non-maintainer merged PRs or accepted leaderboard rows, plus one resolved external critique |
| Execution realism | At least one quote/fill-log comparison using `scripts/compare_execution_to_fills.py` |
| LLM benchmark value | At least one provider-backed baseline and one independently submitted redacted LLM benchmark row |

The v0.2 hardening work starts with three concrete gates:

- frozen comparison contract: `benchmarks/v0.2/spec.json`;
- quote/fill calibration entry point:
  `scripts/calibrate_quote_fill_model.py`;
- external no-key reproduction pack:
  `scripts/run_external_reproduction_pack.py`.

## Roadmap

### 1. Academic Report

checklist. The report should distinguish:

- prototype claims: what the code can run today;
- benchmark claims: what the artifact can measure reproducibly;
- scientific claims: what the experiments imply about LLM financial decisions.

### 2. External Validation

Use [`external_validation.md`](external_validation.md) for independent
replication. A useful validation includes:

- repository commit or release tag;
- operating system, Python version, package installation method;
- exact commands;
- output paths and hashes;
- whether live APIs, downloaded market data, or private fills were used;
- deviations from the documented protocol.

### 3. Community Participation

Use [`community_participation.md`](community_participation.md) to separate
real participation from owner-authored demos. The project should prefer small,
reviewable contributions: one scenario, one artifact, one validation command.

## Repository Surfaces

| Surface | Purpose |
| --- | --- |
| `docs/technical_report.md` | Implementation and calibration details |
| `docs/research_protocol.md` | Research questions and experiment organization |
| `docs/external_validation.md` | Independent replication protocol |
| `docs/community_participation.md` | Participation rules and evidence standards |
| `.github/ISSUE_TEMPLATE/external_validation.yml` | Structured external validation submissions |
| `.github/ISSUE_TEMPLATE/academic_report_gap.yml` | Structured paper-readiness critiques |
