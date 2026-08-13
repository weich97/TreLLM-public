# Reference Answer

Claim 2 is an engineering claim: TreLLM records intent, risk edits,
simulated fills, and replay hashes for paper-only benchmark runs.
TradeArena can summarize that evidence as a leaderboard row, but the recording
capability belongs to TreLLM.

Claims 1 and 3 are scientific claims or model-superiority claims and should be
weakened. The evidence labels are cached-provider, redacted-prompt,
stress-only, and not-external-submitted. Those labels support a reliability
finding at most, not a claim that GPT-5.5 is the best trading model.

Provider drift matters because hosted APIs may change routing, wrapper prompts,
model aliases, or cached behavior. A cached row is not enough evidence for
future-market outperformance.

Required evidence includes repeated runs, seeds, baselines, confidence
intervals, and external validation. Recommended wording: the current row is a
paper-only audit snapshot under provider-drift caveats.
