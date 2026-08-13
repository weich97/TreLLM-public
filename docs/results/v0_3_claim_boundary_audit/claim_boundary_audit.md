# TreLLM v0.3 Claim Boundary Audit

This artifact checks whether public narrative surfaces keep pilot, fixture, benchmark, and scientific claims separated.

- Protocol: `trellm-v0.3-protocol`
- Audit targets: `5`
- Checks: `13`
- Violations: `0`
- Claim boundary: This audit checks whether public narrative surfaces preserve TreLLM's claim boundaries. It is not evidence of model performance and does not close the direct API or external reproduction gaps.

## Findings

| Check | Target | Status | Severity | Detail |
| --- | --- | --- | --- | --- |
| evidence-index-headline-ready | `docs/results/v0_3_evidence_index/v0_3_evidence_index.json` | pass | blocking | headline_scientific_claim_ready must equal the derived gate state (matrix gate passing AND reproduction criterion met), never be asserted. |
| evidence-index-open-gaps | `docs/results/v0_3_evidence_index/v0_3_open_gaps.csv` | pass | blocking | The open-gap list must match the derived gate state exactly: explicit while evidence is pilot/fixture, closed only when the underlying gates genuinely pass. |
| required-boundary-phrase | `README.md` | pass | blocking | Required claim-boundary phrase is present: TreLLM is not investment advice or a promise of profitable trading. |
| required-boundary-phrase | `README.md` | pass | blocking | Required claim-boundary phrase is present: The repo distinguishes three claims: |
| required-boundary-phrase | `README.md` | pass | blocking | Required claim-boundary phrase is present: Current public LLM runs are deliberately labeled as protocol fixtures, |
| risky-claim-context | `README.md:90` | pass | blocking | Risky phrase `\bpromise\s+of\s+profitable\s+trading\b` must appear only in a negated, forbidden, or limitation context. |
| risky-claim-context | `README.md:90` | pass | blocking | Risky phrase `\binvestment\s+advice\b` must appear only in a negated, forbidden, or limitation context. |
| required-boundary-phrase | `docs/benchmark_v0_3_protocol.md` | pass | blocking | Required claim-boundary phrase is present: headline_scientific_claim_ready |
| required-boundary-phrase | `docs/benchmark_v0_3_protocol.md` | pass | blocking | Required claim-boundary phrase is present: false until direct API model matrices and independent external reproduction |
| required-boundary-phrase | `docs/benchmark_v0_3_protocol.md` | pass | blocking | Required claim-boundary phrase is present: Do not use the v0.3 protocol to claim: |
| risky-claim-context | `docs/benchmark_v0_3_protocol.md:291` | pass | blocking | Risky phrase `\bproven\s+to\s+be\s+profitable\b` must appear only in a negated, forbidden, or limitation context. |
| required-boundary-phrase | `docs/claim_boundaries.md` | pass | blocking | Required claim-boundary phrase is present: TreLLM separates three kinds of claims. |
| required-boundary-phrase | `docs/claim_boundaries.md` | pass | blocking | Required claim-boundary phrase is present: Scientific rows should be rare and conservative. |
