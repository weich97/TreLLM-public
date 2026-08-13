# Plugin Author Review

This should be a risk plugin, implemented through the RiskManager boundary or a
small validate_order-style risk protocol. It should not change runner
orchestration. In concrete review terms: do not change the runner.

The plugin should run offline with a deterministic fixture and no live API
dependency. Add a pytest unit test with a fixed seed that exercises a passing
order and a blocked order.

Security and data assumption: do not request credentials or private account
data. Any example data should be synthetic, redacted, or tracked as a test
fixture.
