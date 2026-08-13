# Market Rules Fixture

These are deterministic exchange-rule fixtures for auditability. They are not live-trading advice and do not claim full regulatory coverage for any venue.

## Summary

- Cases: 6
- Approved: 1
- Clipped: 3
- Blocked: 2

## Cases

| Case | Package | Symbol | Side | Requested | Approved | Status | Reasons | Fees | Funding | Impact |
| --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| `ashare_same_day_sell` | `ashare_t_plus_one_price_limit_board_lot` | 600000.SH | sell | 500 | 100 | clipped | t_plus_one_sellable_clip | 0.0000 | 0.0000 | 0.0000 |
| `ashare_limit_up_buy` | `ashare_t_plus_one_price_limit_board_lot` | 600000.SH | buy | 300 | 0 | blocked | limit_up_buy_block | 0.0000 | 0.0000 | 0.0000 |
| `hk_board_lot_rounding` | `hong_kong_board_lot_stamp_duty` | 0700.HK | buy | 760 | 500 | clipped | lot_size_500 | 208.0000 | 0.0000 | 0.0000 |
| `crypto_fee_funding` | `crypto_fee_tier_funding` | BTCUSDT | buy | 2 | 2 | approved | none | 73.4400 | 18.3600 | 0.0000 |
| `liquidity_halt_clip` | `suspension_circuit_liquidity_halt` | SYN | buy | 4000 | 1000 | clipped | liquidity_participation_clip | 0.0000 | 0.0000 | 100.0000 |
| `suspension_block` | `suspension_circuit_liquidity_halt` | SYN | sell | 1000 | 0 | blocked | suspension | 0.0000 | 0.0000 | 0.0000 |

## Reproduce

```bash
python examples/market_rules_fixture_demo.py
```
