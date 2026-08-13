from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_power_module():
    path = ROOT / "scripts" / "run_power_analysis.py"
    spec = importlib.util.spec_from_file_location("run_power_analysis", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_five_pairs_cannot_reject_at_alpha_005():
    # The exact two-sided sign-flip permutation test with n=5 has a minimum
    # p-value of 2/32 = 0.0625, so power at alpha=0.05 is structurally zero.
    # This is the quantitative basis for requiring at least 6 repeats.
    module = _load_power_module()

    power = module.estimate_power_synthetic(2.0, 5, alpha=0.05, draws=50, seed=1)

    assert power == 0.0


def test_power_increases_with_repeats_for_large_effect():
    module = _load_power_module()

    low = module.estimate_power_synthetic(1.0, 6, alpha=0.05, draws=60, seed=1)
    high = module.estimate_power_synthetic(1.0, 20, alpha=0.05, draws=60, seed=1)

    assert high > low
    assert high > 0.5


def test_load_paired_deltas_matches_by_seed(tmp_path: Path):
    module = _load_power_module()
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text(
        "case,group,seed,total_return\n"
        "agent_seed1,main,1,0.05\n"
        "agent_seed2,main,2,0.07\n"
        "hold_seed1,main,1,0.02\n"
        "hold_seed2,main,2,0.03\n"
        "agent_seed9,main,9,0.10\n",
        encoding="utf-8",
    )

    deltas = module.load_paired_deltas(
        csv_path, candidate="agent", baseline="hold", metric="total_return"
    )

    assert len(deltas) == 2
    assert round(deltas[0], 6) == 0.03
    assert round(deltas[1], 6) == 0.04


def test_main_writes_synthetic_curves(tmp_path: Path):
    module = _load_power_module()

    exit_code = module.main(
        [
            "--draws",
            "20",
            "--repeat-levels",
            "6,10",
            "--effect-sizes",
            "1.0",
            "--output",
            str(tmp_path / "power.csv"),
            "--markdown-output",
            str(tmp_path / "power.md"),
        ]
    )

    assert exit_code == 0
    content = (tmp_path / "power.csv").read_text(encoding="utf-8")
    assert "repeat_count" in content
    assert (tmp_path / "power.md").read_text(encoding="utf-8").startswith("# Paired-Test Power Curves")
