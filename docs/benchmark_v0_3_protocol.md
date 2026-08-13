# TreLLM v0.3 Protocol

`benchmarks/v0.3/protocol.json` is the draft research contract for moving
TreLLM from a public leaderboard release toward an publication-grade LLM financial-agent
evaluation protocol.

The protocol keeps the system boundary explicit:

- TreLLM is the audit, control, execution-calibration, and replayability system.
- TradeArena is the public leaderboard and benchmark-card surface for comparable
  auditable runs.

## Why v0.3 Exists

The v0.2 spec freezes a useful public benchmark card. The v0.3 protocol
adds the evidence requirements needed for a main-conference reliability claim:

- direct API provider provenance rather than routed-provider headline results;
- execution levels E0, E1, E2, and E3;
- contamination tiers C0, C1, and C2;
- repeated-seed and repeated-sample statistical requirements;
- intent-to-execution, memory-pollution, and risk-intervention mechanism
  metrics;
- FinAudit trace-auditor tasks with injected-defect ground truth;
- independent external reproduction reports.

## Validate

```bash
python scripts/validate_benchmark_spec.py benchmarks/v0.3/protocol.json
```

The validator checks the presence of the protocol gates. It does not prove
that the experiments have already been run. A missing output table, direct API
pilot, or external reproduction report should still be treated as incomplete
research work.

Validate the direct-provider manifest contract separately:

```bash
python scripts/validate_direct_provider_manifest.py examples/provider_manifests/direct_openai_example.json
```

These manifests bind a direct API call to provider, model, version, prompt hash,
response hash, redaction policy, contamination tier, execution level, seed,
sample index, and trajectory-manifest hash. Routed-provider rows must not use
this contract for headline v0.3 evidence.

The offline pilot runner can generate a hash-only manifest from local
prompt/response fixtures:

```bash
python scripts/run_direct_provider_manifest_pilot.py \
  --provider openai \
  --model-id gpt-5.5 \
  --model-version-or-release 2026-05-17 \
  --api-endpoint-family responses \
  --prompt-file path/to/prompt.json \
  --response-file path/to/response.json \
  --scenario-id synthetic_calm_trend_c0_v0_3 \
  --contamination-tier C0 \
  --execution-level E1 \
  --seed 7 \
  --sample-index 0 \
  --trajectory-manifest-sha256 sha256:<64-hex> \
  --output outputs/direct_provider_manifests/example.json
```

The repository also tracks a tiny deterministic C0/E1 bundle generated with:

```bash
python scripts/run_v03_direct_api_pilot.py
```

See `docs/results/v0_3_direct_api_pilot/direct_api_pilot_summary.md`.

The direct API matrix threshold gate is generated with:

```bash
python scripts/build_v03_direct_api_matrix_gate.py
```

See `docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.md`.
This artifact verifies submission/manifests hashes, direct API provenance, and
the v0.3 threshold of 10 seeds and 3 samples per seed. It currently keeps the
fixture rows labeled as pilot/incomplete evidence, so the direct API model
matrix gap remains open until non-fixture provider rows meet the threshold.

Before live provider calls are made, the direct API matrix plan and credential
preflight is generated with:

```bash
python scripts/build_v03_direct_api_matrix_plan.py
```

See `docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.md`.
This artifact pre-registers the 10-seed by 3-sample call matrix and records only
whether the required credential environment variables are present. It does not
make provider calls, publish secrets, or count as model-performance evidence.

The no-key direct API call-packet queue is generated with:

```bash
python scripts/build_v03_direct_api_call_packets.py
```

See `docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.md`.
This artifact turns pre-registered matrix rows into hash-bound call packets,
expected provider-manifest paths, expected submission paths, and redaction
contracts. It does not call providers or publish raw prompts/responses; rows
become evidence only after a direct-provider manifest and benchmark submission
are generated and pass the matrix gate.

External direct API contributors should follow the generated redaction and
submission checklist:

```bash
python scripts/build_v03_direct_api_submission_checklist.py
```

See
`docs/results/v0_3_direct_api_submission_checklist/direct_api_submission_checklist.md`.
The checklist maps the v0.3 provider manifest fields, benchmark submission
binding, public redaction policy, matrix gate, privacy scan, and claim-boundary
requirements into a public artifact. It is a contribution-readiness artifact,
not model-performance evidence.

The execution-assumption ladder is generated separately so the protocol can
report ranking stability and mechanism metrics before any live provider rows are
promoted:

```bash
python scripts/run_v03_execution_ladder.py
```

See `docs/results/v0_3_execution_ladder/execution_ladder_summary.md`. This
artifact runs deterministic agents through E0, E1, E2, and an E3 calibrated
replay fixture path, then reports Kendall tau, top-k Jaccard, fill rate,
rejected orders, slippage cost, and intent-to-execution gap. The E3 row is a
fixture path unless the run attaches external quote/fill provenance.

The E2 execution stress-grid artifact is generated with:

```bash
python scripts/run_v03_execution_stress_grid.py
```

