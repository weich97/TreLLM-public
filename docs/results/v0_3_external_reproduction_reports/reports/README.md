# TreLLM v0.3 External Reproduction Reports

Place independent reproduction report JSON files in this directory. Reviewers
can generate one with `scripts/run_v03_external_reproduction_pack.py`.

A report counts toward the v0.3 external reproduction gate only when it:

- uses `schema=tradearena_external_reproduction_pack_v1`;
- sets `protocol_id=trellm-v0.3-protocol`;
- sets one `environment_class`: `windows_or_macos`, `linux`, or `colab_or_binder`;
- sets `report_author_type=independent` and `independent_reviewer=true`;
- has no failed required commands or missing required artifacts;
- records artifact SHA-256 digests and a trajectory reproducibility hash;
- does not use private fills.

Generate the gate with:

```bash
python scripts/build_v03_external_reproduction_gate.py
```
