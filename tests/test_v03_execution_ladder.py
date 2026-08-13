from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v03_execution_ladder_generates_protocol_artifacts(tmp_path: Path):
    output_dir = tmp_path / "execution_ladder"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v03_execution_ladder.py",
            "--output-dir",
            str(output_dir),
            "--agents",
            "signal-weighted,random",
            "--seeds",
            "7",
            "--periods",
            "8",
            "--top-k",
            "2",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Rows: 8" in result.stdout
    summary = json.loads((output_dir / "execution_ladder_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "execution_ladder_rows.csv").open(encoding="utf-8")))
    aggregate_rows = list(csv.DictReader((output_dir / "execution_ladder_aggregate.csv").open(encoding="utf-8")))
    stability_rows = list(csv.DictReader((output_dir / "execution_ladder_ranking_stability.csv").open(encoding="utf-8")))
    markdown = (output_dir / "execution_ladder_summary.md").read_text(encoding="utf-8")

    assert summary["schema"] == "trellm_v0_3_execution_ladder_v0.1"
    assert summary["protocol_id"] == "trellm-v0.3-protocol"
    assert summary["contamination_tier"] == "C0"
    assert summary["execution_levels"] == ["E0", "E1", "E2", "E3"]
    assert summary["row_count"] == 8
    assert summary["ranking_stability_row_count"] == 3
    assert "not a trading-profit claim" in summary["claim_boundary"]
    assert "external quote/fill provenance" in summary["e3_boundary"]
    assert "intent_execution_gap_l1" in summary["mechanism_metrics"]

    assert {row["execution_level"] for row in rows} == {"E0", "E1", "E2", "E3"}
    assert {row["contamination_tier"] for row in rows} == {"C0"}
    assert {row["evidence_tier"] for row in rows} == {"protocol-fixture"}
    assert all(row["protocol_id"] == "trellm-v0.3-protocol" for row in rows)
    assert all(row["trajectory_reproducibility_coverage"] == "1.0" for row in rows)
    assert all("trading-profit" not in row["claim_scope"].lower() for row in rows)
    assert all("intent_execution_gap_l1" in row for row in rows)

    assert len(aggregate_rows) == 8
    assert all(row["rank"] for row in aggregate_rows)
    assert {row["baseline_level"] for row in stability_rows} == {"E0"}
    assert {row["comparison_level"] for row in stability_rows} == {"E1", "E2", "E3"}
    assert all(row["rank_metric"] == "sharpe_mean" for row in stability_rows)
    assert all(row["top_k"] == "2" for row in stability_rows)
    assert all(row["top_k_jaccard"] for row in stability_rows)
    assert all(row["mean_intent_execution_gap_delta_vs_e0"] for row in stability_rows)

    assert "# TreLLM v0.3 Execution Ladder" in markdown
    assert "Ranking Stability vs E0" in markdown
    assert "Intent-execution gap" in markdown
    assert "not a trading-profit claim" in markdown
