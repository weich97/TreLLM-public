# TreLLM v0.3 Direct API Matrix Plan

This artifact pre-registers the direct API call matrix and checks whether required credential environment variables are present.
It does not make provider calls and does not count as model-performance evidence.

- Protocol: `trellm-v0.3-protocol`
- Planned rows: `450`
- Coverage groups: `15`
- Threshold-target groups: `15`
- Ready groups: `0`
- Ready to run: `False`
- Claim boundary: This is a pre-registered direct API matrix plan and credential preflight, not model-performance evidence. The direct_api_model_matrix gap remains open until non-fixture provider manifests and submissions pass the matrix gate.

## Coverage Groups

| Provider | Model | Scenario | Tier | Execution | Rows | Seeds | Min samples/seed | Env var | Env present | Status | Blocking reasons |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| deepseek | deepseek-v4-flash | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | DEEPSEEK_API_KEY | false | blocked | credential_env_var_missing |
| deepseek | deepseek-v4-flash | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | DEEPSEEK_API_KEY | false | blocked | credential_env_var_missing |
| deepseek | deepseek-v4-flash | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | DEEPSEEK_API_KEY | false | blocked | credential_env_var_missing |
| deepseek | deepseek-v4-pro | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | DEEPSEEK_API_KEY | false | blocked | credential_env_var_missing |
| deepseek | deepseek-v4-pro | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | DEEPSEEK_API_KEY | false | blocked | credential_env_var_missing |
| deepseek | deepseek-v4-pro | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | DEEPSEEK_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5 | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5 | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5-turbo | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5-turbo | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5-turbo | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5.2 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5.2 | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
| glm | glm-5.2 | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 | 3 | GLM_API_KEY | false | blocked | credential_env_var_missing |
