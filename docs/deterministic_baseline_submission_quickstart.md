# Deterministic Baseline Submission Quickstart

This track is for contributors who want to add a no-API benchmark row. A good
deterministic baseline is valuable because it gives LLM rows a falsifiable
anchor: a model comparison is not very meaningful unless it can beat simple,
reproducible portfolio rules under the same risk and execution assumptions.

## What To Submit

Submit one schema-valid manifest for one deterministic or seeded local policy.
Keep the scope narrow:

| Contribution | Useful when | Expected evidence |
| --- | --- | --- |
| One synthetic baseline row | You want a fast first contribution | JSON manifest, validation command, reproducibility hash |
| One real-market baseline row | You can document the market data source | JSON manifest, data hash, date range, validation command |
| One new deterministic policy | You can add a small strategy and fixture | test, manifest, and registry diff |
| One row critique | You found an overclaim or missing label | claim-boundary issue with suggested wording |

Do not submit live-trading results, private holdings, or broker credentials.

## Validate The Example

From a fresh clone:

```bash
git clone https://github.com/weich97/TreLLM-public.git
cd TreLLM
python -m pip install -e ".[dev]"
python scripts/validate_benchmark_submission.py examples/benchmark_submissions/example_redacted_submission.json
```

Equivalent installed CLI:

```bash
tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json
```

## Build A Local Registry Preview

```bash
python scripts/build_benchmark_registry.py examples/benchmark_submissions \
  --output outputs/community_registry_preview.md \
  --csv-output outputs/community_registry_preview.csv \
  --html-output outputs/community_registry_preview.html
```

Open or attach the preview files when proposing a new row. The registry preview
should include the row's evidence tags, claim class, evidence tier, metrics, and
reproducibility hash.

## Use The Classical Baseline Matrix

The repository can regenerate built-in deterministic anchors:

```bash
python scripts/run_classical_baseline_matrix.py
```

For a smaller local smoke run, restrict the scenario and baseline:

```bash
python scripts/run_classical_baseline_matrix.py \
  --baselines equal_weight \
  --synthetic-scenarios calm_trend \
  --real-scenarios recent_cross_asset \
  --synthetic-periods 8 \
  --real-max-periods 12
```

This writes files under `docs/results/classical_baselines/`. If you are
submitting a new row rather than refreshing maintainer artifacts, include a
separate manifest under `examples/benchmark_submissions/` and keep generated
preview outputs under `outputs/` until a maintainer accepts the update.

## Manifest Checklist

Every deterministic baseline submission should include:

- `scenario_id`;
- deterministic `agent.provider`, `agent.agent_type`, and model display name;
- data source, symbols, frequency, timestamp policy, and data hash;
- execution config with commission, slippage, spread, latency, participation,
  and market impact;
- risk config and risk budget;
- metrics including return, drawdown, Sharpe, fill rate, rejected orders, risk
  edits, and trajectory coverage;
- evidence tags such as `stress-only` and `deterministic-baseline`;
- trajectory manifest path or URI plus public artifact hashes;
- reproducibility hash;
- redaction confirmation.

Use [`evidence_labels.md`](evidence_labels.md) to keep `claim_scope`,
`claim_class`, and `evidence_tier` conservative.

## Evidence Tag Boundary

Use `external-submitted` only when the row comes from a non-maintainer or an
organization outside the maintainer set. Use `fully-auditable` only when the
public manifest links enough artifacts for another reviewer to inspect the raw
decision trail, risk report, execution assumptions, provenance, and trajectory
hashes. Keep maintainer-generated refreshes separate from external evidence:
they can improve examples and registry coverage, but they do not prove
community validation by themselves.

## Submit The Result

Open the deterministic baseline issue:

<https://github.com/weich97/TreLLM-public/issues/46>

Attach:

- the manifest JSON or pull request link;
- the exact validation command;
- the registry preview diff or screenshot;
- the reproducibility hash;
- any deviations from the documented scenario, data, risk, or execution
  settings.

A useful baseline row is boring in the best way: reproducible, clearly labeled,
and hard for a leaderboard claim to outrun.
