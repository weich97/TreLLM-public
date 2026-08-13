from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an issue-ready external validation bundle from a reproduction manifest."
    )
    parser.add_argument("--manifest", default="outputs/reproduction/v0_2/manifest.json")
    parser.add_argument("--run-pack", action="store_true", help="Run scripts/run_external_reproduction_pack.py first.")
    parser.add_argument("--pack-output-dir", default="outputs/reproduction/v0_2")
    parser.add_argument("--environment-label", default="", help="Human label such as macOS 14 / Python 3.10.")
    parser.add_argument("--output", default="docs/results/external_validation_bundle.json")
    parser.add_argument("--markdown-output", default="docs/results/external_validation_bundle.md")
    args = parser.parse_args(argv)

    if args.run_pack:
        result = subprocess.run(
            [sys.executable, "scripts/run_external_reproduction_pack.py", "--output-dir", args.pack_output_dir],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            return result.returncode
        args.manifest = str(Path(args.pack_output_dir) / "manifest.json")

    manifest_path = ROOT / args.manifest
    try:
        manifest = _load_manifest(manifest_path)
    except ValueError as exc:
        print(f"Invalid reproduction manifest: {manifest_path}")
        print(f"  - {exc}")
        return 1
    bundle = build_bundle(manifest, manifest_path=manifest_path, environment_label=args.environment_label)
    output = ROOT / args.output
    markdown_output = ROOT / args.markdown_output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_bundle_markdown(bundle), encoding="utf-8")
    print(f"Wrote {_display_path(output)}")
    print(f"Wrote {_display_path(markdown_output)}")
    return 0


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("reproduction manifest must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("reproduction manifest must be a JSON object")
    return payload


def build_bundle(
    manifest: dict[str, Any],
    *,
    manifest_path: str | Path,
    environment_label: str = "",
) -> dict[str, Any]:
    commands = manifest.get("commands", []) if isinstance(manifest.get("commands"), list) else []
    artifacts = manifest.get("artifacts", []) if isinstance(manifest.get("artifacts"), list) else []
    failed = [command for command in commands if command.get("returncode") not in {0, None}]
    missing = [artifact for artifact in artifacts if not artifact.get("exists")]
    trajectory_hash = manifest.get("trajectory_hash", {}) if isinstance(manifest.get("trajectory_hash"), dict) else {}
    python_info = manifest.get("python", {}) if isinstance(manifest.get("python"), dict) else {}
    return {
        "schema": "tradearena_external_validation_bundle_v0.1",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "environment_label": environment_label or platform.platform(),
        "manifest_path": _portable_path(manifest_path),
        "commit_or_tag": manifest.get("commit_or_tag", ""),
        "git_dirty_entry_count": _dirty_entry_count(manifest.get("git_status_short", "")),
        "git_status_sha256": _status_digest(manifest.get("git_status_short", "")),
        "python": _public_python_info(python_info),
        "command_count": len(commands),
        "failed_command_count": len(failed),
        "failed_commands": [
            {
                "id": command.get("id", ""),
                "returncode": command.get("returncode"),
                "stderr_tail": command.get("stderr_tail", ""),
            }
            for command in failed
        ],
        "artifact_count": len(artifacts),
        "missing_artifact_count": len(missing),
        "missing_artifacts": [artifact.get("path", "") for artifact in missing],
        "artifact_hashes": [
            {
                "path": artifact.get("path", ""),
                "sha256": artifact.get("sha256", ""),
                "bytes": artifact.get("bytes", 0),
            }
            for artifact in artifacts
            if artifact.get("exists")
        ],
        "trajectory_reproducibility_hash": trajectory_hash.get("reproducibility_hash", ""),
        "trajectory_file_sha256": trajectory_hash.get("file_sha256", ""),
        "live_api_used": manifest.get("live_api_used", None),
        "market_data_used": manifest.get("market_data_used", ""),
        "private_fills_used": manifest.get("private_fills_used", None),
        "issue_ready": not failed and not missing and bool(trajectory_hash.get("reproducibility_hash")),
        "claim_boundary": (
            "This bundle summarizes a reproduction run. It is evidence for reproducibility of the no-key path; "
            "it is not evidence that any model trades profitably."
        ),
    }


def render_bundle_markdown(bundle: dict[str, Any]) -> str:
    status = "ready" if bundle["issue_ready"] else "needs investigation"
    dirty_count = int(bundle.get("git_dirty_entry_count", 0) or 0)
    if dirty_count:
        status = f"{status}; dirty working tree noted"
    lines = [
        "# External Validation Bundle",
        "",
        f"Status: **{status}**",
        "",
        bundle["claim_boundary"],
        "",
        "## Environment",
        "",
        f"- Environment label: `{bundle['environment_label']}`",
        f"- Commit/tag: `{bundle['commit_or_tag']}`",
        f"- Python: `{bundle['python'].get('version', '')}`",
        f"- Platform: `{bundle['python'].get('platform', '')}`",
        f"- Manifest: `{bundle['manifest_path']}`",
        f"- Working tree dirty entries: `{dirty_count}`",
        "",
        "## Reproduction Checks",
        "",
        f"- Commands: {bundle['command_count']}",
        f"- Failed commands: {bundle['failed_command_count']}",
        f"- Artifacts: {bundle['artifact_count']}",
        f"- Missing artifacts: {bundle['missing_artifact_count']}",
        f"- Live API used: `{bundle['live_api_used']}`",
        f"- Market data used: {bundle['market_data_used']}",
        f"- Private fills used: `{bundle['private_fills_used']}`",
        "",
        "## Hashes",
        "",
        f"- Trajectory reproducibility hash: `{bundle['trajectory_reproducibility_hash']}`",
        f"- Trajectory file SHA-256: `{bundle['trajectory_file_sha256']}`",
        "",
        "## Artifact Hashes",
        "",
    ]
    for artifact in bundle["artifact_hashes"]:
        lines.append(f"- `{artifact['path']}` ({artifact['bytes']} bytes): `{artifact['sha256']}`")
    if not bundle["artifact_hashes"]:
        lines.append("- none")
    if bundle["failed_commands"]:
        lines.extend(["", "## Failed Commands", ""])
        for command in bundle["failed_commands"]:
            lines.append(f"- `{command['id']}` returned `{command['returncode']}`")
    if bundle["missing_artifacts"]:
        lines.extend(["", "## Missing Artifacts", ""])
        for artifact in bundle["missing_artifacts"]:
            lines.append(f"- `{artifact}`")
    lines.extend(
        [
            "",
            "## Suggested Issue Text",
            "",
            "```markdown",
            f"Environment: {bundle['environment_label']}",
            f"Commit/tag: {bundle['commit_or_tag']}",
            f"Trajectory hash: {bundle['trajectory_reproducibility_hash']}",
            f"Manifest: {bundle['manifest_path']}",
            f"Working-tree dirty entries: {dirty_count}",
            f"Commands failed: {bundle['failed_command_count']}",
            f"Missing artifacts: {bundle['missing_artifact_count']}",
            "No live APIs or private fills were used unless stated above.",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _dirty_entry_count(status: Any) -> int:
    if not isinstance(status, str):
        return 0
    return len([line for line in status.splitlines() if line.strip()])


def _status_digest(status: Any) -> str:
    text = status if isinstance(status, str) else ""
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _public_python_info(python_info: dict[str, Any]) -> dict[str, Any]:
    public = dict(python_info)
    executable = public.get("executable")
    if isinstance(executable, str) and executable:
        public["executable"] = ntpath.basename(executable) or Path(executable).name or executable
    return public


def _portable_path(path: str | Path) -> str:
    resolved = Path(path)
    try:
        return resolved.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return resolved.as_posix()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
