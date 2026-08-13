from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - exercised by fresh public-package CI.
    Draft202012Validator = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "reproduction_report.schema.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a TreLLM external reproduction report.")
    parser.add_argument("report", help="Path to an external reproduction manifest JSON.")
    parser.add_argument(
        "--allow-command-failures",
        action="store_true",
        help="Accept schema-valid reports that document command failures or missing artifacts.",
    )
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    try:
        payload = _load_reproduction_report(report_path)
    except ValueError as exc:
        print(f"Invalid reproduction report: {report_path}")
        print(f"  - {exc}")
        return 1
    errors = validate_reproduction_report(payload, allow_command_failures=args.allow_command_failures)
    if errors:
        print(f"Invalid reproduction report: {report_path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid reproduction report: {report_path}")
    return 0


def _load_reproduction_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("reproduction report must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("reproduction report must be a JSON object")
    return payload


def validate_reproduction_report(
    payload: dict[str, Any],
    *,
    allow_command_failures: bool = False,
) -> list[str]:
    errors: list[str] = []
    if Draft202012Validator is None:
        errors.extend(_fallback_schema_errors(payload))
    else:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        errors.extend(sorted((error.message for error in validator.iter_errors(payload)), key=str))
    if errors:
        return errors

    if not allow_command_failures:
        for command in payload["commands"]:
            returncode = command.get("returncode")
            if returncode not in {0, None}:
                errors.append(f"command {command.get('id', '<unknown>')} returned {returncode}")
        missing_artifacts = [artifact["path"] for artifact in payload["artifacts"] if not artifact.get("exists")]
        if missing_artifacts:
            errors.append(f"missing artifacts: {', '.join(missing_artifacts)}")

    trajectory_hash = payload.get("trajectory_hash", {})
    if not isinstance(trajectory_hash, dict):
        errors.append("trajectory_hash must be an object")
    elif not str(trajectory_hash.get("reproducibility_hash", "")).startswith("sha256:"):
        errors.append("trajectory_hash.reproducibility_hash must start with sha256:")

    for artifact in payload["artifacts"]:
        if artifact.get("exists") and not str(artifact.get("sha256", "")).startswith("sha256:"):
            errors.append(f"artifact {artifact['path']} is missing a sha256 digest")

    return errors


def _fallback_schema_errors(payload: dict[str, Any]) -> list[str]:
    required = {
        "schema",
        "created_at",
        "repository",
        "commit_or_tag",
        "python",
        "commands",
        "artifacts",
        "trajectory_hash",
        "live_api_used",
        "market_data_used",
        "private_fills_used",
    }
    errors: list[str] = []
    missing = sorted(required - set(payload))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if payload.get("schema") != "tradearena_external_reproduction_pack_v1":
        errors.append("schema must be tradearena_external_reproduction_pack_v1")

    python = payload.get("python")
    if not isinstance(python, dict):
        errors.append("python must be an object")
    else:
        _extend_missing_fields(errors, "python", python, {"version", "implementation", "executable", "platform"})

    commands = payload.get("commands")
    if not isinstance(commands, list):
        errors.append("commands must be an array")
    else:
        for index, command in enumerate(commands):
            if not isinstance(command, dict):
                errors.append(f"commands[{index}] must be an object")
                continue
            _extend_missing_fields(errors, f"commands[{index}]", command, {"id", "argv"})
            if "argv" in command and not isinstance(command["argv"], list):
                errors.append(f"commands[{index}].argv must be an array")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be an array")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"artifacts[{index}] must be an object")
                continue
            _extend_missing_fields(errors, f"artifacts[{index}]", artifact, {"path", "exists"})
            if "exists" in artifact and not isinstance(artifact["exists"], bool):
                errors.append(f"artifacts[{index}].exists must be boolean")

    if not isinstance(payload.get("trajectory_hash"), dict):
        errors.append("trajectory_hash must be an object")
    if not isinstance(payload.get("live_api_used"), bool):
        errors.append("live_api_used must be boolean")
    if not isinstance(payload.get("market_data_used"), str):
        errors.append("market_data_used must be a string")
    if not isinstance(payload.get("private_fills_used"), bool):
        errors.append("private_fills_used must be boolean")
    return errors


def _extend_missing_fields(errors: list[str], label: str, payload: dict[str, Any], required: set[str]) -> None:
    missing = sorted(required - set(payload))
    if missing:
        errors.append(f"{label} missing required fields: {', '.join(missing)}")


if __name__ == "__main__":
    raise SystemExit(main())
