from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - dev/test environments install jsonschema.
    Draft202012Validator = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "direct_provider_manifest.schema.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a TreLLM direct provider manifest.")
    parser.add_argument("manifest", help="Path to a direct provider manifest JSON file.")
    args = parser.parse_args(argv)

    path = Path(args.manifest)
    _, errors = validate_direct_provider_manifest_file(path)
    if errors:
        print(f"Invalid direct provider manifest: {path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid direct provider manifest: {path}")
    return 0


def validate_direct_provider_manifest_file(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    manifest_path = Path(path)
    if manifest_path.exists() and not manifest_path.is_file():
        return {}, [f"direct provider manifest path is not a file: {manifest_path}"]
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [f"direct provider manifest not found: {manifest_path}"]
    except json.JSONDecodeError as exc:
        return {}, [f"direct provider manifest must contain valid JSON: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["direct provider manifest must be a JSON object"]
    return payload, validate_direct_provider_manifest(payload)


def validate_direct_provider_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if Draft202012Validator is None:
        errors.extend(_fallback_errors(payload))
    else:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        errors.extend(_format_jsonschema_error(error) for error in validator.iter_errors(payload))
    return sorted(set(errors), key=str)


def _fallback_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema",
        "protocol_id",
        "provider_route",
        "provider",
        "model_id",
        "model_version_or_release",
        "prompt",
        "response",
        "redaction",
        "run_binding",
        "evidence",
    }
    missing = sorted(required - set(payload))
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
    if payload.get("schema") != "trellm_direct_provider_manifest_v0.1":
        errors.append("schema must be trellm_direct_provider_manifest_v0.1")
    if payload.get("provider_route") != "direct-api":
        errors.append("provider_route must be direct-api")
    if payload.get("evidence", {}).get("evidence_label") != "direct-api":
        errors.append("evidence.evidence_label must be direct-api")
    if payload.get("redaction", {}).get("provider_secrets_removed") is not True:
        errors.append("redaction.provider_secrets_removed must be true")
    return errors


def _format_jsonschema_error(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return f"{path}: {error.message}"
    return str(error.message)


if __name__ == "__main__":
    raise SystemExit(main())
