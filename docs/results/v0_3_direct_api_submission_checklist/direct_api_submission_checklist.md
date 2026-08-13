# TreLLM v0.3 Direct API Submission Checklist

This checklist is for contributors preparing public direct API rows for TreLLM v0.3.
It focuses on redaction, manifest binding, matrix-gate readiness, and claim boundaries.

- Protocol: `trellm-v0.3-protocol`
- Checklist items: `14`
- Protocol manifest fields covered by schema: `True`
- Claim boundary: This checklist constrains public direct API submissions, redaction, and claim boundaries. It is not provider-performance evidence and does not close the direct_api_model_matrix gap.

## Items

| Phase | Item | Blocking level | Requirement | Verification | Evidence path |
| --- | --- | --- | --- | --- | --- |
| planning | plan-row-bound | headline-scientific-claim | Each direct API row is present in the pre-registered matrix plan before the provider call is made. | Run scripts/build_v03_direct_api_matrix_plan.py and match provider, model, scenario, tier, execution level, seed, and sample index. | `docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv` |
| manifest | direct-provider-route | headline-scientific-claim | Provider manifests use provider_route=direct-api; routed-provider rows remain appendix or historical evidence. | Validate each manifest with scripts/validate_direct_provider_manifest.py. | `schemas/direct_provider_manifest.schema.json` |
| manifest | model-version-endpoint | headline-scientific-claim | Provider, model_id, model_version_or_release, and api_endpoint_family are recorded without ambiguity. | Check direct provider manifest fields provider, model_id, model_version_or_release, and api_endpoint_family. | `schemas/direct_provider_manifest.schema.json` |
| manifest | call-window-failure-accounting | headline-scientific-claim | Call start, completion, request-id redaction, retry_count, parse_status, and cache_status are explicit. | Check call_window, response.parse_status, and cache fields; failed/partial rows must not be silently dropped. | `schemas/direct_provider_manifest.schema.json` |
| manifest | sampling-parameters | headline-scientific-claim | Temperature, top_p, and max_tokens are recorded for every direct provider call. | Check sampling.temperature, sampling.top_p, and sampling.max_tokens in the manifest. | `schemas/direct_provider_manifest.schema.json` |
| redaction | hash-only-prompt-response | public-artifact-safety | Public artifacts expose prompt_sha256 and response_sha256, not raw provider prompt or response text. | Require prompt.raw_prompt_public=false, response.raw_response_public=false, and public privacy scan success. | `schemas/direct_provider_manifest.schema.json` |
| redaction | secret-and-account-data-removed | public-artifact-safety | Provider secrets and private account data are removed before any public submission. | Require redaction.provider_secrets_removed=true and redaction.private_account_data_removed=true. | `schemas/direct_provider_manifest.schema.json` |
| binding | run-binding | headline-scientific-claim | Scenario, contamination tier, execution level, seed, sample index, and trajectory manifest hash bind the provider call to a replayable run. | Check run_binding fields in the direct provider manifest. | `schemas/direct_provider_manifest.schema.json` |
| submission | submission-manifest-hash | public-artifact-safety | Benchmark submissions include the direct_provider_manifest hash and exclude raw prompt/response payloads. | Check trajectory_manifest.artifact_hashes.direct_provider_manifest plus raw_prompts_included=false and raw_responses_included=false. | `schemas/benchmark_submission.schema.json` |
| submission | evidence-tags-and-claim-class | headline-scientific-claim | Direct rows use evidence tags and claim_scope to prevent over-reading pilot, fixture, cached, or redacted evidence. | Check evidence.tags, evidence.claim_scope, claim_class, evidence_tier, and boundary_notes. | `schemas/benchmark_submission.schema.json` |
| submission | execution-contamination-labels | headline-scientific-claim | Result rows label execution_level and contamination_tier before they can enter v0.3 main comparisons. | Cross-check direct provider run_binding with benchmark submission execution_config and scenario metadata. | `benchmarks/v0.3/protocol.json` |
| validation | matrix-gate | headline-scientific-claim | Direct rows pass the matrix gate or remain explicitly labeled as pilot/incomplete evidence. | Run scripts/build_v03_direct_api_matrix_gate.py against submission and provider manifest directories. | `docs/results/v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json` |
| validation | privacy-scan | public-artifact-safety | Generated public artifacts pass the public artifact privacy scanner before publication. | Run scripts/scan_public_artifacts.py on generated outputs, docs/results, and benchmark submissions. | `scripts/scan_public_artifacts.py` |
| claim-boundary | no-profitability-claim | paper-claim-boundary | Direct API rows do not support trading-profitability claims unless separately backed by live, regulated, and externally audited evidence. | Check claim_scope and report text for evaluation reliability language rather than investment advice or profitability claims. | `docs/claim_boundaries.md` |
