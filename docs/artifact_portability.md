# Artifact Portability Policy

TreLLM artifacts should be easy to move between local machines, CI, paper
appendices, and external validation reports without leaking secrets.

## Track In Git

Small, stable, reviewable artifacts may be tracked:

- redacted benchmark manifests;
- compact CSV/Markdown benchmark summaries;
- SVG charts used by docs or the project site;
- schema examples;
- public synthetic data fixtures.

## Keep Out Of Git

Do not commit:

- API keys, `.env` files, broker tokens, or service credentials;
- raw LLM prompt/response caches;
- broker statements, account exports, or private holdings;
- large generated trajectories;
- downloaded market data whose license does not permit redistribution;
- binary model weights or local vector indexes.

## Share Safely

For reproducibility, prefer:

- redacted manifests over raw provider logs;
- hashes and summaries over full private trajectories;
- command lines and environment metadata over screenshots;
- private ignored paths such as `data/private/`, `data/broker/`, and
  `data/llm_cache/` for sensitive inputs.

If a result depends on private data, say so in the report and provide the
publicly shareable residual statistics, schema, and command shape instead of the
raw file.
