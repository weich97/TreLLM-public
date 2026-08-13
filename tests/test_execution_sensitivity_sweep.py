from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_sweep_module():
    path = ROOT / "scripts" / "run_execution_sensitivity_sweep.py"
    spec = importlib.util.spec_from_file_location("run_execution_sensitivity_sweep", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_default_agents_are_known_factory_strategies():
    module = _load_sweep_module()
    from tradearena.factory import build_default_system

    for agent in module.DEFAULT_AGENTS:
        system = build_default_system(
            name=f"sweep_smoke_{agent}",
            symbols=("SYN",),
            periods=10,
            seed=3,
            strategy_name=agent,
            analyst_names=("momentum",),
        )
        assert system is not None


def test_sweep_writes_runs_aggregates_and_stability(tmp_path: Path):
    module = _load_sweep_module()

    exit_code = module.main(
        [
            "--agents",
            "buy-and-hold,random",
            "--seeds",
            "3,5",
            "--periods",
            "20",
            "--scenarios",
            "calm",
            "--levels",
            "E0_ideal,E1_default_stress,E2_harsh_corner",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    with (tmp_path / "execution_sensitivity_runs.csv").open(encoding="utf-8") as handle:
        runs = list(csv.DictReader(handle))
    # 1 scenario x 3 levels x 2 agents x 2 seeds
    assert len(runs) == 12
    with (tmp_path / "execution_sensitivity_rank_stability.csv").open(encoding="utf-8") as handle:
        stability = list(csv.DictReader(handle))
    # 3 levels -> 3 unordered level pairs
    assert len(stability) == 3
    assert all(row["kendall_tau"] != "" for row in stability)
    assert (tmp_path / "execution_sensitivity.md").read_text(encoding="utf-8").startswith(
        "# Execution-Assumption Sensitivity"
    )
