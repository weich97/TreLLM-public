from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_external_reproduction_gate_reports_zero_when_no_independent_reports(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    output_dir = tmp_path / "gate"
    reports_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_external_reproduction_gate.py",
            "--output-dir",
            str(output_dir),
            "--report-dirs",
            str(reports_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Reports scanned: 0" in result.stdout
    assert "Accepted reports: 0" in result.stdout
    assert "External reproduction ready: False" in result.stdout

    summary = json.loads((output_dir / "external_reproduction_gate_summary.json").read_text(encoding="utf-8"))
    coverage = list(csv.DictReader((output_dir / "external_reproduction_environment_coverage.csv").open(encoding="utf-8")))
    reports = list(csv.DictReader((output_dir / "external_reproduction_gate_reports.csv").open(encoding="utf-8")))
    markdown = (output_dir / "external_reproduction_gate_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_external_reproduction_gate_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["accepted_report_count"] == 0
    assert summary["required_independent_reports"] == 3
    assert summary["external_reproduction_ready"] is False
    assert summary["blocking_reasons"] == [
        "insufficient_independent_report_count",
        "missing_required_environment_class",
    ]
    assert reports == []
    assert {row["coverage_status"] for row in coverage} == {"missing"}
    assert "External reproduction ready: `False`" in markdown


def test_v03_external_reproduction_gate_accepts_one_valid_report_but_keeps_gap_open(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    output_dir = tmp_path / "gate"
    reports_dir.mkdir()
    (reports_dir / "linux_report.json").write_text(
        json.dumps(_valid_report("linux"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_external_reproduction_gate.py",
            "--output-dir",
            str(output_dir),
            "--report-dirs",
            str(reports_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads((output_dir / "external_reproduction_gate_summary.json").read_text(encoding="utf-8"))
    coverage = list(csv.DictReader((output_dir / "external_reproduction_environment_coverage.csv").open(encoding="utf-8")))
    reports = list(csv.DictReader((output_dir / "external_reproduction_gate_reports.csv").open(encoding="utf-8")))

    assert summary["report_count"] == 1
    assert summary["accepted_report_count"] == 1
    assert summary["covered_environment_count"] == 1
    assert summary["external_reproduction_ready"] is False
    assert summary["blocking_reasons"] == [
        "insufficient_independent_report_count",
        "missing_required_environment_class",
    ]
    assert reports[0]["accepted_for_v0_3"] == "true"
    assert reports[0]["validation_status"] == "valid"
    assert reports[0]["environment_class"] == "linux"
    assert reports[0]["independent_reviewer"] == "true"
    linux = next(row for row in coverage if row["environment_class"] == "linux")
    assert linux["coverage_status"] == "covered"
    assert linux["accepted_report_count"] == "1"
    assert {row["coverage_status"] for row in coverage if row["environment_class"] != "linux"} == {"missing"}


def _valid_report(environment_class: str) -> dict[str, object]:
    return {
        "schema": "tradearena_external_reproduction_pack_v1",
        "protocol_id": "trellm-v0.3-protocol",
        "environment_class": environment_class,
        "report_author_type": "independent",
        "independent_reviewer": True,
        "created_at": "2026-06-11T00:00:00Z",
        "repository": "https://github.com/weich97/TreLLM-public",
        "commit_or_tag": "abc1234",
        "python": {
            "version": "3.11.9",
            "implementation": "CPython",
            "executable": "/usr/bin/python",
            "platform": "Linux-6.0",
        },
        "commands": [
            {
                "id": "v03_evidence_index",
                "description": "Build v0.3 evidence index",
                "argv": ["python", "scripts/build_v03_evidence_index.py"],
                "returncode": 0,
            }
        ],
        "artifacts": [
            {
                "path": "docs/results/v0_3_evidence_index/v0_3_evidence_index.json",
                "exists": True,
                "bytes": 1200,
                "sha256": "sha256:" + "a" * 64,
            }
        ],
        "trajectory_hash": {"reproducibility_hash": "sha256:" + "b" * 64},
        "live_api_used": False,
        "market_data_used": "public deterministic synthetic data",
        "private_fills_used": False,
    }
