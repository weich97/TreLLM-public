# v0.3 External Reproduction Pack

The v0.3 reproduction target exercises the protocol evidence path without
requiring API keys. It validates the protocol, regenerates small public fixture
artifacts, builds the direct API matrix plan and credential preflight, generates
the direct API call packets, generates the direct API redaction/submission checklist, runs the direct API matrix gate,
builds the variance decomposition fixture, builds the FinAudit direct-model
audit plan, builds the contamination-control readiness audit, runs the
execution stress-grid fixture, builds the
claim-boundary audit, builds the external reproduction gate, rebuilds the
evidence index, and records hashes for the generated outputs.

## Command

```bash
python scripts/run_v03_external_reproduction_pack.py \
  --environment-class linux
```

Use one of these environment classes:

- `windows_or_macos`
- `linux`
- `colab_or_binder`

By default this writes `outputs/reproduction/v0_3/manifest.json` and
`outputs/reproduction/v0_3/README.md`. Maintainer-authored reports are useful
smoke tests, but they do not count as independent external validation.

Independent reviewers should run:

```bash
python scripts/run_v03_external_reproduction_pack.py \
  --environment-class linux \
  --report-author-type independent \
  --independent-reviewer
```

Then validate the report:

```bash
python scripts/validate_reproduction_report.py outputs/reproduction/v0_3/manifest.json
```

The report counts toward the v0.3 external reproduction gate only if the gate
accepts it:

```bash
python scripts/build_v03_external_reproduction_gate.py \
  --report-dirs outputs/reproduction/v0_3
```

The full v0.3 external reproducibility claim requires three accepted independent
reports covering Windows/macOS, Linux, and Colab/Binder.
