"""Robustness analysis for the execution-sensitivity study.

(A) Regenerate turnover-tercile Kendall tau-b consistently with the merged
    leaderboard (tau-b on merged_aggregate Sharpe means), so the
    full-leaderboard tau matches Table 1 exactly.
(B) Friction-fragility DiD vs. buy-and-hold: descriptive per-regime means
    alongside the canonical pooled 30-cell sign-flip test and combined-family
    BH-FDR values. With only three regime blocks, this script deliberately does
    not present block-level randomization inference.

Reads only released CSVs; no API calls.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs/results/execution_sensitivity_llm"
REGIMES = ["calm", "high_vol", "jump_tail"]
ANCHOR = "buy-and-hold"


def load_merged_aggregate():
    sharpe = {}
    for r in csv.DictReader((D / "merged_aggregate.csv").open(encoding="utf-8")):
        sharpe[(r["scenario"], r["level"], r["agent"])] = float(r["sharpe_mean"])
    return sharpe


def taub(d_a, d_b):
    keys = sorted(set(d_a) & set(d_b))
    if len(keys) < 2:
        return None
    t, _ = kendalltau([d_a[k] for k in keys], [d_b[k] for k in keys], variant="b")
    return t


# ---------- (A) turnover terciles, consistent tau-b ----------
def turnover_analysis(sharpe):
    print("=" * 70)
    print("(A) TURNOVER-TERCILE TAU-B (recomputed on merged_aggregate, tau-b)")
    print("=" * 70)
    bins = defaultdict(list)
    for r in csv.DictReader((D / "turnover_control.csv").open(encoding="utf-8")):
        bins[r["scenario"]].append((r["turnover_bin"], r["bin_agents"].split(";"), float(r["mean_turnover"])))
    for regime in REGIMES:
        e0 = {a: sharpe[(regime, "E0_ideal", a)] for (rg, lv, a) in sharpe if rg == regime and lv == "E0_ideal"}
        e1 = {a: sharpe[(regime, "E1_default_stress", a)] for (rg, lv, a) in sharpe if rg == regime and lv == "E1_default_stress"}
        full = taub(e0, e1)
        print(f"\n{regime}: full-leaderboard tau-b(E0,E1) = {full:.3f}")
        for binname, members, mt in bins[regime]:
            be0 = {a: e0[a] for a in members if a in e0}
            be1 = {a: e1[a] for a in members if a in e1}
            wt = taub(be0, be1)
            short = [m.split(":")[-1] for m in members]
            print(f"  {binname} turn={mt:5.1f} within-tau={wt:+.3f}  [{', '.join(short)}]")


# ---------- (B) DiD: descriptive regimes + canonical pooled inference ----------
def load_returns():
    # average total_return over samples per (scenario, level, agent, seed)
    acc = defaultdict(list)
    for r in csv.DictReader((D / "merged_runs.csv").open(encoding="utf-8")):
        acc[(r["scenario"], r["level"], r["agent"], r["seed"])].append(float(r["total_return"]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def did_deltas(ret, agent, level):
    """Return dict regime -> list of per-seed DiD deltas (anchor = buy-and-hold)."""
    out = defaultdict(list)
    seeds = sorted({k[3] for k in ret if k[2] == agent})
    for rg in REGIMES:
        for s in seeds:
            try:
                ra0 = ret[(rg, "E0_ideal", agent, s)]
                ral = ret[(rg, level, agent, s)]
                rb0 = ret[(rg, "E0_ideal", ANCHOR, s)]
                rbl = ret[(rg, level, ANCHOR, s)]
            except KeyError:
                continue
            out[rg].append((ra0 - ral) - (rb0 - rbl))
    return out


def load_canonical_inference():
    rows = {}
    with (D / "fragility_did.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[(row["stress_level"], row["agent"])] = row
    return rows


def did_analysis():
    print("\n" + "=" * 70)
    print("(B) DiD vs buy-and-hold: descriptive regimes + canonical pooled test")
    print("=" * 70)
    ret = load_returns()
    canonical = load_canonical_inference()
    agents = sorted({k[2] for k in ret} - {ANCHOR})
    for level in ["E1_default_stress", "E2_harsh_corner"]:
        print(f"\n--- {level} ---")
        rows = []
        for a in agents:
            by = did_deltas(ret, a, level)
            flat = [value for regime in REGIMES for value in by[regime]]
            mean_obs = sum(flat) / len(flat)
            permeans = {rg: (sum(by[rg]) / len(by[rg]) if by[rg] else float("nan")) for rg in REGIMES}
            inference = canonical[(level, a)]
            rows.append(
                (
                    a,
                    mean_obs,
                    permeans,
                    float(inference["permutation_p_value"]),
                    float(inference["q_value"]),
                )
            )
        rows.sort(key=lambda r: r[1])
        print(
            f"{'agent':24s} {'meanDiD%':>8s} {'calm%':>7s} {'hv%':>7s} "
            f"{'jt%':>7s} {'p_pool':>7s} {'q_22':>7s}"
        )
        for a, m, pm, pp, qq in rows:
            print(
                f"{a.split(':')[-1]:24s} {m * 100:8.2f} {pm['calm'] * 100:7.2f} "
                f"{pm['high_vol'] * 100:7.2f} {pm['jump_tail'] * 100:7.2f} {pp:7.3f} {qq:7.3f}"
            )
    print("\nRegime columns are descriptive; three blocks cannot support the claimed stratified test.")


if __name__ == "__main__":
    sh = load_merged_aggregate()
    turnover_analysis(sh)
    did_analysis()
