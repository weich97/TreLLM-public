# E2: Validation-Latency Microbenchmark (Live-Readiness Control Plane)

Per-layer wall-clock latency of the deterministic live-readiness control plane (live-readiness E2). Pure local computation: zero LLM calls, zero network, deterministic synthetic market snapshot, fixed session timestamps.

- Generated: 2026-07-04T09:45:56+00:00
- Command: `python scripts/run_live_readiness_e2.py`
- Iterations: 200 per layer (schema layer pools 6 artifacts x 200; orchestrator-step row pools 4 steps x 200), warmup 10 excluded
- Scaling arm: 100 sessions per order count
- Timer: `time.perf_counter_ns`; percentiles are nearest-rank over the sorted samples
- Fixture: one reconciled weekly session, 3 symbols / 3 limit orders, dry-run engine, timestamps 2026-07-02T09:00:00Z -> 2026-07-02T09:07:00Z

## Machine

| Field | Value |
| --- | --- |
| cpu_model | `Intel(R) Xeon(R) W-2245 CPU @ 3.90GHz` |
| logical_cores | `16` |
| os | `Windows-10-10.0.19045-SP0` |
| python | `3.12.10` |
| perf_counter_resolution_ns | `100.0` |

## Headline layers

| Layer | Samples | P50 (ms) | P95 (ms) | P99 (ms) |
| --- | ---: | ---: | ---: | ---: |
| Schema validation (per artifact) | 1200 | 0.5616 | 1.3274 | 1.3742 |
| Single-artifact validators (all six) | 200 | 2.7269 | 2.8195 | 2.8742 |
| Hash computation + binding checks | 200 | 0.4387 | 0.4586 | 0.4939 |
| Cross-artifact preflight (full bundle) | 200 | 6.8461 | 10.7743 | 20.8887 |
| Orchestrator step overhead (per step) | 800 | 16.5256 | 59.5464 | 68.2518 |
| LLM decision call (measured anchor) | 3 | mean 8682.86 | range 5204.72-11945.79 | |

## Anchor comparison

- One measured LLM decision call (docs/results/llm_live_baseline.md): mean 8682.86 ms, min 5204.72 ms, max 11945.79 ms.
- Full-bundle cross-artifact preflight P95 = 10.7743 ms => anchor mean / preflight P95 = 806x (2.9 orders of magnitude).
- Entire gated session chain (propose+approve+execute+reconcile+final gate) P95 = 136.9252 ms => anchor mean / chain P95 = 63x (1.8 orders of magnitude).

## All layers

| Layer | Samples | Orders | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | Max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `schema_validation_per_artifact` | 1200 | 3 | 0.5616 | 1.3274 | 1.3742 | 0.7683 | 1.6068 |
| `schema_validation_capability_manifest` | 200 | 3 | 0.4354 | 0.4619 | 0.4887 | 0.439 | 0.5616 |
| `schema_validation_handoff` | 200 | 3 | 1.017 | 1.0812 | 1.1452 | 1.0219 | 1.2918 |
| `schema_validation_approval` | 200 | 3 | 0.2948 | 0.3144 | 0.3587 | 0.2971 | 0.3764 |
| `schema_validation_response` | 200 | 3 | 1.3165 | 1.3633 | 1.4564 | 1.3172 | 1.6068 |
| `schema_validation_operator_runbook` | 200 | 3 | 1.2335 | 1.3233 | 1.3855 | 1.254 | 1.4117 |
| `schema_validation_preflight_bundle` | 200 | 3 | 0.2792 | 0.3054 | 0.337 | 0.2804 | 0.3696 |
| `single_artifact_validators_all_six` | 200 | 3 | 2.7269 | 2.8195 | 2.8742 | 2.7261 | 2.9289 |
| `risk_gate` | 200 | 3 | 0.0118 | 0.0121 | 0.0125 | 0.0118 | 0.0135 |
| `hash_binding_checks` | 200 | 3 | 0.4387 | 0.4586 | 0.4939 | 0.4356 | 0.5009 |
| `journal_chain_verify` | 200 | 3 | 0.2304 | 0.2496 | 0.2831 | 0.2318 | 0.2914 |
| `cross_artifact_preflight_full_bundle` | 200 | 3 | 6.8461 | 10.7743 | 20.8887 | 7.4142 | 23.2883 |
| `step_propose` | 200 | 3 | 21.557 | 25.2744 | 27.7955 | 20.9737 | 29.225 |
| `step_approve` | 200 | 3 | 13.671 | 16.3059 | 17.0409 | 13.4551 | 36.1027 |
| `step_execute` | 200 | 3 | 13.8252 | 17.1135 | 18.7214 | 13.9393 | 27.4927 |
| `step_reconcile` | 200 | 3 | 50.0947 | 66.1646 | 77.5443 | 50.556 | 100.0414 |
| `final_gate` | 200 | 3 | 13.9581 | 24.7194 | 25.8831 | 15.6139 | 27.3406 |
| `orchestrator_step` | 800 | 3 | 16.5256 | 59.5464 | 68.2518 | 24.731 | 100.0414 |
| `full_chain_session` | 200 | 3 | 113.9331 | 136.9252 | 150.3884 | 114.5379 | 170.1748 |

## Scaling with order count (full chain per session)

| Layer | Samples | Orders | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | Max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `scaling_full_chain_n1` | 100 | 1 | 118.1278 | 139.2928 | 144.7799 | 117.3238 | 156.1063 |
| `scaling_full_chain_n2` | 100 | 2 | 114.5856 | 138.1617 | 152.6934 | 116.6298 | 249.9523 |
| `scaling_full_chain_n5` | 100 | 5 | 117.6713 | 145.1612 | 168.498 | 120.7567 | 174.4211 |
| `scaling_full_chain_n10` | 100 | 10 | 124.5686 | 148.7872 | 154.4079 | 126.7083 | 189.477 |
| `scaling_full_chain_n25` | 100 | 25 | 127.3835 | 157.9583 | 185.1421 | 130.1497 | 195.9928 |
| `scaling_full_chain_n50` | 100 | 50 | 126.5873 | 155.1808 | 164.0582 | 130.6451 | 164.9722 |

The full chain includes every filesystem write, JSON Schema reload/recompile, hash recomputation, and journal append the deployed weekly path performs; the E3 sweep (docs/results/live_readiness_e3/) consumes the `scaling_full_chain_n*` P95 values as its per-session compute-cost input.

