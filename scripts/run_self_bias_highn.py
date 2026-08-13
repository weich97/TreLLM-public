"""Higher-n self-audit-bias run (audit study, higher-n version) -- ZERO provider cost.

The n=30 self-bias is only suggestive (glm self-leniency +0.13, p~0.20). To make
it higher-powered we scale the two DIRECT-API models -- deepseek-v4-pro and glm-5,
both free -- to n=120 and have them audit each other's task sets, giving a
powered 2x2 self-vs-cross test at no provider cost (glm auditing for free is the
whole trick). gemini/claude (Poe) stay at n=30 as the strong-auditor context;
gpt-5.5 is excluded (temporarily unavailable).

Everything is resumable: generate_audit_tasks re-runs hit the LLM cache, and
run_audit_eval checkpoints per (model, task). Robust against parent-process
teardown: single-instance lockfile + launched detached (pythonw) behind a
Scheduled Task that relaunches every 10 min; a relaunch just resumes. Self-
deletes its task + lock on completion. Logs to a file (pythonw has no console).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = 120
BASE_SEED = "1000"  # same market seeds across producers -> matched audit difficulty
PRODUCERS = [
    {"agent": "deepseek:deepseek-v4-pro", "dir": "deepseek_v4_pro"},
    {"agent": "glm:glm-5", "dir": "glm_5_direct"},
]
AUDITORS = "deepseek:deepseek-v4-pro,glm:glm-5"  # both direct/free
LOCK = ROOT / "outputs/self_bias_highn.lock"
STATUS = ROOT / "RUN_STATUS_SELFBIAS.md"
LOG = ROOT / "outputs/self_bias_highn.log"
TASK_NAME = "TreLLM_selfbias_highn"


def _another_instance_alive() -> bool:
    if not LOCK.exists():
        return False
    try:
        old = int(LOCK.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return False
    if old == os.getpid():
        return False
    out = subprocess.run(
        ["tasklist", "/FI", f"PID eq {old}", "/FO", "CSV", "/NH"], capture_output=True, text=True
    ).stdout
    return "python" in out.lower()


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    for line in (ROOT / "APIkey.txt").read_text(encoding="utf-8").splitlines():
        low = line.lower()
        if "deepseek" in low and (m := re.search(r"sk-[A-Za-z0-9]{20,}", line)):
            env["DEEPSEEK_API_KEY"] = m.group(0)
        elif "glm" in low and (m := re.search(r"[0-9a-fA-F]{32}\.[A-Za-z0-9]+", line)):
            env["GLM_API_KEY"] = m.group(0)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def count(d: str) -> int:
    p = ROOT / f"outputs/audit_self/{d}/tasks"
    return sum(1 for x in p.iterdir() if x.is_dir()) if p.exists() else 0


def say(msg: str) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def status(phase: str) -> None:
    body = [f"# Audit-study self-bias higher-n — _{datetime.now():%Y-%m-%d %H:%M:%S}_\n",
            f"target **n={TARGET}** per producer · deepseek+glm direct (free) · 断了自动续\n",
            f"**phase: {phase}**\n"]
    for p in PRODUCERS:
        n = count(p["dir"])
        bar = "#" * int(20 * min(n, TARGET) / TARGET)
        body.append(f"- `[{bar:<20}]` {p['dir']}: **{n}/{TARGET}** tasks")
    STATUS.write_text("\n".join(body) + "\n", encoding="utf-8-sig")


def main() -> int:
    if _another_instance_alive():
        return 0
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    env = load_env()
    say(f"start (target n={TARGET}, free deepseek+glm)")

    # Phase 1: extend both producers to n=120 (cache-resumes the first 30).
    for p in PRODUCERS:
        status(f"gen {p['dir']}")
        say(f"gen {p['dir']} -> {TARGET} (have {count(p['dir'])})")
        subprocess.run(
            [sys.executable, "scripts/generate_audit_tasks.py", "--agent", p["agent"],
             "--tasks", str(TARGET), "--periods", "24", "--base-seed", BASE_SEED,
             "--cache-dir", "outputs/llm_cache/audit_tasks",
             "--output-dir", f"outputs/audit_self/{p['dir']}"],
            cwd=str(ROOT), env=env, check=False,
            stdout=(ROOT / f"outputs/audit_self/{p['dir']}/gen.log").open("a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        say(f"gen {p['dir']} done -> {count(p['dir'])} tasks")

    # Phase 2: deepseek + glm audit both extended sets (checkpoint-resumes).
    for p in PRODUCERS:
        status(f"audit {p['dir']}")
        say(f"audit {p['dir']} with deepseek+glm")
        subprocess.run(
            [sys.executable, "scripts/run_audit_eval.py",
             "--tasks-dir", f"outputs/audit_self/{p['dir']}", "--models", AUDITORS,
             "--output-dir", f"outputs/audit_matrix/{p['dir']}",
             "--cache-dir", "outputs/llm_cache/audit_eval"],
            cwd=str(ROOT), env=env, check=False,
            stdout=(ROOT / f"outputs/audit_self/{p['dir']}/audit_highn.log").open("a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )

    # Phase 3: rebuild the matrix CSV.
    status("rebuild matrix")
    subprocess.run([sys.executable, "scripts/build_self_bias_matrix.py"],
                   cwd=str(ROOT), env=env, check=False,
                   stdout=LOG.open("a", encoding="utf-8"), stderr=subprocess.STDOUT)

    status("DONE")
    say("ALL DONE — deleting scheduled task")
    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], capture_output=True)
    try:
        LOCK.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
