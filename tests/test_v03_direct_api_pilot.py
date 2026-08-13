from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_direct_api_pilot_generates_seed_sample_evidence(tmp_path: Path):
    output_dir = tmp_path / "pilot"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_direct_api_pilot.py",
            "--output-dir",
            str(output_dir),
            "--seeds",
            "7,11",
            "--samples",
            "0,1",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wrote" in result.stdout
    summary = json.loads((output_dir / "direct_api_pilot_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "direct_api_pilot_rows.csv").open(encoding="utf-8")))
    markdown = (output_dir / "direct_api_pilot_summary.md").read_text(encoding="utf-8")
    provider_manifests = sorted((output_dir / "provider_manifests").glob("*.json"))
    submissions = sorted((output_dir / "submissions").glob("*.json"))

    assert summary["schema"] == "trellm_v0_3_direct_api_pilot_v0.1"
    assert summary["row_count"] == 4
    assert len(rows) == 4
    assert len(provider_manifests) == 4
    assert len(submissions) == 4
    assert {row["seed"] for row in rows} == {"7", "11"}
    assert {row["sample_index"] for row in rows} == {"0", "1"}
    assert {row["contamination_tier"] for row in rows} == {"C0"}
    assert {row["execution_level"] for row in rows} == {"E1"}
    assert all("direct-api" in row["evidence_tags"] for row in rows)
    assert all("protocol-fixture" in row["evidence_tags"] for row in rows)
    assert all("live-provider" not in row["evidence_tags"] for row in rows)
    assert "Direct API Pilot" in markdown
    assert "not a trading-profit claim" in markdown

    for manifest_path in provider_manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["provider"] == "fixture-direct-api"
        assert manifest["model_id"] == "fixture-llm-policy-v0"
        assert manifest["cache"]["cache_status"] == "cache_replay"
        assert "protocol fixture" in manifest["evidence"]["claim_scope"].lower()
        subprocess.run(
            [sys.executable, "scripts/validate_direct_provider_manifest.py", str(manifest_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    for submission_path in submissions:
        subprocess.run(
            [sys.executable, "scripts/validate_benchmark_submission.py", str(submission_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        submission = json.loads(submission_path.read_text(encoding="utf-8"))
        assert submission["agent"]["provider"] == "fixture-direct-api"
        assert submission["agent"]["model_family"] == "fixture-llm-policy-v0"
        assert submission["evidence"]["claim_class"] == "engineering"
        assert submission["evidence"]["evidence_tier"] == "manifest-only"

    registry = output_dir / "registry.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_benchmark_registry.py",
            str(output_dir / "submissions"),
            "--output",
            str(registry),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "`direct-api`" in registry.read_text(encoding="utf-8")
    assert registry.with_suffix(".csv").exists()
    assert registry.with_suffix(".html").exists()
