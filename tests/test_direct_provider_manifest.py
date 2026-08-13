from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_direct_provider_pilot_writes_valid_hash_only_manifest(tmp_path: Path):
    prompt = tmp_path / "prompt.json"
    response = tmp_path / "response.json"
    output = tmp_path / "manifest.json"
    prompt.write_text('{"task":"allocate","symbols":["SYN"]}', encoding="utf-8")
    response.write_text('{"weights":[{"symbol":"SYN","target_weight":0.1}]}', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_direct_provider_manifest_pilot.py",
            "--provider",
            "openai",
            "--model-id",
            "gpt-5.5",
            "--model-version-or-release",
            "2026-05-17",
            "--api-endpoint-family",
            "responses",
            "--prompt-file",
            str(prompt),
            "--response-file",
            str(response),
            "--scenario-id",
            "synthetic_calm_trend_c0_v0_3",
            "--contamination-tier",
            "C0",
            "--execution-level",
            "E1",
            "--seed",
            "7",
            "--sample-index",
            "0",
            "--trajectory-manifest-sha256",
            "sha256:5555555555555555555555555555555555555555555555555555555555555555",
            "--benchmark-submission-sha256",
            "sha256:6666666666666666666666666666666666666666666666666666666666666666",
            "--call-started-at",
            "2026-05-17T12:00:00Z",
            "--call-completed-at",
            "2026-05-17T12:00:04Z",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Valid direct provider manifest" in result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["provider_route"] == "direct-api"
    assert payload["prompt"]["prompt_sha256"].startswith("sha256:")
    assert payload["response"]["response_sha256"].startswith("sha256:")
    assert payload["redaction"]["raw_prompt_public"] is False
    assert payload["redaction"]["raw_response_public"] is False
    assert "allocate" not in serialized
    assert "target_weight" not in serialized


def test_direct_provider_pilot_requires_explicit_fixture_response(tmp_path: Path):
    prompt = tmp_path / "prompt.json"
    output = tmp_path / "manifest.json"
    prompt.write_text('{"task":"allocate"}', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_direct_provider_manifest_pilot.py",
            "--provider",
            "openai",
            "--model-id",
            "gpt-5.5",
            "--model-version-or-release",
            "2026-05-17",
            "--api-endpoint-family",
            "responses",
            "--prompt-file",
            str(prompt),
            "--scenario-id",
            "synthetic_calm_trend_c0_v0_3",
            "--contamination-tier",
            "C0",
            "--execution-level",
            "E1",
            "--seed",
            "7",
            "--sample-index",
            "0",
            "--trajectory-manifest-sha256",
            "sha256:5555555555555555555555555555555555555555555555555555555555555555",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--response-file is required for the current offline pilot runner" in result.stderr
    assert not output.exists()
