# TreLLM v0.3 Direct API Submission Bridge (W0 dry run)

`scripts/run_v03_direct_api_submission.py` is the executable link between the
pre-registered direct API matrix plan and the matrix threshold gate. It turns
each call packet row into:

1. a real TreLLM pipeline run (`tradearena.factory.build_default_system` with
   the direct-provider LLM analyst) for the packet's
   `(scenario, contamination tier, execution level, seed, sample)` cell;
2. a private per-run call log (raw prompts/responses; never published);
3. a hash-only direct provider manifest
   (`scripts/validate_direct_provider_manifest.py` clean);
4. a benchmark submission (`validate_submission_file` clean) that binds the
   provider manifest by file hash, which is exactly the join key
   `scripts/build_v03_direct_api_matrix_gate.py` verifies.

Claim boundary: this bridge and its dry-run bundles are pipeline plumbing, not
model-performance evidence. Dry-run rows are labeled `protocol-fixture` and the
matrix gate keeps them non-headline by construction. Live rows become headline
candidates only after the gate verifies direct-API provenance and the 10-seed x
3-sample threshold, and the public artifact privacy scan passes.

## Modes

| Mode | Flag | Network | Credentials | Row labeling |
| --- | --- | --- | --- | --- |
| Dry run (default) | none | none | never read | `protocol-fixture` tags; manifest claim scope says "dry-run protocol fixture"; gate blocks promotion |
| Live | `--execute` | direct provider chat-completions | packet's env var (e.g. `DEEPSEEK_API_KEY`, `GLM_API_KEY`) must be set in the environment; the script never reads key files | `direct-api` + `live-provider`/`cached-provider` tags; gate-eligible |

Existing completed `(seed, sample)` cells are skipped on rerun (checkpoint
resume); a crashed run resumes mid-run through the adapter's response cache.
Failed cells are recorded as failure rows (per the protocol's failure
accounting) and are retried on the next invocation. Use `--overwrite` to force
regeneration, and keep dry-run and live bundles in separate `--output-root`
directories (the bridge refuses to mix modes in one root).

## Offline self-check (no keys, no network)

```bash
python scripts/build_v03_direct_api_call_packets.py --output-dir outputs/v03_dryrun_selftest/packets
python scripts/run_v03_direct_api_submission.py \
  --packets outputs/v03_dryrun_selftest/packets/direct_api_call_packets.jsonl \
  --model deepseek-v4-pro --limit-seeds 2 --samples 0,1 --periods 6 \
  --output-root outputs/v03_dryrun_selftest/bundle
python scripts/build_v03_direct_api_matrix_gate.py \
  --output-dir outputs/v03_dryrun_selftest/gate \
  --submission-dirs outputs/v03_dryrun_selftest/bundle/submissions \
  --provider-manifest-dirs outputs/v03_dryrun_selftest/bundle/provider_manifests
```

Expected: 4 valid rows, 0 main-threshold groups (fixture rows stay pilot), and
`scripts/scan_public_artifacts.py` passes on the bundle's manifests and
submissions.

## W0 live dry run: deepseek-v4-pro, 10 seeds x 3 samples -> gate

Preconditions: `DEEPSEEK_API_KEY` present as an environment variable. The
committed call-packet artifact predates the 2026-07-02 provider amendment, so
step 1 refreshes it from the amended (frozen) plan rows.

```bash
# 1) refresh packets from the amended plan (deepseek/glm; overwrites the stale openai-era packets)
python scripts/build_v03_direct_api_call_packets.py

# 2) one-row live smoke (1 seed x 1 sample; verifies transport, manifest, submission)
python scripts/run_v03_direct_api_submission.py --model deepseek-v4-pro --execute --max-runs 1

# 3) full pre-registered cell set for the model (resumes past the smoke row)
python scripts/run_v03_direct_api_submission.py --model deepseek-v4-pro --execute

# 4) threshold gate over the live bundle
python scripts/build_v03_direct_api_matrix_gate.py \
  --output-dir outputs/v0_3_direct_api_matrix/gate \
  --submission-dirs outputs/v0_3_direct_api_matrix/submissions \
  --provider-manifest-dirs outputs/v0_3_direct_api_matrix/provider_manifests

# 5) privacy scan before promoting anything
python scripts/scan_public_artifacts.py \
  outputs/v0_3_direct_api_matrix/provider_manifests \
  outputs/v0_3_direct_api_matrix/submissions
```

Green light: step 4 reports `Main-threshold groups: 1` and
`headline_scientific_claim_ready: true` for the
`deepseek / deepseek-v4-pro / synthetic_calm_trend_c0_v0_3 / C0 / E1` group.
Repeat steps 2-5 with `--model deepseek-v4-flash` and `--model glm-5`
(`GLM_API_KEY`) for the remaining pre-registered groups.

