"""Generate the v0.3 benchmark result tables as LaTeX fragments from gate-passing
artifacts, so no reported number is hand-entered.

Inputs (all committed artifacts or gate outputs):
- outputs/v0_3_direct_api_matrix/direct_api_submission_runs.csv  (540 LLM rows)
- docs/results/v0_3_anchor_baselines_{calm,high_vol,jump_tail}/execution_ladder_rows.csv
  (1890 deterministic anchor rows; seeds include the 10 matrix seeds)
- docs/results/v0_3_power_note/v0_3_detectable_effects.csv

Outputs:
- tables/{headline_matrix,anchor_baselines,
  anchor_baselines_e0e2,ranking_stability,variance_decomposition,power_note}.tex
- docs/results/v0_3_direct_api_matrix/matrix_by_model_ci.csv (full CI table)

Statistical conventions: cell = mean Sharpe; uncertainty = 95% cluster
bootstrap over seeds (resample seeds with replacement, keep all samples of a
resampled seed; 10,000 draws, fixed RNG seed). Kendall tau_b on mean-Sharpe
boards. The combined board restricts anchors to the 10 matrix seeds so both
agent families average over identical market paths.
"""
from __future__ import annotations

import csv
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "outputs/v0_3_direct_api_matrix/direct_api_submission_runs.csv"
ANCHOR_DIRS = {
    "calm": ROOT / "docs/results/v0_3_anchor_baselines_calm",
    "high_vol": ROOT / "docs/results/v0_3_anchor_baselines_high_vol",
    "jump_tail": ROOT / "docs/results/v0_3_anchor_baselines_jump_tail",
}
POWER = ROOT / "docs/results/v0_3_power_note/v0_3_detectable_effects.csv"
TABLES = ROOT / "tables"
CI_CSV = ROOT / "docs/results/v0_3_direct_api_matrix/matrix_by_model_ci.csv"

MODELS = ["deepseek-v4-pro", "deepseek-v4-flash", "glm-5", "glm-5-turbo", "glm-5.2"]
REGIMES = ["calm", "high_vol", "jump_tail"]
REGIME_TEX = {"calm": "CT", "high_vol": "HV", "jump_tail": "JT"}
ANCHORS = [
    "buy-and-hold", "signal-weighted", "naive-momentum", "mean-reversion",
    "risk-parity", "minimum-variance", "random",
]
ANCHOR_TEX = {
    "buy-and-hold": "buy-and-hold", "signal-weighted": "signal-weighted",
    "naive-momentum": "naive momentum", "mean-reversion": "mean reversion",
    "risk-parity": "risk parity", "minimum-variance": "minimum variance",
    "random": "seeded random",
}
MATRIX_SEEDS = {7, 11, 17, 23, 31, 37, 41, 43, 47, 53}
BOOT = 10_000


def scen_of(plan_or_id: str) -> str:
    if "calm" in plan_or_id:
        return "calm"
    if "high_vol" in plan_or_id or "high_volatility" in plan_or_id:
        return "high_vol"
    return "jump_tail"


def cluster_boot_ci(by_seed: dict[int, list[float]], rng: random.Random) -> tuple[float, float, float]:
    """Mean and 95% cluster-bootstrap CI, resampling seeds with replacement."""
    seeds = sorted(by_seed)
    values = [v for s in seeds for v in by_seed[s]]
    m = st.mean(values)
    if len(seeds) < 2:
        return m, m, m
    means = []
    for _ in range(BOOT):
        sample = [v for s in rng.choices(seeds, k=len(seeds)) for v in by_seed[s]]
        means.append(st.mean(sample))
    means.sort()
    return m, means[int(0.025 * BOOT)], means[int(0.975 * BOOT) - 1]


