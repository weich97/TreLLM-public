import json
import subprocess
import sys
from pathlib import Path

from tradearena.core.trajectory import Trajectory
from tradearena.evaluation.audit import export_audit_bundle

ROOT = Path(__file__).resolve().parents[1]


def test_audit_bundle_manifest_uses_trellm_system_identity(tmp_path: Path):
    trajectory = Trajectory(experiment_name="identity_bundle", seed=7)

    export_audit_bundle(tmp_path, trajectory=trajectory, metrics={"return": 0.0})

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["framework"] == "TreLLM"
    assert manifest["leaderboard_module"] == "TradeArena"
    assert "auditable decision-making systems" in manifest["claim"]


def test_render_audit_report_from_minimal_trajectory(tmp_path: Path):
    trajectory = {
        "experiment_name": "unit_audit",
        "seed": 1,
        "metadata": {"order_simulator": "realistic-order-simulator"},
        "steps": [
            {
                "timestamp": "2026-01-01T00:00:00",
                "observation": {"prices": {"SYN": 100.0}, "news_count": 0, "macro_count": 0},
                "signals": [
                    {
                        "symbol": "SYN",
                        "score": 0.5,
                        "confidence": 0.8,
                        "rationale": "unit signal",
                        "metadata": {"analyst": "unit"},
                    }
                ],
                "decisions": [
                    {
                        "symbol": "SYN",
                        "side": "buy",
                        "target_weight": 0.75,
                        "confidence": 0.8,
                        "rationale": "unit decision",
                        "metadata": {},
                    }
                ],
                "approved_decisions": [
                    {
                        "symbol": "SYN",
                        "side": "buy",
                        "target_weight": 0.25,
                        "confidence": 0.8,
                        "rationale": "unit decision",
                        "metadata": {"risk_clipped_from": 0.75},
                    }
                ],
                "orders": [{"symbol": "SYN", "side": "buy", "quantity": 10}],
                "fills": [],
                "portfolio": {"cash": 100000.0, "positions": {}, "last_prices": {"SYN": 100.0}, "equity": 100000.0},
                "reproducibility_state": {
                    "prompt_version": "unit",
                    "model_version": "deterministic",
                    "market_data_timestamp": "2026-01-01T00:00:00",
                    "memory_digest": "abc123",
                    "random_seed": 1,
                },
                "agent_trace": {},
                "risk_report": _risk_report("pre_trade", clipped=1),
                "in_trade_report": _risk_report("in_trade", clipped=0),
                "post_trade_report": _risk_report("post_trade", clipped=0),
                "execution_report": {
                    "submitted_orders": 1,
                    "eligible_orders": 0,
                    "filled_orders": 0,
                    "partial_fills": 0,
                    "pending_orders": 1,
                    "rejected_orders": 0,
                    "total_commission": 0.0,
                    "total_slippage": 0.0,
                    "average_latency_steps": 0.0,
                },
                "risk_violations": [],
                "memory_events": [],
            }
        ],
    }
    trajectory_path = tmp_path / "trajectory.json"
    output_path = tmp_path / "report.html"
    autopsy_path = tmp_path / "autopsy.html"
    trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/render_audit_report.py",
            "--trajectory",
            str(trajectory_path),
            "--output",
            str(output_path),
        ],
        check=True,
    )

    html = output_path.read_text(encoding="utf-8")
    assert "TreLLM Audit Report" in html
    assert "Proposed vs Risk-Approved Decisions" in html
    assert "unit decision" in html
    assert "abc123" in html

    subprocess.run(
        [
            sys.executable,
            "scripts/render_agent_autopsy_dashboard.py",
            "--trajectory",
            str(trajectory_path),
            "--output",
            str(autopsy_path),
        ],
        check=True,
    )

    autopsy = autopsy_path.read_text(encoding="utf-8")
    assert "Agent Autopsy Dashboard" in autopsy
    assert "Intent vs Executed Weights Time-Series" in autopsy
    assert "Slippage Attribution Waterfall" in autopsy
    assert "Risk Intervention Timeline" in autopsy

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "replay",
            str(trajectory_path),
            "--step",
            "1",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "TreLLM Replay: unit_audit step 1 / 1" in result.stdout
    assert "TradeArena Replay:" not in result.stdout
    assert "Intent -> Approved" in result.stdout
    assert "0.750 -> 0.250" in result.stdout

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps({"case_a": {"trajectory": trajectory, "metrics": {}}}), encoding="utf-8")
    json_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "replay",
            str(bundle_path),
            "--case",
            "case_a",
            "--step",
            "1",
            "--json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    replay_payload = json.loads(json_result.stdout)
    assert replay_payload["experiment"] == "unit_audit"
    assert replay_payload["decisions"][0]["approved_weight"] == 0.25


def test_replay_reports_malformed_trajectory_json(tmp_path: Path):
    trajectory_path = tmp_path / "broken_trajectory.json"
    trajectory_path.write_text('{"steps": ', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradearena.cli",
            "replay",
            str(trajectory_path),
            "--step",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Trajectory file must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def _risk_report(phase: str, clipped: int) -> dict:
    return {
        "timestamp": "2026-01-01T00:00:00",
        "checks": [
            {
                "name": "unit_check",
                "passed": True,
                "severity": "warning" if clipped else "info",
                "message": "unit risk message",
                "metadata": {},
            }
        ],
        "approved_count": 1,
        "blocked_count": 0,
        "clipped_count": clipped,
        "phase": phase,
        "budget": {},
        "violations": [],
    }
