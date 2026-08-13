# Reference Answer

The shortfall attribution separates spread, impact, latency, and fees:
9.8 bps spread, 21.6 bps impact, 11.3 bps latency, and 4.7 bps fees.

The evidence tier is stress-only / realistic-stress, not fill replay. The row
uses a small public quote sample but has zero realized fills.

Liquidity friction appears through requested participation above the
participation cap and a partial fill ratio of 0.48.

Missing provenance includes venue-specific realized fills, broker timestamps,
and order identifiers. Therefore this cannot support a broker-grade
transaction-cost prediction claim. It can support an execution-boundary audit.
