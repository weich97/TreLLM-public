from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ARTIFACTS = [
    "README.md",
    "benchmarks/v0.2/spec.json",
    "docs/results/benchmark_v0_2.md",
    "docs/results/execution_replay_calibration_loop.json",
    "docs/results/execution_calibration_stability.json",
    "docs/results/market_rules_fixture.json",
    "docs/results/external_validation_bundle.md",
    "docs/results/poe_skill_task_matrix.md",
    "docs/results/poe_skill_challenge_matrix.md",
    "docs/results/poe_skill_challenge_followup_matrix.md",
    "docs/results/poe_skill_challenge_followup_claude_adversarial.md",
    "docs/results/skill_task_matrix.md",
    "docs/results/community_registry.md",
    "docs/public_artifact_privacy.md",
    "docs/launch/release_notes_v0.2.1.md",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a local release-candidate manifest for a patch release.")
    parser.add_argument("--target-release", default="v0.2.1")
    parser.add_argument("--output", default="docs/launch/release_candidate_v0.2.1.json")
    parser.add_argument("--markdown-output", default="docs/launch/release_candidate_v0.2.1.md")
    args = parser.parse_args(argv)

    manifest = build_manifest(args.target_release)
    output = ROOT / args.output
    markdown_output = ROOT / args.markdown_output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(manifest), encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT).as_posix()}")
    print(f"Wrote {markdown_output.relative_to(ROOT).as_posix()}")
    return 0


def build_manifest(target_release: str) -> dict[str, Any]:
    status = _git(["status", "--short"])
    return {
        "schema": "tradearena_release_candidate_manifest_v0.1",
        "target_release": target_release,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "current_package_version": _package_version(),
        "commit": _git(["rev-parse", "HEAD"]),
        "dirty_file_count": _dirty_file_count(status),
        "git_status_sha256": _status_digest(status),
        "artifact_hashes": [_artifact_hash(path) for path in DEFAULT_ARTIFACTS],
        "pre_release_commands": [
            "python -m compileall src scripts examples tests -q",
            "python -m ruff check src scripts examples tests",
            "python -m mypy",
            "python -m pytest tests -q",
            "python scripts/check_release_readiness.py",
            "python scripts/scan_public_artifacts.py outputs docs/results examples/benchmark_submissions",
        ],
        "publish_boundary": (
            "This is a local release-candidate manifest. Tagging and PyPI publication are separate maintainer "
            "actions and require CI plus trusted-publishing credentials."
        ),
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest['target_release']} Release Candidate Manifest",
        "",
        manifest["publish_boundary"],
        "",
        "## Candidate State",
        "",
        f"- Target release: `{manifest['target_release']}`",
        f"- Current package version: `{manifest['current_package_version']}`",
        f"- Commit: `{manifest['commit']}`",
        f"- Working tree dirty entries when generated: `{manifest['dirty_file_count']}`",
        "",
        "## Pre-Release Commands",
        "",
    ]
    for command in manifest["pre_release_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(["", "## Artifact Hashes", ""])
    for artifact in manifest["artifact_hashes"]:
        status = "present" if artifact["exists"] else "missing"
        digest = artifact.get("sha256", "")
        lines.append(f"- `{artifact['path']}`: {status} {digest}")
    lines.extend(
        [
            "",
            "## Release Notes Draft",
            "",
            "- Public artifact redaction is now enforced by default for trajectory JSON and public result scans.",
            "- Provider audit matrix results compare frontier models as financial-audit agents rather than stock pickers.",
            "- Execution evidence now includes a replay loop across OHLCV stress, quote replay, and fill replay.",
            "- External validation bundle generation turns reproduction manifests into issue-ready reports.",
            "- OpenTelemetry-style local trace export maps trajectories into portable audit spans.",
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_hash(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.exists():
        return {"path": rel, "exists": False}
    content = _artifact_bytes(rel, path)
    return {
        "path": rel,
        "exists": True,
        "bytes": len(content),
        "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
    }


def _artifact_bytes(rel: str, path: Path) -> bytes:
    if _git_path_has_worktree_changes(rel):
        return _canonical_worktree_bytes(path)
    blob = _git_blob_bytes(rel)
    if blob is not None:
        return blob
    return _canonical_worktree_bytes(path)


def _git_path_has_worktree_changes(rel: str) -> bool:
    result = subprocess.run(
        _git_command(["status", "--short", "--", rel]),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _canonical_worktree_bytes(path: Path) -> bytes:
    content = path.read_bytes()
    if b"\0" in content:
        return content
    return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _git_blob_bytes(rel: str) -> bytes | None:
    normalized_rel = rel.replace("\\", "/")
    result = subprocess.run(
        _git_command(["show", f"HEAD:{normalized_rel}"]),
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _package_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def _git(args: list[str]) -> str:
    try:
        result = subprocess.run(_git_command(args), cwd=ROOT, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return ""


def _git_command(args: list[str]) -> list[str]:
    return ["git", "-c", f"safe.directory={ROOT.as_posix()}", *args]


def _dirty_file_count(status: str) -> int:
    return len([line for line in status.splitlines() if line.strip()])


def _status_digest(status: str) -> str:
    if not status:
        return ""
    return "sha256:" + hashlib.sha256(status.encode()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
