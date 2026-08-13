## Summary

- 

## Type

- [ ] Bug fix
- [ ] Demo or documentation
- [ ] New plugin or adapter
- [ ] Research experiment
- [ ] TreLLM system change
- [ ] TradeArena leaderboard or registry artifact update

## Validation

- [ ] `python -m pytest tests -q`
- [ ] `python scripts/check_release_readiness.py`
- [ ] `python scripts/validate_demo_artifacts.py` when demo outputs change
- [ ] `python scripts/validate_benchmark_submission.py <submission>` when registry rows change
- [ ] Relevant demo command:

## Broker Or Live-Safety Boundary

Complete this section for broker-review exports, dry-run adapters,
paper-sandbox adapters, approval artifacts, response reconciliation, or any
future live-capable path.

- [ ] Not broker-facing / no live-safety impact
- Live-ready contribution track:
  - [ ] Broker capability manifest
  - [ ] Broker review export
  - [ ] Approval binding
  - [ ] Paper-sandbox adapter
  - [ ] Reconciliation
  - [ ] Operator runbook
  - [ ] Live-readiness preflight
- [ ] Adapter mode is explicit:
- [ ] Broker adapter capability manifest validates with:
- [ ] Live-readiness preflight bundle validates with:
- [ ] Default path cannot submit live orders
- [ ] No credentials, account identifiers, private holdings, or raw broker
      payloads are committed
- [ ] Handoff/approval/response artifacts are redacted and validate with:
- [ ] Added or updated tests for changed broker safety limits, kill-switches,
      approval binding, or reconciliation behavior

## Artifacts

List any generated files reviewers should inspect under `outputs/examples/`,
`docs/results/`, or `examples/benchmark_submissions/`.
