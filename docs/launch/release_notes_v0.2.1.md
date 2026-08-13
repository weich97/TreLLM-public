# v0.2.1 Release Notes Draft

TreLLM v0.2.1 is a patch-release candidate focused on evidence quality,
artifact boundaries, and third-party reproducibility. It does not change the
public claim boundary: TreLLM remains an audit and live-readiness control system.
TradeArena remains the public leaderboard module and benchmark-card layer with no default
live-order path, not an unattended trading bot or profitability leaderboard.

## Highlights

- Public artifact redaction is enforced for LLM-like trajectories and public
  result scans.
- OpenTelemetry-style local trace export maps a trajectory into redacted audit
  spans for observability experiments.
- External validation bundles convert reproduction manifests into issue-ready
  reports with command, hash, artifact, and environment fields.
- Execution calibration stability now reports rolling-window residuals on the
  public BTCUSDT quote/fill sample.
- Market-rule fixtures exercise A-share T+1 and limit bands, Hong Kong board
  lots, crypto fee/funding estimates, liquidity clipping, and suspension blocks.
- Release readiness now checks the v0.2.1 candidate artifacts before publication.
- Release readiness now checks public identity boundaries before publication.

## Reproduce The New Evidence

```bash
python scripts/run_execution_calibration_stability.py
python examples/market_rules_fixture_demo.py
python scripts/run_external_reproduction_pack.py --output-dir outputs/reproduction/v0_2
python scripts/build_external_validation_bundle.py --manifest outputs/reproduction/v0_2/manifest.json
python scripts/build_release_candidate_manifest.py --target-release v0.2.1
```

## Boundaries

- Execution evidence remains a public quote/fill calibration sample, not
  broker-grade transaction-cost prediction.
- External validation bundle output is strongest when produced by a clean
  third-party environment; maintainer-local bundles are smoke evidence.
- Provider-backed rows remain subject to provider drift, routing, caching, and
  redaction constraints.
