# Reference Answer

Implement this as a narrow `MarketRule` plugin, not as a risk manager or
execution simulator change. The plugin should use the validate_order,
transform_order, and explain_block boundary to handle exchange-level rules.

Keep risk and simulator behavior separate. T+1 settlement, lot rounding, and
limit-up / limit-down checks are market-rule validation or transformation
concerns; portfolio risk budgets remain in risk code and fills remain in
execution code.

Add deterministic tests for T+1 same-day sell blocking, board lot rounding,
limit-up buys, limit-down sells, and explanation text. Use fixtures and no live
API access. Do not request broker credentials; keep it paper-only.

Also update schema, docs, plugin registration, and an example fixture so
external contributors can test the plugin without market downloads.
