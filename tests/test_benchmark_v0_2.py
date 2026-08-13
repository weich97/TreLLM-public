from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.run_external_reproduction_pack import _render_readme, summarize_failed_commands
from tradearena.tools.calibration import summarize_quote_fill_calibration

ROOT = Path(__file__).resolve().parents[1]


def test_v02_spec_validates_and_names_required_surfaces():
    result = subprocess.run(
        [sys.executable, "scripts/validate_benchmark_spec.py", "benchmarks/v0.2/spec.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    spec = json.loads((ROOT / "benchmarks/v0.2/spec.json").read_text(encoding="utf-8"))

    assert payload["valid"] is True
    assert payload["canonical_sha256"].startswith("sha256:")
    assert spec["status"] == "frozen"
    assert "paired_sign_flip_permutation" in spec["statistics"]["paired_tests"]
    assert "random" in spec["baselines"]
    assert "always-hold" in spec["baselines"]


def test_v03_protocol_validates_required_submission_gates():
    result = subprocess.run(
        [sys.executable, "scripts/validate_benchmark_spec.py", "benchmarks/v0.3/protocol.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    spec = json.loads((ROOT / "benchmarks/v0.3/protocol.json").read_text(encoding="utf-8"))

    assert payload["valid"] is True
    assert payload["schema_version"] == "trellm_protocol_v0.3"
    assert payload["spec_id"] == "trellm-v0.3-protocol"
    assert payload["canonical_sha256"].startswith("sha256:")
    assert spec["system_identity"]["system_name"] == "TreLLM"
    assert spec["system_identity"]["leaderboard_name"] == "TradeArena"
    assert spec["provider_protocol"]["headline_results"]["allow_routed_providers"] is False
    assert {level["id"] for level in spec["execution_ladder"]} == {"E0", "E1", "E2", "E3"}
    assert {tier["id"] for tier in spec["contamination_tiers"]} == {"C0", "C1", "C2"}
    assert spec["statistics"]["llm_main_comparison"]["minimum_seeds"] >= 10
    assert spec["statistics"]["llm_main_comparison"]["samples_per_seed"] >= 3
    assert "power_curve_or_detectable_effect_note" in spec["statistics"]["required_methods"]
    assert "variance_decomposition" in spec["statistics"]["required_methods"]
    assert "power curve or detectable effect note" in spec["required_artifacts"]
    assert "variance decomposition table" in spec["required_artifacts"]
    assert "claim-boundary audit" in spec["required_artifacts"]
    assert "direct API redaction and submission checklist" in spec["required_artifacts"]
    assert "direct API model matrix gate" in spec["required_artifacts"]
    assert "direct API call packet manifest" in spec["required_artifacts"]
    assert "contamination-control readiness audit" in spec["required_artifacts"]
    assert "execution stress-grid report" in spec["required_artifacts"]
    assert "FinAudit direct-model audit plan" in spec["required_artifacts"]
    assert "external reproduction report gate" in spec["required_artifacts"]
    assert "intent_to_execution_gap" in spec["metrics"]["mechanism"]
    assert "self_audit_bias" in spec["finaudit_track"]["required_analyses"]
    assert spec["external_reproduction"]["minimum_independent_reports"] >= 3


def test_benchmark_spec_validator_reports_malformed_json(tmp_path: Path):
    spec = tmp_path / "broken_spec.json"
    spec.write_text('{"schema_version": ', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_benchmark_spec.py", str(spec)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["errors"] == ["benchmark spec file must contain valid JSON"]
    assert "Traceback" not in result.stderr


def test_quote_fill_calibration_fixture_fits_execution_parameters():
    summary = summarize_quote_fill_calibration(
        ROOT / "data/public/microstructure_sample/quotes.csv",
        ROOT / "data/public/microstructure_sample/fills.csv",
    )

    assert summary["input"]["aligned_rows"] == 8
    assert summary["fitted_parameters"]["spread_bps_median"] > 0
    assert summary["fitted_parameters"]["spread_bps_p99"] >= summary["fitted_parameters"]["spread_bps_p90"]
    assert summary["fitted_parameters"]["market_impact"] >= 0
    assert summary["fit_quality"]["residual_mae_bps"] < 2.0
    assert summary["fit_quality"]["residual_p90_abs_bps"] >= summary["fit_quality"]["residual_mae_bps"]
    assert "stress_only_comparison" in summary
    assert summary["suggested_simulator_config"]["spread_bps"] > 0


def test_binance_public_microstructure_sample_reports_quote_fill_replay_error():
    summary = summarize_quote_fill_calibration(
        ROOT / "data/public/binance_btcusdt_perp_2024_03_01_sample/quotes.csv",
        ROOT / "data/public/binance_btcusdt_perp_2024_03_01_sample/fills.csv",
    )
    manifest = json.loads(
        (ROOT / "data/public/binance_btcusdt_perp_2024_03_01_sample/manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["provenance"]["downloaded_market_data_used"] is True
    assert summary["input"]["aligned_rows"] == 500
    assert summary["fitted_parameters"]["quote_event_lag_seconds_median"] is not None
    assert summary["fitted_parameters"]["quote_staleness_seconds_p90"] is not None
    assert summary["fit_quality"]["p90_shortfall_bps"] >= summary["fit_quality"]["median_shortfall_bps"]
    assert summary["stress_only_comparison"]["residual_mae_bps"] > summary["fit_quality"]["residual_mae_bps"]


def test_execution_replay_calibration_loop_compares_three_modes(tmp_path: Path):
    output = tmp_path / "loop.json"
    markdown = tmp_path / "loop.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_execution_replay_calibration_loop.py",
            "--samples",
            "fixture",
            "--output",
            str(output),
            "--markdown-output",
            str(markdown),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(output.read_text(encoding="utf-8"))
    modes = {row["mode"]: row for row in summary["mode_rows"]}

    assert set(modes) == {"ohlcv_stress", "quote_replay", "fill_replay"}
    assert "conservative proxy" in summary["claim_boundary"]
    assert modes["ohlcv_stress"]["evidence_labels"] == ["stress-only", "conservative-proxy"]
    assert "quote-replay" in modes["quote_replay"]["evidence_labels"]
    assert modes["fill_replay"]["quantity_fill_ratio"] == 1.0
    assert modes["ohlcv_stress"]["mean_slippage_bps"] > modes["fill_replay"]["mean_slippage_bps"]
    assert "not for ground-truth transaction-cost prediction" in markdown.read_text(encoding="utf-8")


def test_external_reproduction_pack_writes_manifest(tmp_path: Path):
    output_dir = tmp_path / "repro"
    subprocess.run(
        [sys.executable, "scripts/run_external_reproduction_pack.py", "--output-dir", str(output_dir)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["schema"] == "tradearena_external_reproduction_pack_v1"
    assert manifest["commit_or_tag"]
    assert manifest["live_api_used"] is False
    assert manifest["private_fills_used"] is False
    assert manifest["trajectory_hash"]["reproducibility_hash"].startswith("sha256:")
    assert any(artifact["path"].endswith("agent_autopsy_dashboard.html") for artifact in manifest["artifacts"])
    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# TreLLM v0.2 External Reproduction Pack")
    assert "# TradeArena v0.2 External Reproduction Pack" not in readme


def test_external_reproduction_pack_readme_includes_issue_ready_text():
    readme = _render_readme(
        {
            "commit_or_tag": "abc1234",
            "python": {"version": "3.11.9", "platform": "Windows-10"},
            "commands": [
                {"id": "trajectory", "argv": ["python", "examples/audit_trajectory_walkthrough.py"], "returncode": 0},
                {"id": "release_readiness", "argv": ["python", "scripts/check_release_readiness.py"], "returncode": 1},
            ],
            "artifacts": [
                {"path": "outputs/examples/audit_walkthrough_trajectory.json", "exists": True, "sha256": "sha256:abc"},
                {"path": "outputs/examples/audit_report.html", "exists": False},
            ],
            "trajectory_hash": {"reproducibility_hash": "sha256:trajectory"},
            "live_api_used": False,
            "market_data_used": "deterministic synthetic data",
            "private_fills_used": False,
        }
    )

    assert "## Suggested Issue Text" in readme
    assert "Environment: Windows-10 / Python 3.11.9" in readme
    assert "Commit/tag: abc1234" in readme
    assert "Trajectory hash: sha256:trajectory" in readme
    assert "Manifest: outputs/reproduction/v0_2/manifest.json" in readme
    assert "Commands failed: release_readiness" in readme
    assert "Missing artifacts: outputs/examples/audit_report.html" in readme
    assert "No live APIs or private fills were used." in readme


def test_external_reproduction_pack_reports_failed_command_details():
    summary = summarize_failed_commands(
        [
            {
                "id": "agent_autopsy",
                "returncode": 1,
                "stdout_tail": "Wrote partial dashboard\n",
                "stderr_tail": "Traceback tail\nValueError: broken fixture\n",
            },
            {"id": "release_readiness", "returncode": 0, "stdout_tail": "ok", "stderr_tail": ""},
        ]
    )

    assert "Failed reproduction commands:" in summary
    assert "agent_autopsy returned 1" in summary
    assert "stderr tail:" in summary
    assert "ValueError: broken fixture" in summary
    assert "release_readiness" not in summary