See
`docs/results/v0_3_execution_stress_grid/execution_stress_grid_summary.md`.
This artifact pairs each stressed run against an E1 reference by agent and seed,
then reports deltas for spread, latency, participation, impact, and combined
stress axes. It is mechanism evidence for execution-assumption sensitivity, not
a calibrated live transaction-cost forecast.

The FinAudit injected-defect pilot is generated with:

```bash
python scripts/run_v03_finaudit_pilot.py
```

See `docs/results/v0_3_finaudit_pilot/finaudit_pilot_summary.md`. This artifact
keeps the answer key private by default, publishes only task hashes and aggregate
scores, and reports cross-audit versus self-audit fixture performance with
precision, recall, F1, Wilson intervals, and difficulty breakdowns. Fixture
auditor scores validate the scoring path; they are not model-performance
evidence.

The FinAudit direct-model audit plan is generated with:

```bash
python scripts/build_v03_finaudit_direct_model_plan.py
```

See
`docs/results/v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan.md`.
This artifact pre-registers direct-provider model auditor calls over the public
task manifest while keeping answer keys and raw model responses private. It does
not call providers or report model audit performance.

The memory-contamination mechanism pilot is generated with:

```bash
python scripts/run_v03_memory_contamination.py
```

See `docs/results/v0_3_memory_contamination/memory_contamination_summary.md`.
This artifact runs a C0 synthetic memory-aware agent through clean and polluted
read-time memory states, reports paired dose-response deltas for
`memory_pollution_ratio` and `memory_driven_leverage_amplification`, and
publishes a C0/C1/C2 contamination-control table. C1 and C2 are control
contracts in this fixture, not completed real-data evidence.

The contamination-control readiness audit is generated with:

```bash
python scripts/build_v03_contamination_control_audit.py
```

See
`docs/results/v0_3_contamination_control_audit/contamination_control_audit.md`.
This artifact maps C0, C1, and C2 controls to public evidence. It currently
marks C0 as fixture mechanism evidence, C1 as contract-only, and C2 as
forward-freeze tooling present but still missing a committed future-window
result and walk-forward provenance.

The v0.3 power and detectable-effect note is generated with:

```bash
python scripts/run_v03_power_note.py
```

See `docs/results/v0_3_power_note/v0_3_power_note_summary.md`. This artifact
records synthetic paired-test power curves and the smallest detectable Cohen's d
within the configured grid for each repeat count. It is a planning and
claim-boundary artifact, not evidence that any model is superior. Rows below the
v0.3 LLM main-comparison threshold of 10 seeds and 3 samples per seed remain
pilot evidence.

The v0.3 variance decomposition artifact is generated with:

```bash
python scripts/build_v03_variance_decomposition.py
```

See `docs/results/v0_3_variance_decomposition/variance_decomposition.md`.
This artifact decomposes fixture direct API pilot rows into between-seed
market-path variance and within-seed repeated-sample variance. It validates the
reporting surface required by the protocol, but it is not model-performance or
model-stochasticity evidence.

The v0.3 claim-boundary audit is generated with:

```bash
python scripts/build_v03_claim_boundary_audit.py
```

See `docs/results/v0_3_claim_boundary_audit/claim_boundary_audit.md`. This
artifact checks public narrative surfaces and the evidence index for overclaim
risk, including unsupported profitability, best-model, investment-advice, and
headline scientific-claim wording. It keeps paper text aligned with the open
direct API model-matrix and external-reproduction gaps.

The external reproduction intake gate is generated with:

```bash
python scripts/build_v03_external_reproduction_gate.py
```

See
`docs/results/v0_3_external_reproduction_reports/external_reproduction_gate_summary.md`.
This artifact scans independent report JSON files, checks the v0.3
`protocol_id`, environment class, independent-reviewer flag, command success,
artifact hashes, and private-data boundary. The external reproduction gap
remains open until three accepted independent reports cover Windows/macOS,
Linux, and Colab/Binder.

External reviewers can generate a v0.3 no-key reproduction report with:

```bash
python scripts/run_v03_external_reproduction_pack.py \
  --environment-class linux \
  --report-author-type independent \
  --independent-reviewer
```

See `docs/reproduction_pack_v0_3.md`. Maintainer-authored reports are useful
smoke tests, but the gate counts only independent, successful, public-data-safe
reports.

The conservative evidence index is generated with:

```bash
python scripts/build_v03_evidence_index.py
```

See `docs/results/v0_3_evidence_index/v0_3_evidence_index.md`. It maps each
public v0.3 artifact to protocol-required evidence, statistical methods, claim
classes, and open gaps. It intentionally keeps `headline_scientific_claim_ready`
false until direct API model matrices and independent external reproduction
reports exist.

## Claim Boundary

Use the v0.3 protocol to support this kind of claim:

> TreLLM evaluates how LLM financial-agent conclusions change under execution
> assumptions, contamination controls, risk gates, and audit-trace defects.

Do not use the v0.3 protocol to claim:

> An LLM is proven to be profitable in live trading.
