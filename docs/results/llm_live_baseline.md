# Live LLM Baseline Smoke Result

This page records one real provider-backed LLM baseline run. It is intentionally
small: the goal is to prove that the LLM analyst path can execute end to end
through model call, risk gate, realistic paper execution, trajectory hashing,
and redacted cache manifest generation. It is not a performance claim.

## Run Configuration

| Field | Value |
| --- | --- |
| Run date | 2026-05-18 |
| Command | `python -m tradearena.cli --benchmark llm-smoke --analysts poe-llm --llm-model gpt-5.5 --periods 3 --symbols SYN,ALT --llm-cache data/llm_cache/poe_gpt55_live_smoke_2026-05-18.jsonl --output outputs/examples/poe_gpt55_live_smoke_2026-05-18_trajectory.json` |
| Provider path | Poe OpenAI-compatible chat-completions endpoint |
| Model label | `gpt-5.5` |
| Data source | deterministic synthetic market |
| Symbols | `SYN`, `ALT` |
| Seed | `7` |
| Periods | `3` |
| Strategy | `signal-weighted` |
| Risk manager | `max-position` |
| Execution | `realistic` |
| Raw cache policy | local only, ignored by Git |
| Public artifact policy | redacted manifest and aggregate metrics only |

## Baseline Metrics

| Metric | Value |
| --- | ---: |
| Total return | `-0.000840` |
| Final equity | `99916.0165` |
| Max drawdown | `-0.000840` |
| Order count | `3` |
| Fill count | `2` |
| Execution fill rate | `0.6667` |
| Pending order count | `1` |
| Rejected order count | `0` |
| Partial fill count | `0` |
| Total commission | `7.0176` |
| Total slippage cost | `77.2719` |
| Risk reports | `3` |
| In-trade reports | `3` |
| Post-trade reports | `3` |
| Risk clipped decisions | `2` |
| Risk blocked decisions | `0` |
| Risk violation count | `0` |
| Risk audit coverage | `1.0000` |
| Risk lifecycle coverage | `1.0000` |
| Trajectory reproducibility coverage | `1.0000` |
| Agent trace coverage | `1.0000` |

## Provider Call Diagnostics

The run populated a fresh local JSONL cache with three provider responses.
Only redacted summary fields are tracked in the repository.

| Diagnostic | Value |
| --- | ---: |
| Provider/model rows | `poe:gpt-5.5 = 3` |
| Parsed response rate | `1.0000` |
| Average signals per parsed response | `2.0000` |
| Initial/no-feedback prompts | `1` |
| Visible-risk-feedback prompts | `2` |
| Average provider latency | `8682.86 ms` |
| Minimum provider latency | `5204.72 ms` |
| Maximum provider latency | `11945.79 ms` |

Redacted manifest files:

- [`llm_live_baseline_manifest/manifest.json`](llm_live_baseline_manifest/manifest.json)
- [`llm_live_baseline_manifest/poe_gpt55_live_smoke_2026-05-18_summary.json`](llm_live_baseline_manifest/poe_gpt55_live_smoke_2026-05-18_summary.json)

Manifest hashes:

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `41ceb8b8feeb4327af09075459e2a3d88853cbac03cdb5bfe0771577d456a084` |
| `poe_gpt55_live_smoke_2026-05-18_summary.json` | `a196be7c7f64dab82e553b2589ce90a21a94c513bbae9d6e3a3219f587db0faa` |

Trajectory hash for the local ignored trajectory:

```json
{
  "file_sha256": "sha256:a88839cd34a01a3c4eb6efdf62a79be2f785a42668e0bbb78f4abbac7c0652df",
  "reproducibility_hash": "sha256:459cf550e13ffe49240c1d76576f793658ec58f7ed1ba435e6a90b6f6632107c"
}
```

## Interpretation

This result establishes a minimal real-LLM baseline for the repository:

- a live Poe-hosted `gpt-5.5` analyst call produced parseable JSON signals;
- the signals were converted into target-weight decisions;
- the max-position risk layer clipped two decisions and blocked none;
- realistic paper execution produced two fills and one pending order;
- the trajectory and cache were summarized without committing raw prompts,
  responses, credentials, or private portfolio data.

Because the run is only three synthetic periods, it should be read as an
integration and audit baseline, not as evidence of trading performance.