def load_llm(metric: str = "sharpe") -> dict[tuple[str, str, str], dict[int, list[float]]]:
    """(model, regime, level) -> seed -> [metric x samples]."""
    cells: dict[tuple[str, str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(RUNS.open(encoding="utf-8")):
        key = (r["model_id"], scen_of(r["scenario_id"]), r["execution_level"])
        cells[key][int(r["seed"])].append(float(r[metric] or 0.0))
    return cells


def load_anchors() -> dict[tuple[str, str, str], dict[int, list[float]]]:
    """(agent, regime, level) -> seed -> [sharpe]."""
    cells: dict[tuple[str, str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for regime, d in ANCHOR_DIRS.items():
        for r in csv.DictReader((d / "execution_ladder_rows.csv").open(encoding="utf-8")):
            key = (r["agent"], regime, r["execution_level"])
            cells[key][int(r["seed"])].append(float(r["sharpe"] or 0.0))
    return cells


def board_tau(names: list[str], e_a: dict[str, float], e_b: dict[str, float]) -> float:
    a = [e_a[n] for n in names]
    b = [e_b[n] for n in names]
    return float(stats.kendalltau(a, b).statistic)


def fmt(m: float, lo: float, hi: float) -> str:
    return f"{m:.2f} {{\\scriptsize$\\pm${(hi - lo) / 2:.2f}}}"


def main() -> int:
    rng = random.Random(20260706)
    TABLES.mkdir(parents=True, exist_ok=True)
    llm = load_llm()
    anc = load_anchors()

    # --- headline matrix fragment + full CI CSV -------------------------------
    ci_rows = []
    lines = ["\\begin{tabular}{llccc}", "\\toprule",
             "Model & E & CT & HV & JT \\\\", "\\midrule"]
    for model in MODELS:
        for i, level in enumerate(("E0", "E1")):
            cells = []
            for regime in REGIMES:
                m, lo, hi = cluster_boot_ci(llm[(model, regime, level)], rng)
                cells.append(fmt(m, lo, hi))
                ci_rows.append({"model": model, "regime": regime, "level": level,
                                "sharpe_mean": f"{m:.4f}", "ci95_lo": f"{lo:.4f}",
                                "ci95_hi": f"{hi:.4f}", "n_seeds": 10, "n_samples_per_seed": 3})
            head = model if i == 0 else ""
            lines.append(f"{head} & {level} & {' & '.join(cells)} \\\\")
        lines.append("\\addlinespace")
    lines = lines[:-1] + ["\\bottomrule", "\\end{tabular}"]
    (TABLES / "headline_matrix.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with CI_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ci_rows[0]))
        w.writeheader()
        w.writerows(ci_rows)

    # --- anchor baselines: E1 fragment plus full E0/E1/E2 appendix fragment ----
    for fname, levels in (("anchor_baselines.tex", ("E1",)),
                          ("anchor_baselines_e0e2.tex", ("E0", "E2")),
                          ("anchor_baselines_full.tex", ("E0", "E1", "E2"))):
        cols = "l" + "c" * (len(REGIMES) * len(levels))
        header = " & ".join(f"{REGIME_TEX[r]} {lv}" for lv in levels for r in REGIMES)
        rows = [f"\\begin{{tabular}}{{{cols}}}", "\\toprule",
                f"Baseline & {header} \\\\", "\\midrule"]
        for agent in ANCHORS:
            cells = []
            for lv in levels:
                for regime in REGIMES:
                    m, lo, hi = cluster_boot_ci(anc[(agent, regime, lv)], rng)
                    cells.append(fmt(m, lo, hi))
            rows.append(f"{ANCHOR_TEX[agent]} & {' & '.join(cells)} \\\\")
        rows += ["\\bottomrule", "\\end{tabular}"]
        (TABLES / fname).write_text("\n".join(rows) + "\n", encoding="utf-8")

    # --- ranking stability fragment -------------------------------------------
    def mean_board(source: dict, names: list[str], regime: str, level: str,
                   restrict: set[int] | None = None) -> dict[str, float]:
        board = {}
        for n in names:
            by_seed = source[(n, regime, level)]
            vals = [v for s, vs in by_seed.items() if restrict is None or s in restrict for v in vs]
            board[n] = st.mean(vals)
        return board

    disp = {**{m: m for m in MODELS}, **{a: f"\\textit{{{ANCHOR_TEX[a]}}}" for a in ANCHORS}}
    rows = ["\\begin{tabular}{lccclc}", "\\toprule",
            "Regime & combined $\\tau_b$(E0,E1) & LLM-only & anchors "
            "& winner E0 $\\to$ E1 (combined) & anchors $\\tau_b$(E0,E2) \\\\",
            "\\midrule"]
    for regime in REGIMES:
        combined_names = MODELS + ANCHORS
        src = {**{(m, regime, lv): llm[(m, regime, lv)] for m in MODELS for lv in ("E0", "E1")},
               **{(a, regime, lv): anc[(a, regime, lv)] for a in ANCHORS for lv in ("E0", "E1", "E2")}}
        c0 = mean_board(src, combined_names, regime, "E0", restrict=MATRIX_SEEDS)
        c1 = mean_board(src, combined_names, regime, "E1", restrict=MATRIX_SEEDS)
        tau_combined = board_tau(combined_names, c0, c1)
        l0 = mean_board(src, MODELS, regime, "E0")
        l1 = mean_board(src, MODELS, regime, "E1")
        tau_llm = board_tau(MODELS, l0, l1)
        a0 = mean_board(src, ANCHORS, regime, "E0")
        a1 = mean_board(src, ANCHORS, regime, "E1")
        a2 = mean_board(src, ANCHORS, regime, "E2")
        tau_anchor = board_tau(ANCHORS, a0, a1)
        tau_corner = board_tau(ANCHORS, a0, a2)
        w0 = max(c0, key=lambda n: c0[n])
        w1 = max(c1, key=lambda n: c1[n])
        arrow = f"{disp[w0]} $\\to$ {disp[w1]}"
        if w0 != w1:
            arrow += " \\textbf{(flip)}"
        regime_label = {"calm": "calm trend", "high_vol": "high volatility",
                        "jump_tail": "jump--tail"}[regime]
        rows.append(f"{regime_label} & {tau_combined:.2f} & {tau_llm:.2f} & "
                    f"{tau_anchor:.2f} & {arrow} & {tau_corner:.2f} \\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    (TABLES / "ranking_stability.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # --- variance decomposition fragment ---------------------------------------
    # Per model at E1, per regime: between-seed variance of seed means vs mean
    # within-seed variance across the 3 samples, on total return (the
    # pre-registered decomposition metric); shares averaged over regimes.
    llm_ret = load_llm(metric="total_return")
    d_10 = d_30 = ""
    for r in csv.DictReader(POWER.open(encoding="utf-8")):
        if r["target_power"] == "0.8" and r["repeat_count"] == "10":
            d_10 = r["minimum_detectable_cohens_d"]
        if r["target_power"] == "0.8" and r["repeat_count"] == "30":
            d_30 = r["minimum_detectable_cohens_d"]
    rows = ["\\begin{tabular}{lccc}", "\\toprule",
            "Model (at E1) & between-seed share & within-seed share & note \\\\",
            "\\midrule"]
    for model in MODELS:
        shares = []
        degenerate = True
        for regime in REGIMES:
            by_seed = llm_ret[(model, regime, "E1")]
            seed_means = [st.mean(v) for v in by_seed.values()]
            between = st.pvariance(seed_means)
            within = st.mean([st.pvariance(v) for v in by_seed.values()])
            if between + within > 1e-12:
                degenerate = False
                shares.append(between / (between + within))
        if degenerate:
            rows.append(f"{model} & -- & -- & degenerate (declines to trade) \\\\")
        else:
            b = st.mean(shares)
            rows.append(f"{model} & {b:.2f} & {1 - b:.2f} & mean over regimes \\\\")
    rows += ["\\midrule",
             f"\\multicolumn{{4}}{{l}}{{detectable paired $d$ at 80\\% power: "
             f"{d_10} at 10 seeds (LLM cells), {d_30} at 30 seeds (anchors)}} \\\\",
             "\\bottomrule", "\\end{tabular}"]
    (TABLES / "variance_decomposition.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # --- power note fragment ----------------------------------------------------
    rows = ["\\begin{tabular}{lcc}", "\\toprule",
            "Paired repeats (seeds) & detectable $d$ (80\\% power) & detectable $d$ (50\\% power) \\\\",
            "\\midrule"]
    grid: dict[str, dict[str, str]] = defaultdict(dict)
    for r in csv.DictReader(POWER.open(encoding="utf-8")):
        grid[r["repeat_count"]][r["target_power"]] = r["minimum_detectable_cohens_d"]
    notes = {"6": "below threshold: pilot label", "10": "LLM main-comparison minimum",
             "20": "intermediate", "30": "deterministic-anchor minimum"}
    for rep in ("6", "10", "20", "30"):
        rows.append(f"{rep} ({notes[rep]}) & {grid[rep].get('0.8', '--')} & {grid[rep].get('0.5', '--')} \\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    (TABLES / "power_note.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")

    print(f"Wrote 6 fragments to {TABLES.relative_to(ROOT)} and {CI_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
