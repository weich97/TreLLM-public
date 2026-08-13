"""B7: open-loop vs closed-loop decomposition of the LLM reordering (cache replay).

The closed-loop E0->E1 reordering mixes a *mechanical* execution effect (same
intended targets, different fills) with a *feedback/adaptation* effect (the LLM
re-decides under E1's portfolio state). This harness isolates the mechanical part
by replaying each LLM's E0 decision sequence under E1 execution (open loop, no
re-decision), on the reproducible direct board (deepseek-v4-pro + glm-5 direct +
7 classical), high-vol, N=2, 12 steps, 10 seeds.

E0 and closed-loop E1 LLM decisions replay from the B1 cache (no live calls);
the open-loop E1 leg makes no LLM calls at all. Deterministic baselines emit
identical E0/E1 targets (verified separately), so only the two LLMs need the
open-loop leg. Writes docs/results/execution_sensitivity_b7_openloop/.
"""
from __future__ import annotations

import csv
import statistics as st
from pathlib import Path

from scipy.stats import kendalltau

from tradearena.agents.strategy import SignalWeightedStrategy
from tradearena.factory import build_default_system

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/results/execution_sensitivity_b7_openloop"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / "outputs/llm_cache/b1_horizon"

HV = {"synthetic_volatility_scale": 2.25, "synthetic_trend_scale": 0.65, "synthetic_macro_scale": 1.4}
SYMS = ("SYN", "ALT")
SEEDS = [100 + s for s in range(1, 11)]
CLS = ["buy-and-hold", "signal-weighted", "naive-momentum", "mean-reversion",
       "risk-parity", "minimum-variance", "random"]
# agent id -> (analyst_name, llm_model, cache_slug)
LLMS = {
    "deepseek:deepseek-v4-pro": ("deepseek-llm", "deepseek-v4-pro", "deepseek_deepseek_v4_pro"),
    "glm:glm-5": ("glm-llm", "glm-5", "glm_glm_5"),
}


class RecordingStrategy:
    """Wrap an inner strategy; record the decisions emitted at each step."""

    name = "recording"

    def __init__(self, inner):
        self.inner = inner
        self.records: list[list] = []

    def decide(self, snapshot, signals, portfolio, memory):
        decisions = self.inner.decide(snapshot, signals, portfolio, memory)
        self.records.append(list(decisions))
        return decisions


class ReplayStrategy:
    """Emit a previously recorded decision sequence, ignoring live inputs."""

    name = "replay"

    def __init__(self, records):
        self.records = records
        self.i = 0

    def decide(self, snapshot, signals, portfolio, memory):
        out = self.records[self.i] if self.i < len(self.records) else []
        self.i += 1
        return out


def _run(strategy_override, analysts, level_mode, model=None, slug=None):
    kw = dict(HV)
    kw["execution_mode"] = level_mode
    if model is not None:
        kw.update({"llm_model": model, "llm_cache_path": str(CACHE / f"{slug}.jsonl"),
                   "llm_mask_timestamps": True, "llm_use_risk_feedback": True,
                   "llm_risk_feedback_mode": "true"})
    return build_default_system(name="b7", symbols=SYMS, periods=12, seed=_run.seed,
                                risk_name="max-position", strategy_override=strategy_override,
                                analyst_names=analysts, **kw)


def llm_legs(analyst, model, slug, seed):
    """Return (E0 sharpe, E1 closed-loop sharpe, E1 open-loop sharpe) for one LLM/seed."""
    _run.seed = seed
    # E0 closed-loop: capture the decision sequence (LLM replays from cache)
    rec = RecordingStrategy(SignalWeightedStrategy())
    _, m_e0 = _run(rec, (analyst,), "ideal", model, slug).run()
    # E1 closed-loop: LLM re-decides under E1 (cache replay)
    _, m_e1c = _run(RecordingStrategy(SignalWeightedStrategy()), (analyst,), "realistic", model, slug).run()
    # E1 open-loop: replay the E0 decisions under E1, no analyst, no re-decision
    _, m_e1o = _run(ReplayStrategy(rec.records), (), "realistic").run()
    return m_e0.get("sharpe", 0.0), m_e1c.get("sharpe", 0.0), m_e1o.get("sharpe", 0.0)


def cls_legs(agent, seed):
    """Deterministic baseline E0 and E1 sharpe (open-loop == closed-loop)."""
    kw0 = dict(HV); kw0["execution_mode"] = "ideal"
    kw1 = dict(HV); kw1["execution_mode"] = "realistic"
    common = {"symbols": SYMS, "periods": 12, "seed": seed, "risk_name": "max-position",
              "strategy_name": agent, "analyst_names": ("momentum", "macro-news")}
    _, m0 = build_default_system(name="b7c", **common, **kw0).run()
    _, m1 = build_default_system(name="b7c", **common, **kw1).run()
    return m0.get("sharpe", 0.0), m1.get("sharpe", 0.0)


def main() -> int:
    e0, e1_closed, e1_open = {}, {}, {}
    for agent in CLS:
        s0 = [cls_legs(agent, s) for s in SEEDS]
        e0[agent] = st.mean(x[0] for x in s0)
        e1_closed[agent] = st.mean(x[1] for x in s0)
        e1_open[agent] = e1_closed[agent]  # baselines do not adapt
        print(f"  cls {agent:18} E0={e0[agent]:.3f} E1={e1_closed[agent]:.3f}", flush=True)
    for agent, (analyst, model, slug) in LLMS.items():
        legs = [llm_legs(analyst, model, slug, s) for s in SEEDS]
        e0[agent] = st.mean(x[0] for x in legs)
        e1_closed[agent] = st.mean(x[1] for x in legs)
        e1_open[agent] = st.mean(x[2] for x in legs)
        print(f"  LLM {agent:24} E0={e0[agent]:.3f} E1c={e1_closed[agent]:.3f} E1o={e1_open[agent]:.3f}", flush=True)

    board = CLS + list(LLMS)
    r_e0 = [e0[a] for a in board]
    tau_closed = kendalltau(r_e0, [e1_closed[a] for a in board], variant="b")[0]
    tau_open = kendalltau(r_e0, [e1_open[a] for a in board], variant="b")[0]

    rows = [{"board": "9-agent direct", "leg": "closed_loop", "tau_b_E0_E1": round(float(tau_closed), 3)},
            {"board": "9-agent direct", "leg": "open_loop_mechanical", "tau_b_E0_E1": round(float(tau_open), 3)}]
    with (OUT / "b7_openloop_tau.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["board", "leg", "tau_b_E0_E1"])
        w.writeheader()
        w.writerows(rows)
    # per-agent legs for the appendix
    with (OUT / "b7_per_agent.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["agent", "e0_sharpe", "e1_closed_sharpe", "e1_open_sharpe"])
        w.writeheader()
        for a in board:
            w.writerow({"agent": a, "e0_sharpe": round(e0[a], 4),
                        "e1_closed_sharpe": round(e1_closed[a], 4), "e1_open_sharpe": round(e1_open[a], 4)})
    print(f"\nclosed-loop E0->E1 tau_b = {tau_closed:.3f}  (mechanical + adaptation)")
    print(f"open-loop  E0->E1 tau_b = {tau_open:.3f}  (mechanical only)")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
