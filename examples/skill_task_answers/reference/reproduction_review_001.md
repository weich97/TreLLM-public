# Reproduction Review

The report includes release tag v0.2.0 but the commit field is missing. That
blocks a fully auditable external reproduction claim.

The command log is present: both commands include a command string and returncode
0. The artifact path is present at outputs/fresh/quickstart_trajectory.json.

Hash coverage is partial: the artifact has a sha256 value, but a stronger report
should also include the trajectory hash or reproducibility hash emitted by
hash-run.

The data-source flags are present: live_api_used is false,
downloaded_market_data is false, and private_fills_used is false.
