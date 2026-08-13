# v0.1.1: High-Spread Execution Stress Preset

TreLLM v0.1.1 is a small maintenance release focused on making execution
realism easier to inspect and reproduce.

## Highlights

- Added an explicit `spread_bps` parameter to the realistic order simulator.
- Added a `high_spread` row to `examples/execution_realism_sweep_demo.py`.
- The high-spread preset models market orders crossing half the quoted
  bid-ask spread before market impact and volatility slippage.
- The execution sweep now emits spread configuration fields into its JSON and
  CSV artifacts.
- Added tests covering spread-driven crossing cost and the high-spread demo
  row.

## Why It Matters

The preset separates spread cost from generic slippage. This makes it easier
to show that an agent can keep a high fill rate while still losing realized
performance to wide quoted markets.

## Reproduce

```bash
python -m pip install -e ".[dev]"
python examples/execution_realism_sweep_demo.py
python scripts/run_showcase.py --reuse-existing
python -m pytest tests -q
```

## Related Issue

- Closes #3.
