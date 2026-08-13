# v0.2.0: Frozen Benchmark Protocol And Reproduction Pack

TreLLM v0.2.0 is the first protocol-focused release for the TradeArena
leaderboard module and benchmark-card layer. It freezes the v0.2 comparison
contract, separates engineering, benchmark, and scientific claims, and adds a
no-key external reproduction path that validates a benchmark row and
regenerates dashboard artifacts from a fresh checkout.

## Highlights

- Frozen v0.2 benchmark spec with canonical spec hashing.
- Claim boundary badge and public claim-boundary policy for README and result
  interpretation.
- External reproduction pack command that records commit/tag, Python platform,
  commands, output paths, artifact hashes, trajectory hash, and data/API
  provenance.
- Expanded non-LLM baselines: buy-and-hold, equal weight, naive momentum, mean
  reversion, risk parity, minimum variance, Markowitz/MVO, random, and
  always-hold.
- Failure autopsy tooling for over-trading, leverage, risk-gate pressure,
  slippage sensitivity, liquidity sensitivity, confidence/calibration mismatch,
  and memory-driven behavior.
- Public execution-calibration priority note that distinguishes stress
  simulation from calibrated quote/fill replay.
- Rebuilt benchmark card and dashboard artifacts for the v0.2 release version.

## Install

```bash
python -m pip install tradearena-benchmark==0.2.0
tradearena --benchmark tradearena-core
```

## One-Command Reproduction

```bash
python scripts/run_external_reproduction_pack.py --output-dir outputs/reproduction/v0_2
```

The generated manifest includes the deterministic trajectory hash, dashboard
hashes, benchmark-row hash, command logs, environment metadata, and provenance
flags for live APIs, downloaded market data, and private fills.

## Known Limitations

- The no-key reproduction pack is a deterministic engineering target; it is not
  a scientific claim about model trading skill.
- Provider-backed model rows remain sensitive to provider routing, wrapper
  prompts, rate limits, cache provenance, and model-version drift.
- The default execution simulator is a stress-test simulator, not a calibrated
  substitute for venue-level quote, order-book, or fill replay.
- Redacted leaderboard submissions are useful for participation but cannot by
  themselves support strong model-ranking claims.
- Scientific claims require repeated seeds or rolling windows, classical
  baselines, statistical intervals, failure autopsy, and independent
  reproduction reports.

## Release Assets

The release artifact inventory and hashes are tracked in
`docs/launch/release_artifacts_v0.2.0.md` and
`docs/launch/release_artifacts_v0.2.0.json`.
