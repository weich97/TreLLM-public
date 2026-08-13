"""B5: deterministic 7-agent E0->E1 Kendall tau_b at larger universes N in {20,50}.

Extends the existing N in {2,3,5,10} universe curve (analyze_horizon_and_universe.py)
to delineate where the stress-induced reordering fully vanishes as the asset
universe grows. Free / deterministic (no provider calls). High-volatility regime,
12 decision steps, 10 seeds. Writes docs/results/execution_sensitivity_b5_universe/.
"""
from __future__ import annotations

import csv
import statistics as st
from pathlib import Path

from scipy.stats import kendalltau

from tradearena.factory import build_default_system

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/results/execution_sensitivity_b5_universe"
OUT.mkdir(parents=True, exist_ok=True)

HV = {"synthetic_volatility_scale": 2.25, "synthetic_trend_scale": 0.65, "synthetic_macro_scale": 1.4}
LEVELS = {"E0": {"execution_mode": "ideal"}, "E1": {"execution_mode": "realistic"}}
AGENTS = ["buy-and-hold", "signal-weighted", "naive-momentum", "mean-reversion",
          "risk-parity", "minimum-variance", "random"]
SEEDS = [100 + s for s in range(1, 11)]  # high_vol offset, seeds 101-110
ALLSYM = tuple(["SYN", "ALT"] + [f"A{i}" for i in range(3, 51)])  # up to N=50


def mean_sharpe(symbols, level, agent, seed):
    kw = dict(HV)
    kw.update(level)
    kw.update({"strategy_name": agent, "analyst_names": ("momentum", "macro-news")})
    _, m = build_default_system(name="b5", symbols=symbols, periods=12, seed=seed,
                                risk_name="max-position", **kw).run()
    return m.get("sharpe", 0.0)


def tau_e0_e1(symbols):
    sh = {lv: {a: st.mean([mean_sharpe(symbols, LEVELS[lv], a, s) for s in SEEDS])
               for a in AGENTS} for lv in LEVELS}
    e0 = [sh["E0"][a] for a in AGENTS]
    e1 = [sh["E1"][a] for a in AGENTS]
    return kendalltau(e0, e1, variant="b")[0]


def main() -> int:
    rows = []
    for n in (20, 50):
        t = tau_e0_e1(ALLSYM[:n])
        rows.append({"n_assets": n, "periods": 12, "tau_b_E0_E1": round(float(t), 3)})
        print(f"N={n}: tau_b E0->E1 = {t:.3f}", flush=True)
    out = OUT / "b5_universe_curve.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["n_assets", "periods", "tau_b_E0_E1"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")
    print("(prior deterministic curve: N=2/3/5/10 = 0.81/1.0/0.905/1.0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
