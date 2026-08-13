# Sector Concentration Guard

This curated example implements a deterministic risk plugin. It inherits
TreLLM's built-in `MaxPositionRiskManager` and adds one reviewable behavior:
aggregate target weights are clipped when a sector exceeds `max_sector_weight`.

Use this example when you want to study a complete, documented plugin pattern
with:

- an importable package under `plugins/examples/`;
- a narrow risk-layer extension;
- deterministic behavior with no live APIs;
- a test that checks the exact clipped target weights and risk report.

Use `tradearena new-plugin` instead when starting a private or experimental
plugin that is not ready to live in the curated registry.

Validation:

```bash
python -m pytest tests/test_plugin_examples.py -q
```
