from __future__ import annotations

from pathlib import Path

from tradearena.core.serialization import read_json, write_json

MANIFEST_PATH = Path("data/llm_cache_manifest/crisis_scene_llm_summary.json")
OUTPUT_DIR = Path("outputs/examples")


def main() -> int:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "Missing redacted crisis-scene LLM cache manifest. Run scripts/build_llm_cache_manifest.py "
            "from a local raw cache, or fetch the repository manifest artifact."
        )
    summary = read_json(MANIFEST_PATH)
    demo_summary = {
        **summary,
        "manifest_path": str(MANIFEST_PATH),
        "raw_cache_tracked_in_repo": False,
        "demo_notes": [
            "This demo makes no live provider calls and reads a redacted manifest, not raw Poe or DeepSeek prompt/response text.",
            "The main repository tracks provider/model coverage, hash prefixes, prompt modes, and parse statistics only.",
            "Raw JSONL caches are local or external artifacts and are ignored by Git.",
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "llm_cache_replay_summary.json", demo_summary)

    print("LLM cache manifest demo")
    print(f"  manifest_rows={summary['rows']} parsed_response_rate={summary['parsed_response_rate']:.3f}")
    print(f"  provider_models={', '.join(summary['provider_model_counts'])}")
    print(f"  timestamp_masked_rows={summary['timestamp_masked_rows']}")
    print("  raw_prompts_included=False raw_responses_included=False")
    print(f"\nWrote {OUTPUT_DIR / 'llm_cache_replay_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
