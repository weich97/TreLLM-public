# Claim Boundary Review

The trajectory recording statement is an engineering claim: the artifact shows
that TreLLM can record a trajectory from intent to risk and execution state.
TradeArena can present the resulting evidence as a leaderboard artifact.

The shared stress comparison is a benchmark claim because it uses common
stress-only execution assumptions across rows. It should not be promoted to a
scientific claim about model profitability.

The single-run profitability claim is unsupported and should be weakened to a
reliability observation from one run. It is not enough evidence for a general
model claim.

The calibration pipeline claim should be narrow: the calibration machinery is
an engineering claim unless the row has quote-calibrated or fill-replay evidence.

Evidence label: stress-only for default public rows; quote-calibrated only for
rows with quote or fill provenance; cached-provider and fully-auditable labels
must be stated separately.
