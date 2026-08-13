"""FinAudit self-audit-bias matrix (audit study, experiment B).

Each of the 4 producer task sets (trajectories produced by that model, with one
injected defect each) is audited by all 4 auditor models. The diagonal
(auditor == producer) is *self*-audit; off-diagonal is *cross*-audit. The
self-audit bias for a model is cross_recall - self_recall (positive => it goes
easier on its own trajectories).

run_audit_eval is resilient (provider errors are caught and the task skipped,
not crashed) and resumable (per-(model, task) checkpoint), so this script can be
re-run to fill any cells a Poe outage skipped. gpt-5.5 is excluded (temporarily
unavailable); glm-routed is dropped (same model as glm direct).

Launched detached so it survives parent-process teardown.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for line in (ROOT / "APIkey.txt").read_text(encoding="utf-8").splitlines():
    low = line.lower()
    if "poe" in low and (m := re.search(r"sk-poe-[A-Za-z0-9_\-]+", line)):
        os.environ.setdefault("POE_API_KEY", m.group(0))
    elif "deepseek" in low and (m := re.search(r"sk-[A-Za-z0-9]{20,}", line)):
        os.environ["DEEPSEEK_API_KEY"] = m.group(0)
    elif "glm" in low and (m := re.search(r"[0-9a-fA-F]{32}\.[A-Za-z0-9]+", line)):
        os.environ["GLM_API_KEY"] = m.group(0)
os.environ.setdefault("PYTHONPATH", str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("run_audit_eval", ROOT / "scripts" / "run_audit_eval.py")
assert _spec and _spec.loader
run_audit_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_audit_eval)

PRODUCERS = ["deepseek_v4_pro", "glm_5_direct", "gemini_3_1_pro", "claude_opus_4_7"]
AUDITORS = "deepseek:deepseek-v4-pro,glm:glm-5,poe:gemini-3.1-pro,poe:claude-opus-4.7"


def main() -> int:
    for p in PRODUCERS:
        print(f"[{datetime.now():%H:%M:%S}] === auditing producer {p} with all 4 auditors ===", flush=True)
        run_audit_eval.main([
            "--tasks-dir", f"outputs/audit_self/{p}",
            "--models", AUDITORS,
            "--output-dir", f"outputs/audit_matrix/{p}",
            "--cache-dir", "outputs/llm_cache/audit_eval",
        ])
    print(f"[{datetime.now():%H:%M:%S}] MATRIX DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
