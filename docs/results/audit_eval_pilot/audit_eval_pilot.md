# Audit-Agent Evaluation: 6 Models on 100 Defect-Injected Trajectories

FinAudit task family (research plan 04): one defect per trajectory (25 per
kind), auditor reports structured findings scored vs injected ground truth.
Compact audit view, single pass. Five Poe-routed/direct models plus the
deepseek direct pilot.

## Overall and by difficulty (recall)

| Model | ALL | L1 single-record | L2 cross-record | L3 recompute |
| --- | ---: | ---: | ---: | ---: |
| poe:gpt-5.5 | 0.99 | 1.00 | 0.98 | 1.00 |
| poe:claude-opus-4.7 | 0.97 | 0.88 | 1.00 | 1.00 |
| poe:gemini-3.1-pro | 0.95 | 0.80 | 1.00 | 1.00 |
| deepseek:deepseek-v4-pro | 0.79 | 0.52 | 0.90 | 0.84 |
| glm:glm-5 | 0.71 | 0.32 | 0.80 | 0.92 |
| poe:glm-5 | 0.70 | 0.40 | 0.80 | 0.80 |

## Headline: the difficulty inversion is a weak-auditor phenomenon

Strong auditors (gpt-5.5 L1=1.00, claude-opus-4.7 L1=0.88, gemini-3.1-pro
L1=0.80) detect the nominally easiest single-record rule violation reliably.
Weaker auditors (glm-5 L1=0.32-0.40, deepseek-v4-pro L1=0.52) miss it while
still scoring well on cross-record (L2) and recompute (L3) checks - they
pattern-match inter-record inconsistencies but do not systematically verify
stated constraints against values. The inversion reported in the single-model
pilot is therefore a property of weaker auditors, not a universal one.

## Routing note

poe:glm-5 (ALL 0.70) and glm:glm-5 direct (ALL 0.71) match overall but differ
by difficulty (L1 0.40 vs 0.32; L3 0.80 vs 0.92), a same-name routing effect.

Reproduce: generate_audit_tasks.py --tasks 100 then run_audit_eval.py.
