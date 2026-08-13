# Specification freeze and replay provenance (instructed batch)

The instructed batch's design, hypotheses, and analysis were frozen in
`CONFIRMATORY_SPEC_2026-07-16.md` and committed to version control before the
fixed grid was replayed. A later per-call reconstruction found that the replay
used the shared response cache; it was therefore not a wholly new prospective
provider sample. The original specification is retained verbatim so its hash
and commit ordering remain verifiable.

Verification chain:

- **Spec content hash** (sha256 of the frozen spec file shipped verbatim in
  this artifact):
  `e9181d87685e702251cfa53dcf056fa54e27d25db152b4c79ee1b9ce44c08610`
- **Spec commit timestamp**: 2026-07-16 16:21:42 (UTC+9).
- **Fixed-grid replay launch**: 2026-07-16 17:12:55 (UTC+9), i.e. 51 minutes
  after the freeze commit. The supervisor log and per-run CSV checkpoints
  postdate the freeze.
- **Shared-cache finding**: 8,316 of the instructed arm's 8,640 logical calls
  resolve to cache entries created before the specification commit. The grid
  and analysis were frozen before replay, but most responses were not freshly
  collected after the freeze. We therefore describe this arm as a frozen-grid
  replay rather than an independent prospective replication.
- **Hash-only reconstruction**: `docs/results/memory_pollution_provenance/`
  records the prompt and response SHA-256 values and original UTC cache time
  for every headline call without releasing prompt or response text. The
  reconstruction ran in cache-only mode and reproduced every checked run
  metric.
- The freeze ordering — specification committed before the replay ran — was
  established in the maintainer's development history. This published snapshot
  starts from a fresh commit and therefore does not carry that history, so the
  ordering is asserted here rather than independently checkable from this
  repository alone. Treat it accordingly.

Analysis implementation: `analyze_mempoll_confirm.py` follows the frozen
analysis section exactly (paired vs internal d=0 cells, provider samples
averaged within seed, sign-flip permutation, BH-FDR per agent across the
12-test dose x risk x metric family).
