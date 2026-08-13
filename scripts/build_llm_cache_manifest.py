from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from tradearena.core.serialization import write_json

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a redacted manifest from local LLM JSONL caches.")
    parser.add_argument(
        "--cache",
        action="append",
        default=[],
        help="Local JSONL cache path. Can be passed more than once.",
    )
    parser.add_argument("--output-dir", default="data/llm_cache_manifest")
    args = parser.parse_args()

    cache_paths = [Path(path) for path in args.cache] or [
        Path("data/llm_cache/crisis_scene_llm.jsonl"),
        Path("data/llm_cache/deepseek_analyst.jsonl"),
    ]
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for cache_path in cache_paths:
        resolved = cache_path if cache_path.is_absolute() else ROOT / cache_path
        if not resolved.exists():
            print(f"[skip] missing {cache_path}", flush=True)
            continue
        rows = _read_cache(resolved)
        summary = _summarize(rows, cache_path)
        output_path = output_dir / f"{resolved.stem}_summary.json"
        write_json(output_path, summary)
        summaries.append(summary)
        print(f"[ok] wrote {output_path.relative_to(ROOT)}", flush=True)

    write_json(
        output_dir / "manifest.json",
        {
            "schema": "tradearena_llm_cache_manifest_v1",
            "raw_cache_policy": "Raw prompt/response JSONL caches are local or external artifacts and are not tracked in the main repository.",
            "summaries": [
                {
                    "cache_name": summary["cache_name"],
                    "rows": summary["rows"],
                    "provider_model_counts": summary["provider_model_counts"],
                    "prompt_mode_counts": summary["prompt_mode_counts"],
                    "parsed_response_rate": summary["parsed_response_rate"],
                }
                for summary in summaries
            ],
        },
    )
    print(f"[ok] wrote {(output_dir / 'manifest.json').relative_to(ROOT)}", flush=True)
    return 0


def _read_cache(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _summarize(rows: list[dict[str, Any]], cache_path: Path) -> dict[str, Any]:
    provider_models: Counter[str] = Counter()
    prompt_modes: Counter[str] = Counter()
    timestamp_masked_rows = 0
    parsed_responses = 0
    signal_counts: list[int] = []
    sample_rows: list[dict[str, Any]] = []

    for row in rows:
        provider_model = f"{row.get('provider', 'unknown')}:{row.get('model', row.get('api_model', 'unknown'))}"
        provider_models[provider_model] += 1

        prompt = _loads_json_object(row.get("prompt", ""))
        response = _loads_json_object(_strip_json_fence(row.get("response_text", "")))
        signals = response.get("signals") if isinstance(response.get("signals"), list) else []
        if response:
            parsed_responses += 1
            signal_counts.append(len(signals))

        timestamp = str(prompt.get("timestamp", ""))
        if timestamp.startswith("T+"):
            timestamp_masked_rows += 1
        mode = _prompt_mode(prompt)
        prompt_modes[mode] += 1
        if len(sample_rows) < 8:
            sample_rows.append(
                {
                    "provider_model": provider_model,
                    "timestamp": timestamp,
                    "symbols": len(prompt.get("bars", [])),
                    "prompt_hash_prefix": str(row.get("prompt_hash", ""))[:12],
                    "cache_key_prefix": str(row.get("cache_key", ""))[:24],
                    "prompt_mode": mode,
                    "parsed_signals": len(signals),
                }
            )

    return {
        "schema": "tradearena_llm_cache_manifest_v1",
        "cache_name": cache_path.name,
        "cache_path_hint": str(cache_path).replace("\\", "/"),
        "rows": len(rows),
        "provider_model_counts": dict(sorted(provider_models.items())),
        "prompt_mode_counts": dict(sorted(prompt_modes.items())),
        "timestamp_masked_rows": timestamp_masked_rows,
        "parsed_response_rate": parsed_responses / max(1, len(rows)),
        "average_signals_per_parsed_response": sum(signal_counts) / max(1, len(signal_counts)),
        "sample_rows": sample_rows,
        "redaction": {
            "raw_prompts_included": False,
            "raw_responses_included": False,
            "api_keys_included": False,
            "retained_fields": [
                "provider_model_counts",
                "prompt_mode_counts",
                "timestamp_masked_rows",
                "parsed_response_rate",
                "average_signals_per_parsed_response",
                "prompt_hash_prefix",
                "cache_key_prefix",
                "parsed_signal_count",
            ],
        },
        "notes": [
            "This manifest is derived from a local prompt/response cache but does not include raw prompts or raw model outputs.",
            "Raw JSONL caches are intentionally ignored by Git; keep them local or distribute them through an explicit external artifact if licensing permits.",
            "Hash prefixes are included only as lightweight replay fingerprints.",
        ],
    }


def _loads_json_object(value: str) -> dict[str, Any]:
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _strip_json_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _prompt_mode(prompt: dict[str, Any]) -> str:
    instruction = str(prompt.get("risk_feedback_instruction", "")).lower()
    feedback = prompt.get("recent_risk_feedback", [])
    if "intentionally hidden" in instruction:
        return "hidden_risk_feedback"
    if feedback:
        return "visible_risk_feedback"
    return "initial_or_no_recent_feedback"


if __name__ == "__main__":
    raise SystemExit(main())
