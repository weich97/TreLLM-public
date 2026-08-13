"""Run LLM monitors on the Airlock approval-bundle triage task (E6).

Each item is one approval bundle (clean / semantic-contradiction / arbitrary
free-text / authority-bearing fault); the monitor returns JSON findings, scored
against the injection. Reuses the trading eval's cached model transport and
finding parser. Resumable: checkpoints per (model, item, sample).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("run_audit_eval", ROOT / "scripts" / "run_audit_eval.py")
assert _spec and _spec.loader
run_audit_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_audit_eval)

from tradearena.evaluation.airlock_monitor import (
    build_monitor_items,
    build_prompt,
    parse_monitor_findings,
    score_monitor,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate LLM monitors on Airlock bundles.")
    parser.add_argument("--models", default="deepseek:deepseek-v4-pro")
    parser.add_argument("--samples-per-item", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--cache-dir", default="outputs/llm_cache/airlock_monitor")
    parser.add_argument("--output-dir", default="outputs/airlock_monitor")
    parser.add_argument("--template-variant", choices=["a", "b"], default="a",
                        help="Session template variant (cross-template arm); dirs get a _<variant> suffix for b.")
    args = parser.parse_args(argv)

    suffix = "" if args.template_variant == "a" else f"_{args.template_variant}"
    output_dir = ROOT / (args.output_dir + suffix)
    cache_dir = ROOT / (args.cache_dir + suffix)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    items = build_monitor_items(Path(tempfile.mkdtemp(prefix="airlock_mon_")), variant=args.template_variant)

    results_path = output_dir / "airlock_monitor_results.jsonl"
    done: set[tuple[str, str, int]] = set()
    if results_path.exists():
        with results_path.open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                done.add((row["model"], row["item_id"], int(row.get("sample", 0))))
    if done:
        print(f"Resuming: {len(done)} results checkpointed", flush=True)

    samples = max(1, int(args.samples_per_item))
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    with results_path.open("a", encoding="utf-8") as out:
        for spec in models:
            provider, model = spec.split(":", 1)
            for item in items:
                prompt = build_prompt(item)
                for s in range(samples):
                    if (spec, item.item_id, s) in done:
                        continue
                    try:
                        response = run_audit_eval.call_model(
                            provider, model, prompt, cache_dir, item.item_id,
                            sample=s, temperature=args.temperature,
                        )
                    except Exception as exc:
                        print(f"FAILED {spec} {item.item_id} s{s}: {type(exc).__name__}: {exc}",
                              file=sys.stderr, flush=True)
                        continue
                    findings = parse_monitor_findings(response)
                    scored = score_monitor(findings, item)
                    record = {
                        "model": spec, "item_id": item.item_id, "sample": s,
                        "tier": item.tier, "is_faulted": item.is_faulted,
                        "faulted_field": item.faulted_field,
                        "flagged": scored["flagged"], "field_hit": scored["field_hit"],
                        "finding_count": scored["finding_count"], "findings": findings,
                    }
                    out.write(json.dumps(record, sort_keys=True) + "\n")
                    out.flush()
                    print(f"OK {spec} {item.item_id} ({item.tier}) "
                          f"flag={scored['flagged']} hit={scored['field_hit']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
