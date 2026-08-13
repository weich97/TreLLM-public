"""Finish the glm-auditor constraint cells (audit-study intervention), teardown-proof.

glm-as-auditor was the only undersampled intervention cell (deepseek auditor and
both strong auditors completed). A non-detached background task kept dying at parent-process
teardown; this is launched DETACHED (pythonw, survives teardown) and retries each
cell until glm reaches 120 (run_audit_eval checkpoints, so a retry resumes).
Free (glm + deepseek direct). Writes outputs/glm_finish.done when complete.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / "APIkey.txt").read_text(encoding="utf-8").splitlines():
    low = line.lower()
    if "deepseek" in low and (m := re.search(r"sk-[A-Za-z0-9]{20,}", line)):
        os.environ["DEEPSEEK_API_KEY"] = m.group(0)
    elif "glm" in low and (m := re.search(r"[0-9a-fA-F]{32}\.[A-Za-z0-9]+", line)):
        os.environ["GLM_API_KEY"] = m.group(0)
os.environ["PYTHONPATH"] = str(ROOT / "src")
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("rae", ROOT / "scripts" / "run_audit_eval.py")
rae = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rae)

CELLS = ["deepseek_v4_pro", "glm_5_direct"]
LOG = ROOT / "outputs" / "glm_finish.log"


def glm_count(p: str) -> int:
    rp = ROOT / f"outputs/audit_intervention/{p}_constraint/audit_eval_results.jsonl"
    if not rp.exists():
        return 0
    return sum(1 for line in rp.open(encoding="utf-8") if json.loads(line)["model"] == "glm:glm-5")


def log(msg: str) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def main() -> int:
    for p in CELLS:
        for attempt in range(8):
            if glm_count(p) >= 120:
                break
            log(f"{p}: attempt {attempt}, glm at {glm_count(p)}/120")
            try:
                rae.main([
                    "--tasks-dir", f"outputs/audit_self/{p}",
                    "--models", "glm:glm-5",
                    "--prompt-variant", "constraint",
                    "--output-dir", f"outputs/audit_intervention/{p}_constraint",
                    "--cache-dir", "outputs/llm_cache/audit_eval",
                ])
            except Exception as exc:  # keep retrying on any failure
                log(f"{p}: error {type(exc).__name__}: {exc}")
        log(f"{p}: final glm {glm_count(p)}/120")
    (ROOT / "outputs" / "glm_finish.done").write_text(
        json.dumps({p: glm_count(p) for p in CELLS}), encoding="utf-8")
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
