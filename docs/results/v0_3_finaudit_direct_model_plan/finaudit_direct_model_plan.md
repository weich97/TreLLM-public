# TreLLM v0.3 FinAudit Direct-Model Plan

This artifact pre-registers direct-model auditor calls for FinAudit tasks.
It does not call providers, publish raw responses, or publish answer keys.

- Protocol: `trellm-v0.3-protocol`
- Source task manifest: `docs/results/v0_3_finaudit_pilot/finaudit_pilot_task_manifest.csv`
- Planned rows: `16`
- Task count: `8`
- Ready groups: `0`
- Answer key public: `False`
- Claim boundary: This artifact pre-registers direct-model FinAudit auditor calls. It does not call providers, publish answer keys, publish raw responses, or support model audit-performance claims.

## Coverage Groups

| Provider | Model | Condition | Tasks | Rows | Env var | Env present | Status | Blocking reasons |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |
| openai | gpt-5.5 | cross-audit | 8 | 8 | OPENAI_API_KEY | false | blocked | credential_env_var_missing |
| openai | gpt-5.5 | self-audit | 8 | 8 | OPENAI_API_KEY | false | blocked | credential_env_var_missing |
