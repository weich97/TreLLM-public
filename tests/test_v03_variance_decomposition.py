from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_variance_decomposition_writes_fixture_artifact(tmp_path: Path):
    output_dir = tmp_path / "variance_decomposition"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_v03_variance_decomposition.py",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Variance rows: 4" in result.stdout

    summary = json.loads((output_dir / "variance_decomposition_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "variance_decomposition_rows.csv").open(encoding="utf-8")))
    markdown = (output_dir / "variance_decomposition.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_variance_decomposition_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["artifact_id"] == "variance_decomposition"
    assert summary["source_row_count"] == 4
    assert summary["variance_row_count"] == 4
    assert summary["testable_metric_count"] == 4
    assert summary["minimum_seed_group_count"] == 2
    assert summary["minimum_total_sample_count"] == 4
    assert summary["metrics"] == [
        "total_return",
        "max_drawdown",
        "execution_fill_rate",
        "risk_clipped_decisions",
    ]
    assert "does not support model-performance" in summary["claim_boundary"]

    assert len(rows) == 4
    assert {row["metric"] for row in rows} == set(summary["metrics"])
    assert {row["evidence_stage"] for row in rows} == {"protocol-fixture"}
    assert {row["seed_group_count"] for row in rows} == {"2"}
    assert {row["total_sample_count"] for row in rows} == {"4"}
    assert all(row["between_seed_variance"] for row in rows)
    assert all(row["within_seed_variance"] for row in rows)
    assert all(row["within_seed_share"] for row in rows)

    total_return = next(row for row in rows if row["metric"] == "total_return")
    assert 0.0 < float(total_return["within_seed_share"]) < 1.0
    assert markdown.startswith("# TreLLM v0.3 Variance Decomposition")
