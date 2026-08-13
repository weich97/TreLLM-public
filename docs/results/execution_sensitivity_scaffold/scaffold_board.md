# Memory-Scaffold Board vs Plain Direct Board

Scaffold board = 7 classical baselines + deterministic memory-aware agent
+ deepseek-v4-pro+mem + glm-5+mem (direct APIs, memory-aware exposure
overlay wrapping the LLM signal). Plain reference = the b1 9-agent direct
board at 12 steps, recomputed with the identical estimator. Cells are
mean Sharpe over seeds; 95% cluster bootstrap over seeds, 10,000 draws.

| Board | Scenario | Levels | Agents | Seeds | tau_b | 95% CI |
| --- | --- | --- | ---: | ---: | ---: | --- |
| scaffold | calm | E0_ideal->E1_default_stress | 10 | 10 | +0.899 | [+0.629, +0.955] |
| scaffold | calm | E0_ideal->E2_harsh_corner | 10 | 10 | +0.809 | [+0.584, +0.944] |
| scaffold | high_vol | E0_ideal->E1_default_stress | 10 | 10 | +0.584 | [+0.270, +0.764] |
| scaffold | high_vol | E0_ideal->E2_harsh_corner | 10 | 10 | +0.629 | [+0.135, +0.727] |
| scaffold_matched9 | calm | E0_ideal->E1_default_stress | 9 | 10 | +0.889 | [+0.611, +0.944] |
| scaffold_matched9 | calm | E0_ideal->E2_harsh_corner | 9 | 10 | +0.778 | [+0.514, +0.944] |
| scaffold_matched9 | high_vol | E0_ideal->E1_default_stress | 9 | 10 | +0.500 | [+0.167, +0.722] |
| scaffold_matched9 | high_vol | E0_ideal->E2_harsh_corner | 9 | 10 | +0.611 | [+0.000, +0.722] |
| plain_direct | high_vol | E0_ideal->E1_default_stress | 9 | 10 | +0.444 | [+0.167, +0.611] |
