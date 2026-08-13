"""Seed-bootstrap CIs for the board-level tau curves of the execution-sensitivity study.

The headline tau (0.21) and the scaffold-board taus carry seed-bootstrap 95%
intervals; the horizon and universe curves were reported as bare points. This
script computes the same cluster bootstrap (resample seeds with replacement,
recompute mean-Sharpe boards, 10,000 draws, fixed RNG) for every cleanly
reconstructible curve point:

- direct 9-agent horizon board (ds_h* + glm_h* merged), E0 vs E1, high_vol;
- routed 9-agent horizon board (routed_h*), E0 vs E1, high_vol;
- 12-agent universe boards at N=3 and N=5, E0 vs E1, high_vol.

Writes docs/results/execution_sensitivity_scaffold/tau_curve_cis.csv (released
with the artifact; the N=10 assembly is coverage-restricted across several
result dirs and keeps its published point estimates).
"""
from __future__ import annotations

import csv
from pathlib import Path

from build_scaffold_board import load_runs, tau_with_ci

ROOT = Path(__file__).resolve().parents[1]
B1 = ROOT / "docs/results/execution_sensitivity_b1_horizon"
OUT = ROOT / "docs/results/execution_sensitivity_scaffold/tau_curve_cis.csv"

BOARDS: dict[str, tuple[Path, ...]] = {
    "direct_h12": (B1 / "ds_h12", B1 / "glm_h12"),
    "direct_h30": (B1 / "ds_h30", B1 / "glm_h30"),
    "direct_h60": (B1 / "ds_h60", B1 / "glm_h60"),
    "direct_h120": (B1 / "ds_h120", B1 / "glm_h120"),
    "routed_h30": (B1 / "routed_h30",),
    "routed_h60": (B1 / "routed_h60",),
    "routed_h120": (B1 / "routed_h120",),
    "universe_N3": (ROOT / "docs/results/execution_sensitivity_N3",),
    "universe_N5": (ROOT / "docs/results/execution_sensitivity_N5",),
    "classical_h12": (B1 / "ds_h12",),
    "classical_h30": (B1 / "ds_h30",),
    "classical_h60": (B1 / "ds_h60",),
    "classical_h120": (B1 / "ds_h120",),
}


def main() -> int:
    rows = []
    for name, dirs in BOARDS.items():
        table = load_runs(dirs)
        if name.startswith("classical"):
            # deterministic reference board: drop the LLM rows (provider:model)
            table = {
                scen: {lvl: {a: sv for a, sv in agents.items() if ":" not in a}
                       for lvl, agents in levels.items()}
                for scen, levels in table.items()
            }
        for scenario in sorted(table):
            levels = table[scenario]
            if "E0_ideal" not in levels or "E1_default_stress" not in levels:
                continue
            fit = tau_with_ci(levels["E0_ideal"], levels["E1_default_stress"])
            if fit is None:
                continue
            n_agents, n_seeds, tau, lo, hi = fit
            rows.append({
                "board": name, "scenario": scenario,
                "level_a": "E0_ideal", "level_b": "E1_default_stress",
                "agents": n_agents, "seeds": n_seeds,
                "kendall_tau_b": round(tau, 3),
                "ci_low": round(lo, 3), "ci_high": round(hi, 3),
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in rows:
        print(f"{r['board']:14s} {r['scenario']:9s} tau={r['kendall_tau_b']:+.3f} "
              f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] "
              f"(agents={r['agents']}, seeds={r['seeds']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
