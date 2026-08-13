from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

FIELDS = ["scenario", "level", "agent", "seed", "sample", "total_return", "sharpe", "max_drawdown", "execution_fill_rate", "total_slippage_cost"]


def _load_module():
    path = ROOT / "scripts" / "analyze_execution_sensitivity_llm.py"
    spec = importlib.util.spec_from_file_location("analyze_execution_sensitivity_llm", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_runs(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _row(scenario, level, agent, seed, total_return, sharpe=1.0, sample=0):
    return {
        "scenario": scenario,
        "level": level,
        "agent": agent,
        "seed": seed,
        "sample": sample,
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": -0.05,
        "execution_fill_rate": 0.9,
        "total_slippage_cost": 1.0,
    }


def _fixture_dirs(tmp_path: Path) -> list[Path]:
    # Baseline loses 0.01 to friction on every seed; the LLM agent loses 0.05.
    seeds = (1, 2, 3, 4, 5, 6)
    shared = []
    for seed in seeds:
        shared.append(_row("calm", "E0_ideal", "buy-and-hold", seed, 0.10))
        shared.append(_row("calm", "E1_default_stress", "buy-and-hold", seed, 0.09))
    dir_a = tmp_path / "model_a"
    rows_a = list(shared)
    for seed in seeds:
        rows_a.append(_row("calm", "E0_ideal", "poe:model-a", seed, 0.12, sharpe=2.0))
        rows_a.append(_row("calm", "E1_default_stress", "poe:model-a", seed, 0.07, sharpe=0.5))
    _write_runs(dir_a / "execution_sensitivity_runs.csv", rows_a)

    dir_b = tmp_path / "model_b"
    rows_b = list(shared)  # duplicated baselines must deduplicate on merge
    for seed in seeds:
        rows_b.append(_row("calm", "E0_ideal", "poe:model-b", seed, 0.11, sharpe=1.5))
        rows_b.append(_row("calm", "E1_default_stress", "poe:model-b", seed, 0.10, sharpe=1.4))
    _write_runs(dir_b / "execution_sensitivity_runs.csv", rows_b)
    return [dir_a, dir_b]


def test_merge_deduplicates_shared_baseline_rows(tmp_path: Path):
    module = _load_module()
    dirs = _fixture_dirs(tmp_path)

    rows = module.load_merged_runs(dirs)

    baseline_rows = [r for r in rows if r["agent"] == "buy-and-hold"]
    assert len(baseline_rows) == 12  # 6 seeds x 2 levels, not doubled
    assert len(rows) == 12 + 24  # baselines + two LLM agents


def test_fragility_did_signs_and_significance(tmp_path: Path):
    module = _load_module()
    dirs = _fixture_dirs(tmp_path)
    rows = module.load_merged_runs(dirs)

    did = module.fragility_did_rows(rows, baseline_agent="buy-and-hold", stress_levels=("E1_default_stress",))

    by_agent = {row["agent"]: row for row in did}
    # model-a loses 0.05 vs baseline's 0.01: DiD = +0.04 (more fragile).
    assert round(float(by_agent["poe:model-a"]["mean_did"]), 6) == 0.04
    # model-b loses 0.01, same as baseline: DiD = 0.
    assert round(float(by_agent["poe:model-b"]["mean_did"]), 6) == 0.0
    assert by_agent["poe:model-a"]["agent_type"] == "llm"
    # Six identical-sign deltas: exact permutation p = 2/64 = 0.03125; BH over
    # the two-test family (model-b's null contributes p=1) doubles it.
    assert float(by_agent["poe:model-a"]["permutation_p_value"]) == 0.03125
    assert float(by_agent["poe:model-a"]["q_value"]) == 0.0625


def test_sampling_variance_decomposition_with_repeated_samples(tmp_path: Path):
    module = _load_module()
    rows = []
    # Two seeds whose means differ (between-seed variance) and three provider
    # samples per seed with within-seed spread.
    for seed, base in ((1, 0.10), (2, 0.20)):
        for sample, offset in enumerate((-0.01, 0.0, 0.01)):
            rows.append(_row("calm", "E1_default_stress", "poe:model-a", seed, base + offset, sample=sample))
    # Deterministic agent rows must never appear in the decomposition.
    rows.append(_row("calm", "E1_default_stress", "buy-and-hold", 1, 0.05))
    _write_runs(tmp_path / "m" / "execution_sensitivity_runs.csv", rows)

    merged = module.load_merged_runs([tmp_path / "m"])
    decomposition = module.sampling_variance_rows(merged)

    assert len(decomposition) == 1
    record = decomposition[0]
    assert record["agent"] == "poe:model-a"
    assert record["seed_count"] == 2
    assert record["total_runs"] == 6
    # Between-seed variance (means 0.10 vs 0.20 -> 0.005) dominates the
    # within-seed sampling variance (1e-4): share is small.
    assert 0.0 < float(record["within_seed_share"]) < 0.05


def test_did_averages_repeated_samples_within_seed(tmp_path: Path):
    module = _load_module()
    rows = []
    for seed in (1, 2, 3, 4, 5, 6):
        rows.append(_row("calm", "E0_ideal", "buy-and-hold", seed, 0.10))
        rows.append(_row("calm", "E1_default_stress", "buy-and-hold", seed, 0.09))
        # Samples scatter +/-0.02 around a mean E0 return of 0.12.
        for sample, value in enumerate((0.10, 0.12, 0.14)):
            rows.append(_row("calm", "E0_ideal", "poe:model-a", seed, value, sample=sample))
        rows.append(_row("calm", "E1_default_stress", "poe:model-a", seed, 0.07))
    _write_runs(tmp_path / "m" / "execution_sensitivity_runs.csv", rows)

    merged = module.load_merged_runs([tmp_path / "m"])
    did = module.fragility_did_rows(merged, baseline_agent="buy-and-hold", stress_levels=("E1_default_stress",))

    # Sample-averaged E0 = 0.12, so DiD = (0.12-0.07) - (0.10-0.09) = 0.04.
    assert round(float(did[0]["mean_did"]), 6) == 0.04


def test_main_writes_all_tables(tmp_path: Path):
    module = _load_module()
    dirs = _fixture_dirs(tmp_path)
    output_dir = tmp_path / "analysis"

    exit_code = module.main(
        [
            "--input-dirs",
            ",".join(str(d) for d in dirs),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    for name in ("merged_runs.csv", "merged_aggregate.csv", "rank_stability.csv", "fragility_did.csv", "execution_sensitivity_llm.md"):
        assert (output_dir / name).exists(), name
    content = (output_dir / "execution_sensitivity_llm.md").read_text(encoding="utf-8")
    assert "Friction Fragility" in content
    aggregate = list(csv.DictReader((output_dir / "merged_aggregate.csv").open(encoding="utf-8")))
    # Rankings exist per (scenario, level) and include both agent types.
    assert {row["agent_type"] for row in aggregate} == {"llm", "classical"}
    assert all(row["rank"] for row in aggregate)


def test_released_snapshot_loader_preserves_samples_but_rejects_duplicate_keys(tmp_path: Path):
    module = _load_module()
    path = tmp_path / "merged_runs.csv"
    rows = [
        _row("calm", "E0_ideal", "poe:model-a", 1, 0.10, sample=0),
        _row("calm", "E0_ideal", "poe:model-a", 1, 0.12, sample=1),
    ]
    _write_runs(path, rows)

    assert len(module.load_existing_merged_runs(path)) == 2

    rows.append(dict(rows[0]))
    _write_runs(path, rows)
    with pytest.raises(SystemExit, match="Duplicate merged-run key"):
        module.load_existing_merged_runs(path)


def test_released_snapshot_loader_rejects_schema_drift_and_nonfinite_metrics(tmp_path: Path):
    module = _load_module()
    path = tmp_path / "merged_runs.csv"
    row = _row("calm", "E0_ideal", "poe:model-a", 1, 0.10)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS + ["raw_response"])
        writer.writeheader()
        writer.writerow({**row, "raw_response": "must not be released"})
    with pytest.raises(SystemExit, match="Unexpected merged-runs schema"):
        module.load_existing_merged_runs(path)

    row["sharpe"] = "nan"
    _write_runs(path, [row])
    with pytest.raises(SystemExit, match="Non-finite sharpe"):
        module.load_existing_merged_runs(path)


def test_released_compression_table_separates_direct_and_mixed_interface_rows():
    path = ROOT / "docs/results/execution_sensitivity_horizon_universe/direct_llm_compression.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    direct_glm = [row for row in rows if row["board"] == "glm-direct+cls"]
    mixed = [row for row in rows if row["provenance"] == "mixed-glm-route-swap-diagnostic"]

    assert direct_glm
    assert "2" not in {row["n_assets"] for row in direct_glm}
    assert mixed
    assert all("mixed-interface" in row["board"] for row in mixed)
