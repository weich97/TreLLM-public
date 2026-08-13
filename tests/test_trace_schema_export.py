from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from tradearena.evaluation.trace_schema_export import export_trajectory_to_trace_schema_json

ROOT = Path(__file__).resolve().parents[1]


def test_trace_schema_export_maps_risk_and_execution_events_without_raw_provider_text(tmp_path: Path):
    trajectory_path = tmp_path / "trajectory.json"
    output_path = tmp_path / "trace_schema.json"
    trajectory_path.write_text(json.dumps(_trajectory_with_risk_and_execution()), encoding="utf-8")

    artifact = export_trajectory_to_trace_schema_json(trajectory_path, output_path)

    schema = json.loads((ROOT / "schemas/eval_trace_style.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(artifact)

    assert output_path.exists()
    assert artifact["schema"] == "trellm_eval_trace_schema_v0.1"
    assert artifact["compatibility"]["openai_evals"] == "style_mapping_only"
    assert artifact["compatibility"]["langsmith"] == "style_mapping_only"
    assert artifact["redaction"]["raw_provider_text_policy"] == "excluded_by_default"
    assert artifact["records"][0]["inputs"] == {"symbol_count": 1, "news_count": 1, "macro_count": 0}

    events = artifact["records"][0]["events"]
    event_types = {event["type"] for event in events}
    assert {"model_candidate", "guardrail", "tool_result"} <= event_types

    guardrail = next(event for event in events if event["type"] == "guardrail")
    assert guardrail["name"] == "risk.approve"
    assert guardrail["status"] == "blocked"
    assert guardrail["payload"]["blocked_count"] == 1
    assert guardrail["payload"]["violation_count"] == 1

    tool_result = next(event for event in events if event["type"] == "tool_result")
    assert tool_result["name"] == "execution.simulate"
    assert tool_result["payload"]["fill_count"] == 1
    assert tool_result["payload"]["rejected_orders"] == 1

    serialized = output_path.read_text(encoding="utf-8")
    assert "secret prompt" not in serialized
    assert "secret provider response" not in serialized
    assert "private rationale" not in serialized


def _trajectory_with_risk_and_execution() -> dict[str, object]:
    return {
        "experiment_name": "trace_schema_fixture",
        "seed": 39,
        "schema_version": "tradearena_trajectory_v1",
        "steps": [
            {
                "timestamp": "2026-06-01T00:00:00+00:00",
                "observation": {
                    "prices": {"SYN": 100.0},
                    "news_count": 1,
                    "macro_count": 0,
                    "filings_count": 0,
                    "alt_data_count": 0,
                    "prompt": "secret prompt",
                },
                "signals": [
                    {
                        "symbol": "SYN",
                        "score": 0.3,
                        "rationale": "private rationale",
                        "metadata": {"response_text": "secret provider response"},
                    }
                ],
                "decisions": [{"symbol": "SYN", "target_weight": 0.2, "raw_response": "secret provider response"}],
                "approved_decisions": [],
                "orders": [{"symbol": "SYN", "side": "buy", "quantity": 2.0}],
                "fills": [{"symbol": "SYN", "quantity": 1.0, "price": 100.0}],
                "risk_violations": [{"constraint": "max_position", "severity": "error"}],
                "risk_report": {
                    "phase": "pre_trade",
                    "passed": False,
                    "approved_count": 0,
                    "blocked_count": 1,
                    "clipped_count": 0,
                    "checks": [{"name": "max_position", "passed": False}],
                },
                "execution_report": {
                    "submitted_orders": 1,
                    "filled_orders": 0,
                    "partial_fills": 1,
                    "pending_orders": 0,
                    "rejected_orders": 1,
                    "total_commission": 0.01,
                    "total_slippage": 0.02,
                },
            }
        ],
    }
