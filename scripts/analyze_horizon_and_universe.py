"""Two robustness curves on the deterministic 7-agent board (no API):

  (1) Horizon robustness: E0->E1 Kendall tau_b in the high-volatility regime as
      the decision horizon grows {12, 24, 60, 120} steps. The main matrix uses
      12 steps; this asks whether the reordering is a short-horizon artifact.

  (2) Intermediate-N compression curve: E0->E1 tau_b at the main-matrix horizon
      (12 steps) for universes of N in {2,3,5,10} assets, turning the two-point
      N=2->N=10 contrast into a curve.

Writes CSVs + a markdown summary to docs/results/execution_sensitivity_horizon_universe/.
"""
from __future__ import annotations

import csv
import statistics as st
from pathlib import Path

from scipy.stats import kendalltau

from tradearena.factory import build_default_system

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/results/execution_sensitivity_horizon_universe"
OUT.mkdir(parents=True, exist_ok=True)

HV = {"synthetic_volatility_scale": 2.25, "synthetic_trend_scale": 0.65, "synthetic_macro_scale": 1.4}
LEVELS = {"E0": {"execution_mode": "ideal"}, "E1": {"execution_mode": "realistic"}}
AGENTS = ["buy-and-hold", "signal-weighted", "naive-momentum", "mean-reversion",
          "risk-parity", "minimum-variance", "random"]
SEEDS = [100 + s for s in range(1, 11)]  # high_vol offset, 10 seeds
ALLSYM = ("SYN", "ALT", "C3", "D4", "E5", "F6", "G7", "H8", "I9", "J10")


def mean_sharpe(symbols, periods, level, agent, seed):
    kw = dict(HV); kw.update(level)
    kw.update({"strategy_name": agent, "analyst_names": ("momentum", "macro-news")})
    _, m = build_default_system(name="hu", symbols=symbols, periods=periods,
                                seed=seed, risk_name="max-position", **kw).run()
    return m.get("sharpe", 0.0)


def tau_e0_e1(symbols, periods):
    sh = {lv: {a: st.mean([mean_sharpe(symbols, periods, LEVELS[lv], a, s) for s in SEEDS])
               for a in AGENTS} for lv in LEVELS}
    e0 = [sh["E0"][a] for a in AGENTS]
    e1 = [sh["E1"][a] for a in AGENTS]
    return kendalltau(e0, e1, variant="b")[0]


# ---- (1) horizon curve (N=2) ----
horizon_rows = []
for periods in (12, 24, 60, 120):
    t = tau_e0_e1(("SYN", "ALT"), periods)
    horizon_rows.append({"periods": periods, "n_assets": 2, "tau_b_E0_E1": round(t, 3)})
    print(f"horizon periods={periods}: tau_b E0->E1 = {t:.3f}", flush=True)

# ---- (2) intermediate-N curve (12 steps) ----
universe_rows = []
for n in (2, 3, 5, 10):
    t = tau_e0_e1(ALLSYM[:n], 12)
    universe_rows.append({"n_assets": n, "periods": 12, "tau_b_E0_E1": round(t, 3)})
    print(f"universe N={n}: tau_b E0->E1 = {t:.3f}", flush=True)

with (OUT / "horizon_curve.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["periods", "n_assets", "tau_b_E0_E1"]); w.writeheader(); w.writerows(horizon_rows)
with (OUT / "universe_curve.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["n_assets", "periods", "tau_b_E0_E1"]); w.writeheader(); w.writerows(universe_rows)

lines = ["# Horizon and intermediate-N curves (deterministic 7-agent board, high-vol)\n",
         "## (1) Horizon robustness (N=2, E0->E1 tau_b)\n",
         "| Decision steps | tau_b E0->E1 |", "|---|---|"]
lines += [f"| {r['periods']} | {r['tau_b_E0_E1']} |" for r in horizon_rows]
lines += ["\n## (2) Intermediate-N compression curve (12 steps, E0->E1 tau_b)\n",
          "| N assets | tau_b E0->E1 |", "|---|---|"]
lines += [f"| {r['n_assets']} | {r['tau_b_E0_E1']} |" for r in universe_rows]
(OUT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
print("\n" + "\n".join(lines))
print(f"\nWrote to {OUT}")
