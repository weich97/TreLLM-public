# v0.2 External Reproduction Pack

The reproduction target is deliberately small: an external user should be able
to generate the same deterministic trajectory hash, validate one benchmark row,
and open the same audit/dashboard artifacts in about 15 minutes.

## Command

```bash
python scripts/run_external_reproduction_pack.py
```

By default this writes `outputs/reproduction/v0_2/manifest.json` and
`outputs/reproduction/v0_2/README.md`. The output directory is ignored by Git so
external validators can publish their own report without mutating the repository
history. The script runs:

- `examples/audit_trajectory_walkthrough.py`
- `scripts/render_audit_report.py`
- `scripts/render_agent_autopsy_dashboard.py`
- `scripts/run_failure_autopsy.py`
- `tradearena validate-submission examples/benchmark_submissions/example_redacted_submission.json`
- `scripts/check_release_readiness.py`

Validate the generated manifest before submitting it:

```bash
python scripts/validate_reproduction_report.py outputs/reproduction/v0_2/manifest.json
```

## Required Report Fields

Every reproduction report must include:

- repository commit or release tag;
- Python version and platform;
- exact commands;
- output paths;
- SHA-256 hashes for trajectory, dashboard/report artifacts, and benchmark row;
- trajectory reproducibility hash;
- whether live APIs were used;
- whether downloaded market data were used;
- whether private fills or broker data were used.

Provider-backed model reports and calibrated execution reports can use the same
format, but they must set the live API and data provenance fields accurately.
