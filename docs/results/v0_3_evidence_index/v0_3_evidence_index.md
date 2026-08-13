# TreLLM v0.3 Evidence Index

This index maps generated public artifacts to the v0.3 protocol claims.
It is deliberately conservative: fixture and pilot artifacts do not support headline scientific model-performance claims.

- Protocol: `trellm-v0.3-protocol`
- Present artifacts: `17 / 17`
- Public-artifact-covered protocol artifacts: `21 / 21`
- Fixture-covered protocol artifacts: `9 / 21`
- Open gaps: `1`
- Headline scientific claim ready: `False`
- Claim boundary: This index maps public v0.3 artifacts to protocol claims. Current artifacts validate protocol plumbing and pilot mechanisms; they do not yet support headline scientific model-performance claims.

## Artifact Map

| Artifact | Claim area | Stage | Methods | Supports headline claim | Status |
| --- | --- | --- | --- | --- | --- |
| direct_api_pilot | direct API provenance | protocol-fixture | seed/sample manifest coverage | false | present |
| direct_api_matrix_gate | direct API model matrix threshold gate | threshold-gate | direct_manifest_hash_binding;seed_sample_threshold_gate | false | present |
| direct_api_model_matrix_plan | direct API model matrix run plan and credential preflight | planning-note | pre_registered_10x3_matrix_plan;credential_env_var_preflight | false | present |
| direct_api_call_packets | direct API call-packet execution queue | planning-note | deterministic_call_packet_hashing;redaction_contract_binding | false | present |
| direct_api_submission_checklist | direct API redaction and submission checklist | planning-note | schema_field_coverage_check;redaction_submission_checklist | false | present |
| claim_boundary_audit | public narrative claim-boundary audit | planning-note | claim_boundary_text_audit;evidence_index_gap_check | false | present |
| execution_ladder | execution assumption sensitivity | protocol-fixture | kendall_tau;top_k_jaccard;bootstrap_ci | false | present |
| execution_stress_grid | E2 execution stress-grid sensitivity | protocol-fixture | paired_seed_delta_vs_e1_reference;execution_assumption_axis_sweep | false | present |
| finaudit_pilot | financial trace audit | protocol-fixture | precision;recall;f1;wilson_interval;difficulty_breakdown | false | present |
| finaudit_direct_model_plan | FinAudit direct-model auditor call plan | planning-note | direct_model_auditor_plan;private_answer_key_boundary | false | present |
| memory_contamination | memory contamination mechanism | protocol-fixture | paired_bootstrap_delta;BH-FDR q_value;bootstrap_ci | false | present |
| contamination_control_audit | contamination-tier readiness and claim boundaries | planning-note | contamination_tier_readiness_audit;forward_freeze_tooling_check | false | present |
| power_detectable_effect_note | statistical power and detectable effects | planning-note | paired_sign_flip_permutation_power;detectable_effect_grid | false | present |
| variance_decomposition | between-seed and within-seed variance decomposition | planning-note | variance_decomposition;between_within_seed_variance_components | false | present |
| external_reproduction_gate | external reproduction intake and environment coverage | threshold-gate | environment_coverage_gate;independent_report_count_gate | false | present |
| replication_pack_verification | no-key reproduction pack machine self-verification | threshold-passing | frozen_expected_value_comparison;trajectory_hash_verification | false | present |
| direct_api_matrix_results | headline direct API matrix results (E0/E1 x three C0 regimes) | threshold-passing | seed_sample_threshold_gate;kendall_tau_ranking_stability | true | present |

## Protocol Coverage

| Required artifact | Status | Evidence | Boundary |
| --- | --- | --- | --- |
| direct-provider manifest schema or contract | covered-by-fixture | direct_api_pilot | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| raw seed rows | covered-by-fixture | direct_api_pilot;execution_ladder;memory_contamination | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| aggregate rows | covered-by-fixture | execution_ladder;memory_contamination | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| significance table | covered-by-fixture | memory_contamination | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| ranking-stability table | covered-by-fixture | execution_ladder | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| contamination probe report | covered-by-fixture | memory_contamination | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| contamination-control readiness audit | covered-by-artifact | contamination_control_audit | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| execution-sensitivity report | covered-by-fixture | execution_ladder | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| execution stress-grid report | covered-by-fixture | execution_stress_grid | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| FinAudit pilot report | covered-by-fixture | finaudit_pilot | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| FinAudit direct-model audit plan | covered-by-artifact | finaudit_direct_model_plan | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| power curve or detectable effect note | covered-by-artifact | power_detectable_effect_note | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| variance decomposition table | covered-by-artifact | variance_decomposition | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| claim-boundary audit | covered-by-artifact | claim_boundary_audit | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| direct API redaction and submission checklist | covered-by-artifact | direct_api_submission_checklist | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| direct API model matrix plan | covered-by-artifact | direct_api_model_matrix_plan | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| direct API call packet manifest | covered-by-artifact | direct_api_call_packets | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| direct API model matrix gate | covered-by-artifact | direct_api_matrix_gate | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| external reproduction report gate | covered-by-artifact | external_reproduction_gate | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| external reproduction bundle | covered-by-artifact | replication_pack_verification | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |
| direct API matrix results | covered-by-artifact | direct_api_matrix_results | Public artifact coverage supports protocol plumbing and claim boundaries; scientific claims require non-fixture direct API rows and scale thresholds. |

## Open Gaps

| Gap | Required for | Missing evidence | Current status |
| --- | --- | --- | --- |
| external_reproduction_reports | reproduction criterion: at least one accepted independent external report | a passing pack self-verification report, or at least one accepted independent external reproduction report (intake gate remains open either way) | v0.3 intake gate exists; no accepted independent reports are present |
