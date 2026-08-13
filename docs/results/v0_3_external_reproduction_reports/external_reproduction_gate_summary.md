# TreLLM v0.3 External Reproduction Gate

This artifact tracks whether independent reproduction reports satisfy the v0.3 protocol.
It is intentionally conservative: project-maintainer reports, failed command logs, private-data runs, and missing environment labels do not count as independent evidence.

- Protocol: `trellm-v0.3-protocol`
- Reports scanned: `0`
- Accepted reports: `0 / 3`
- Covered environment classes: `0 / 3`
- External reproduction ready: `False`
- Blocking reasons: `insufficient_independent_report_count;missing_required_environment_class`
- Claim boundary: This gate validates external reproduction reports against the v0.3 protocol. It does not count project-maintainer, failed, private-data, or wrong-environment reports as independent evidence.
- Open-gap policy: Amended 2026-07-05 (pre-registered fallback): the protocol's reproduction criterion is satisfied by the pack's machine self-verification (replication_pack_verification artifact) or by at least one accepted independent report. This intake gate remains open either way; full external validation (three independent reports covering windows_or_macos, linux, and colab_or_binder) is tracked as an optional stretch tier via external_reproduction_ready.

## Environment Coverage

| Environment class | Accepted reports | Status |
| --- | ---: | --- |
| windows_or_macos | 0 | missing |
| linux | 0 | missing |
| colab_or_binder | 0 | missing |

## Report Requirements

A report counts only when it is schema-valid, uses `protocol_id=trellm-v0.3-protocol`, marks `report_author_type=independent`, sets `independent_reviewer=true`, records one required environment class, and contains no failed required commands or missing artifacts.
