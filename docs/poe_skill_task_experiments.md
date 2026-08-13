# Poe And Direct-DeepSeek Skill-Task Experiments

The highest-value use of additional Poe tokens is not another trading-profit
leaderboard. TreLLM already has synthetic, real-market, execution-shock,
classical-baseline, and calibration snapshots, with TradeArena providing the
comparable leaderboard surface. The more distinctive research question is
whether frontier models can act as financial-audit agents:

> Can an LLM reliably inspect trajectories, understand risk feedback, identify
> execution frictions, reproduce artifacts, and avoid claim overreach?

## Recommended Poe Token Run

```bash
python scripts/run_poe_skill_task_matrix.py --repeats 3
```

Default settings:

- models: `poe:gpt-5.5`, `poe:gemini-3.1-pro`, `poe:kimi-k2.5`,
  `poe:glm-5`, and `poe:claude-opus-4.7`;
- tasks: all 12 public tasks under `examples/skill_tasks/`;
- repeats: 3 answer sets per model;
- planned calls: 180;
- estimated budget: roughly 350k-400k Poe tokens, depending on provider tokenization
  and answer length.

For a robustness run that spends tokens on prompt sensitivity rather than more
model names, use the three reviewer variants:

```bash
python scripts/run_poe_skill_task_matrix.py \
  --repeats 1 \
  --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary \
  --refresh-cache
```

The repeat id is part of the cache key, so repeated samples are independent
provider calls rather than cache replays.
For append-only follow-up samples after a two-repeat run, use
`--sample-start-index 3` so the new answers are recorded as `r3` rather than
overwriting the interpretation of earlier `r1/r2` cache keys.

## Challenge Suite

The standard task suite checks broad coverage. The challenge suite in
`examples/skill_tasks_challenge/` is deliberately sharper: it tries to tempt
models into profitability overclaims, stress-model calibration overclaims,
privacy leaks, dirty reproduction claims, and market-rule overgeneralization.

Run the challenge matrix with:

```bash
python scripts/run_poe_skill_task_matrix.py \
  --tasks-dir examples/skill_tasks_challenge \
  --repeats 2 \
  --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary \
  --max-output-tokens 1800 \
  --public-output docs/results/poe_skill_challenge_matrix.md \
  --public-csv docs/results/poe_skill_challenge_matrix.csv
```

Tracked public results:

- standard matrix: `docs/results/poe_skill_task_matrix.md`;
- challenge matrix: `docs/results/poe_skill_challenge_matrix.md`.

Current tracked snapshots:

- standard 12-task robustness run: 5 Poe models, 3 reviewer variants, 180 live
  calls; Gemini 3.1 Pro averaged 88.3%, GPT-5.5 averaged 85.0%, and the lower
  rows exposed more hard failures on claim, reproduction, and plugin tasks.
- challenge 8-task run: 5 Poe models, 3 reviewer variants, 2 independent
  samples, 240 live calls; Gemini 3.1 Pro averaged 80.4%, Claude Opus 4.7
  averaged 78.3%, GPT-5.5 averaged 77.9%, GLM-5 averaged 77.5%, and Kimi K2.5
  averaged 73.8%.
- challenge follow-up run: 3 Poe models, 3 reviewer variants, one appended
  `r3` sample, 72 live calls; Gemini 3.1 Pro averaged 82.5%, Kimi K2.5 averaged
  80.0%, and GPT-5.5 averaged 72.5%.
- Claude adversarial follow-up: one appended `r3` sample on the adversarial
  challenge variant, 8 live calls; Claude Opus 4.7 scored 95.0% with no hard
  failures, showing that the earlier Claude adversarial variance deserves
  repeat-level reporting rather than a single aggregate claim.

The challenge scores are lower by design. They are useful because they surface
where models still overread leaderboard rows, underreport reproduction
defects, or soften public-artifact privacy boundaries under adversarial wording.

When extra Poe budget remains, prefer append-only challenge repeats over new
profitability rows:

```bash
python scripts/run_poe_skill_task_matrix.py \
  --tasks-dir examples/skill_tasks_challenge \
  --models poe:gpt-5.5,poe:gemini-3.1-pro,poe:kimi-k2.5 \
  --repeats 1 \
  --sample-start-index 3 \
  --prompt-variants standard,skeptical_reviewer,adversarial_claim_boundary \
  --max-output-tokens 1800 \
  --public-output docs/results/poe_skill_challenge_followup_matrix.md \
  --public-csv docs/results/poe_skill_challenge_followup_matrix.csv
```

The small high-variance follow-up probe is:

```bash
python scripts/run_poe_skill_task_matrix.py \
  --tasks-dir examples/skill_tasks_challenge \
  --models poe:claude-opus-4.7 \
  --repeats 1 \
  --sample-start-index 3 \
  --prompt-variants adversarial_claim_boundary \
  --max-output-tokens 1800 \
  --public-output docs/results/poe_skill_challenge_followup_claude_adversarial.md \
  --public-csv docs/results/poe_skill_challenge_followup_claude_adversarial.csv
```

DeepSeek is intentionally not routed through Poe. To include direct DeepSeek
rows, run:

```bash
python scripts/run_poe_skill_task_matrix.py --repeats 3 --include-deepseek
```

This appends `deepseek:deepseek-v4-flash` and `deepseek:deepseek-v4-pro`, using
`DEEPSEEK_API_KEY` and `https://api.deepseek.com`. The Poe rows still use
`POE_API_KEY` and `https://api.poe.com/v1`.

Raw provider prompts and raw model answers are written only under ignored local
outputs/cache:

- `outputs/poe_skill_task_answers/<run>/`;
- `outputs/llm_cache/poe_skill_tasks/`.

Tracked public outputs contain aggregate scores only:

- `docs/results/poe_skill_task_matrix.md`;
- `docs/results/poe_skill_task_matrix.csv`.

## Why this experiment is worth the tokens

The experiment directly supports the repo's current research positioning:

- **Audit accuracy:** does the model find risk edits, rejected orders, partial
  fills, and intent-to-execution mismatches?
- **Risk-gate understanding:** does it explain clipped/blocked decisions and
  feedback adaptation without reducing everything to return?
- **Execution-boundary awareness:** does it avoid treating stress simulation as
  calibrated transaction-cost evidence?
- **Claim discipline:** does it separate engineering, benchmark, and scientific
  claims?
- **Reproduction awareness:** does it report commit, command, hash, artifact
  path, and data-source flags?
- **Plugin engineering:** can it propose a narrow plugin plus deterministic
  tests without changing runner orchestration?

This is a cleaner publication-style model comparison than asking which model appears
profitable in one market window.

## Smoke run

Use one model and two tasks before spending the full budget:

```bash
python scripts/run_poe_skill_task_matrix.py \
  --models poe:gpt-5.5 \
  --limit-tasks trajectory_audit_001,execution_boundary_001 \
  --repeats 1
```

Direct DeepSeek smoke:

```bash
python scripts/run_poe_skill_task_matrix.py \
  --models deepseek:deepseek-v4-pro \
  --limit-tasks trajectory_audit_001,execution_boundary_001 \
  --repeats 1
```

## Dry run

```bash
python scripts/run_poe_skill_task_matrix.py --dry-run --repeats 3
```

The dry run writes the planned call matrix without contacting Poe or DeepSeek.
