"""Run the paired ambiguity experiments (audit study) across all four auditors.

Phase 1: tool-use pairs   (outputs/toolaudit_pairs    -> outputs/toolaudit_pairs_eval)
Phase 2: trading pairs    (outputs/audit_pairs/<p>    -> outputs/audit_pairs_eval/<p>)
Phase 3: rebuild the paired-analysis CSVs.

Auditors: deepseek + glm (direct, free) first, then claude-opus-4.7 + gemini
(Poe). Trading base variants reuse the default-cell response cache, so only the
edited siblings cost anything. Both runners checkpoint per (model, task), so a
relaunch resumes; single-instance lockfile + a Scheduled Task that relaunches
every 10 min make it survive session teardown. Self-deletes task + lock when
done. Logs to a file (pythonw has no console).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = "deepseek:deepseek-v4-pro,glm:glm-5,poe:claude-opus-4.7,poe:gemini-3.1-pro"
PRODUCERS = ["deepseek_v4_pro", "glm_5_direct"]
LOCK = ROOT / "outputs/paired_experiments.lock"
STATUS = ROOT / "RUN_STATUS_PAIRED.md"
LOG = ROOT / "outputs/paired_experiments.log"
TASK_NAME = "TreLLM_paired_exps"


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


POE_FAILOVER_FLAG = ROOT / "outputs/paired_poe_failover.flag"


def _poe_exhausted() -> bool:
    """A burst of 402s in the recent log means the active key ran dry."""
    if POE_FAILOVER_FLAG.exists():
        return True
    if not LOG.exists():
        return False
    tail = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
    if sum("402" in line for line in tail) >= 3:
        POE_FAILOVER_FLAG.write_text("switched", encoding="utf-8")  # one-way toggle
        say("poe key exhausted (402 burst) -> failing over to newest backup key")
        return True
    return False


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    poe_keys: list[str] = []
    for line in (ROOT / "APIkey.txt").read_text(encoding="utf-8").splitlines():
        low = line.lower()
        if "poe" in low and (m := re.search(r"sk-poe-[A-Za-z0-9_\-]{20,}", line)):
            poe_keys.append(m.group(0))  # file order; last = newest backup
        elif "deepseek" in low and (m := re.search(r"sk-[A-Za-z0-9]{20,}", line)):
            env["DEEPSEEK_API_KEY"] = m.group(0)
        elif "glm" in low and (m := re.search(r"[0-9a-fA-F]{32}\.[A-Za-z0-9]+", line)):
            env["GLM_API_KEY"] = m.group(0)
    if poe_keys:
        env["POE_API_KEY"] = poe_keys[-1] if (len(poe_keys) > 1 and _poe_exhausted()) else poe_keys[0]
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def done_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def say(msg: str) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def status(phase: str) -> None:
    tool = done_rows(ROOT / "outputs/toolaudit_pairs_eval/toolaudit_eval_results.jsonl")
    trade = {p: done_rows(ROOT / f"outputs/audit_pairs_eval/{p}/audit_eval_results.jsonl")
             for p in PRODUCERS}
    body = [f"# Audit-study paired ambiguity experiments — _{datetime.now():%Y-%m-%d %H:%M:%S}_\n",
            "4 auditors (deepseek/glm direct + claude-opus-4.7/gemini Poe) · 断了自动续\n",
            f"**phase: {phase}**\n",
            f"- tool-use pairs: **{tool}/320** results",
            f"- trading pairs deepseek-set: **{trade['deepseek_v4_pro']}/240** results (base 半数走缓存)",
            f"- trading pairs glm-set: **{trade['glm_5_direct']}/240** results (base 半数走缓存)"]
    STATUS.write_text("\n".join(body) + "\n", encoding="utf-8-sig")


def run_logged(args: list[str], env: dict[str, str]) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        subprocess.run(args, cwd=str(ROOT), env=env, check=False, stdout=fh, stderr=subprocess.STDOUT)


def main() -> int:
    if _another_instance_alive():
        return 0
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    env = load_env()
    say("start paired experiments (tool-use + trading, 4 auditors)")

    status("tool-use pairs")
    run_logged([sys.executable, "scripts/run_toolaudit_eval.py",
                "--tasks-dir", "outputs/toolaudit_pairs",
                "--output-dir", "outputs/toolaudit_pairs_eval",
                "--cache-dir", "outputs/llm_cache/toolaudit_eval",
                "--models", MODELS], env)

    for p in PRODUCERS:
        status(f"trading pairs {p}")
        run_logged([sys.executable, "scripts/run_audit_eval.py",
                    "--tasks-dir", f"outputs/audit_pairs/{p}",
                    "--output-dir", f"outputs/audit_pairs_eval/{p}",
                    "--cache-dir", "outputs/llm_cache/audit_eval",
                    "--models", MODELS], env)

    status("analysis")
    run_logged([sys.executable, "scripts/build_paired_tables.py"], env)

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
