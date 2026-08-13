from __future__ import annotations

import json
from pathlib import Path

from tradearena.evaluation.offline_tracking import export_trajectory_to_offline_tracking


def test_offline_tracking_export_consumes_existing_trajectory_without_live_dependencies(tmp_path: Path):
    trajectory_path = tmp_path / "trajectory.json"
    output_dir = tmp_path / "tracking"
    trajectory_path.write_text(json.dumps(_trajectory()), encoding="utf-8")

    artifact = export_trajectory_to_offline_tracking(trajectory_path, output_dir)

    assert artifact["schema"] == "trellm_offline_tracking_export_v0.1"
    assert artifact["mode"] == "plain_file_mlflow_style"
    assert artifact["dependencies_required"] == []
    assert artifact["source"]["trajectory_path"].endswith("trajectory.json")
    assert artifact["metrics"]["step_count"] == 2
    assert artifact["metrics"]["fill_count"] == 1
    assert artifact["metrics"]["rejected_order_count"] == 1
    assert artifact["metrics"]["risk_blocked_count"] == 1
    assert artifact["metrics"]["final_equity"] == 100_010.0

    assert (output_dir / "meta.yaml").exists()
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "artifacts" / "trajectory_manifest.json").exists()
    assert (output_dir / "artifacts" / "redaction.json").exists()

    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "artifacts" / "trajectory_manifest.json").read_text(encoding="utf-8"))
    redaction = json.loads((output_dir / "artifacts" / "redaction.json").read_text(encoding="utf-8"))

    assert metrics["risk_blocked_count"] == 1
    assert manifest["experiment_name"] == "offline_tracking_fixture"
    assert redaction["raw_provider_text_policy"] == "excluded_by_default"
    assert "secret provider response" not in (output_dir / "metrics.json").read_text(encoding="utf-8")
    assert "secret prompt" not in (output_dir / "artifacts" / "trajectory_manifest.json").read_text(encoding="utf-8")


def _trajectory() -> dict[str, object]:
    return {
        "experiment_name": "offline_tracking_fixture",
        "seed": 38,
        "schema_version": "tradearena_trajectory_v1",
        "steps": [
            {
                "timestamp": "2026-06-01T00:00:00+00:00",
                "observation": {"prices": {"SYN": 100.0}, "prompt": "secret prompt"},
                "signals": [{"symbol": "SYN", "score": 0.1, "metadata": {"response_text": "secret provider response"}}],
                "orders": [{"symbol": "SYN", "quantity": 1.0}],
                "fills": [{"symbol": "SYN", "quantity": 1.0, "price": 100.0}],
                "portfolio": {"equity": 100_000.0},
                "risk_report": {"blocked_count": 0, "clipped_count": 0, "checks": []},
                "execution_report": {
                    "submitted_orders": 1,
                    "filled_orders": 1,
                    "partial_fills": 0,
                    "pending_orders": 0,
                    "rejected_orders": 0,
                    "total_commission": 0.01,
                    "total_slippage": 0.02,
                },
            },
            {
                "timestamp": "2026-06-01T00:01:00+00:00",
                "observation": {"prices": {"SYN": 101.0}},
                "signals": [],
                "orders": [{"symbol": "SYN", "quantity": 2.0}],
                "fills": [],
                "portfolio": {"equity": 100_010.0},
                "risk_report": {"blocked_count": 1, "clipped_count": 0, "checks": [{"name": "max_position"}]},
                "execution_report": {
                    "submitted_orders": 1,
                    "filled_orders": 0,
                    "partial_fills": 0,
                    "pending_orders": 0,
                    "rejected_orders": 1,
                    "total_commission": 0.0,
                    "total_slippage": 0.0,
                },
            },
        ],
    }
