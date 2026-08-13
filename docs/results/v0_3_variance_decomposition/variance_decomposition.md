# TreLLM v0.3 Variance Decomposition

This artifact verifies the v0.3 variance-decomposition table shape on fixture direct API pilot rows.
It separates between-seed market-path variance from within-seed repeated-sample variance.

- Protocol: `trellm-v0.3-protocol`
- Source artifact: `docs/results/v0_3_direct_api_pilot/direct_api_pilot_rows.csv`
- Source rows: `4`
- Variance rows: `4`
- Claim boundary: This fixture validates variance-decomposition reporting for v0.3. It uses protocol-fixture rows and does not support model-performance or model-stochasticity claims.

## Rows

| Provider | Model | Scenario | Tier | Execution | Metric | Seeds | Samples | Between seed var | Within seed var | Within share |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| fixture-direct-api | fixture-llm-policy-v0 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | total_return | 2 | 4 | 8e-06 | 2e-08 | 0.002493765586 |
| fixture-direct-api | fixture-llm-policy-v0 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | max_drawdown | 2 | 4 | 5e-07 | 1.25e-07 | 0.2 |
| fixture-direct-api | fixture-llm-policy-v0 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | execution_fill_rate | 2 | 4 | 0.0002 | 5e-05 | 0.2 |
| fixture-direct-api | fixture-llm-policy-v0 | synthetic_calm_trend_c0_v0_3 | C0 | E1 | risk_clipped_decisions | 2 | 4 | 0.0 | 4.5 | 1.0 |
