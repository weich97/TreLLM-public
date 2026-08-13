"""Fit and render the graded-ambiguity dose response (audit study).

Pools three data sources per (domain, model): the matched-pair endpoints
(clean arm = gap 0; confounded arm = the natural per-item gap) and the graded
arm (controlled gaps). Reports per-gap strict violation-commitment recall with
95% Wilson intervals, and a within-source Monte Carlo permutation trend test:
a Spearman-type statistic between the rank of the gap and the hit, with gap
labels permuted within each source task over 10,000 random draws (not an exact
enumeration), so items act as their own controls.

Outputs:
- docs/results/finaudit/dose_response.csv
- figures/finaudit/dose_response.pdf (two panels: trading, tool-use)
"""
from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "docs/results/finaudit/dose_response.csv"
OUT_FIG = ROOT / "figures/finaudit/dose_response.pdf"

LABEL = {
    "deepseek:deepseek-v4-pro": "deepseek-v4-pro$^\\dagger$",
    "glm:glm-5": "glm-5$^\\dagger$",
    "poe:claude-opus-4.7": "claude-opus-4.7",
    "poe:gemini-3.1-pro": "gemini-3.1-pro",
}
DIRECT = ["deepseek:deepseek-v4-pro", "glm:glm-5"]
FRONTIER = ["poe:claude-opus-4.7", "poe:gemini-3.1-pro"]


def wilson(h: int, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    z = 1.96
    p = h / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def collect(domain: str) -> dict[str, list[tuple[str, float, bool, str]]]:
    """model -> list of (source_id, gap, hit, arm) item observations."""
    obs: dict[str, list[tuple[str, float, bool, str]]] = defaultdict(list)
    if domain == "trading":
        vkind = "unclipped_position"
        pair_sets = [(p, f"outputs/audit_pairs/{p}/ground_truth.jsonl",
                      f"outputs/audit_pairs_eval_v2/{p}/audit_eval_results.jsonl") for p in
                     ("deepseek_v4_pro", "glm_5_direct")]
        graded_sets = [(p, f"outputs/audit_graded/{p}/ground_truth.jsonl",
                        f"outputs/audit_graded_eval_v2/{p}/audit_eval_results.jsonl") for p in
                       ("deepseek_v4_pro", "glm_5_direct")]
        endpoint_gap = lambda d: 0.8 - float(d["original_target_weight"])
    else:
        # tool-use gaps are dimension-scaled: everything is a fraction of the
        # approved value, so USD, instance, GB, and recipient sources share
        # one dose axis.
        vkind = "over_limit_call"
        pair_sets = [("tooluse", "outputs/toolaudit_pairs/ground_truth.jsonl",
                      "outputs/toolaudit_pairs_eval_v2/toolaudit_eval_results.jsonl")]
        graded_sets = [("tooluse", "outputs/audit_graded_v2/tooluse/ground_truth.jsonl",
                        "outputs/audit_graded_eval_v2/tooluse/toolaudit_eval_results.jsonl")]
        endpoint_gap = lambda d: (float(d["approved"]) - float(d["original_requested"])) / float(d["approved"])

    for producer, gt_path, res_path in pair_sets + graded_sets:
        gt = {g["task_id"]: g for g in _load_jsonl(ROOT / gt_path)}
        for r in _load_jsonl(ROOT / res_path):
            g = gt.get(r["task_id"])
            if not g or g["kind"] != vkind or int(r.get("sample", 0)) != 0:
                continue
            amb = g["detail"].get("ambiguity", "")
            if amb == "clean":
                gap = 0.0
            elif amb == "confounded":
                gap = endpoint_gap(g["detail"])
            elif amb == "graded":
                detail = g["detail"]
                gap = float(detail["gap_frac"]) if "gap_frac" in detail else float(detail["gap"])
            else:
                continue
            hit = any(str(f.get("kind")) == vkind and int(f.get("step_index", -9)) == int(g["step_index"])
                      for f in r["findings"])
            # source ids are producer-prefixed: pair_id namespaces repeat
            # across producer dirs and must not merge into one cluster.
            obs[r["model"]].append((f"{producer}:{g['detail']['pair_id']}", gap, hit, amb))
    return obs


def trend_test(items: list[tuple[str, float, bool]], draws: int = 10000) -> tuple[float, float]:
    """Within-source permutation test of the gap-hit association.

    Statistic: covariance between rank(gap) and hit summed over sources.
    Gap labels are permuted within each source task, so the null keeps each
    item's marginal hit rate and tests only the ordering.
    """
    by_src: dict[str, list[tuple[float, bool]]] = defaultdict(list)
    for src, gap, hit in items:
        by_src[src].append((gap, hit))
    usable = {s: v for s, v in by_src.items() if len(v) >= 2 and len({g for g, _ in v}) >= 2}
    if not usable:
        return 0.0, 1.0

    def stat(assign: dict[str, list[tuple[float, bool]]]) -> float:
        """Covariance between the *rank* of the gap and the hit, summed over sources.

        Ranks rather than raw magnitudes, because the doses are deliberately
        spaced non-uniformly (a roughly geometric ladder plus a natural
        endpoint), so a raw-magnitude covariance tests linearity in the gap
        while the question is monotonicity. The choice is not cosmetic: on the
        tool-use deepseek-v4-pro cell the raw-magnitude statistic gives
        p = 0.114 and the rank statistic p = 0.032, so the released CSV records
        which one produced it.
        """

        total = 0.0
        for v in assign.values():
            gaps = [g for g, _ in v]
            order = sorted(range(len(gaps)), key=lambda i: gaps[i])
            ranks = [0.0] * len(gaps)
            for position, index in enumerate(order):
                ranks[index] = float(position + 1)
            hits = [1.0 if h else 0.0 for _, h in v]
            mr, mh = sum(ranks) / len(ranks), sum(hits) / len(hits)
            total += sum((r - mr) * (h - mh) for r, h in zip(ranks, hits))
        return total

    observed = stat(usable)
    rng = random.Random(20260716)
    worse = 0
    for _ in range(draws):
        perm: dict[str, list[tuple[float, bool]]] = {}
        for s, v in usable.items():
            gaps = [g for g, _ in v]
            rng.shuffle(gaps)
            perm[s] = list(zip(gaps, [h for _, h in v]))
        if abs(stat(perm)) >= abs(observed):
            worse += 1
    return observed, (worse + 1) / (draws + 1)


def cliff_test(items: list[tuple[str, float, bool]], small_gap: float) -> tuple[int, int, float]:
    """Within-source McNemar of clean (gap 0) vs the smallest graded gap.

    The complementary lens to the linear trend: a cliff-shaped model fails as
    soon as ANY competing reading exists, which a slope statistic dilutes.
    Returns (b, c, p) with b = clean-only hits, c = small-gap-only hits.
    """
    key = round(small_gap, 6)
    by_src: dict[str, dict[float, bool]] = defaultdict(dict)
    for src, gap, hit in items:
        by_src[src][round(gap, 6)] = hit
    b = c = 0
    for gaps in by_src.values():
        if 0.0 in gaps and key in gaps:
            b += gaps[0.0] and not gaps[key]
            c += gaps[key] and not gaps[0.0]
    n = b + c
    if n == 0:
        return 0, 0, 1.0
    k = min(b, c)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n)
    return b, c, p


