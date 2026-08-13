# Community Participation

TreLLM should not describe itself as community-backed until public, reviewable
participation exists. TradeArena names the public leaderboard module where
reviewed rows and benchmark cards can be compared. This document defines what
counts and how to contribute without exposing provider text, credentials, or
private trading data.

## Current Position

TreLLM is an early-stage research prototype. Maintainer-authored examples,
release notes, TradeArena leaderboard cards, and generated demos are
scaffolding. They are not evidence of external adoption.

## What Counts

| Contribution type | Counts as community evidence? | Notes |
| --- | --- | --- |
| Non-maintainer bug report with reproduction | Yes | Include environment, command, and observed output |
| External validation report | Yes | Use `docs/external_validation.md` |
| TradeArena leaderboard row | Yes, after review | Must pass schema validation and omit raw provider text |
| New data, risk, execution, or evaluator plugin | Yes, after merge | Include a demo and test |
| Maintainer-generated paper artifacts | No | Useful but not external participation |
| Star count or download count alone | No | Interest is not validation |

## Good First Participation Paths

Start with one of these 1-3 hour tasks:

| Task | What it proves |
| --- | --- |
| [Run the v0.2 reproduction pack on macOS](https://github.com/weich97/TreLLM-public/issues/43) | A fresh non-maintainer environment can generate the same artifact manifest |
| [Run the v0.2 reproduction pack on Ubuntu](https://github.com/weich97/TreLLM-public/issues/44) | The no-key path is not maintainer-machine specific |
| [Run the v0.2 reproduction pack on Colab/Binder](https://github.com/weich97/TreLLM-public/issues/45) | The browser notebook path can reproduce the public artifact manifest without local setup |
| [Submit one deterministic baseline row](https://github.com/weich97/TreLLM-public/issues/46) | The registry can accept comparable non-LLM evidence |
| [Submit one quote/fill calibration mini-report](https://github.com/weich97/TreLLM-public/issues/47) | Execution claims can be checked against quote/fill data rather than stress assumptions alone |
| [Review one benchmark claim boundary](https://github.com/weich97/TreLLM-public/issues/48) | Public wording stays tied to engineering, benchmark, or scientific evidence |

The task checklist and commands live in
[`docs/community_tasks.md`](community_tasks.md). Use the external validation
issue template for reports and small PRs for manifests or documentation fixes.

## Review Standards

A community contribution should be small enough to audit:

- one scenario or adapter at a time;
- one validation command;
- no credentials or raw LLM responses;
- no live trading by default;
- no private account statements or holdings;
- clear distinction between synthetic, historical, and private data.

## Participation Milestones

| Milestone | Meaning |
| --- | --- |
| First external validation | A non-maintainer reproduces a documented command or submits a calibrated critique |
| First accepted benchmark row | A non-maintainer manifest passes schema validation and review |
| First external adapter PR | A non-maintainer contributes a data, model, risk, or execution adapter |
| First external methodology critique resolved | A reviewer concern leads to a code or documentation change |

Until these milestones exist, public language should say "TreLLM is an
early-stage research prototype with a public TradeArena leaderboard module"
rather than implying external community validation for the whole system.
