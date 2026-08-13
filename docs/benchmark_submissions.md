# Redacted Leaderboard Submissions

TradeArena accepts redacted leaderboard manifests so users can compare runs
without sharing raw provider prompts, responses, credentials, or private
portfolio data.

## Validate One Submission

For a contributor-facing deterministic baseline walkthrough, see
[`deterministic_baseline_submission_quickstart.md`](deterministic_baseline_submission_quickstart.md).

```bash
tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json
tradearena validate-submission examples/benchmark_submissions/anonymous_entry_redacted_submission.json
```

Equivalent script entry:

```bash
python scripts/validate_benchmark_submission.py examples/benchmark_submissions/example_redacted_submission.json
```

## Build The Registry

```bash
tradearena build-registry examples/benchmark_submissions \
  --output docs/results/community_registry.md \
  --csv-output docs/results/community_registry.csv \
  --html-output docs/results/community_registry.html
```

The generated registry is tracked at
[`docs/results/community_registry.md`](results/community_registry.md).
The browser-readable version is
[`docs/results/community_registry.html`](results/community_registry.html).
Challenge format, leaderboard badges, anonymous rows, and citation guidance are
defined in [`docs/benchmark_challenges.md`](benchmark_challenges.md).
Evidence labels such as `stress-only`, `cached-provider`, `redacted-prompt`,
and `quote-calibrated` are defined in
[`docs/evidence_labels.md`](evidence_labels.md).

The current registry also includes an LLM model matrix generator: seven models
plus lower anchors over six synthetic market and execution-stress scenarios.
The three execution shock rows are
`liquidity_collapse`, `spread_explosion`, and `latency_spike`; they are
intended to expose overconfident target weights through partial fills, crossing
costs, pending orders, and rejections. The default protocol runs five seeds per
`(model, scenario)` and reports mean, sample standard deviation, 95% bootstrap
confidence intervals, paired bootstrap p-values, and paired sign-flip
permutation p-values against the anchors.
Regenerate it with:

```bash
python scripts/run_leaderboard_model_matrix.py --seeds 7,11,17,23,31 --update-registry
```

The matrix summary is tracked at
[`docs/results/model_matrix/leaderboard_model_matrix.md`](results/model_matrix/leaderboard_model_matrix.md).
The execution-shock slice is also tracked as
[`docs/results/model_matrix/leaderboard_execution_shock_aggregate.csv`](results/model_matrix/leaderboard_execution_shock_aggregate.csv).
Model rows live under
[`examples/benchmark_submissions/model_matrix/`](../examples/benchmark_submissions/model_matrix/).

The registry also includes a real-market matrix over Yahoo Finance `^GSPC`,
`BTC-USD`, and CME Bitcoin futures (`BTC=F`) data. It compares the same model
set over a recent cross-asset window and a 2022 drawdown window. Here the seed
dimension maps to rolling-window offsets so repeated runs do not merely reuse
the same historical slice. The script also writes
`docs/results/real_market_matrix/real_market_walk_forward.csv`, which records
the exact seed/window-offset mapping, timestamp policy, cache policy, and
provider-call provenance for audit:

```bash
python scripts/run_real_market_leaderboard.py --seeds 7,11,17,23,31 --update-registry
```

The real-market summary is tracked at
[`docs/results/real_market_matrix/real_market_model_matrix.md`](results/real_market_matrix/real_market_model_matrix.md).
Real-market rows live under
[`examples/benchmark_submissions/real_market_matrix/`](../examples/benchmark_submissions/real_market_matrix/).

The same scenarios also have deterministic non-LLM baselines: buy-and-hold,
equal weight, naive momentum, mean reversion, risk parity, minimum variance,
Markowitz/MVO, random, and always-hold. These rows are a main benchmark
surface. They make the model matrix falsifiable against standard portfolio
construction rules instead of only comparing LLMs with other LLMs:

```bash
python scripts/run_classical_baseline_matrix.py
```

The classical baseline summary is tracked at
[`docs/results/classical_baselines/classical_baselines.md`](results/classical_baselines/classical_baselines.md).
The benchmark card also has a three-axis quality decomposition that separates
pre-risk alpha quality, risk discipline, and execution robustness:

```bash
python scripts/build_quality_decomposition.py
```

The quality summary and radar chart are tracked at
[`docs/results/quality_decomposition/quality_decomposition.md`](results/quality_decomposition/quality_decomposition.md).

The registry format is designed for both deterministic baselines and redacted
LLM policy runs. Public submissions can include provider family, public-safe
model display name, prompt mode, risk-feedback mode, parse coverage, metrics,
and hashes for derived artifacts while still omitting raw prompts and responses.
See:

- [`examples/benchmark_submissions/example_redacted_submission.json`](../examples/benchmark_submissions/example_redacted_submission.json)
- [`examples/benchmark_submissions/example_llm_redacted_submission.json`](../examples/benchmark_submissions/example_llm_redacted_submission.json)
- [`examples/benchmark_submissions/example_direct_api_redacted_submission.json`](../examples/benchmark_submissions/example_direct_api_redacted_submission.json)
- [`examples/benchmark_submissions/anonymous_entry_redacted_submission.json`](../examples/benchmark_submissions/anonymous_entry_redacted_submission.json)
- [`examples/benchmark_submissions/model_matrix/`](../examples/benchmark_submissions/model_matrix/)
- [`examples/benchmark_submissions/real_market_matrix/`](../examples/benchmark_submissions/real_market_matrix/)
- [`docs/results/classical_baselines/`](results/classical_baselines/)
- [`docs/results/quality_decomposition/`](results/quality_decomposition/)
- [`schemas/benchmark_submission.schema.json`](../schemas/benchmark_submission.schema.json)

## Anonymous Entry IDs

Anonymous submissions should keep `agent.model_identifier_redacted: true` and
use a public-safe display name such as `entry-id:ta-anonymous-demo`. The
registry derives the citable entry ID from the reproducibility hash, so the
anonymous example appears as:

```text
ta-109a118ee5d7
```

When citing or discussing an anonymous row, cite the entry ID, scenario ID, and
reproducibility hash rather than a provider account, model endpoint, private
portfolio, or prompt transcript. For example:

```text
TradeArena benchmark entry ta-109a118ee5d7,
scenario anonymous_entry_synthetic_stress_v0_1,
manifest hash sha256:109a118ee5d70ca663873c613da8caef7802ceb2f80a45df7b05f48e25ecced9.
```

## Hash A Trajectory

```bash
tradearena hash-run outputs/examples/audit_walkthrough_trajectory.json
```

The hash is computed from stable scenario, data, execution, risk, agent,
redaction, and trajectory-manifest fields. Outcome metrics are intentionally
excluded so the fingerprint identifies the reproducible run context rather than
the score.

## Safety Boundary

Submissions should include:

- redacted model metadata,
- prompt mode, parse coverage, and risk feedback mode when an LLM is involved,
- execution and risk configuration,
- compact metrics,
- trajectory manifest path or URI plus public artifact hashes,
- reproducibility hash.

Submissions should not include:

- API keys or broker credentials,
- raw model prompts or responses,
- private holdings,
- live-order instructions.

## Privacy And Reproducibility Tradeoff

The registry is intentionally not a raw trajectory warehouse. It preserves
enough metadata to compare audit-ready runs and detect duplicate submissions,
but it does not require providers, researchers, or users to publish raw prompts,
raw completions, exact private holdings, or credentials. The reproducibility
hash covers scenario, data, agent/config, risk, execution, redaction, and
manifest identity; outcome metrics are excluded so a score change does not
rewrite the run identity.
