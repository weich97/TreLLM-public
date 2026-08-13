"""Compression curves with explicit access-path provenance.

E0->E1 Kendall tau_b is reported in the high-volatility regime at universe
sizes N in {2,3,5,10}. The direct-only GLM boards intentionally have no N=2
point because that matrix contains only the routed ``poe:glm-5`` identity;
silently substituting it for ``glm:glm-5`` would splice two interfaces into a
curve labeled direct. A separate full-board row retains that historical splice
as an explicitly labeled diagnostic. The study's fixed 11-policy descriptive
curve uses deepseek direct plus the same three routed policy identities at every
N and never performs the GLM route swap.
"""
from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[1]
DS = "deepseek:deepseek-v4-pro"
GLM = "glm:glm-5"
GLM_ROUTED = "poe:glm-5"
POE = ["poe:gpt-5.5", "poe:claude-opus-4.7", "poe:gemini-3.1-pro"]
CLS = ["buy-and-hold", "signal-weighted", "naive-momentum", "mean-reversion",
       "risk-parity", "minimum-variance", "random"]
FULL12 = CLS + [DS, GLM] + POE
CONSISTENT11 = CLS + [DS] + POE
E0, E1 = "E0_ideal", "E1_default_stress"


def sharpe_from_runs(path, want):
    out = defaultdict(list)
    if not Path(path).exists():
        return {}
    for r in csv.DictReader(Path(path).open(encoding="utf-8")):
        if r.get("scenario") == "high_vol" and r["agent"] in want and r["level"] in (E0, E1):
            out[(r["level"], r["agent"])].append(float(r["sharpe"]))
    return {k: st.mean(v) for k, v in out.items()}


# per-N sharpe tables, keyed (level, agent)
N2 = {(r["level"], r["agent"]): float(r["sharpe_mean"])
      for r in csv.DictReader((ROOT / "docs/results/execution_sensitivity_llm/merged_aggregate.csv").open(encoding="utf-8"))
      if r["scenario"] == "high_vol"}
N3 = sharpe_from_runs(ROOT / "docs/results/execution_sensitivity_N3/execution_sensitivity_runs.csv", set(FULL12))
N5 = sharpe_from_runs(ROOT / "docs/results/execution_sensitivity_N5/execution_sensitivity_runs.csv", set(FULL12))
N10 = {}
N10.update(sharpe_from_runs(ROOT / "docs/results/execution_sensitivity_universe10/execution_sensitivity_runs.csv", set(CLS)))
N10.update(sharpe_from_runs(ROOT / "docs/results/execution_sensitivity_universe10_ds/execution_sensitivity_runs.csv", {DS}))
N10.update(sharpe_from_runs(ROOT / "docs/results/execution_sensitivity_universe10_glm/execution_sensitivity_runs.csv", {GLM}))
N10.update(sharpe_from_runs(ROOT / "docs/results/execution_sensitivity_universe10_poe/execution_sensitivity_runs.csv", set(POE)))
TABLES = {2: N2, 3: N3, 5: N5, 10: N10}


def getval(sh, lv, agent, *, allow_glm_route_swap=False):
    direct = sh.get((lv, agent))
    if direct is not None:
        return direct
    if agent == GLM and allow_glm_route_swap:
        return sh.get((lv, GLM_ROUTED))
    return sh.get((lv, agent))


def tau(board, sh, *, allow_glm_route_swap=False):
    e0 = [getval(sh, E0, a, allow_glm_route_swap=allow_glm_route_swap) for a in board]
    e1 = [getval(sh, E1, a, allow_glm_route_swap=allow_glm_route_swap) for a in board]
    if any(v is None for v in e0 + e1):
        return None
    return kendalltau(e0, e1, variant="b")[0]


boards = {
    "deepseek-direct+cls": (CLS + [DS], "direct-fixed", False),
    "glm-direct+cls": (CLS + [GLM], "direct-fixed", False),
    "deepseek+glm-direct+cls": (CLS + [DS, GLM], "direct-fixed", False),
    "consistent11 (fixed identities; no GLM route swap)": (
        CONSISTENT11,
        "fixed-identities-mixed-access",
        False,
    ),
    "mixed-interface full12 (GLM routed at N=2; diagnostic only)": (
        FULL12,
        "mixed-glm-route-swap-diagnostic",
        True,
    ),
}
results = {name: {} for name in boards}
for n, sh in TABLES.items():
    for name, (board, _provenance, allow_swap) in boards.items():
        t = tau(board, sh, allow_glm_route_swap=allow_swap)
        if t is not None:
            results[name][n] = round(t, 3)

out = ROOT / "docs/results/execution_sensitivity_horizon_universe/direct_llm_compression.csv"
with out.open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["board", "n_assets", "tau_b_E0_E1", "provenance"])
    for name, (_board, provenance, _allow_swap) in boards.items():
        for n in sorted(results[name]):
            w.writerow([name, n, results[name][n], provenance])
print("Compression curves with access-path provenance (high-vol E0->E1 tau_b):")
for name in boards:
    pts = "  ".join(f"N{n}={results[name][n]}" for n in sorted(results[name]))
    print(f"  {name:>18}: {pts or '(incomplete)'}")
print(f"wrote {out}")
