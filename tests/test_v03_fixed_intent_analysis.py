from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_v03_fixed_intent_replay.py"
SPEC = importlib.util.spec_from_file_location("analyze_v03_fixed_intent_replay_test", SCRIPT)
assert SPEC and SPEC.loader
ANALYZE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYZE
SPEC.loader.exec_module(ANALYZE)


def _cell(value: float) -> dict[str, object]:
    return {"metric_values": {"total_return": value}}


def test_factorial_formulas_reconstruct_the_observed_diagonal() -> None:
    values = ANALYZE.factorial_values(
        {
            ("E0", "E0"): _cell(1.0),
            ("E0", "E1"): _cell(2.0),
            ("E1", "E0"): _cell(4.0),
            ("E1", "E1"): _cell(8.0),
        },
        "total_return",
    )

    assert values == {
        "execution_within_I0": 1.0,
        "execution_within_I1": 4.0,
        "response_origin_within_X0": 3.0,
        "response_origin_within_X1": 6.0,
        "interaction": 3.0,
        "execution_shapley": 2.5,
        "response_origin_shapley": 4.5,
        "observed_diagonal": 7.0,
    }


def test_shared_seed_bootstrap_and_small_cluster_sensitivity_are_deterministic() -> None:
    seeds = list(range(10))
    cluster_values = {seed: float(seed) for seed in seeds}
    first = ANALYZE.bootstrap_weights(seeds, draws=100, rng_seed=20260719)
    second = ANALYZE.bootstrap_weights(seeds, draws=100, rng_seed=20260719)

    assert first == second
    assert all(sum(draw) == 10 for draw in first)
    estimate, low, high = ANALYZE.cluster_interval(cluster_values, seeds, first)
    sensitivity = ANALYZE.cluster_sensitivity(cluster_values, seeds)
    assert estimate == 4.5
    assert low < estimate < high
    assert sensitivity["t9_ci_low"] < estimate < sensitivity["t9_ci_high"]
    assert sensitivity["leave_one_seed_low"] == 4.0
    assert sensitivity["leave_one_seed_high"] == 5.0
    assert ANALYZE.percentile([0.0, 10.0], 0.25) == 2.5
    frozen_seeds = [7, 11, 17, 23, 31, 37, 41, 43, 47, 53]
    frozen_weights = ANALYZE.bootstrap_weights(
        frozen_seeds, ANALYZE.BOOTSTRAP_DRAWS, ANALYZE.BOOTSTRAP_SEED
    )
    assert frozen_weights[0] == (0, 0, 2, 0, 1, 2, 2, 1, 1, 1)
    assert ANALYZE.sha256_text(ANALYZE.canonical_json(frozen_weights)) == (
        "sha256:54a03062f583c71ea4ef571385922506d113847926f6f34a66c3298fc800cc06"
    )


def test_kendall_tau_b_handles_agreement_reversal_and_ties() -> None:
    increasing = {"a": 1.0, "b": 2.0, "c": 3.0}
    decreasing = {"a": 3.0, "b": 2.0, "c": 1.0}
    tied = {"a": 1.0, "b": 1.0, "c": 3.0}

    assert ANALYZE.kendall_tau_b(increasing, increasing) == 1.0
    assert ANALYZE.kendall_tau_b(increasing, decreasing) == -1.0
    assert 0.0 < ANALYZE.kendall_tau_b(increasing, tied) < 1.0


def test_production_analysis_matches_the_frozen_shared_seed_result(tmp_path: Path) -> None:
    input_dir = ROOT / "docs" / "results" / "v0_3_fixed_intent_replay"
    plan = input_dir / "analysis_plan.json"
    manifest = ANALYZE.analyze(input_dir, plan, tmp_path)

    assert manifest["failed_count"] == 0
    assert manifest["observed"] == {
        "base_pairs": 450,
        "replay_rows": 1800,
        "factorial_rows": 72,
        "scoped_factorial_rows": 240,
        "ranking_rows": 6,
        "divergence_summary_rows": 9,
    }
    with (tmp_path / "factorial_estimands.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    execution = next(
        row
        for row in rows
        if row["metric"] == "total_return" and row["estimand"] == "execution_shapley"
    )
    assert math.isclose(float(execution["estimate"]), -0.017000764197563335, abs_tol=1e-15)
    assert math.isclose(float(execution["ci95_low"]), -0.02299372791417583, abs_tol=1e-15)
    assert math.isclose(float(execution["ci95_high"]), -0.011650134536446864, abs_tol=1e-15)

    with (tmp_path / "ranking_stability.csv").open(encoding="utf-8", newline="") as handle:
        ranking_rows = list(csv.DictReader(handle))
    jump_e1 = next(
        row
        for row in ranking_rows
        if row["scenario_id"] == "synthetic_jump_tail_c0_v0_3"
        and row["response_origin"] == "E1"
    )
    assert float(jump_e1["kendall_tau_b"]) == 0.8
    assert float(jump_e1["ci95_low"]) == 0.4
    assert float(jump_e1["ci95_high"]) == 1.0
    assert float(jump_e1["exact_order_probability"]) == 0.3265
    assert float(jump_e1["same_winner_probability"]) == 0.5325

    persisted = json.loads((tmp_path / "analysis_manifest.json").read_text(encoding="utf-8"))
    assert persisted == manifest
    assert manifest["bootstrap"]["rng_algorithm"] == "CPython random.Random (MT19937)"
    assert manifest["bootstrap"]["percentile_method"] == (
        "Hyndman-Fan type 7 (linear interpolation)"
    )
    assert manifest["bootstrap"]["weight_matrix_sha256"] == (
        "sha256:54a03062f583c71ea4ef571385922506d113847926f6f34a66c3298fc800cc06"
    )
    for name, expected in manifest["output_sha256"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == expected