Promotion (publishing decision, after green + privacy scan): copy
`provider_manifests/` and `submissions/` from the output root into a committed
`docs/results/v0_3_direct_api_matrix/` directory, then rebuild the committed
gate artifact over both the pilot and matrix directories:

```bash
python scripts/build_v03_direct_api_matrix_gate.py \
  --submission-dirs docs/results/v0_3_direct_api_pilot/submissions,docs/results/v0_3_direct_api_matrix/submissions \
  --provider-manifest-dirs docs/results/v0_3_direct_api_pilot/provider_manifests,docs/results/v0_3_direct_api_matrix/provider_manifests
```

Never copy anything from `private/llm_cache/` into a committed directory; it
contains raw prompts and responses.

## Scenario and execution parameters (values and basis)

The pre-registered plan pins provider, model, version, scenario id, tier,
level, seeds, samples, prompt template/version, and sampling. It does not pin
the simulator-side scenario parameters, so the bridge fixes them as follows and
records them in every submission:

| Parameter | Value | Basis |
| --- | --- | --- |
| Scenario generator | synthetic, volatility scale 1.0, trend scale 1.0 | operational definition of `synthetic_calm_trend_c0_v0_3` in `scripts/run_v03_execution_ladder.py` (the artifact that introduced this scenario id) |
| Symbols | SYN, ALT | same ladder definition; C0 synthetic identities |
| Periods | 24 (flag `--periods`) | ladder default for this scenario id; one provider call per period per run |
| Initial cash | 100000 | `build_default_system` default; consistent with the execution-sensitivity studies |
| E1 execution | realistic simulator; commission 1.0 bps; base slippage 2.0 bps; spread 0; latency 1 step; participation 0.05; impact 0.15 | ladder E1 definition and the fixture pilot's recorded `execution_config` |
| Risk gate | max-position 0.35 / gross 1.0 / turnover 0.75; risk feedback mode `true` | factory defaults; matches the pilot `risk_config` |
| LLM prompt contract | `weights_only` output, masked relative timestamps (`T+n`), risk feedback enabled, `sample_index` from packet | `trellm-allocation-v0.3` is the allocation (target-weight) template; matches the pilot agent metadata (`prompt_mode: weights_only`) and C0 `relative_masked` policy |
| Sampling | temperature 0.2, top_p 1.0, max_tokens 1200 | pinned from the call packet; the bridge's transport sends all three (the base adapter sends temperature only, so the bridge enforces the full pre-registered envelope) |
| `data_source.frequency` | `daily` | `SyntheticMarketDataProvider` emits one bar per day; the pilot fixture's `weekly` was a fixture stub, the bridge records the actual cadence |
| E2/E3 packets | rejected | only E1 is pre-registered in the current matrix plan |

Changing `--periods` after rows exist requires `--overwrite` or a fresh output
root, because completed cells are otherwise skipped as-is.

## Format alignment with the pilot bundle

- Provider manifests and submissions have the same field shape as
  `scripts/run_v03_direct_api_pilot.py` output; only labeling differs by mode.
- Per-call prompt/response hashes come from the adapter's private call log.
  Because a run makes one provider call per period, the manifest's
  `prompt_sha256` / `response_sha256` are run-level digests: the SHA-256 of the
  canonical JSON array of per-call SHA-256 hashes in call order.
- `run_binding.trajectory_manifest_sha256` and the submission's
  `trajectory_manifest.manifest_hash` are both the SHA-256 of the private
  per-run call log file, so the public row is hash-bound to the private
  evidence without publishing it.
- `trajectory_manifest.artifact_hashes.direct_provider_manifest` is the
  SHA-256 of the provider manifest file (computed after writing it); this is
  the exact lookup key the matrix gate uses to join submissions to manifests.
- `reproducibility_hash` uses `compute_reproducibility_hash` (outcome metrics
  excluded), identical to the pilot.
- `cache.cache_status` is `live_call` when a live run appended new calls and
  `cache_replay` when every call replayed from the private cache; the original
  call window (`created_at` of the first live calls) is retained on replay, per
  the protocol cache policy. `call_window.retry_count` is 0 because the
  adapter's in-call retries are internal; bridge-level reruns appear as
  resumed rows instead.

## Bundle layout (under `--output-root`)

- `provider_manifests/<plan_id>.json` - hash-only direct provider manifests
- `submissions/<plan_id>.json` - benchmark submissions
- `runs/<plan_id>.json` - per-run records (status, metrics, call stats, hashes)
- `direct_api_submission_runs.csv` / `.jsonl` - run table rebuilt every invocation
- `direct_api_submission_summary.json` / `.md` - coverage and failure summary
- `private/llm_cache/<plan_id>.jsonl` - raw call logs (private, never publish)

Tests: `tests/test_v03_direct_api_submission.py` covers the dry-run chain, the
`--execute` code path with an injected offline transport (gate goes green on a
full 10x3 rehearsal bundle), idempotent resume, and failure-row accounting.
