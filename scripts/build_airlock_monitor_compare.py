"""Cross-template comparison for the E6 monitor arm (Airlock live readiness).

Reads template A results (outputs/airlock_monitor/) and template B results
(outputs/airlock_monitor_b/), and writes per (model, tier): flag rate on each
template with 95% Wilson intervals, plus the pre-stated stability reading from
TEMPLATE_B_SPEC_2026-07-06.md -- a cell is "stable" when the two templates'
Wilson intervals overlap, "template-sensitive" otherwise, whichever direction
it moves. Outputs docs/results/live_readiness_e6/e6_cross_template.csv and a
per-template-B table e6_monitor_b.csv (same schema as e6_monitor.csv).
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from tradearena.evaluation.statistics import wilson_interval

ROOT = Path(__file__).resolve().parents[1]
RESULTS_A = ROOT / "outputs/airlock_monitor/airlock_monitor_results.jsonl"
RESULTS_B = ROOT / "outputs/airlock_monitor_b/airlock_monitor_results.jsonl"
OUT_DIR = ROOT / "docs/results/live_readiness_e6"
TIERS = ("clean", "semantic", "freetext", "authority")
ORDER = ["poe:claude-opus-4.7", "poe:gemini-3.1-pro", "deepseek:deepseek-v4-pro", "glm:glm-5"]


def _agg(path: Path) -> dict[tuple[str, str], list[int]]:
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    agg: dict[tuple[str, str], list[int]] = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        cell = agg[(r["model"], r["tier"])]
        cell[0] += int(bool(r["flagged"]))
        cell[1] += int(bool(r["field_hit"]))
        cell[2] += 1
    return agg


def main() -> int:
    a, b = _agg(RESULTS_A), _agg(RESULTS_B)
    models = [m for m in ORDER if any((m, t) in b for t in TIERS)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with (OUT_DIR / "e6_monitor_b.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "tier", "flag_rate", "field_hit_rate", "n", "wilson_low", "wilson_high"])
        for m in models:
            for t in TIERS:
                flag, hit, n = b[(m, t)]
                if not n:
                    continue
                _pt, lo, hi = wilson_interval(flag, n)
                w.writerow([m, t, f"{flag / n:.3f}", f"{hit / n:.3f}", n, f"{lo:.3f}", f"{hi:.3f}"])

    out_rows = []
    for m in models:
        for t in TIERS:
            fa, _ha, na = a[(m, t)]
            fb, _hb, nb = b[(m, t)]
            if not na or not nb:
                continue
            _p, alo, ahi = wilson_interval(fa, na)
            _p, blo, bhi = wilson_interval(fb, nb)
            overlap = not (ahi < blo or bhi < alo)
            out_rows.append({
                "model": m, "tier": t,
                "rate_a": f"{fa / na:.3f}", "a_low": f"{alo:.3f}", "a_high": f"{ahi:.3f}",
                "rate_b": f"{fb / nb:.3f}", "b_low": f"{blo:.3f}", "b_high": f"{bhi:.3f}",
                "n_a": na, "n_b": nb,
                "reading": "stable" if overlap else "template-sensitive",
            })
    with (OUT_DIR / "e6_cross_template.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)

    print(f"wrote {(OUT_DIR / 'e6_cross_template.csv').relative_to(ROOT)}")
    print(f"{'model':26s}{'tier':10s}{'A':>7s}{'B':>7s}  reading")
    for r in out_rows:
        print(f"{r['model']:26s}{r['tier']:10s}{r['rate_a']:>7s}{r['rate_b']:>7s}  {r['reading']}")
    sensitive = [r for r in out_rows if r["reading"] == "template-sensitive"]
    print(f"\ntemplate-sensitive cells: {len(sensitive)}/{len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
