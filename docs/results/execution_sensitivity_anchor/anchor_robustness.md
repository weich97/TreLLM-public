# Buy-and-Hold Anchor Initialization Robustness

Cold anchor builds its full position from cash; warm-start anchor is
seeded with the same holdings free of construction cost. A large
`init_cost_gap` at stressed levels means the cold anchor's penalty is
partly an initialization artifact rather than a fair execution result.

| Regime | Level | Cold return | Warm-start return | Init-cost gap |
| --- | --- | ---: | ---: | ---: |
| calm | E0_ideal | +0.0932 | +0.0932 | -0.0000 |
| calm | E1_default_stress | +0.0885 | +0.0931 | +0.0045 |
| calm | E2_harsh_corner | +0.0723 | +0.0925 | +0.0203 |
| high_vol | E0_ideal | +0.0994 | +0.0994 | +0.0000 |
| high_vol | E1_default_stress | +0.1044 | +0.0987 | -0.0057 |
| high_vol | E2_harsh_corner | +0.0924 | +0.0996 | +0.0072 |
| jump_tail | E0_ideal | +0.1036 | +0.1036 | -0.0000 |
| jump_tail | E1_default_stress | +0.0870 | +0.1016 | +0.0146 |
| jump_tail | E2_harsh_corner | +0.0609 | +0.1072 | +0.0463 |

Mean init-cost gap: ideal +0.0000, harsh corner +0.0246. The gap widens under stress, so part of the anchor's harsh-corner disadvantage is construction cost; we report the warm-start anchor alongside the cold one and separate this from the leaderboard-fragility result.
