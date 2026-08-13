"""Analyze the Airlock LLM-monitor triage results (E6).

Per model and tier: flag rate (clean = false-positive rate; semantic = the
detectable residue an LLM monitor can cover; freetext = the human-only floor;
authority = a content-visible-fault control), field-hit rate, and 95% Wilson
intervals on the semantic tier. Writes docs/results/live_readiness_e6/.
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from tradearena.evaluation.statistics import wilson_interval

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs/airlock_monitor/airlock_monitor_results.jsonl"
OUT_DIR = ROOT / "docs/results/live_readiness_e6"
TIERS = ("clean", "semantic", "freetext", "authority")
ORDER = ["poe:claude-opus-4.7", "poe:gemini-3.1-pro", "deepseek:deepseek-v4-pro", "glm:glm-5"]


def main() -> int:
    rows = [json.loads(x) for x in RESULTS.read_text(encoding="utf-8").splitlines() if x.strip()]
    agg: dict[tuple[str, str], list[int]] = collections.defaultdict(lambda: [0, 0, 0])  # flag, hit, n
    for r in rows:
        cell = agg[(r["model"], r["tier"])]
        cell[0] += int(bool(r["flagged"]))
        cell[1] += int(bool(r["field_hit"]))
        cell[2] += 1
    models = [m for m in ORDER if any((m, t) in agg for t in TIERS)]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "e6_monitor.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "tier", "flag_rate", "field_hit_rate", "n",
                    "wilson_low", "wilson_high"])
        for m in models:
            for t in TIERS:
                flag, hit, n = agg[(m, t)]
                if not n:
                    continue
                _pt, lo, hi = wilson_interval(flag, n)
                w.writerow([m, t, f"{flag / n:.3f}", f"{hit / n:.3f}", n,
                            f"{lo:.3f}", f"{hi:.3f}"])

    print(f"wrote {(OUT_DIR / 'e6_monitor.csv').relative_to(ROOT)}\n")
    header = f"{'model':26s}" + "".join(f"{t[:8]:>12s}" for t in TIERS)
    print(header + "   (flag rate; semantic=detection, clean=FPR, freetext=floor)")
    for m in models:
        cells = []
        for t in TIERS:
            flag, _hit, n = agg[(m, t)]
            cells.append(f"{flag}/{n}={flag / n:.0%}" if n else "-")
        print(f"{m:26s}" + "".join(f"{c:>12s}" for c in cells))
    # headline: semantic detection with Wilson, sorted
    print("\nsemantic-contradiction detection (the residue an LLM monitor can cover):")
    for m in models:
        flag, hit, n = agg[(m, "semantic")]
        _pt, lo, hi = wilson_interval(flag, n)
        print(f"  {m:26s} {flag}/{n} = {flag / n:.0%}  [{lo:.0%}, {hi:.0%}]  field-localized {hit}/{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
