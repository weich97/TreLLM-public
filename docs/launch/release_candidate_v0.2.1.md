# v0.2.1 Release Candidate Manifest

This is a local release-candidate manifest. Tagging and PyPI publication are separate maintainer actions and require CI plus trusted-publishing credentials.

## Candidate State

- Target release: `v0.2.1`
- Current package version: `0.2.0`
- Commit: `690817ae737ae3a65bf36083153286d919110334`
- Working tree dirty entries when generated: `21`

## Pre-Release Commands

- `python -m compileall src scripts examples tests -q`
- `python -m ruff check src scripts examples tests`
- `python -m mypy`
- `python -m pytest tests -q`
- `python scripts/check_release_readiness.py`
- `python scripts/scan_public_artifacts.py outputs docs/results examples/benchmark_submissions`

## Artifact Hashes

- `README.md`: present sha256:6f6883aba9874317f8cd4dbea16127475136abc7a33f5d32266ba26fa8d6ae6c
- `benchmarks/v0.2/spec.json`: present sha256:8e688190ff17bc0fca691bcd600bc56bb13d1215d2b5d6a8ac611ae70e17b156
- `docs/results/benchmark_v0_2.md`: present sha256:319a45938b5708862ea06e280b78089bfe5b08f37a69006fe3707d1796126122
- `docs/results/execution_replay_calibration_loop.json`: present sha256:afed5a3dd9940f654b0d28186dca2ca6bdafaf4e3da119308efe397aa47a9705
- `docs/results/execution_calibration_stability.json`: present sha256:f3c3ea588ca6a0bb7a7e4c9123aac73a7907a5664522dd6da0e2490cbc04006d
- `docs/results/market_rules_fixture.json`: present sha256:cd79f3c9b0bfe5061a8c835d721973f607b557b1292bc5b0be2e084f0946216f
- `docs/results/external_validation_bundle.md`: present sha256:73827281f52acc3dbc87e45ef0a98459fa52299242fc77fa1cde6040282af9db
- `docs/results/poe_skill_task_matrix.md`: present sha256:b65ad15ca310f8b3af18e03bd69eaa16301017e12d9f2dfef83731ee175ca3f4
- `docs/results/poe_skill_challenge_matrix.md`: present sha256:6a15c24a0c355c2ddc21aa7b915854e94796c91a181e11b1ae2897841d88f6d2
- `docs/results/poe_skill_challenge_followup_matrix.md`: present sha256:be2e3fe9c9186367b59c65110da159047b24909730b11f83abb0362e08394b47
- `docs/results/poe_skill_challenge_followup_claude_adversarial.md`: present sha256:de116d52697da541083dab9193e79d0a4b931e233b2f26846e4c34b0dbf5e4e9
- `docs/results/skill_task_matrix.md`: present sha256:560dd7f8427e44af316f90a84765acb80fd931b4862cf32cd6f41a73ecce26ae
- `docs/results/community_registry.md`: present sha256:e875e8cddd6c6405a4d7718c6f26b488f087ce3644633bbdd7fd4b8052f4a9cc
- `docs/public_artifact_privacy.md`: present sha256:4c52add96868290eab0b2f17aa060aaf94db052dd5a0bc048974e8b240b60d94
- `docs/launch/release_notes_v0.2.1.md`: present sha256:8a0d326255aacca2f55cb32f0b822ce5ef7501e0d545f1e4a8dabf86a6fd6b60

## Release Notes Draft

- Public artifact redaction is now enforced by default for trajectory JSON and public result scans.
- Provider audit matrix results compare frontier models as financial-audit agents rather than stock pickers.
- Execution evidence now includes a replay loop across OHLCV stress, quote replay, and fill replay.
- External validation bundle generation turns reproduction manifests into issue-ready reports.
- OpenTelemetry-style local trace export maps trajectories into portable audit spans.
