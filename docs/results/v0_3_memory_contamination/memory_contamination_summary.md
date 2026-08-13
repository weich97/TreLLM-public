# TreLLM v0.3 Memory Contamination Pilot

This fixture bundle validates the v0.3 memory-contamination mechanism path.
It is not model-performance or trading-profit evidence.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_memory_contamination_c0_v0_3`
- Implemented tier: `C0`
- Declared tiers: `C0, C1, C2`
- Control-contract-only tiers: `C1, C2`
- Kinds: `fake_rejections, fake_violations`
- Doses: `0.0, 0.5`
- Decays: `1.0, 0.6`
- Primary outcome: `memory_driven_leverage_amplification`
- Claim boundary: Memory-contamination protocol fixture for C0 mechanism validation. It quantifies read-time memory pollution effects and tier controls; it is not model-performance or trading-profit evidence.

## Contamination Tier Controls

| Tier | Status | Required controls | Claim scope |
| --- | --- | --- | --- |
| C0 | implemented | repository-generated paths; published seeds; no historical symbol identity | no-known-training-contamination controlled memory mechanism evaluation |
| C1 | control-contract-only | symbol anonymization; relative timestamp masking; memorization probe; data hash | residual contamination risk must be measured before C1 rows support scientific claims |
| C2 | control-contract-only | dated hash commitment; future evaluation window; no post-freeze scenario edits; walk-forward provenance | strongest public contamination evidence, not produced by this fixture bundle |

## Dose Response

| Kind | Decay | Risk | Dose | Outcome | Delta vs dose 0 | q value | Cohen's d |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: |
| fake_rejections | 0.6 | max-position | 0.5 | memory_pollution_ratio | 0.357100 | 0.750000 | 11.553002 |
| fake_rejections | 0.6 | max-position | 0.5 | memory_driven_leverage_amplification | -0.213611 | 0.750000 | -3.490048 |
| fake_rejections | 1.0 | max-position | 0.5 | memory_pollution_ratio | 0.386111 | 0.750000 |  |
| fake_rejections | 1.0 | max-position | 0.5 | memory_driven_leverage_amplification | -0.176666 | 0.750000 | -74.960744 |
| fake_violations | 0.6 | max-position | 0.5 | memory_pollution_ratio | 0.357100 | 0.750000 | 11.553002 |
| fake_violations | 0.6 | max-position | 0.5 | memory_driven_leverage_amplification | -0.368592 | 0.750000 | -21.798541 |
| fake_violations | 1.0 | max-position | 0.5 | memory_pollution_ratio | 0.386111 | 0.750000 |  |
| fake_violations | 1.0 | max-position | 0.5 | memory_driven_leverage_amplification | -0.375000 | 0.750000 | -159.162691 |

## Manipulation Check

| Kind | Dose | Decay | Risk | Runs | Pollution ratio | Leverage amplification |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| fake_rejections | 0.0 | 0.6 | max-position | 2 | 0.000000 | 0.753750 |
| fake_rejections | 0.0 | 1.0 | max-position | 2 | 0.000000 | 0.753750 |
| fake_rejections | 0.5 | 0.6 | max-position | 2 | 0.357100 | 0.540139 |
| fake_rejections | 0.5 | 1.0 | max-position | 2 | 0.386111 | 0.577084 |
| fake_violations | 0.0 | 0.6 | max-position | 2 | 0.000000 | 0.753750 |
| fake_violations | 0.0 | 1.0 | max-position | 2 | 0.000000 | 0.753750 |
| fake_violations | 0.5 | 0.6 | max-position | 2 | 0.357100 | 0.385158 |
| fake_violations | 0.5 | 1.0 | max-position | 2 | 0.386111 | 0.378750 |
