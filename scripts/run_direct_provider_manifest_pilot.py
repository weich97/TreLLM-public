from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_direct_provider_manifest import validate_direct_provider_manifest_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a hash-only TreLLM direct provider manifest from a prompt/response fixture. "
            "The current pilot runner is offline by design; live direct API adapters can reuse this manifest contract."
        )
    )
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-version-or-release", required=True)
    parser.add_argument("--api-endpoint-family", required=True)
    parser.add_argument("--prompt-file", required=True, help="Prompt payload to hash. Raw prompt text is not copied.")
    parser.add_argument("--response-file", help="Provider response fixture to hash. Raw response text is not copied.")
    parser.add_argument("--prompt-template-id", default="trellm-allocation-v0.3")
    parser.add_argument("--prompt-version", default="v0.3.0")
    parser.add_argument("--system-prompt-file", help="Optional system prompt payload to hash.")
    parser.add_argument("--protocol-id", default="trellm-v0.3-protocol")
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--contamination-tier", choices=["C0", "C1", "C2"], required=True)
    parser.add_argument("--execution-level", choices=["E0", "E1", "E2", "E3"], required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--sample-index", type=int, required=True)
    parser.add_argument("--trajectory-manifest-sha256", required=True)
    parser.add_argument("--benchmark-submission-sha256")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--call-started-at", default="")
    parser.add_argument("--call-completed-at", default="")
    parser.add_argument("--retry-count", type=int, default=0)
    parser.add_argument("--cache-status", choices=["live_call", "cache_hit", "cache_replay"], default="live_call")
    parser.add_argument("--cache-key-sha256")
    parser.add_argument("--claim-scope", default="Direct-provider manifest for an v0.3 pilot row; not a trading-profit claim.")
    parser.add_argument("--appendix-only", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    if not args.response_file:
        parser.error("--response-file is required for the current offline pilot runner")

    manifest = build_manifest(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _, errors = validate_direct_provider_manifest_file(output_path)
    if errors:
        print(f"Invalid generated direct provider manifest: {output_path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid direct provider manifest: {output_path}")
    return 0


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    prompt_path = Path(args.prompt_file)
    response_path = Path(args.response_file)
    prompt_bytes = prompt_path.read_bytes()
    response_bytes = response_path.read_bytes()
    started_at = args.call_started_at or _utc_now()
    completed_at = args.call_completed_at or started_at

    prompt: dict[str, Any] = {
        "prompt_template_id": args.prompt_template_id,
        "prompt_version": args.prompt_version,
        "prompt_sha256": _sha256_bytes(prompt_bytes),
        "raw_prompt_public": False,
    }
    if args.system_prompt_file:
        prompt["system_prompt_sha256"] = _sha256_file(Path(args.system_prompt_file))

    response_format, parse_status = _response_format_and_parse_status(response_bytes)
    response = {
        "response_sha256": _sha256_bytes(response_bytes),
        "response_format": response_format,
        "parse_status": parse_status,
        "raw_response_public": False,
    }

    cache: dict[str, Any] = {"cache_status": args.cache_status}
    cache_key_sha256 = args.cache_key_sha256 or _sha256_bytes(
        "|".join(
            [
                args.provider,
                args.model_id,
                args.model_version_or_release,
                prompt["prompt_sha256"],
                response["response_sha256"],
                str(args.sample_index),
            ]
        ).encode("utf-8")
    )
    cache["cache_key_sha256"] = cache_key_sha256

    run_binding: dict[str, Any] = {
        "scenario_id": args.scenario_id,
        "contamination_tier": args.contamination_tier,
        "execution_level": args.execution_level,
        "seed": args.seed,
        "sample_index": args.sample_index,
        "trajectory_manifest_sha256": args.trajectory_manifest_sha256,
    }
    if args.benchmark_submission_sha256:
        run_binding["benchmark_submission_sha256"] = args.benchmark_submission_sha256

    return {
        "schema": "trellm_direct_provider_manifest_v0.1",
        "protocol_id": args.protocol_id,
        "provider_route": "direct-api",
        "provider": args.provider,
        "model_id": args.model_id,
        "model_version_or_release": args.model_version_or_release,
        "api_endpoint_family": args.api_endpoint_family,
        "call_window": {
            "call_started_at": started_at,
            "call_completed_at": completed_at,
            "request_id_redacted": True,
            "retry_count": args.retry_count,
        },
        "sampling": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_tokens": args.max_tokens,
        },
        "prompt": prompt,
        "response": response,
        "redaction": {
            "provider_secrets_removed": True,
            "raw_prompt_public": False,
            "raw_response_public": False,
            "private_account_data_removed": True,
            "redaction_policy": "hash-only-public-manifest",
            "notes": "Generated manifest stores hashes and direct-provider metadata, not raw provider text.",
        },
        "cache": cache,
        "run_binding": run_binding,
        "evidence": {
            "evidence_label": "direct-api",
            "claim_scope": args.claim_scope,
            "appendix_only": bool(args.appendix_only),
        },
    }


def _response_format_and_parse_status(response_bytes: bytes) -> tuple[str, str]:
    try:
        parsed = json.loads(response_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "text", "partial"
    return ("json_object", "parsed") if isinstance(parsed, dict) else ("text", "partial")


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
