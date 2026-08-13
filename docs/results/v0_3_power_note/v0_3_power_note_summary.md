# TreLLM v0.3 Power and Detectable-Effect Note

This artifact is a planning and claim-boundary note for the v0.3 protocol.
It estimates synthetic paired-test power over repeat counts and effect sizes, then records the smallest effect size in the grid that reaches each target power.

- Protocol: `trellm-v0.3-protocol`
- Alpha: `0.05`
- Power rows: `24`
- Detectable-effect rows: `8`
- Minimum repeats for alpha 0.05: `6`
- Claim boundary: This power note constrains repeat-count and detectable-effect claims for v0.3 planning; it is not evidence of model superiority or trading profitability.
- Structural note: With n=5 paired rows, an exact two-sided sign-flip test has minimum p=2/32=0.0625, so it cannot reject under alpha=0.05. The v0.3 planning grid therefore starts at n=6.

## Detectable Effects

| Repeats | Target power | Minimum detectable Cohen's d | Status |
| ---: | ---: | ---: | --- |
| 6 | 0.50 | 1.2 | detected |
| 6 | 0.80 | 2 | detected |
| 10 | 0.50 | 0.8 | detected |
| 10 | 0.80 | 1.2 | detected |
| 20 | 0.50 | 0.5 | detected |
| 20 | 0.80 | 0.8 | detected |
| 30 | 0.50 | 0.5 | detected |
| 30 | 0.80 | 0.8 | detected |

## Interpretation

Rows below the v0.3 LLM main-comparison threshold of 10 seeds and 3 samples per seed remain pilot evidence.
The note should be cited when choosing matrix size or explaining why a model comparison is underpowered.
