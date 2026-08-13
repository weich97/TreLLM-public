"""Capital-scale evidence for the execution-units correction (execution-units study).

Produces three things, all from the deterministic 7-agent board (no API):

  1. Cap-binding diagnostic: at $100k and $30M, for E1/participation/harsh,
     median order size (shares), median/max realized participation, mean fill
     rate, % fills cap-bound, % fills cash/position-bound. Shows the
     participation cap is inert at $100k and binds at $30M.

  2. Capital-scale robustness: per regime, Kendall tau_b of the E0 ranking vs
     E1 and vs harsh, at $100k and $30M. Shows the E0->E1 reordering is
     essentially unchanged when the cap binds (cap is a leveler, not a driver).

  3. Open-loop check: per level, drawdown kill-switch trigger rate, and the
     max per-step pre-gate (strategy) target-weight difference between E0 and
     E1 (should be ~0 for price-determined baselines).

Writes CSVs + a markdown summary to docs/results/execution_sensitivity_capital_scale/.
"""
from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

from scipy.stats import kendalltau

import tradearena.agents.risk as risk_mod
import tradearena.execution.stress as stress_mod
from tradearena.factory import build_default_system

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/results/execution_sensitivity_capital_scale"
OUT.mkdir(parents=True, exist_ok=True)

REGIMES = {
    # high-volatility headline regime (where the E0->E1 collapse occurs)
    "high_vol": ({"synthetic_volatility_scale": 2.25, "synthetic_trend_scale": 0.65,
                  "synthetic_macro_scale": 1.4}, 100),
}
LEVELS = {
    "E0": {"execution_mode": "ideal"},
    "E1": {"execution_mode": "realistic"},
    "participation_1pct": {"execution_mode": "realistic", "participation_rate": 0.01},
    "harsh": {"execution_mode": "realistic", "spread_bps": 20.0, "latency_steps": 3,
              "participation_rate": 0.01, "market_impact": 0.3},
}
AGENTS = ["buy-and-hold", "signal-weighted", "naive-momentum", "mean-reversion",
          "risk-parity", "minimum-variance", "random"]
CAPITALS = {"100k": 1e5, "30M": 3e7}
BASE_SEEDS = list(range(1, 11))  # 10 seeds (match main matrix + horizon curve)

# ---- instrumentation -------------------------------------------------------
FILLREC: list[dict] = []
KILL = {"triggers": 0, "steps": 0}
PREGATE: dict[tuple, list[tuple]] = {}  # (cap,regime,agent,seed,level) -> per-step weight tuples
CTX = {"cap": "", "regime": "", "agent": "", "seed": 0, "level": ""}

_orig_exec = stress_mod.RealisticOrderSimulator.execute
_orig_approve = risk_mod.MaxPositionRiskManager.approve


def _patched_exec(self, snapshot, orders, portfolio):
    fills = _orig_exec(self, snapshot, orders, portfolio)
    for f in fills:
        vol = snapshot.bars[f.symbol].volume if f.symbol in snapshot.bars else float("nan")
        FILLREC.append({
            "cap": CTX["cap"], "level": CTX["level"], "agent": CTX["agent"],
            "req": f.requested_quantity, "capacity": f.liquidity_available,
            "filled": f.quantity, "ratio": f.fill_ratio, "vol": vol,
            "part_rate": self.participation_rate,
        })
    return fills


def _patched_approve(self, snapshot, decisions, portfolio, memory):
    key = (CTX["cap"], CTX["regime"], CTX["agent"], CTX["seed"], CTX["level"])
    PREGATE.setdefault(key, []).append(
        tuple(round(d.target_weight, 8) for d in decisions))
    approved = _orig_approve(self, snapshot, decisions, portfolio, memory)
    KILL["steps"] += 1
    if any(d.metadata.get("drawdown_kill_switch") is True for d in approved):
        KILL["triggers"] += 1
    return approved


stress_mod.RealisticOrderSimulator.execute = _patched_exec
risk_mod.MaxPositionRiskManager.approve = _patched_approve

# ---- run -------------------------------------------------------------------
sharpe: dict[tuple, float] = {}
kill_by_level: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])  # (cap,level)->[trig,steps]

for cap_name, cap_val in CAPITALS.items():
    for regime, (syn, offset) in REGIMES.items():
        for agent in AGENTS:
            for level_name, level in LEVELS.items():
                vals = []
                for base in BASE_SEEDS:
                    seed = base + offset
                    CTX.update(cap=cap_name, regime=regime, agent=agent, seed=seed, level=level_name)
                    before = (KILL["triggers"], KILL["steps"])
                    kwargs = dict(syn)
                    kwargs.update(level)
                    kwargs.update({"strategy_name": agent, "analyst_names": ("momentum", "macro-news")})
                    _, m = build_default_system(
                        name=f"cs_{agent}_{seed}", symbols=("SYN", "ALT"), periods=12,
                        seed=seed, initial_cash=cap_val, risk_name="max-position", **kwargs,
                    ).run()
                    vals.append(m.get("sharpe", 0.0))
                    dt = KILL["triggers"] - before[0]
                    ds = KILL["steps"] - before[1]
                    kb = kill_by_level[(cap_name, level_name)]
                    kb[0] += dt
                    kb[1] += ds
                sharpe[(cap_name, regime, agent, level_name)] = st.mean(vals)
            print(f"  done {cap_name} {regime} {agent}", flush=True)

