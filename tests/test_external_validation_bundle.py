from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_external_validation_bundle_summarizes_manifest(tmp_path: Path):
    manifest = {
        "schema": "tradearena_external_reproduction_pack_v1",
        "commit_or_tag": "abc123",
        "git_status_short": "",
        "python": {
            "version": "3.11.0",
            "implementation": "CPython",
            "executable": r"C:\Users\Example\AppData\Local\Programs\Python\Python311\python.exe",
            "platform": "Linux-test",
        },
        "commands": [{"id": "release_readiness", "argv": ["python"], "returncode": 0}],
        "artifacts": [{"path": "outputs/examples/audit_report.html", "exists": True, "bytes": 10, "sha256": "sha256:abc"}],
        "trajectory_hash": {"reproducibility_hash": "sha256:def", "file_sha256": "sha256:file"},
        "live_api_used": False,
        "market_data_used": "synthetic",
        "private_fills_used": False,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "bundle.json"
    markdown = tmp_path / "bundle.md"

    subprocess.run(
        [
            sys.executable,
            "scripts/build_external_validation_bundle.py",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output),
            "--markdown-output",
            str(markdown),
            "--environment-label",
            "unit-test",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    bundle = json.loads(output.read_text(encoding="utf-8"))

    assert bundle["issue_ready"] is True
    assert bundle["environment_label"] == "unit-test"
    assert bundle["manifest_path"] == str(manifest_path.as_posix())
    assert bundle["python"]["executable"] == "python.exe"
    assert "C:\\Users\\Example" not in output.read_text(encoding="utf-8")
    assert bundle["trajectory_reproducibility_hash"] == "sha256:def"
    assert "Suggested Issue Text" in markdown.read_text(encoding="utf-8")


def test_external_validation_bundle_reports_malformed_manifest_json(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"schema": ', encoding="utf-8")
    output = tmp_path / "bundle.json"
    markdown = tmp_path / "bundle.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_external_validation_bundle.py",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output),
            "--markdown-output",
            str(markdown),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid reproduction manifest" in result.stdout
    assert "reproduction manifest must contain valid JSON" in result.stdout
    assert "Traceback" not in result.stderr
    assert not output.exists()
    assert not markdown.exists()


def test_tracked_external_validation_bundle_is_portable():
    bundle_text = (ROOT / "docs/results/external_validation_bundle.json").read_text(encoding="utf-8")
    markdown_text = (ROOT / "docs/results/external_validation_bundle.md").read_text(encoding="utf-8")
    bundle = json.loads(bundle_text)

    assert bundle["manifest_path"] == "outputs/reproduction/v0_2/manifest.json"
    assert bundle["python"]["executable"] == "python.exe"
    assert not re.search(r"[A-Za-z]:[\\/]",bundle_text)
    assert "C:\\Users\\" not in bundle_text
    assert not re.search(r"[A-Za-z]:[\\/]",markdown_text)
    assert "C:\\Users\\" not in markdown_text
