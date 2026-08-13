# E1: Fault-Injection Interception Matrix (Airlock Control Plane)

Adversarial single-defect faults across six families are pushed through the five validation layers in deployment order; each variant is attributed to the first layer that rejects it, or recorded as an escape. Pure local computation: zero LLM calls, zero network.

- Generated: 2026-08-09T09:48:54+00:00
- Command: `python scripts/run_airlock_faults.py`
- Variants: 60 per family (20 reserved for out-of-catalog fuzzing), seed 2027
- Total faulted bundles: 365 across 6 headline families + 1 auxiliary
- Review time (`--now`): 2026-07-02T09:07:00Z; template is one reconciled dry-run session
- Wall clock: 6.7s

## Machine

| Field | Value |
| --- | --- |
| cpu_model | `Intel(R) Xeon(R) W-2245 CPU @ 3.90GHz` |
| logical_cores | `16` |
| os | `Windows-10-10.0.19045-SP0` |
| python | `3.12.10` |

## Headline interception matrix

Cell values are the percentage of a family's variants whose *first-intercepting* layer is that row. The Total row carries the 95% Wilson interval over the family's variants; per-cell intervals are in `e1_matrix.csv`.

| First-intercepting layer | F1 identifier | F2 capability | F3 approval | F4 response | F5 clock | F6 runbook |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Schema validation | 63.3 | 61.7 | 61.7 | 71.7 | 81.7 | 75.0 |
| Single-artifact validator | 6.7 | 3.3 | 3.3 | 10.0 | 1.7 | 8.3 |
| Approval/hash binding | 18.3 | 18.3 | 18.3 | 0.0 | 3.3 | 0.0 |
| Cross-artifact preflight | 0.0 | 11.7 | 0.0 | 8.3 | 3.3 | 6.7 |
| Orchestrator re-validation | 0.0 | 0.0 | 6.7 | 0.0 | 0.0 | 0.0 |
| **Total intercepted (%)** | 88.3 [78,94] | 95.0 [86,98] | 90.0 [80,95] | 90.0 [80,95] | 90.0 [80,95] | 90.0 [80,95] |
| **Escapes (count)** | 7 | 3 | 6 | 6 | 6 | 6 |

**Overall:** 331/365 variants intercepted = 90.68% (95% Wilson [87.26, 93.26]); 34 escapes.

## Auxiliary families (outside the six-column headline)

| Family | Variants | Intercepted (%) | Escapes |
| --- | ---: | ---: | ---: |
| F7 journal chain (aux) | 5 | 100.0 [57,100] | 0 |

The append-only journal is not one of the six headline columns of the interception matrix, but `verify_journal_chain` is a real guard (orchestrator/audit layer) and is exercised here.

## Escape autopsy and co-evolution

34 escapes: 5 class (a) schema-expressible but unchecked, 0 class (b) requires semantic cross-artifact checking, 29 class (c) requires a human.

| Class | Target field | Count | Families | Mechanism | Proposed hardening |
| --- | --- | ---: | --- | --- | --- |
| (a) schema-expressible but unchecked | `approval.approved_by` | 5 | F1 | approval.approved_by accepted a homoglyph/invisible/case-folded identifier that is self-asserted and not cross-checked | restrict the operator/identifier pattern to an ASCII allow-list and apply Unicode NFKC + confusable normalization |
| (c) requires a human | `approval.approval_reason` | 7 | F1,F3,F4,F5,F6 | approval.approval_reason is free-text rationale/labeling; the artifact chain stays internally consistent | none at the artifact layer; this is the argument for the human gate (record in autopsy prose) |
| (c) requires a human | `bundle.safety_note` | 4 | F1,F2,F4,F6 | bundle.safety_note is free-text rationale/labeling; the artifact chain stays internally consistent | none at the artifact layer; this is the argument for the human gate (record in autopsy prose) |
| (c) requires a human | `capability.adapter_name` | 6 | F2,F3,F4,F6 | capability.adapter_name is free-text rationale/labeling; the artifact chain stays internally consistent | none at the artifact layer; this is the argument for the human gate (record in autopsy prose) |
| (c) requires a human | `capability.safety_note` | 8 | F2,F3,F4,F5,F6 | capability.safety_note is free-text rationale/labeling; the artifact chain stays internally consistent | none at the artifact layer; this is the argument for the human gate (record in autopsy prose) |
| (c) requires a human | `runbook.safety_note` | 4 | F4,F5,F6 | runbook.safety_note is free-text rationale/labeling; the artifact chain stays internally consistent | none at the artifact layer; this is the argument for the human gate (record in autopsy prose) |

### Reading the autopsy

- **Class (a)** escapes are hardening targets: the fault could be rejected by a constraint that does not yet exist (here: operator/identifier fields accept homoglyph, zero-width, full-width, and case-folded look-alikes because the id is self-asserted and never cross-checked). The proposed diff tightens the identifier pattern and normalizes Unicode.
- **Class (c)** escapes are the argument for the human gate: free-text rationale and labeling fields (`approval_reason`, per-artifact `safety_note`, `adapter_name`) can be rewritten while every hash and cross-artifact binding stays consistent. No machine constraint can decide whether the *content* is truthful; a human reviewer must.
- **Class (b)** escapes (none observed) would indicate a gap in the cross-artifact preflight itself.

## Circularity mitigation

The out-of-catalog fuzzer draws from generic mutation operators (field deletion, type replacement, boundary numerics, unknown fields, cross-artifact splices, nesting abuse, free-text tamper) chosen independently of the guard list. It is where the 29 class-(c) escapes were found rather than authored. The 5 class-(a) escapes came from the directed catalog instead: they were authored as probes, and the pipeline failed to reject them, which is a hardening finding rather than a discovery by search. A matrix returning 100% interception with an empty escape set would signal that the evaluation was too weak (a pre-registered kill criterion), not that the system is impenetrable.

