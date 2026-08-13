# Amendment 2026-07-02: provider set replaced before any matrix run

**Status: amendment made BEFORE data collection.** No matrix run row had been
executed under the original registration at the time of this amendment; the
original plan was blocked on a credential that never existed on this
infrastructure, so no result is or ever was affected by the swap.

## What changed

| | Original (commit `324c9cc`) | Amended (this commit) |
|---|---|---|
| Models | `openai:gpt-5.5` (fixture-2026-05-17, responses API) | `deepseek:deepseek-v4-pro`, `deepseek:deepseek-v4-flash`, `glm:glm-5` (api-pinned-2026-07-02, chat-completions) |
| Planned rows | 30 (1 group) | 90 (3 groups) |
| Preflight | blocked (`OPENAI_API_KEY` absent) | all groups ready |

**Unchanged:** scenario set (`synthetic_calm_trend_c0_v0_3`), contamination
tier (C0), execution level (E1), the 10 pre-registered seeds, 3 samples per
seed, prompt template `trellm-allocation-v0.3` / `v0.3.0`, and decoding
settings. The amendment swaps providers only.

## Why

- This infrastructure has no first-party OpenAI access, and `gpt-5.5` via the
  routing aggregator has been returning not-found since ~2026-06-30; routed
  access would in any case violate the protocol's direct-API requirement for
  headline rows.
- DeepSeek and Zhipu GLM are the two providers with working, version-pinnable
  first-party API access here (already the reproducible spine of the
  execution-sensitivity and memory-pollution studies). All three amended
  models are verified callable on this infrastructure.

## Provision

A fourth model (a second GLM tier) may be added by a further amendment,
subject to the same rule: any change must land, git-timestamped, **before the
first matrix run row is executed**. Once the first row runs, the plan freezes.
