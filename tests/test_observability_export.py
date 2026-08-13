from __future__ import annotations

import json
from pathlib import Path

from tradearena.evaluation.trace_export import export_trajectory_to_trace_json


def test_observability_export_uses_existing_trajectory_and_records_parent_links(tmp_path: Path):
    trajectory_path = tmp_path / "trajectory.json"
    output_path = tmp_path / "trace.json"
    trajectory_path.write_text(json.dumps(_trajectory_with_provider_text()), encoding="utf-8")

    trace = export_trajectory_to_trace_json(trajectory_path, output_path)

    assert output_path.exists()
    assert trace["redaction"]["prompt_payloads_exported"] is False
    assert trace["redaction"]["provider_outputs_exported"] is False
    assert trace["redaction"]["rationale_payloads_exported"] is False
    assert set(trace["redaction"]["excluded_field_categories"]) >= {
        "prompt_payloads",
        "message_payloads",
        "provider_outputs",
        "rationales",
    }
    assert trace["redaction"]["raw_provider_text_policy"] == "excluded_by_default"

    spans = trace["spans"]
    by_name = {span["name"]: span for span in spans}
    root = by_name["tradearena.run"]
    step = by_name["tradearena.step"]

    assert root["parent_span_id"] == ""
    assert step["parent_span_id"] == root["span_id"]
    for name in ("market.observe", "agent.analyze", "agent.decide", "risk.approve", "execution.simulate"):
        assert by_name[name]["parent_span_id"] == step["span_id"]

    serialized = output_path.read_text(encoding="utf-8")
    assert "secret prompt" not in serialized
    assert "secret provider response" not in serialized
    assert "private rationale" not in serialized


def _trajectory_with_provider_text() -> dict[str, object]:
    return {
        "experiment_name": "existing_artifact_only",
        "seed": 37,
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
                    "messages": [{"role": "user", "content": "secret prompt"}],
                },
                "signals": [
                    {
                        "symbol": "SYN",
                        "score": 0.2,
                        "rationale": "private rationale",
                        "metadata": {"response_text": "secret provider response"},
                    }
                ],
                "decisions": [{"symbol": "SYN", "target_weight": 0.1, "raw_response": "secret provider response"}],
                "approved_decisions": [{"symbol": "SYN", "target_weight": 0.1}],
                "orders": [{"symbol": "SYN", "side": "buy", "quantity": 1.0}],
                "fills": [{"symbol": "SYN", "quantity": 1.0, "price": 100.0}],
                "portfolio": {"cash": 99_900.0, "equity": 100_000.0, "positions": {"SYN": 1.0}},
                "risk_report": {
                    "phase": "pre_trade",
                    "approved_count": 1,
                    "blocked_count": 0,
                    "clipped_count": 0,
                    "checks": [{"name": "max_position", "passed": True}],
                },
                "execution_report": {
                    "submitted_orders": 1,
                    "filled_orders": 1,
                    "partial_fills": 0,
                    "pending_orders": 0,
                    "rejected_orders": 0,
                },
                "reproducibility_state": {
                    "prompt_version": "v1",
                    "model_version": "provider/model/private",
                    "memory_digest": "secret memory digest",
                },
            }
        ],
    }
