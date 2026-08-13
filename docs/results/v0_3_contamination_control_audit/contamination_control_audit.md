# TreLLM v0.3 Contamination Control Audit

This artifact maps C0/C1/C2 contamination controls to current public evidence.

- Protocol: `trellm-v0.3-protocol`
- Tiers audited: `3`
- Fixture-ready tiers: `1`
- Contract-only tiers: `2`
- Scientific-ready tiers: `0`
- Forward-freeze tooling present: `True`
- Claim boundary: This audit maps v0.3 contamination tiers to current public evidence. C0 is fixture mechanism evidence; C1 and C2 remain contract-only and must not support scientific contamination-control claims yet.

## Tier Readiness

| Tier | Name | Readiness | Memory artifact status | Blocking gaps | Claim scope |
| --- | --- | --- | --- | --- | --- |
| C0 | synthetic | fixture-mechanism-ready | implemented |  | no-known-training-contamination controlled evaluation; current public artifact is C0 fixture mechanism evidence, not model-performance evidence. |
| C1 | anonymized_real | contract-only | control-contract-only | anonymized_real_rows_missing;memorization_probe_rows_missing | pattern-recognition evaluation with residual contamination risk measured by probes; control requirements are declared but not yet backed by public rows. |
| C2 | forward_frozen | tooling-present-contract-only | control-contract-only | forward_window_commitment_missing;post_window_results_missing;walk_forward_provenance_missing | strongest public evidence against memorized historical answers; freeze tooling exists, but no committed future-window result is present in v0.3 public artifacts. |
