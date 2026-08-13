from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate required TreLLM demo artifacts.")
    parser.add_argument("--manifest", default="docs/demo_artifacts.yaml")
    args = parser.parse_args(argv)

    artifacts = _parse_manifest(ROOT / args.manifest)
    failures: list[str] = []
    for artifact in artifacts:
        for rel in artifact.get("required_outputs", []):
            path = ROOT / rel
            if not path.exists():
                failures.append(f"{artifact['id']}: missing output {rel}")
            elif path.is_file() and path.stat().st_size == 0:
                failures.append(f"{artifact['id']}: empty output {rel}")
        for spec in artifact.get("required_json_fields", []):
            rel, dotted_path = spec.split(":", 1)
            path = ROOT / rel
            if not path.exists():
                failures.append(f"{artifact['id']}: cannot check missing JSON {rel}")
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"{artifact['id']}: invalid JSON {rel}: {exc}")
                continue
            if _get_path(payload, dotted_path) is None:
                failures.append(f"{artifact['id']}: missing JSON field {spec}")
            if dotted_path == "verification_commands":
                failures.extend(_check_verification_commands(artifact, rel, payload))
        for command in artifact.get("required_validators", []):
            result = _run_validator(command)
            if result.returncode != 0:
                failures.append(f"{artifact['id']}: validator failed: {command}")
                if result.stdout.strip():
                    failures.append(f"{artifact['id']}: validator stdout: {result.stdout.strip()}")
                if result.stderr.strip():
                    failures.append(f"{artifact['id']}: validator stderr: {result.stderr.strip()}")

    if failures:
        print("Demo artifact contract failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"Demo artifact contract passed ({len(artifacts)} artifacts).")
    return 0


def _parse_manifest(path: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    section: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.strip()
        if stripped.startswith("- id:"):
            if current:
                artifacts.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
            section = None
            continue
        if current is None:
            continue
        if stripped.startswith("command:"):
            current["command"] = stripped.split(":", 1)[1].strip()
            section = None
        elif stripped in {"required_outputs:", "required_json_fields:", "required_validators:"}:
            section = stripped[:-1]
            current[section] = []
        elif stripped.startswith("- ") and section:
            current[section].append(stripped[2:].strip())
    if current:
        artifacts.append(current)
    return artifacts


def _run_validator(command: str) -> subprocess.CompletedProcess[str]:
    argv = shlex.split(command)
    if argv and argv[0] == "python":
        argv[0] = sys.executable
    return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


def _check_verification_commands(artifact: dict[str, Any], rel: str, payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{artifact['id']}: cannot check verification_commands in non-object JSON {rel}"]
    commands = payload.get("verification_commands")
    if not isinstance(commands, list) or not all(isinstance(command, str) for command in commands):
        return [f"{artifact['id']}: verification_commands must be a list of strings in {rel}"]
    expected = artifact.get("required_validators", [])
    if commands != expected:
        return [f"{artifact['id']}: verification_commands do not match required_validators in {rel}"]
    return []


def _get_path(payload: Any, dotted_path: str) -> Any:
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            if not current:
                return None
            current = current[0]
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        else:
            return None
    return current


if __name__ == "__main__":
    raise SystemExit(main())