def main() -> int:
    rows_out = []
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.1))
    for ax, domain, title in ((axes[0], "trading", "Trading"), (axes[1], "tooluse", "Tool-use")):
        obs = collect(domain)
        for model in DIRECT + FRONTIER:
            items = obs.get(model, [])
            if not items:
                continue
            # clean/graded arms bin by their exact controlled gap; the
            # confounded endpoints (natural per-item gaps) pool into one
            # rightmost point regardless of gap magnitude.
            bins: dict[float, list[bool]] = defaultdict(list)
            end_hits: list[bool] = []
            end_gap_sum = 0.0
            for _, gap, hit, arm in items:
                if arm == "confounded":
                    end_hits.append(hit)
                    end_gap_sum += gap
                else:
                    bins[round(gap, 4)].append(hit)
            xs, ys, los, his, ns = [], [], [], [], []
            for g in sorted(bins):
                h, n = sum(bins[g]), len(bins[g])
                xs.append(g); ys.append(h / n)
                lo, hi = wilson(h, n)
                los.append(lo); his.append(hi); ns.append(n)
            statv, p = trend_test([(s, g, h) for s, g, h, _ in items])
            style: dict[str, Any] = (
                {"marker": "o", "lw": 1.6} if model in DIRECT
                else {"marker": "s", "lw": 1.2, "ls": "--"}
            )
            yerr = [[max(0.0, y - lo) for y, lo in zip(ys, los)],
                    [max(0.0, hi - y) for y, hi in zip(ys, his)]]
            line = ax.errorbar(xs, ys, yerr=yerr, capsize=2.5, label=LABEL[model], **style)
            if end_hits:
                # confounded endpoints: hollow marker at the mean natural gap
                h, n = sum(end_hits), len(end_hits)
                ge, ye = end_gap_sum / n, h / n
                lo, hi = wilson(h, n)
                color = line.lines[0].get_color()
                ax.errorbar([ge], [ye], yerr=[[max(0.0, ye - lo)], [max(0.0, hi - ye)]],
                            capsize=2.5, marker=style["marker"], ls="none",
                            markerfacecolor="none", color=color)
                xs.append(ge); ys.append(ye)
                los.append(lo); his.append(hi); ns.append(n)
            for x, y, n in zip(xs, ys, ns):
                rows_out.append({"domain": domain, "model": model, "gap": x,
                                 "commit_recall": round(y, 3), "n": n,
                                 "wilson_lo": round(wilson(round(y * n), n)[0], 3),
                                 "wilson_hi": round(wilson(round(y * n), n)[1], 3),
                                 "trend_stat_rank_cov": round(statv, 3), "trend_p": f"{p:.4f}"})
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("ambiguity gap (approved $-$ recorded intent)" if domain == "trading"
                      else "ambiguity gap (fraction of approved value)")
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.25, lw=0.4)
    axes[0].set_ylabel("violation-commitment recall")
    axes[0].legend(fontsize=7, loc="lower left", framealpha=0.9)
    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, bbox_inches="tight")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0]))
        w.writeheader(); w.writerows(rows_out)
    print(f"wrote {OUT_FIG.relative_to(ROOT)} and {OUT_CSV.relative_to(ROOT)}")
    for domain, small in (("trading", 0.05), ("tooluse", 0.03125)):
        obs = collect(domain)
        for model in DIRECT + FRONTIER:
            items4 = obs.get(model, [])
            if not items4:
                continue
            items3 = [(s, g, h) for s, g, h, _ in items4]
            _, trend_p = trend_test(items3)
            b, c, cliff_p = cliff_test(items3, small)
            print(f"{domain:8s}{LABEL[model]:26s} trend_p={trend_p:.4f}  "
                  f"cliff(clean vs g{small}): b={b} c={c} p={cliff_p:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
