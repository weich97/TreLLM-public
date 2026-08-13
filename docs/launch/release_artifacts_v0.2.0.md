# v0.2.0 Release Artifact Inventory

This file records the canonical benchmark spec hash, reproducible artifact
hashes, and local distribution hashes for the v0.2.0 release.

The machine-readable companion is
`docs/launch/release_artifacts_v0.2.0.json`.

## Canonical Benchmark Spec

| Item | Value |
| --- | --- |
| Spec path | `benchmarks/v0.2/spec.json` |
| Spec id | `tradearena-v0.2` |
| Schema version | `tradearena_benchmark_spec_v0.2` |
| Canonical SHA-256 | `sha256:a777cdfb962a07e658996c9366070d4b0ffb867659c2ccc45685a5c788bf6204` |
| File SHA-256 | `sha256:8e688190ff17bc0fca691bcd600bc56bb13d1215d2b5d6a8ac611ae70e17b156` |

## Reproduction Pack

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `outputs/examples/audit_walkthrough_trajectory.json` | 6019599 | `sha256:cd34f609ffebc373341c923b5242c4d90d1a532733eb3feca01e0343415b438c` |
| `outputs/examples/audit_report.html` | 14822 | `sha256:2c468f2f14eb9f2bec8003fe7366b5da60132f0871a7e9ade52743ead764bab6` |
| `outputs/examples/agent_autopsy_dashboard.html` | 50069 | `sha256:863e69301d44b8b8db8f30fb9694ffe4961bd5a22cec797ed05403cee6ce6235` |
| `outputs/examples/failure_autopsy.json` | 59420 | `sha256:3b3b34fc2529322006198cf2c39a64619233ffdd99d05fcd4a2e928ce4caad7b` |
| `outputs/examples/failure_autopsy.md` | 28064 | `sha256:ac767839b4e6a1a0c020258b7fc31bd7b0cfc9550430a5f23babd7d5030d944d` |
| `examples/benchmark_submissions/example_redacted_submission.json` | 2184 | `sha256:c5221c49a5b6d01215325561cd0ed4811b8a0fbf03cff2c8a47f0474b9a95395` |

Trajectory reproducibility hash:
`sha256:bf3b1084aeec89f3bf0f99ab91b6c16a989dc8c8a29d9e93c8c72109548e442f`.

The generated manifest itself lives under `outputs/reproduction/v0_2/` and is
ignored by Git because it records machine-local Python paths, platform metadata,
and the current commit/tag.

## Distribution Files

These hashes are from the official GitHub Release assets and match the PyPI
`tradearena-benchmark==0.2.0` file digests uploaded on 2026-05-22.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `tradearena_benchmark-0.2.0-py3-none-any.whl` | 133274 | `sha256:2d21b11554100a9c52fd3b934e2919976e7e5ce4f2912aa7df0ff9110eda621e` |
| `tradearena_benchmark-0.2.0.tar.gz` | 144573 | `sha256:25d0fc6a58914558e3197a17d85ed64dd754e67a09d4aa176c48f7a8544a2568` |

## Verification Commands

```bash
python scripts/validate_benchmark_spec.py benchmarks/v0.2/spec.json
python scripts/run_external_reproduction_pack.py --output-dir outputs/reproduction/v0_2
python -m build
python -m twine check dist/*
```
