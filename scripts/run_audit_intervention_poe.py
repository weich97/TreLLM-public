"""Prompt-intervention experiment -- STRONG-model arm (audit study), Poe.

Companion to run_audit_intervention.py (the free deepseek+glm arm). Here the two
routed strong auditors -- gemini-3.1-pro and claude-opus-4.7 -- audit the same
n=120 producer sets under both prompts (default / constraint), so the unified
4-model intervention table can answer: does the explicit constraint-check prompt
*help* the weak auditors without *hurting* the strong ones? That turns the fix
into an actionable default-prompt recommendation.

Writes to a SEPARATE tree (outputs/audit_intervention_poe) so it never races the
free arm's results.jsonl. Uses the funded Poe key; run_audit_eval skips a task on
a provider 402 (does not crash) and checkpoints per (model, task), so when the
budget is topped up a relaunch resumes. Robust: lockfile + detached + Scheduled
Task; self-deletes on completion. build_intervention_table.py merges both arms.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCERS = ["deepseek_v4_pro", "glm_5_direct"]   # same on-disk n=120 sets as the free arm
VARIANTS = ["", "constraint"]
MODELS = "poe:gemini-3.1-pro,poe:claude-opus-4.7"  # strong routed auditors
OUTBASE = ROOT / "outputs/audit_intervention_poe"
LOCK = ROOT / "outputs/audit_intervention_poe.lock"
STATUS = ROOT / "RUN_STATUS_INTERVENTION_POE.md"
LOG = ROOT / "outputs/audit_intervention_poe.log"
TASK_NAME = "TreLLM_audit_intervention_poe"

for line in (ROOT / "APIkey.txt").read_text(encoding="utf-8").splitlines():
    if "poe" in line.lower() and (m := re.search(r"sk-poe-[A-Za-z0-9_\-]+", line)):
        os.environ.setdefault("POE_API_KEY", m.group(0))  # first = funded
        break
os.environ.setdefault("PYTHONPATH", str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("run_audit_eval", ROOT / "scripts" / "run_audit_eval.py")
assert _spec and _spec.loader
run_audit_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_audit_eval)


def say(msg: str) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def _another_instance_alive() -> bool:
    if not LOCK.exists():
        return False
    try:
        old = int(LOCK.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return False
    if old == os.getpid():
        return False
    out = subprocess.run(["tasklist", "/FI", f"PID eq {old}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return "python" in out.lower()


def done_count(producer: str, variant: str) -> int:
    rp = OUTBASE / f"{producer}_{variant or 'default'}" / "audit_eval_results.jsonl"
    return sum(1 for _ in rp.open(encoding="utf-8")) if rp.exists() else 0


def main() -> int:
    if _another_instance_alive():
        return 0
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    key = os.environ.get("POE_API_KEY", "")
    say(f"start (gemini+claude x {{default,constraint}}, poe key {key[:12]}...)")
    target = len(PRODUCERS) * len(VARIANTS) * 2 * 120  # 2 models * 120 tasks each
    for producer in PRODUCERS:
        for variant in VARIANTS:
            label = f"{producer}/{variant or 'default'}"
            total = sum(done_count(p, v) for p in PRODUCERS for v in VARIANTS)
            STATUS.write_text(
                f"# Audit-study intervention STRONG arm (Poe) — _{datetime.now():%Y-%m-%d %H:%M:%S}_\n\n"
                f"gemini+claude · running **{label}** · ~**{total}/{target}** audits done\n"
                f"_Poe 干了会跳过该任务并续跑;充值后自动补_\n",
                encoding="utf-8-sig")
            say(f"audit {label} (have {done_count(producer, variant)})")
            run_audit_eval.main([
                "--tasks-dir", f"outputs/audit_self/{producer}",
                "--models", MODELS,
                "--output-dir", str((OUTBASE / f"{producer}_{variant or 'default'}").relative_to(ROOT)),
                "--cache-dir", "outputs/llm_cache/audit_eval",
                "--prompt-variant", variant,
            ])

    # only tear down if every cell is actually complete (else leave the task to resume after a top-up)
    complete = all(done_count(p, v) >= 2 * 120 for p in PRODUCERS for v in VARIANTS)
    if complete:
        STATUS.write_text(
            f"# Audit-study intervention STRONG arm (Poe) — DONE _{datetime.now():%Y-%m-%d %H:%M:%S}_\n\n"
            f"run build_intervention_table.py to merge with the free arm\n", encoding="utf-8-sig")
        say("ALL CELLS COMPLETE — deleting scheduled task")
        subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], capture_output=True)
    else:
        say("incomplete (likely Poe budget) — leaving scheduled task to resume after top-up")
    try:
        LOCK.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
