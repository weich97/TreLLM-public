"""Combine the three-regime classical execution ladder into one ranking-movement
table for the v0.3 benchmark.

Reads the per-regime `execution_ladder_aggregate.csv` and
`execution_ladder_ranking_stability.csv` artifacts (calm from the canonical dir,
high_vol / jump_tail from the sibling dirs written by
`run_v03_execution_ladder.py --scenario ...`) and emits a compact per-regime,
per-comparison table with Kendall tau, top-3 Jaccard, the E0 winner, the
comparison winner, and whether the winner changed. This is the benchmark's OWN
deterministic evidence that execution assumptions move rankings -- complementing
the cited concurrent execution-sensitivity study and the direct-API LLM matrix
(which shows uniform compression without reorder on three well-separated models).
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/results"
REGIMES = {
    "calm": BASE / "v0_3_execution_ladder",
    "high_vol": BASE / "v0_3_execution_ladder_high_vol",
    "jump_tail": BASE / "v0_3_execution_ladder_jump_tail",
}
OUT = BASE / "v0_3_execution_ladder" / "ladder_reordering_by_regime.csv"


def _winner(agg_path: Path, level: str) -> tuple[str, float]:
    rows = [r for r in csv.DictReader(agg_path.open(encoding="utf-8"))
            if r["execution_level"] == level]
    rows.sort(key=lambda r: int(r["rank"]))
    return (rows[0]["agent"], float(rows[0]["sharpe_mean"])) if rows else ("", 0.0)


def main() -> int:
    out_rows: list[dict[str, str]] = []
    for regime, d in REGIMES.items():
        agg = d / "execution_ladder_aggregate.csv"
        stab = d / "execution_ladder_ranking_stability.csv"
        if not (agg.exists() and stab.exists()):
            continue
        e0_winner, e0_sharpe = _winner(agg, "E0")
        for s in csv.DictReader(stab.open(encoding="utf-8")):
            cmp_level = s["comparison_level"]
            cmp_winner, cmp_sharpe = _winner(agg, cmp_level)
            out_rows.append({
                "regime": regime,
                "scenario_id": s["scenario_id"],
                "baseline": s["baseline_level"],
                "comparison": cmp_level,
                "kendall_tau": f"{float(s['kendall_tau']):.3f}",
                "top3_jaccard": f"{float(s['top_k_jaccard']):.3f}",
                "e0_winner": e0_winner,
                "cmp_winner": cmp_winner,
                "winner_changed": "yes" if cmp_winner != e0_winner else "no",
                "e0_top_sharpe": f"{e0_sharpe:.2f}",
                "cmp_top_sharpe": f"{cmp_sharpe:.2f}",
            })

    fields = ["regime", "scenario_id", "baseline", "comparison", "kendall_tau",
              "top3_jaccard", "e0_winner", "cmp_winner", "winner_changed",
              "e0_top_sharpe", "cmp_top_sharpe"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {OUT.relative_to(ROOT)}  ({len(out_rows)} rows)")
    print(f"{'regime':10s}{'cmp':5s}{'tau':>7s}{'jac':>6s}  winner E0 -> cmp")
    for r in out_rows:
        flag = "  <-- WINNER FLIP" if r["winner_changed"] == "yes" else ""
        print(f"{r['regime']:10s}{r['comparison']:5s}{r['kendall_tau']:>7s}"
              f"{r['top3_jaccard']:>6s}  {r['e0_winner']} -> {r['cmp_winner']}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
