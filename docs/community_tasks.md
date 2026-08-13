# Contributor Task Backlog

This page turns the roadmap into small, reviewable work items. Each task should
fit in one focused PR with one validation command.

## Label Policy

| Label | Meaning |
| --- | --- |
| `good first issue` | Small scope, offline-friendly, and reviewable without domain expertise |
| `help wanted` | Maintainer wants outside input or implementation help |
| `discussion` | Needs design agreement before code |
| `benchmark` | Affects benchmark scenarios, manifests, registry, or metrics |
| `risk` | Affects risk checks, stress tests, or risk reports |
| `execution` | Affects order simulation, fills, fees, latency, or liquidity |
| `docs` | Documentation-only or documentation-first work |

## External Evidence Tasks

These five tasks are the preferred first contributions because they strengthen
the benchmark evidence chain: a non-maintainer can run it, question it, or
submit a comparable result. Each task should take about 1-3 hours and can be
filed through the external validation issue template or a small pull request.

New contributors can start with the shorter
[`external_validation_quickstart.md`](external_validation_quickstart.md), then
come back here when choosing a specific issue-sized task. For baseline rows,
use
[`deterministic_baseline_submission_quickstart.md`](deterministic_baseline_submission_quickstart.md).
For execution work,
use [`execution_calibration_quickstart.md`](execution_calibration_quickstart.md)
to pick the weakest honest evidence label and report fields. For wording and
claim checks, use
[`claim_boundary_review_quickstart.md`](claim_boundary_review_quickstart.md).

