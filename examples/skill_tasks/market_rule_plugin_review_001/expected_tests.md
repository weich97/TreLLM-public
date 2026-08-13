# Requested Plugin

Add an A-share market-rule plugin for paper-only experiments.

Expected behavior:

- block same-day sell orders under T+1 settlement;
- round order quantities to board lots;
- block buys at limit-up and sells at limit-down;
- explain every transformed or blocked order;
- avoid live API access and broker credentials.
