# TreLLM v0.3 Direct API Matrix Gate

This artifact verifies whether direct API model rows satisfy the v0.3 seed/sample threshold for main-paper scientific comparisons.
It does not run provider calls and does not promote fixture rows to model-performance evidence.

- Protocol: `trellm-v0.3-protocol`
- Rows: `900`
- Valid rows: `900`
- Coverage groups: `30`
- Main-threshold groups: `30`
- Headline scientific claim ready: `True`
- Claim boundary: This gate verifies direct API row provenance and seed/sample coverage. Rows tagged as protocol fixtures or below the threshold remain pilot evidence.
- Open-gap policy: The direct_api_model_matrix gap remains open until at least one non-fixture direct API group meets the v0.3 threshold of 10 seeds and 3 samples per seed.

## Coverage Groups

| Provider | Model | Scenario | Tier | Execution | Rows | Seeds | Min samples/seed | Main threshold | Blocking reasons |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| deepseek | deepseek-v4-flash | synthetic_calm_trend_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-flash | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-flash | synthetic_high_volatility_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-flash | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-flash | synthetic_jump_tail_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-flash | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-pro | synthetic_calm_trend_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-pro | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-pro | synthetic_high_volatility_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-pro | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-pro | synthetic_jump_tail_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| deepseek | deepseek-v4-pro | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5 | synthetic_calm_trend_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5 | synthetic_high_volatility_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5 | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5 | synthetic_jump_tail_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5 | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5-turbo | synthetic_calm_trend_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5-turbo | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5-turbo | synthetic_high_volatility_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5-turbo | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5-turbo | synthetic_jump_tail_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5-turbo | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5.2 | synthetic_calm_trend_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5.2 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5.2 | synthetic_high_volatility_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5.2 | synthetic_high_volatility_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5.2 | synthetic_jump_tail_c0_v0_3 | C0 | E0 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
| glm | glm-5.2 | synthetic_jump_tail_c0_v0_3 | C0 | E1 | 30 | 10 observed / 10 eligible | 3 observed / 3 eligible | true |  |