# ---- 1. cap-binding diagnostic --------------------------------------------
diag_rows = []
by = defaultdict(list)
for r in FILLREC:
    by[(r["cap"], r["level"])].append(r)
for (cap_name, level_name), recs in sorted(by.items()):
    reqs = [r["req"] for r in recs]
    parts = [r["filled"] / max(1.0, r["vol"]) for r in recs]
    ratios = [r["ratio"] for r in recs]
    capbnd = sum(1 for r in recs if r["capacity"] < r["req"] - 1e-6)
    cashbnd = sum(1 for r in recs if r["filled"] < min(r["req"], r["capacity"]) - 1e-6)
    n = len(recs)
    diag_rows.append({
        "capital": cap_name, "level": level_name, "n_fills": n,
        "median_order_shares": round(st.median(reqs), 1),
        "median_participation": round(st.median(parts), 5),
        "max_participation": round(max(parts), 5),
        "mean_fill_rate": round(st.mean(ratios), 4),
        "pct_cap_bound": round(100 * capbnd / n, 1),
        "pct_cash_pos_bound": round(100 * cashbnd / n, 1),
    })

with (OUT / "cap_binding_diagnostic.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(diag_rows[0].keys()))
    w.writeheader()
    w.writerows(diag_rows)

# ---- 2. capital-scale robustness (tau_b) ----------------------------------
tau_rows = []
for cap_name in CAPITALS:
    for regime in REGIMES:
        e0 = [sharpe[(cap_name, regime, a, "E0")] for a in AGENTS]
        e1 = [sharpe[(cap_name, regime, a, "E1")] for a in AGENTS]
        hh = [sharpe[(cap_name, regime, a, "harsh")] for a in AGENTS]
        t_e1, _ = kendalltau(e0, e1, variant="b")
        t_hh, _ = kendalltau(e0, hh, variant="b")
        tau_rows.append({"capital": cap_name, "regime": regime,
                         "tau_b_E0_E1": round(t_e1, 3), "tau_b_E0_harsh": round(t_hh, 3)})
with (OUT / "capital_scale_tau.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(tau_rows[0].keys()))
    w.writeheader()
    w.writerows(tau_rows)

# ---- 3. open-loop: kill-switch rate + pre-gate identity -------------------
kill_rows = []
for (cap_name, level_name), (trig, steps) in sorted(kill_by_level.items()):
    kill_rows.append({"capital": cap_name, "level": level_name, "kill_triggers": trig,
                      "decision_steps": steps,
                      "kill_rate_pct": round(100 * trig / max(1, steps), 3)})
with (OUT / "kill_switch_rate.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(kill_rows[0].keys()))
    w.writeheader()
    w.writerows(kill_rows)

# pre-gate identity: max abs diff between E0 and E1 per-step weight vectors
max_pregate_diff = 0.0
mismatch = 0
for cap_name in CAPITALS:
    for regime in REGIMES:
        for agent in AGENTS:
            for base in BASE_SEEDS:
                seed = base + REGIMES[regime][1]
                e0 = PREGATE.get((cap_name, regime, agent, seed, "E0"), [])
                e1 = PREGATE.get((cap_name, regime, agent, seed, "E1"), [])
                for a, b in zip(e0, e1):
                    if len(a) == len(b):
                        d = max((abs(x - y) for x, y in zip(a, b)), default=0.0)
                        max_pregate_diff = max(max_pregate_diff, d)
                        if d > 1e-9:
                            mismatch += 1

# ---- markdown summary ------------------------------------------------------
lines = ["# Capital-scale evidence (execution-units correction)\n"]
lines.append("## 1. Cap-binding diagnostic (deterministic board, all regimes pooled)\n")
lines.append("| Capital | Level | Median order (sh) | Median part. | Max part. | Mean fill | % cap-bound | % cash/pos-bound |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in diag_rows:
    lines.append(f"| {r['capital']} | {r['level']} | {r['median_order_shares']} | "
                 f"{r['median_participation']} | {r['max_participation']} | {r['mean_fill_rate']} | "
                 f"{r['pct_cap_bound']} | {r['pct_cash_pos_bound']} |")
lines.append("\n## 2. Capital-scale robustness (E0 ranking vs E1 / harsh, tau_b)\n")
lines.append("| Capital | Regime | tau_b E0->E1 | tau_b E0->harsh |")
lines.append("|---|---|---|---|")
for r in tau_rows:
    lines.append(f"| {r['capital']} | {r['regime']} | {r['tau_b_E0_E1']} | {r['tau_b_E0_harsh']} |")
lines.append("\n## 3. Open-loop check: drawdown kill-switch rate\n")
lines.append("| Capital | Level | Kill triggers | Steps | Kill rate % |")
lines.append("|---|---|---|---|---|")
for r in kill_rows:
    lines.append(f"| {r['capital']} | {r['level']} | {r['kill_triggers']} | "
                 f"{r['decision_steps']} | {r['kill_rate_pct']} |")
lines.append(f"\nPre-gate (strategy) target-weight identity across E0/E1: "
             f"max abs per-step diff = {max_pregate_diff:.2e}; mismatched steps = {mismatch}.")
(OUT / "capital_scale_summary.md").write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print(f"\nWrote CSVs + summary to {OUT}")
