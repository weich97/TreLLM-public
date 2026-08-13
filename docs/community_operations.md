# Community Operations

This page lists maintainer actions that cannot be completed purely from code
changes but should be visible to outside contributors.

## Discussions

Recommended pinned categories:

| Category | Purpose | First pinned post |
| --- | --- | --- |
| Roadmap | what is planned and what is intentionally out of scope | current milestone and project-board link |
| Show and Tell | demos, benchmark rows, plugins, notebooks | template for artifact links and validation commands |
| Q&A | installation, provider keys, data sources, and live-readiness safety | short support expectations |
| RFC | design proposals before larger PRs | template with motivation, interface impact, and validation plan |

## Project Board

Use a GitHub Projects board with four columns:

| Column | Meaning |
| --- | --- |
| Triage | issue needs labels, scope, or owner |
| Ready | task has file owner and validation command |
| In progress | assigned or claimed work |
| Review | PR or artifact ready for maintainer review |

Seed the board from [`docs/community_tasks.md`](community_tasks.md). Keep tasks
small enough that a contributor can finish one without learning the full code
base.

## Realtime Channel

A Discord or Matrix room is useful only if the maintainer can answer within a
reasonable time. Suggested channels:

- `announcements`: releases, benchmark challenges, accepted registry rows;
- `help`: install, notebook, provider-key, and data questions;
- `plugins`: data, model, risk, execution, and evaluator extensions;
- `research`: methodology, papers, and external validation;
- `showcase`: demos and benchmark artifacts.

Keep support boundaries explicit: no financial advice, no unattended live
trading support, and no credential sharing.

## Changelog And Newsletter

Monthly updates can be short:

- merged features and docs;
- new benchmark rows or external validations;
- active good-first tasks;
- next challenge scenario;
- known limitations.

Use `docs/launch/` for release notes and link the latest one from the README or
Discussions.

## Academic Outreach

For LLM agents or financial AI labs, use a reproducibility-first pitch:

```text
We maintain TreLLM, an early-stage live-ready audit and control system for auditing
financial-agent intent under risk gates, execution evidence, broker-review
handoffs, and reproducibility checks.
If your group has an agent or prompt policy, we can help package a redacted
benchmark manifest and reproducibility report without exposing raw prompts,
responses, credentials, or private holdings. TradeArena can package comparable
benchmark manifests and leaderboard evidence from that TreLLM audit trail.
```

The useful outcome is not a star count. It is an external validation report,
accepted redacted benchmark row, methodology critique, or cited experiment.
