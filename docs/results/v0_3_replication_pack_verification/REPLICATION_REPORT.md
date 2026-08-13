# TradeArena Replication Pack Report

**Verdict: PASS**

- Pack: `tradearena-replication-pack-v1` v1.0.0
- Protocol: `trellm-v0.3-protocol`
- Mode: `full`
- Environment class: `windows_or_macos`
- Python: `3.12.10` (CPython)
- Platform: `Windows-10-10.0.19045-SP0`
- Created: `2026-07-02T14:18:33.043898+00:00`
- Total wall-clock: `301.112 s`
- Live APIs used: `False`  Private data used: `False`

## Commands

| Step | Return code | Elapsed (s) |
| --- | ---: | ---: |
| `validate_protocol` | 0 | 0.145 |
| `deterministic_trajectory` | 0 | 2.682 |
| `anchor_execution_ladder` | 0 | 297.041 |
| `anchor_power_note` | 0 | 0.857 |

## Checks (tolerance tier)

| Check | Status | Detail |
| --- | --- | --- |
| `pack_integrity` | PASS | 86 files verified |
| `protocol_valid` | PASS | protocol contract validates |
| `protocol_canonical_hash` | PASS | match |
| `trajectory_structure` | PASS | experiment name, seed, schema, and step count match |
| `ladder_aggregate` | PASS | 24 rows compared within tolerance |
| `ladder_ranking_stability` | PASS | 1 rows compared within tolerance |
| `power_curves` | PASS | 6 rows compared within tolerance |
| `detectable_effects` | PASS | 2 rows compared within tolerance |

## Strict determinism checks (informational)

| Check | Status |
| --- | --- |
| `strict_trajectory_content_hash` | STRICT_PASS |
| `strict_trajectory_file_hash` | STRICT_PASS |

Strict checks compare exact hashes. `STRICT_DIFFER` with all tolerance checks passing
usually indicates last-digit libm differences across platforms and does not fail the replication.

## Reviewer sign-off (fill in and return with outputs/replication_report.json)

- Name: _______________
- Affiliation: _______________
- Contact: _______________
- Date: _______________
- How I obtained this pack (URL or note): _______________
- Deviations from the README instructions (if any): none / _______________
- I am not an author or maintainer of this project: yes / no
- I used no API keys and no private data: yes / no
- Signature: _______________
