# Task

Audit this trajectory excerpt:

```json
{
  "step": 17,
  "raw_decisions": [
    {"symbol": "BTC-USD", "target_weight": 0.72, "confidence": 0.41},
    {"symbol": "ETH-USD", "target_weight": 0.38, "confidence": 0.35}
  ],
  "approved_decisions": [
    {"symbol": "BTC-USD", "target_weight": 0.35, "reason": "max_abs_weight_clip"},
    {"symbol": "ETH-USD", "target_weight": 0.0, "reason": "min_confidence_block"}
  ],
  "orders": [
    {"symbol": "BTC-USD", "quantity": 8.4, "status": "submitted"},
    {"symbol": "ETH-USD", "quantity": 0.0, "status": "blocked"}
  ],
  "fills": [
    {"symbol": "BTC-USD", "fill_ratio": 0.62, "slippage_bps": 28.4, "status": "partial"}
  ],
  "execution_report": {
    "partial_fills": 1,
    "rejected_orders": 1,
    "average_latency_steps": 3
  }
}
```

Write a concise audit report. Do not evaluate whether BTC or ETH is a good
trade. Focus on intent-to-risk-to-execution differences and what evidence is
missing before making any benchmark or scientific claim.

