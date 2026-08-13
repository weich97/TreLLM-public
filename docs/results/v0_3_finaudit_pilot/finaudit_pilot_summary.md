# TreLLM v0.3 FinAudit Pilot

This fixture bundle validates the injected-defect audit task path for the v0.3 protocol.
It is not model-performance evidence.

- Protocol: `trellm-v0.3-protocol`
- Scenario: `synthetic_finaudit_c0_v0_3`
- Contamination tier: `C0`
- Tasks: 8
- Conditions: `cross-audit, self-audit`
- Required metrics: `precision, recall, f1, wilson_interval, difficulty_breakdown`
- Answer key public: `False`
- Answer key hash: `sha256:c6aa8cfc09c4f1442bf33e431a1351f40211e901242da69b2d62fffd9d060361`
- Claim boundary: FinAudit pilot protocol fixture for injected-defect scoring and self/cross audit plumbing; fixture auditor scores are not model-performance evidence.
- Self-audit bias recall delta: `0.25`

## Difficulty Breakdown

| Condition | Auditor | Difficulty | Tasks | Precision | Recall | F1 | Recall Wilson 95% CI |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| cross-audit | fixture-cross-auditor-v0 | L1 | 2 | 1.000000 | 1.000000 | 1.000000 | [0.342380, 1.000000] |
| cross-audit | fixture-cross-auditor-v0 | L2 | 4 | 1.000000 | 1.000000 | 1.000000 | [0.510109, 1.000000] |
| cross-audit | fixture-cross-auditor-v0 | L3 | 2 | 0.000000 | 0.000000 | 0.000000 | [0.000000, 0.657620] |
| cross-audit | fixture-cross-auditor-v0 | all | 8 | 1.000000 | 0.750000 | 0.857143 | [0.409275, 0.928521] |
| self-audit | fixture-self-auditor-v0 | L1 | 2 | 1.000000 | 1.000000 | 1.000000 | [0.342380, 1.000000] |
| self-audit | fixture-self-auditor-v0 | L2 | 4 | 1.000000 | 0.500000 | 0.666667 | [0.150039, 0.849961] |
| self-audit | fixture-self-auditor-v0 | L3 | 2 | 0.000000 | 0.000000 | 0.000000 | [0.000000, 0.657620] |
| self-audit | fixture-self-auditor-v0 | all | 8 | 1.000000 | 0.500000 | 0.666667 | [0.215216, 0.784784] |