| Task | Time | Commands | Evidence to attach | Suggested labels |
| --- | ---: | --- | --- | --- |
| [Run v0.2 reproduction pack on macOS](https://github.com/weich97/TreLLM-public/issues/43) | 1 hour | `python scripts/build_external_validation_bundle.py --run-pack --environment-label "macOS / Python X.Y"` | generated bundle Markdown, `outputs/reproduction/v0_2/manifest.json`, Python version, shell log, deviations | `validation`, `reproducibility`, `good first issue` |
| [Run v0.2 reproduction pack on Ubuntu](https://github.com/weich97/TreLLM-public/issues/44) | 1 hour | `python scripts/build_external_validation_bundle.py --run-pack --environment-label "Ubuntu / Python X.Y"` | generated bundle Markdown, manifest, distro, Python, and install notes | `validation`, `reproducibility`, `good first issue` |
| [Run v0.2 reproduction pack on Colab/Binder](https://github.com/weich97/TreLLM-public/issues/45) | 1 hour | open the README Colab or Binder badge and run the notebook cells | notebook URL, runtime type, generated manifest or README suggested issue text, deviations | `validation`, `reproducibility`, `good first issue` |
| [Submit one deterministic baseline row](https://github.com/weich97/TreLLM-public/issues/46) | 1-2 hours | `python scripts/validate_benchmark_submission.py <row.json>`; `python scripts/build_benchmark_registry.py examples/benchmark_submissions` | one schema-valid deterministic manifest, rebuilt registry diff, and reproducibility hash | `benchmark`, `good first issue` |
| [Submit one quote/fill calibration mini-report](https://github.com/weich97/TreLLM-public/issues/47) | 2-3 hours | `python scripts/calibrate_quote_fill_model.py` or the Binance sample command in `docs/execution_calibration_quickstart.md` | calibration JSON/Markdown with source, venue, date range, sample size, replay error, and residuals | `execution`, `validation`, `help wanted` |
| [Review one benchmark claim boundary](https://github.com/weich97/TreLLM-public/issues/48) | 1 hour | `python scripts/check_release_readiness.py`; inspect `docs/claim_boundary_review_quickstart.md` | one issue or PR that maps a README/result claim to engineering, benchmark, or scientific evidence | `docs`, `discussion`, `validation` |

Acceptance is deliberately narrow: one environment report, one row, one
calibration report, or one claim critique. This keeps external validation
reviewable without asking newcomers to understand the whole codebase.

## Good First Issues

| Task | Suggested labels | Expected validation |
| --- | --- | --- |
| Add a drawdown recovery chart to the showcase | `good first issue`, `risk`, `docs` | one fixture where kill-switch events are visible |
| Improve alt text for generated HTML reports | `good first issue`, `docs` | inspect rebuilt HTML artifacts |
| Add a notebook cell that hashes a trajectory | `good first issue`, `docs` | run the notebook or the equivalent CLI command |

## Completed Good-First Fixture Map

These good-first starter fixtures have landed and are no longer first
issues. Keep them visible so contributors can extend the next layer instead of
recreating scaffolding.

| Capability | Closed issue | Current artifact or validator | Next useful extension |
| --- | --- | --- | --- |
| Anonymous benchmark manifest example | [#29](https://github.com/weich97/TreLLM-public/issues/29) | `examples/benchmark_submissions/anonymous_entry_redacted_submission.json`; `test_anonymous_redacted_submission_validates_and_uses_entry_id_boundary`; `docs/results/community_registry.html` | add more anonymous entry variants with different evidence tiers, data-frequency policies, and redaction notes |
| SMA crossover strategy plugin | [#27](https://github.com/weich97/TreLLM-public/issues/27) | `tests/test_sma_strategy.py`; `SMACrossoverStrategy`; `sma-crossover` registry entry | add a second deterministic strategy plugin with a tiny manifest row and registry preview |
| Binder and notebook quickstart path | [#40](https://github.com/weich97/TreLLM-public/issues/40) | `tests/test_notebook_quickstart.py`; `notebooks/tradearena_5min_colab.ipynb`; `tradearena hash-run outputs/examples/notebook_trajectory.json` | add a notebook cell that compares a local hash with the README quickstart hash |
| Plugin registry example package | [#41](https://github.com/weich97/TreLLM-public/issues/41) | `plugins/examples/sector_concentration_guard/`; `tests/test_plugin_examples.py`; `docs/plugin_development.md` | add another installable plugin package variant with packaging metadata and one validation command |

## Finance And Market Realism

The first market-realism fixtures have landed. New contributions should extend
one row in the completed map with independently reviewed assumptions,
additional venues, or richer stress evidence rather than recreating the
starter demos.

## Completed Market Realism Map

| Capability | Closed issue | Current artifact or validator | Next useful extension |
| --- | --- | --- | --- |
| A-share T+1 and price-limit scenario coverage | [#31](https://github.com/weich97/TreLLM-public/issues/31) | `examples/ashare_market_rules_demo.py`; `docs/results/market_rules_fixture.json`; A-share rule package tests | add exchange-calendar references and board-specific rule variants beyond the starter fixture |
| Hong Kong lot-size and trading-calendar demo | [#32](https://github.com/weich97/TreLLM-public/issues/32) | `examples/hk_market_rules_demo.py`; `docs/results/market_rules_fixture.md`; Hong Kong board-lot package | add trading-session and lunch-break fixtures with cited exchange assumptions |
| Crypto fee-tier and spread-shock preset | [#33](https://github.com/weich97/TreLLM-public/issues/33) | `examples/crypto_microstructure_stress_demo.py`; `outputs/examples/crypto_microstructure_stress/summary.json` | add venue-specific fee tiers, funding windows, and spread shocks from public exchange schedules |
| Almgren-Chriss impact stress plugin | [#34](https://github.com/weich97/TreLLM-public/issues/34) | `examples/almgren_chriss_stress_demo.py`; `tests/test_almgren_chriss_stress.py`; `AlmgrenChrissImpactStress` | add calibrated parameter presets and compare modeled shortfall against public quote/fill samples |
| Black-swan liquidity halt stress scenario | [#35](https://github.com/weich97/TreLLM-public/issues/35) | `examples/liquidity_halt_demo.py`; `outputs/examples/liquidity_halt/summary.json`; liquidity halt rule package | add venue halt/suspension references and broker response artifacts for pending orders |

## Broker And Live-Ready Tracks

Each task should remain offline export, dry run, or paper sandbox by default.
Use [`live_trading_readiness.md`](live_trading_readiness.md#external-contribution-tracks)
and [`broker_adapter_contract.md`](broker_adapter_contract.md) as the review
boundary. No task in this table should introduce default live submission.

The first-layer broker-facing scaffolding tasks have landed. New live-ready
contributions should extend one row in the completed capability map below with
broker-specific fixtures, stricter safety evidence, or independently reviewed
paper-trading assumptions.

## Completed Live-Ready Capability Map

These issues have landed and are no longer first-task backlog items. They are
kept here as a capability map so contributors can extend the next layer instead
of reopening completed scaffolding.

| Capability | Closed issue | Current artifact or validator | Next useful extension |
| --- | --- | --- | --- |
| Broker adapter capability manifest | [#57](https://github.com/weich97/TreLLM-public/issues/57) | `outputs/examples/broker_capability_manifest/capability_manifest.json`; `tradearena validate-broker-capability ...` | add broker-specific capability fixtures with stricter credential and network policies |
| Live-readiness preflight consistency check | [#58](https://github.com/weich97/TreLLM-public/issues/58) | `outputs/examples/live_readiness_preflight/preflight_bundle.json`; `tradearena validate-live-readiness ...` | add more cross-artifact mismatch fixtures across capability, runbook, handoff, approval, and response |
| Approval-binding edge-case coverage | [#59](https://github.com/weich97/TreLLM-public/issues/59) | `tests/test_issue_demos.py`; broker approval binding validators | add stale approval, symbol, order-type, notional, and quantity examples tied to realistic paper requests |
| Broker response status-mapping fixture | [#60](https://github.com/weich97/TreLLM-public/issues/60) | `outputs/examples/broker_response_artifact/response_artifact.json`; response validator | add venue-specific accepted, rejected, partial-fill, cancel, expiry, and unknown mappings |
| Paper-sandbox adapter skeleton | [#61](https://github.com/weich97/TreLLM-public/issues/61) | `PaperSandboxAdapterSkeleton`; mocked paper-client tests | add an optional broker-specific paper client without default network access |
| Operator runbook checklist | [#62](https://github.com/weich97/TreLLM-public/issues/62) | `outputs/examples/operator_runbook/summary.json`; `tradearena validate-operator-runbook ...` | add incident drills with rollback owner, disable switch, retention path, and re-enable approval evidence |
| Live-readiness safety-control mismatch fixture | follow-up to [#58](https://github.com/weich97/TreLLM-public/issues/58) | `outputs/examples/live_readiness_preflight/preflight_bundle.json`; safety controls checked by `tradearena validate-live-readiness ...` | add venue-specific capability/runbook mismatch fixtures for throttle, kill-switch, and notional controls |
| Broker-specific paper sandbox client fixture | follow-up to [#61](https://github.com/weich97/TreLLM-public/issues/61) | `outputs/examples/mock_paper_sandbox_client/paper_sandbox_response_artifact.json`; mock-paper sandbox fixture with no default network call | add opt-in broker SDK fixtures that keep credentials optional and response artifacts schema-valid |
| Incident-response drill artifact | follow-up to [#62](https://github.com/weich97/TreLLM-public/issues/62) | `outputs/examples/operator_runbook/summary.json`; `incident_response_drill` kill switch and re-enable approval evidence | add incident drill variants for stale approval, halted venue, and partial-fill rollback cases |
| Broker-response reconciliation edge cases | follow-up to [#60](https://github.com/weich97/TreLLM-public/issues/60) | `outputs/examples/broker_response_reconciliation/broker_response_artifact.json`; `outputs/examples/broker_response_artifact/response_artifact.json`; duplicate validator error `responses[1].client_order_id duplicates an earlier response` | add venue-specific duplicate, missing, unmatched, cancel, expiry, and unknown-state fixtures with recomputed reconciliation counts |

## Benchmark Flywheel

| Task | Suggested labels | Expected validation |
| --- | --- | --- |
| Add row-level detail panels to the leaderboard | `good first issue`, `benchmark` | open generated `community_registry.html` |
| Add a quarterly challenge seed file | `help wanted`, `benchmark` | documented command and expected artifact paths |
| Add a redacted citation entry template | `good first issue`, `docs` | schema validation still passes |

## Completed Benchmark Flywheel Map

| Capability | Closed issue | Current artifact or validator | Next useful extension |
| --- | --- | --- | --- |
| Reproducibility badge checks to registry rows | [#36](https://github.com/weich97/TreLLM-public/issues/36) | `docs/results/community_registry.html`; `docs/results/community_registry.md`; `python scripts/build_benchmark_registry.py examples/benchmark_submissions` | add row-level detail panels that expose evidence tier, redaction status, and reproducibility hash without raw provider text |

## Observability

The first local observability exporters have landed. Follow-up work should keep
exports offline by default and avoid adding required live-service dependencies.

## Completed Observability Map

| Capability | Closed issue | Current artifact or validator | Next useful extension |
| --- | --- | --- | --- |
| OpenTelemetry-style trajectory span export | [#37](https://github.com/weich97/TreLLM-public/issues/37) | `tests/test_trace_export.py`; `src/tradearena/evaluation/trace_export.py`; `tradearena export-trace ...` | add optional console/JSONL exporters while preserving redaction defaults |
| W&B or MLflow offline export prototype | [#38](https://github.com/weich97/TreLLM-public/issues/38) | `tests/test_observability_export.py`; `src/tradearena/evaluation/offline_tracking.py`; `docs/observability.md` | add opt-in adapters for real tracking clients without making them required dependencies |
| OpenAI Evals or LangSmith-style trace mapping | [#39](https://github.com/weich97/TreLLM-public/issues/39) | `tests/test_trace_schema_export.py`; `schemas/eval_trace_style.schema.json`; `export_trajectory_to_trace_schema_json` | add sample imports into external trace tools using local JSON fixtures only |

For issue bodies, copy the task row, add a file path owner, and name the command
that a reviewer should run.

Maintainer starter fixtures now exist for the first market-rule slice:

```bash
python examples/market_rules_fixture_demo.py
```

The command writes `docs/results/market_rules_fixture.json` and
`docs/results/market_rules_fixture.md`. External follow-up work should extend
the fixture with real exchange calendar assumptions or independently reviewed
venue-rule references rather than treating the starter fixture as complete
market coverage.
