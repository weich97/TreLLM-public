"""Direct-API matrix headline analysis (v0.3 benchmark): per-model performance and
E0-vs-E1 ranking stability across the three C0 regimes.

Honest scope note: the direct-API matrix carries five models, one of which
(deepseek-v4-pro) declines to trade in every cell (a reliability-profile
datapoint, not a bug). Where rows are well separated in Sharpe, execution
friction compresses every cell (E0->E1) without reordering (tau=1 in calm and
high-vol); where the two flagship rows are near-tied (E0 gaps far inside the
cluster-bootstrap intervals), the displayed order is decided by the execution
convention -- they swap the top spot under jump-tail (tau=0.8) -- exactly the
contender-compression mechanism of the execution-sensitivity study. The
combined LLM+anchor board (see build_v03_result_tables.py) carries the full
winner-flip evidence.
"""
from __future__ import annotations

import collections
import csv
import statistics as st
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "outputs/v0_3_direct_api_matrix/direct_api_submission_runs.csv"
OUT_DIR = ROOT / "docs/results/v0_3_direct_api_matrix"
MODELS = ["deepseek-v4-pro", "deepseek-v4-flash", "glm-5", "glm-5-turbo", "glm-5.2"]
SCENARIOS = [("calm", "calm"), ("highvol", "high_vol"), ("jumptail", "jump_tail")]


def scen_of(plan: str) -> str:
    if "calm" in plan:
        return "calm"
    if "high_vol" in plan:
        return "highvol"
    return "jumptail"


def main() -> int:
    rows = list(csv.DictReader(RUNS.open(encoding="utf-8")))
    agg: dict[tuple[str, str, str], dict[str, list[float]]] = collections.defaultdict(
        lambda: {"sh": [], "ret": []}
    )
    for r in rows:
        model = r.get("model_id") or r.get("model") or ""
        plan = r.get("plan_id", "")
        level = "E0" if "__e0__" in plan else "E1"
        try:
            agg[(model, scen_of(plan), level)]["sh"].append(float(r.get("sharpe") or 0.0))
            agg[(model, scen_of(plan), level)]["ret"].append(float(r.get("total_return") or 0.0))
        except (TypeError, ValueError):
            continue

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "matrix_by_model.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "scenario", "E0_sharpe", "E1_sharpe", "E0_return", "E1_return",
                    "sharpe_drop_E0_to_E1", "n_per_cell"])
        for model in MODELS:
            for short, _long in SCENARIOS:
                e0, e1 = agg[(model, short, "E0")], agg[(model, short, "E1")]
                if not e0["sh"] or not e1["sh"]:
                    continue
                s0, s1 = st.mean(e0["sh"]), st.mean(e1["sh"])
                w.writerow([model, short, f"{s0:.3f}", f"{s1:.3f}",
                            f"{st.mean(e0['ret']):.4f}", f"{st.mean(e1['ret']):.4f}",
                            f"{s0 - s1:.3f}", len(e0["sh"])])

    # E0-vs-E1 Kendall tau on the LLM-only board per scenario.
    with (OUT_DIR / "matrix_ranking_stability.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "n_models", "tau_b_E0_vs_E1", "note"])
        for short, _long in SCENARIOS:
            e0 = [st.mean(agg[(m, short, "E0")]["sh"]) for m in MODELS if agg[(m, short, "E0")]["sh"]]
            e1 = [st.mean(agg[(m, short, "E1")]["sh"]) for m in MODELS if agg[(m, short, "E1")]["sh"]]
            tau = stats.kendalltau(e0, e1).statistic if len(e0) >= 2 else float("nan")
            note = ("near-tied flagship rows swap the top spot"
                    if tau < 0.999 else "separated rows: uniform compression, no reorder")
            w.writerow([short, len(e0), f"{tau:.3f}", note])

    print("per-model (mean Sharpe over 30 seed x sample):")
    print(f"{'model':20s}{'scen':10s}{'E0':>8s}{'E1':>8s}{'drop':>8s}")
    for model in MODELS:
        for short, _long in SCENARIOS:
            e0, e1 = agg[(model, short, "E0")], agg[(model, short, "E1")]
            if e0["sh"] and e1["sh"]:
                s0, s1 = st.mean(e0["sh"]), st.mean(e1["sh"])
                print(f"{model:20s}{short:10s}{s0:>8.2f}{s1:>8.2f}{s0 - s1:>8.2f}")
    print("\nE0-vs-E1 Kendall tau (LLM-only board):")
    for short, _long in SCENARIOS:
        e0 = [st.mean(agg[(m, short, "E0")]["sh"]) for m in MODELS if agg[(m, short, "E0")]["sh"]]
        e1 = [st.mean(agg[(m, short, "E1")]["sh"]) for m in MODELS if agg[(m, short, "E1")]["sh"]]
        tau = stats.kendalltau(e0, e1).statistic if len(e0) >= 2 else float("nan")
        print(f"  {short:10s} tau={tau:+.2f}  (n={len(e0)} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
