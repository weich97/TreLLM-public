# Observability Roadmap

TreLLM trajectories are already structured logs. The next step is to make
them portable into common experiment-tracking and trace-inspection systems
without changing the runner.

## Trace Mapping

| TreLLM record | OpenTelemetry-style span | Evals or trace-style field |
| --- | --- | --- |
| market snapshot | `market.observe` | input context |
| analyst signal | `agent.analyze` | tool or model-derived signal |
| strategy decision | `agent.decide` | output candidate |
| risk report | `risk.approve` or `risk.monitor` | grader or guardrail result |
| order and fill | `execution.simulate` | tool call and tool result |
| memory record | `agent.memory` | state update |
| evaluator metrics | `eval.metrics` | score payload |

## Export Targets

| Target | Useful for | Design constraint |
| --- | --- | --- |
| OpenTelemetry | local span inspection and service traces | no raw provider text by default |
| W&B | experiment dashboards and artifact lineage | optional dependency and offline mode |
| MLflow | metric comparison and artifact tracking | plain file-store support first |
| OpenAI Evals-style JSON | evaluation exchange | preserve redaction boundaries |
| LangSmith-style traces | agent step inspection | map risk and execution as explicit tools |

## Implementation Principles

- Exporters should be optional and disabled by default.
- Raw prompts and responses should be excluded unless the user opts in locally.
- Every exported artifact should include scenario, data, risk, execution, agent,
  and hash metadata.
- Exporters should accept an existing trajectory JSON rather than rerunning an
  experiment.

## First Implementable Slice

1. Add `tradearena export-trace trajectory.json --format opentelemetry-json`.
2. Convert each step into spans with stable parent IDs.
3. Add a fixture-based test that verifies span count, event names, and redacted
   fields.
4. Document one local viewer command.

This keeps observability work useful without adding live services to the default
path.

The first slice is now implemented as a local JSON exporter:

```bash
tradearena export-trace outputs/examples/audit_walkthrough_trajectory.json \
  --format opentelemetry-json \
  --output outputs/examples/audit_walkthrough_trace.json
```

The exporter reads an existing trajectory and does not rerun experiments. It
emits `market.observe`, `agent.analyze`, `agent.decide`, `risk.approve`, and
`execution.simulate` spans with stable parent IDs. Raw prompts, raw responses,
and raw rationales are excluded; model and memory identifiers are represented
as hashes or structured counts.

The trace artifact records the default redaction boundary explicitly:

- `prompt_payloads_exported: false`
- `provider_outputs_exported: false`
- `rationale_payloads_exported: false`
- `raw_provider_text_policy: excluded_by_default`
- `excluded_field_categories`: prompt payloads, message payloads, provider
  outputs, and rationales

The issue-level validation path is:

```bash
python -m pytest tests/test_observability_export.py -q
```

## Evals And LangSmith-Style Mapping

TreLLM also exposes a local compatibility schema for adjacent agent-evaluation
tools:

```python
from tradearena.evaluation import export_trajectory_to_trace_schema_json

export_trajectory_to_trace_schema_json(
    "outputs/examples/audit_walkthrough_trajectory.json",
    "outputs/examples/audit_walkthrough_eval_trace_schema.json",
)
```

The schema example lives at `schemas/eval_trace_style.schema.json`. Each
trajectory step becomes one record with compact `inputs`, `outputs`, `events`,
and `scores` fields. Risk reports map to `guardrail` events so blocked or
clipped decisions can be reviewed like grader results. Simulated execution
reports map to `tool_result` events so fills, partial fills, pending orders,
and rejections remain visible without treating them as model text.

Compatibility limits:

- The artifact is a local JSON style mapping, not a direct OpenAI Evals or
  LangSmith API request body.
- Raw prompts, provider responses, and rationales remain excluded by default.
- Execution events describe simulated or replayed fills unless a separate
  broker or fill-replay artifact proves live-market provenance.

Validation:

```bash
python -m pytest tests/test_trace_schema_export.py -q
```

## Offline Tracking Export

For experiment-tracking workflows, TreLLM provides a plain-file offline export
that follows an MLflow-style directory shape without importing MLflow or W&B:

```python
from tradearena.evaluation import export_trajectory_to_offline_tracking

export_trajectory_to_offline_tracking(
    "outputs/examples/audit_walkthrough_trajectory.json",
    "outputs/examples/audit_walkthrough_tracking",
)
```

The exporter consumes an existing trajectory JSON and writes:

- `meta.yaml`: run metadata and source trajectory path
- `metrics.json`: step count, fills, rejected/pending orders, risk blocks,
  costs, slippage, and final equity
- `artifacts/trajectory_manifest.json`: scenario, seed, schema version, step
  count, and trajectory hash
- `artifacts/redaction.json`: local redaction boundary
- `export_summary.json`: the full plain-file tracking artifact

This mode intentionally keeps `dependencies_required: []`. It is useful for
local dashboards, CI artifacts, and later import into external experiment
trackers, but it does not create a live W&B run or MLflow tracking server entry.

Validation:

```bash
python -m pytest tests/test_offline_tracking_export.py -q
```
