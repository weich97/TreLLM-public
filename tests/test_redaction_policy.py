from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from tradearena.core.redaction import (
    PRIVATE_DEBUG_POLICY,
    RedactionPolicy,
    scan_public_artifact_paths,
    scan_public_artifact_payload,
)
from tradearena.core.serialization import read_json, write_json
from tradearena.core.trajectory import StepRecord, Trajectory

ROOT = Path(__file__).resolve().parents[1]


def test_public_redaction_policy_hashes_raw_llm_fields_and_redacts_text():
    payload = {
        "provider": "poe",
        "model": "gpt-5.5",
        "prompt": "private holdings plus raw prompt",
        "response_text": '{"signals":[{"symbol":"BTC-USD","target_weight":0.2}]}',
        "Authorization": "Bearer sk-testsecret000000000000",
        "account_email": "researcher@example.com",
        "signals": [
            {
                "symbol": "BTC-USD",
                "target_weight": 0.2,
                "rationale": "buy because private note says so",
            }
        ],
    }

    redacted = RedactionPolicy().redact(payload)
    rendered = json.dumps(redacted)

    assert redacted["provider"] == "poe"
    assert redacted["model"] == "gpt-5.5"
    assert redacted["prompt_hash"].startswith("sha256:")
    assert redacted["response_hash"].startswith("sha256:")
    assert redacted["Authorization_redacted"] is True
    assert redacted["account_email_redacted"] is True
    assert redacted["signals"][0]["target_weight"] == 0.2
    assert redacted["signals"][0]["rationale"].startswith("[redacted rationale sha256:")
    assert "private holdings" not in rendered
    assert "response_text" not in rendered
    assert scan_public_artifact_payload(redacted) == []


def test_private_debug_policy_preserves_raw_fields_and_public_scanner_flags_them():
    payload = {"prompt": "raw prompt", "response_text": "raw response"}

    private_payload = PRIVATE_DEBUG_POLICY.redact(payload)

    assert private_payload == payload
    findings = scan_public_artifact_payload(private_payload)
    assert any("raw prompt/response field" in finding for finding in findings)


def test_public_scanner_allows_hash_only_direct_provider_manifest_containers():
    payload = {
        "prompt": {
            "prompt_template_id": "trellm-allocation-v0.3",
            "prompt_version": "v0.3.0",
            "prompt_sha256": "sha256:" + "a" * 64,
            "system_prompt_sha256": "sha256:" + "b" * 64,
            "raw_prompt_public": False,
        },
        "response": {
            "response_sha256": "sha256:" + "c" * 64,
            "response_format": "json_object",
            "parse_status": "parsed",
            "raw_response_public": False,
        },
    }

    assert scan_public_artifact_payload(payload) == []


def test_trajectory_to_dict_is_public_redacted_by_default():
    trajectory = Trajectory(experiment_name="llm-like", seed=7)
    trajectory.append(
        StepRecord(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            observation={"prices": {"BTC-USD": 100.0}},
            signals=[
                {
                    "symbol": "BTC-USD",
                    "score": 0.4,
                    "confidence": 0.8,
                    "rationale": "raw model rationale with researcher@example.com",
                    "metadata": {
                        "provider": "poe",
                        "model": "gpt-5.5",
                        "prompt": "private prompt with account_id=ABC123456",
                        "response_text": '{"signals":[]}',
                    },
                }
            ],
            decisions=[],
            approved_decisions=[],
            orders=[],
            fills=[],
            portfolio={"cash": 100_000.0, "positions": {}, "equity": 100_000.0},
        )
    )

    payload = trajectory.to_dict()
    rendered = json.dumps(payload, default=str)

    assert "raw model rationale" not in rendered
    assert "private prompt" not in rendered
    assert "response_text" not in rendered
    assert "researcher@example.com" not in rendered
    assert payload["steps"][0]["signals"][0]["metadata"]["prompt_hash"].startswith("sha256:")
    assert payload["steps"][0]["signals"][0]["metadata"]["response_hash"].startswith("sha256:")
    assert scan_public_artifact_payload(payload) == []


def test_write_json_defaults_to_public_artifact_redaction(tmp_path):
    output = tmp_path / "public" / "trajectory.json"

    write_json(output, {"prompt": "raw prompt", "response_text": "raw response", "rationale": "raw rationale"})

    payload = read_json(output)
    text = output.read_text(encoding="utf-8")

    assert payload["prompt_hash"].startswith("sha256:")
    assert payload["response_hash"].startswith("sha256:")
    assert payload["rationale"].startswith("[redacted rationale sha256:")
    assert "raw prompt" not in text
    assert "raw response" not in text
    assert scan_public_artifact_paths([output]) == []


def test_public_artifact_scan_skips_private_llm_cache_dirs(tmp_path):
    cache = tmp_path / "outputs" / "llm_cache" / "provider.jsonl"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"prompt": "raw prompt", "response_text": "raw response"}) + "\n", encoding="utf-8")
    answer = tmp_path / "outputs" / "poe_skill_task_answers" / "run" / "answer.md"
    answer.parent.mkdir(parents=True)
    answer.write_text("Raw model answer may mention API key boundaries.", encoding="utf-8")

    assert scan_public_artifact_paths([tmp_path / "outputs"]) == []


def test_public_artifact_scan_reports_missing_paths(tmp_path):
    missing = tmp_path / "missing-public-artifacts"

    findings = scan_public_artifact_paths([missing])

    assert findings == [f"{missing}: path does not exist"]


def test_public_artifact_scan_flags_local_filesystem_paths(tmp_path):
    public_report = tmp_path / "report.md"
    public_report.write_text(
        "Manifest: C:\\Users\\Example\\TradeArena\\outputs\\reproduction\\v0_2\\manifest.json\n",
        encoding="utf-8",
    )
    portable_report = tmp_path / "portable.md"
    portable_report.write_text("Manifest: outputs/reproduction/v0_2/manifest.json\n", encoding="utf-8")

    findings = scan_public_artifact_paths([tmp_path])

    assert any("local filesystem path pattern" in finding for finding in findings)
    assert not any("portable.md" in finding for finding in findings)


def test_public_artifact_scan_cli_fails_on_missing_paths(tmp_path):
    missing = tmp_path / "missing-public-artifacts"

    result = subprocess.run(
        [sys.executable, "scripts/scan_public_artifacts.py", str(missing)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Public artifact privacy scan failed" in result.stdout
    assert "path does not exist" in result.stdout
