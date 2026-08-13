# Errata — sampling-variance decomposition

`sampling_variance.csv` in this directory is preserved as released: it is the
artifact the released execution-sensitivity analysis reports from. Two
corrections apply to it, both found by an adversarial audit of the repository on
2026-08-11 and both affecting the reported summary rather than the raw runs.

## 1. The between-seed component was biased, so the within-seed share was too low

`variance_components` estimated the between-group component as the variance of
the group means. That quantity estimates `sigma_b^2 + sigma_w^2/n`, not
`sigma_b^2`, so the denominator of the within-seed share was inflated and the
share was biased downward — that is, it made provider sampling look like a
*smaller* fraction of total variance than it is. The implementation now
subtracts the sampling term (floored at zero).

Recomputed on the same 16 comparable cells of `merged_runs.csv`:

| Quantity | As released (biased) | Corrected |
| --- | ---: | ---: |
| Mean within-seed share | 0.140 | 0.155 |
| Maximum within-seed share | 0.447 | 0.526 |

Largest per-cell movements: `calm / E0_ideal / deepseek-v4-pro` 0.447 -> 0.526;
`calm / E0_ideal / gemini-3.1-pro` 0.392 -> 0.451; `calm / E1_default_stress /
deepseek-v4-pro` 0.320 -> 0.358.

Effect on the reported summary: the reported average (~15%) is unchanged to the
precision quoted, but the stated upper end of the range should read ~0.53 rather
than ~0.45. The direction matters for the argument — sampling noise is somewhat
larger than reported, not smaller.

## 2. The "smallest share" cell was misidentified

The released summary states that the within-seed share is smallest "exactly where the
headline reordering occurs under stress". The headline reordering is the
high-volatility E0-vs-E1 contrast, whose E1 share is 0.136 (E0: 0.142). The
value 0.027 belongs to the high-volatility *harsh corner*, a different level.
The correct statement is that the share is smallest at the harsh corner, and is
near the study average in the cell where the headline reordering occurs.

## Status

The code is fixed and covered by a regression test that documents the estimator.
`sampling_variance.csv` is deliberately **not** regenerated, so that the released
artifact continues to match the released summary and this note carries the
difference. Any new analysis uses the corrected estimator.
