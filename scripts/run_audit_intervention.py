"""Prompt-intervention experiment (audit study): does explicit constraint-
verification prompting recover weak auditors' L1 recall?

The difficulty inversion says the weak direct models (deepseek, glm) miss the
"easy" L1 defect -- an approved value exceeding a stated cap. Is that because
they *cannot* verify a stated constraint, or because they *do not* by default?
We re-audit the on-disk n=120 deepseek + glm producer task sets with both weak
models under two prompts -- default and a `constraint` variant that tells the
auditor to check each numeric limit against the actual values -- and compare L1
recall. A recovery means the miss is a default-behaviour failure with a cheap
fix (prompting / a deterministic pre-check): the actionable contribution.

Free (deepseek + glm direct). The default condition replays from the audit cache;
only the constraint condition makes new calls. Robust: single-instance lockfile
+ launched detached behind a Scheduled Task; run_audit_eval checkpoints per
(model, task) so a relaunch just resumes. Self-deletes its task + lock on done.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCERS = ["deepseek_v4_pro", "glm_5_direct"]   # on-disk n=120 sets
VARIANTS = ["", "constraint"]                       # default vs intervention
MODELS = "deepseek:deepseek-v4-pro,glm:glm-5"       # the two weak DIRECT (free) auditors
OUTBASE = ROOT / "outputs/audit_intervention"
RESULT = ROOT / "docs/results/finaudit/intervention.csv"
LOCK = ROOT / "outputs/audit_intervention.lock"
STATUS = ROOT / "RUN_STATUS_INTERVENTION.md"
LOG = ROOT / "outputs/audit_intervention.log"
TASK_NAME = "TreLLM_audit_intervention"

for line in (ROOT / "APIkey.txt").read_text(encoding="utf-8").splitlines():
    low = line.lower()
    if "deepseek" in low and (m := re.search(r"sk-[A-Za-z0-9]{20,}", line)):
        os.environ["DEEPSEEK_API_KEY"] = m.group(0)
    elif "glm" in low and (m := re.search(r"[0-9a-fA-F]{32}\.[A-Za-z0-9]+", line)):
        os.environ["GLM_API_KEY"] = m.group(0)
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


def outdir(producer: str, variant: str) -> Path:
    return OUTBASE / f"{producer}_{variant or 'default'}"


def compare() -> None:
    """Pool both producers; per (auditor, condition, difficulty) recall = TP / n."""
    agg: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for producer in PRODUCERS:
        for variant in VARIANTS:
            rp = outdir(producer, variant) / "audit_eval_results.jsonl"
            if not rp.exists():
                continue
            cond = "constraint" if variant else "default"
            for line in rp.open(encoding="utf-8"):
                r = json.loads(line)
                agg[(r["model"], cond, r["difficulty"])].append(int(r["true_positives"]))
                agg[(r["model"], cond, "ALL")].append(int(r["true_positives"]))

    RESULT.parent.mkdir(parents=True, exist_ok=True)
    diffs = ["ALL", "L1", "L2", "L3"]
    with RESULT.open("w", encoding="utf-8", newline="") as fh:
        fh.write("auditor,condition," + ",".join(f"{d}_recall,{d}_n" for d in diffs) + "\n")
        for model in ("deepseek:deepseek-v4-pro", "glm:glm-5"):
            for cond in ("default", "constraint"):
                cells = []
                for d in diffs:
                    v = agg.get((model, cond, d), [])
                    cells.append(f"{(sum(v)/len(v) if v else 0):.3f},{len(v)}")
                fh.write(f"{model},{cond}," + ",".join(cells) + "\n")
    say(f"wrote {RESULT.relative_to(ROOT)}")

    # headline: L1 default -> constraint per weak auditor
    for model in ("deepseek:deepseek-v4-pro", "glm:glm-5"):
        d = agg.get((model, "default", "L1"), [])
        c = agg.get((model, "constraint", "L1"), [])
        if d and c:
            say(f"L1 {model}: default {sum(d)/len(d):.3f} (n={len(d)}) "
                f"-> constraint {sum(c)/len(c):.3f} (n={len(c)})")


def main() -> int:
    if _another_instance_alive():
        return 0
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    say("start (deepseek+glm x {default,constraint}, free)")
    for producer in PRODUCERS:
        for variant in VARIANTS:
            label = f"{producer}/{variant or 'default'}"
            STATUS.write_text(
                f"# Audit-study prompt-intervention — _{datetime.now():%Y-%m-%d %H:%M:%S}_\n\n"
                f"running **{label}** (deepseek+glm, free; default=cache replay)\n",
                encoding="utf-8-sig")
            say(f"audit {label}")
            run_audit_eval.main([
                "--tasks-dir", f"outputs/audit_self/{producer}",
                "--models", MODELS,
                "--output-dir", str(outdir(producer, variant).relative_to(ROOT)),
                "--cache-dir", "outputs/llm_cache/audit_eval",
                "--prompt-variant", variant,
            ])
    compare()
    STATUS.write_text(
        f"# Audit-study prompt-intervention — DONE _{datetime.now():%Y-%m-%d %H:%M:%S}_\n\n"
        f"see `docs/results/finaudit/intervention.csv`\n", encoding="utf-8-sig")
    say("ALL DONE — deleting scheduled task")
    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], capture_output=True)
    try:
        LOCK.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
