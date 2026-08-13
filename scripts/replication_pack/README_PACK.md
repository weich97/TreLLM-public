# TradeArena Deterministic Replication Pack v1

This is the zero-API-key external replication pack for the **TradeArena** LLM
financial-agent benchmark (v0.3 protocol). It reproduces the protocol's
deterministic anchor arms on any machine with **Python 3.10+ and nothing else**
— no API keys, no network access, no third-party packages, no private data —
and automatically verifies every produced number against frozen expected
results.

**Expected total effort: about 1 hour** (a few minutes of setup, roughly
5–15 minutes of compute depending on your machine, and a short report to fill
in). Nothing here makes or supports any trading-profit claim; you are
verifying protocol reproducibility only.

## What it runs

| Step | What it is | Why it matters |
| --- | --- | --- |
| `validate_protocol` | Validates the frozen v0.3 protocol JSON and its canonical hash | Confirms the research contract you are replicating |
| `deterministic_trajectory` | Regenerates a replayable audit trajectory and its reproducibility hash | End-to-end determinism of the harness |
| `anchor_execution_ladder` | 12 classical (non-LLM) agents x execution levels E0/E1 x 30 seeds x 45 decision steps (720 runs, C0 synthetic data) | The benchmark's deterministic leaderboard anchor, incl. ranking-stability statistics (Kendall tau, top-k Jaccard, bootstrap CIs) |
| `anchor_power_note` | Bootstrap/permutation power curves and smallest-detectable-effect note | The statistics machinery behind the protocol's repeat-count thresholds |

## Quick start (native Python)

```bash
# 1. Unzip this pack anywhere, then from the pack root:
python replicate.py --environment-class linux      # or: windows_or_macos / colab_or_binder

# 2. Read the verdict. You should see PASS on every check and an OVERALL: PASS line.

# 3. Fill in the sign-off section of outputs/REPLICATION_REPORT.md
#    and return it together with outputs/replication_report.json.
```

If you received this pack through an invitation that names a repository or
release URL, add `--repository-url <that URL>` so your report records where
the pack came from, and add `--reviewer-name "Your Name"` if you want the
report pre-filled.

## Docker (one command, Linux environment class)

```bash
docker build -t tradearena-replication .
docker run --rm -v "$PWD/outputs:/pack/outputs" tradearena-replication --environment-class linux
```

The report appears in `./outputs/` on the host.

## Colab / Binder

Open `colab_replicate.ipynb` in Google Colab, upload the pack zip when
prompted, and run all cells. Use `--environment-class colab_or_binder`
(the notebook does this for you).

## How verification works

`replicate.py` re-runs every anchor from scratch and compares the results
against `expected_results/expected_results.json`, which was frozen from a real
run of this exact pack:

- **Tolerance tier (must pass):** every aggregate metric (Sharpe mean/std,
  bootstrap CI bounds, returns, drawdowns, fill rates, slippage,
  intent-to-execution gaps), every leaderboard rank, and every
  ranking-stability statistic is compared within `|a - e| <= max(2e-6, 1e-6*|e|)`.
  All compared floats are rounded to 6 decimals by the generating scripts, so
  this tolerance absorbs at most one last-digit rounding step caused by
  platform math-library differences, while any real behavioral difference
  fails loudly.
- **Strict tier (informational):** exact SHA-256 hashes of the replayable
  trajectory. These normally match bit-for-bit; a `STRICT_DIFFER` with all
  tolerance checks passing indicates last-ulp floating-point differences on
  your platform and does **not** fail the replication.
- **Pack integrity:** every file in the pack is hash-checked against
  `PACK_MANIFEST.json` before running, so a corrupted download fails fast.

The final verdict is `OVERALL: PASS` only if all commands exit 0 and every
tolerance-tier check passes.

## What to send back

1. `outputs/replication_report.json` — machine-readable, schema-compatible
   with the project's external-reproduction intake gate.
2. `outputs/REPLICATION_REPORT.md` — with the sign-off section completed
   (see also `REPORT_TEMPLATE.md` for the same form as a blank template).

Send both files back through the channel named in your invitation (email
attachment or a GitHub issue). Your report is counted as independent evidence
only if you are not an author or maintainer of the project and you ran the
pack without API keys or private data — which is the only way this pack can
run.

## Troubleshooting

- `python` not found or too old: any CPython >= 3.10 works
  (`python3 replicate.py ...`).
- A step fails: re-run with the same command; the pack is deterministic. If it
  still fails, send the report files anyway — failure reports are useful too.
- Quick smoke check first (about 1 minute, no verdict):
  `python replicate.py --quick`.

## Scope and claims

This pack exercises the deterministic, CPU-only anchor arms of the TradeArena
v0.3 protocol (contamination tier C0, execution levels E0/E1). It does not
call any LLM provider and does not evaluate any LLM. It supports the claim
"the protocol's deterministic anchors and statistics are independently
reproducible", and no claim about trading profitability.

License: MIT (see `LICENSE`).
