# Max Drawdown Risk Preset Fixture

Deterministic risk-preset fixture for audit and extension tests. It demonstrates blocked or clipped decisions; it is not trading advice.

## Settings

- Max drawdown: 5.00%
- Observed rolling drawdown: -6.00%
- Drawdown lookback: 3 equity records

## Cases

| Case | De-risk weight | Requested | Approved | Blocked | Clipped | Violation |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `block_after_drawdown` | 0.00 | 0.40 | 0.00 | 1 | 0 | `drawdown_kill_switch` |
| `clip_after_drawdown` | 0.10 | 0.40 | 0.10 | 0 | 1 | `drawdown_kill_switch` |

## Reproduce

```bash
python examples/max_drawdown_risk_preset_demo.py
```
