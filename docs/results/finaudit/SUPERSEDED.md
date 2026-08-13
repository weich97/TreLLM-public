# Superseded tables in this directory

Three CSVs here were built from runs collected under the **trading-analyst**
system prompt, before the audit arms were re-collected under a neutral audit
role, and one of them also uses a four-producer matrix that no longer exists.
They are retained because deleting superseded evidence is worse than labelling
it, but nothing in the technical report is computed from them and they should
not be cited.

| Superseded file | Built from | Replaced by |
| --- | --- | --- |
| `ablation_family.csv` | `outputs/audit_pairs_eval{,_constraint,_cot,_sc}` (v1 prompt) | `intervention_v2.csv` |
| `paired_intervention.csv` | `outputs/audit_pairs_eval{,_constraint}` (v1 prompt) | `intervention_v2.csv` |
| `self_bias_matrix.csv` | `outputs/audit_matrix/` (v1 prompt, 4 producers) | `self_audit_v2.csv` |

The numbers differ materially, which is the point of the re-collection. For
example the constraint arm for deepseek-v4-pro reads 0.333 -> 0.950 in the
superseded table and 0.300 -> 0.833 in the current one, and the self-consistency
arm reads 0.500 in the superseded table against 0.500 (majority) but from a
contaminated sample-0 that replayed the deterministic arm's response; the
current table is computed from the re-collected arm.

Regenerate the current tables with:

    python scripts/build_intervention_v2.py
