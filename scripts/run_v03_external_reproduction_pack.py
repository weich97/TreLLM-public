from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "trellm-v0.3-protocol"
SCHEMA = "tradearena_external_reproduction_pack_v1"
REQUIRED_ENVIRONMENT_CLASSES = ("windows_or_macos", "linux", "colab_or_binder")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and record the TreLLM v0.3 no-key external reproduction pack.")
    parser.add_argument("--output-dir", default="outputs/reproduction/v0_3")
    parser.add_argument(
        "--environment-class",
        choices=REQUIRED_ENVIRONMENT_CLASSES,
        default=_default_environment_class(),
        help="Environment class used by the v0.3 external reproduction gate.",
    )
    parser.add_argument(
        "--report-author-type",
        choices=["project-maintainer", "independent"],
        default="project-maintainer",
    )
    parser.add_argument(
        "--independent-reviewer",
        action="store_true",
        help="Set only for reports produced by a reviewer outside the project authorship team.",
    )
    parser.add_argument("--skip-commands", action="store_true", help="Only hash existing artifacts.")
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    commands = _commands(output_dir)
    if args.skip_commands:
        command_results = [{**command, "returncode": None, "skipped": True} for command in commands]
    else:
        command_results = [_run_command(command) for command in commands]

    artifacts = [_artifact_record(path) for path in _artifacts(output_dir)]
    manifest = {
        "schema": SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "environment_class": args.environment_class,
        "report_author_type": args.report_author_type,
        "independent_reviewer": bool(args.independent_reviewer),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository": "https://github.com/weich97/TreLLM-public",
        "commit_or_tag": _git(["rev-parse", "HEAD"]),
        "git_status_short": _git(["status", "--short"]),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": _public_python_executable(),
            "platform": platform.platform(),
        },
        "commands": command_results,
        "artifacts": artifacts,
        "trajectory_hash": _hash_trajectory(ROOT / "outputs/examples/audit_walkthrough_trajectory.json"),
        "live_api_used": False,
        "market_data_used": "deterministic synthetic data and committed public v0.3 fixture artifacts",
        "private_fills_used": False,
        "notes": (
            "This v0.3 no-key reproduction pack exercises protocol validation, fixture artifact generation, "
            "threshold gates, privacy scanning, and evidence indexing. It does not run live provider APIs or prove trading profitability."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(_render_readme(manifest), encoding="utf-8")
    print(f"Wrote {_display_path(manifest_path)}")
    print(f"Wrote {_display_path(output_dir / 'README.md')}")
    failed_summary = summarize_failed_commands(command_results)
    if failed_summary:
        print(failed_summary, file=sys.stderr)
        return 1
    return 0


def _commands(output_dir: Path) -> list[dict[str, Any]]:
    direct_api_dir = output_dir / "v0_3_direct_api_pilot"
    direct_plan_dir = output_dir / "v0_3_direct_api_matrix_plan"
    direct_call_packet_dir = output_dir / "v0_3_direct_api_call_packets"
    direct_checklist_dir = output_dir / "v0_3_direct_api_submission_checklist"
    direct_gate_dir = output_dir / "v0_3_direct_api_matrix_gate"
    variance_dir = output_dir / "v0_3_variance_decomposition"
    stress_grid_dir = output_dir / "v0_3_execution_stress_grid"
    finaudit_dir = output_dir / "v0_3_finaudit_pilot"
    finaudit_direct_model_dir = output_dir / "v0_3_finaudit_direct_model_plan"
    return [
        {
            "id": "trajectory",
            "argv": [sys.executable, "examples/audit_trajectory_walkthrough.py"],
            "description": "Generate the deterministic replayable trajectory used for the report hash.",
        },
        {
            "id": "validate_v03_protocol",
            "argv": [sys.executable, "scripts/validate_benchmark_spec.py", "benchmarks/v0.3/protocol.json"],
            "description": "Validate the v0.3 protocol contract.",
        },
        {
            "id": "v03_direct_api_pilot",
            "argv": [
                sys.executable,
                "scripts/run_v03_direct_api_pilot.py",
                "--output-dir",
                _command_path(direct_api_dir),
                "--seeds",
                "7",
                "--samples",
                "0",
            ],
            "description": "Generate a no-key direct API fixture pilot row.",
        },
        {
            "id": "v03_direct_api_matrix_plan",
            "argv": [
                sys.executable,
                "scripts/build_v03_direct_api_matrix_plan.py",
                "--output-dir",
                _command_path(direct_plan_dir),
                "--models",
                "openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",
                "--seeds",
                "7,11",
                "--samples",
                "0,1",
            ],
            "description": "Pre-register the direct API matrix rows and credential preflight without live provider calls.",
        },
        {
            "id": "v03_direct_api_call_packets",
            "argv": [
                sys.executable,
                "scripts/build_v03_direct_api_call_packets.py",
                "--plan-rows",
                _command_path(direct_plan_dir / "direct_api_matrix_plan_rows.csv"),
                "--output-dir",
                _command_path(direct_call_packet_dir),
            ],
            "description": "Generate hash-bound no-key call packets from the pre-registered direct API matrix plan.",
        },
        {
            "id": "v03_direct_api_submission_checklist",
            "argv": [
                sys.executable,
                "scripts/build_v03_direct_api_submission_checklist.py",
                "--output-dir",
                _command_path(direct_checklist_dir),
            ],
            "description": "Generate the direct API redaction, manifest-binding, and submission-readiness checklist.",
        },
        {
            "id": "v03_direct_api_matrix_gate",
            "argv": [
                sys.executable,
                "scripts/build_v03_direct_api_matrix_gate.py",
                "--output-dir",
                _command_path(direct_gate_dir),
                "--submission-dirs",
                _command_path(direct_api_dir / "submissions"),
                "--provider-manifest-dirs",
                _command_path(direct_api_dir / "provider_manifests"),
            ],
            "description": "Verify direct API manifest bindings and seed/sample threshold status.",
        },
        {
            "id": "v03_execution_ladder",
            "argv": [
                sys.executable,
                "scripts/run_v03_execution_ladder.py",
                "--output-dir",
                _command_path(output_dir / "v0_3_execution_ladder"),
                "--agents",
                "signal-weighted,random",
                "--seeds",
                "7",
                "--periods",
                "8",
                "--top-k",
                "2",
            ],
            "description": "Generate the v0.3 execution-assumption ladder smoke artifact.",
        },
        {
            "id": "v03_execution_stress_grid",
            "argv": [
                sys.executable,
                "scripts/run_v03_execution_stress_grid.py",
                "--output-dir",
                _command_path(stress_grid_dir),
                "--agents",
                "signal-weighted,random",
                "--seeds",
                "7",
                "--periods",
                "8",
            ],
            "description": "Generate the v0.3 E2 execution stress-grid smoke artifact.",
        },
        {
            "id": "v03_finaudit_pilot",
            "argv": [
                sys.executable,
                "scripts/run_v03_finaudit_pilot.py",
                "--output-dir",
                _command_path(finaudit_dir),
                "--tasks",
                "4",
                "--periods",
                "16",
                "--base-seed",
                "410",
            ],
            "description": "Generate the v0.3 FinAudit injected-defect smoke artifact.",
        },
        {
            "id": "v03_finaudit_direct_model_plan",
            "argv": [
                sys.executable,
                "scripts/build_v03_finaudit_direct_model_plan.py",
                "--task-manifest",
                _command_path(finaudit_dir / "finaudit_pilot_task_manifest.csv"),
                "--output-dir",
                _command_path(finaudit_direct_model_dir),
                "--models",
                "openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",
            ],
            "description": "Pre-register direct-model FinAudit auditor calls without making provider calls.",
        },
        {
            "id": "v03_memory_contamination",
            "argv": [
                sys.executable,
                "scripts/run_v03_memory_contamination.py",
                "--output-dir",
                _command_path(output_dir / "v0_3_memory_contamination"),
                "--kinds",
                "fake_rejections",
                "--doses",
                "0,0.5",
                "--decays",
                "1.0",
                "--risks",
                "max-position",
                "--seeds",
                "7",
                "--periods",
                "12",
            ],
            "description": "Generate the v0.3 memory-contamination smoke artifact.",
        },
        {
            "id": "v03_power_note",
            "argv": [
                sys.executable,
                "scripts/run_v03_power_note.py",
                "--output-dir",
                _command_path(output_dir / "v0_3_power_note"),
                "--repeat-levels",
                "6,10",
                "--effect-sizes",
                "0.8,1.2",
                "--target-powers",
                "0.5",
                "--draws",
                "30",
                "--permutation-draws",
                "128",
                "--seed",
                "3",
            ],
            "description": "Generate the v0.3 power-note smoke artifact.",
        },
        {
            "id": "v03_variance_decomposition",
            "argv": [
                sys.executable,
                "scripts/build_v03_variance_decomposition.py",
                "--input-rows",
                _command_path(direct_api_dir / "direct_api_pilot_rows.csv"),
                "--output-dir",
                _command_path(variance_dir),
            ],
            "description": "Generate the v0.3 between-seed and within-seed variance decomposition fixture.",
        },
        {
            "id": "v03_contamination_control_audit",
            "argv": [
                sys.executable,
                "scripts/build_v03_contamination_control_audit.py",
                "--output-dir",
                _command_path(output_dir / "v0_3_contamination_control_audit"),
            ],
            "description": "Audit C0/C1/C2 contamination-tier readiness and current public evidence gaps.",
        },
        {
            "id": "v03_claim_boundary_audit",
            "argv": [
                sys.executable,
                "scripts/build_v03_claim_boundary_audit.py",
                "--output-dir",
                _command_path(output_dir / "v0_3_claim_boundary_audit"),
            ],
            "description": "Audit public v0.3 narrative surfaces against claim boundaries and open evidence gaps.",
        },
        {
            "id": "v03_external_reproduction_gate",
            "argv": [
                sys.executable,
                "scripts/build_v03_external_reproduction_gate.py",
                "--output-dir",
                _command_path(output_dir / "v0_3_external_reproduction_gate"),
            ],
            "description": "Build the external reproduction gate against currently submitted reports.",
        },
        {
            "id": "v03_evidence_index",
            "argv": [
                sys.executable,
                "scripts/build_v03_evidence_index.py",
                "--output-dir",
                _command_path(output_dir / "v0_3_evidence_index"),
            ],
            "description": "Build the conservative v0.3 evidence index.",
        },
        {
            "id": "privacy_scan",
            "argv": [
                sys.executable,
                "scripts/scan_public_artifacts.py",
                _command_path(output_dir),
                "docs/results",
                "examples/benchmark_submissions",
            ],
            "description": "Scan generated and committed public artifacts for private LLM fields.",
        },
    ]


def _artifacts(output_dir: Path) -> list[Path]:
    return [
        ROOT / "outputs/examples/audit_walkthrough_trajectory.json",
        output_dir / "v0_3_direct_api_pilot/direct_api_pilot_summary.json",
        output_dir / "v0_3_direct_api_matrix_plan/direct_api_matrix_plan_summary.json",
        output_dir / "v0_3_direct_api_call_packets/direct_api_call_packets_summary.json",
        output_dir / (
            "v0_3_direct_api_submission_checklist/direct_api_submission_checklist_summary.json"
        ),
        output_dir / "v0_3_direct_api_matrix_gate/direct_api_matrix_gate_summary.json",
        output_dir / "v0_3_execution_ladder/execution_ladder_summary.json",
        output_dir / "v0_3_execution_stress_grid/execution_stress_grid_summary.json",
        output_dir / "v0_3_finaudit_pilot/finaudit_pilot_summary.json",
        output_dir / "v0_3_finaudit_direct_model_plan/finaudit_direct_model_plan_summary.json",
        output_dir / "v0_3_memory_contamination/memory_contamination_summary.json",
        output_dir / "v0_3_power_note/v0_3_power_note_summary.json",
        output_dir / "v0_3_variance_decomposition/variance_decomposition_summary.json",
        output_dir / "v0_3_contamination_control_audit/contamination_control_audit_summary.json",
        output_dir / "v0_3_claim_boundary_audit/claim_boundary_audit_summary.json",
        output_dir / "v0_3_external_reproduction_gate/external_reproduction_gate_summary.json",
        output_dir / "v0_3_evidence_index/v0_3_evidence_index.json",
    ]


def _run_command(command: dict[str, Any]) -> dict[str, Any]:
    result = subprocess.run(command["argv"], cwd=ROOT, capture_output=True, text=True)
    return {
        "id": command["id"],
        "description": command["description"],
        "argv": _public_argv(command["argv"]),
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def summarize_failed_commands(command_results: list[dict[str, Any]]) -> str:
    failed = [result for result in command_results if result.get("returncode") not in {0, None}]
    if not failed:
        return ""
    lines = ["Failed v0.3 reproduction commands:"]
    for result in failed:
        lines.append(f"- {result.get('id', '<unknown>')} returned {result.get('returncode')}")
        stdout_tail = str(result.get("stdout_tail", "")).strip()
        stderr_tail = str(result.get("stderr_tail", "")).strip()
        if stdout_tail:
            lines.append("  stdout tail:")
            lines.extend(f"    {line}" for line in stdout_tail.splitlines())
        if stderr_tail:
            lines.append("  stderr tail:")
            lines.extend(f"    {line}" for line in stderr_tail.splitlines())
    return "\n".join(lines)


def _hash_trajectory(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"error": f"missing trajectory: {_display_path(path)}"}
    from tradearena.core.reproducibility import hash_trajectory_file

    return hash_trajectory_file(path)


def _artifact_record(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": _display_path(path), "exists": False}
    return {
        "path": _display_path(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _render_readme(manifest: dict[str, Any]) -> str:
    failed_commands = _failed_command_ids(manifest)
    missing_artifacts = _missing_artifact_paths(manifest)
    trajectory_hash = _trajectory_reproducibility_hash(manifest)
    lines = [
        "# TreLLM v0.3 External Reproduction Pack",
        "",
        "This directory is generated by:",
        "",
        "```bash",
        "python scripts/run_v03_external_reproduction_pack.py",
        "```",
        "",
        "It records the commit, environment, v0.3 protocol commands, artifact hashes, and trajectory hash for the no-key protocol reproduction path.",
        "",
        "## Environment",
        "",
        f"- Protocol: `{manifest['protocol_id']}`",
        f"- Environment class: `{manifest['environment_class']}`",
        f"- Report author type: `{manifest['report_author_type']}`",
        f"- Independent reviewer: `{manifest['independent_reviewer']}`",
        f"- Commit/tag: `{manifest['commit_or_tag']}`",
        f"- Python: `{manifest['python']['version']}`",
        f"- Platform: `{manifest['python']['platform']}`",
        f"- Live API used: `{manifest['live_api_used']}`",
        f"- Market data: {manifest['market_data_used']}",
        f"- Private fills used: `{manifest['private_fills_used']}`",
        "",
        "## Commands",
        "",
    ]
    for command in manifest["commands"]:
        lines.append(f"- `{command['id']}`: `{' '.join(command['argv'])}` -> `{command.get('returncode')}`")
    lines.extend(["", "## Artifacts", ""])
    for artifact in manifest["artifacts"]:
        status = "present" if artifact.get("exists") else "missing"
        lines.append(f"- `{artifact['path']}`: {status} {artifact.get('sha256', '')}")
    lines.extend(
        [
            "",
            "## Suggested Issue Text",
            "",
            "```markdown",
            f"Environment: {manifest['environment_class']} / {manifest['python']['platform']} / Python {manifest['python']['version']}",
            f"Commit/tag: {manifest['commit_or_tag']}",
            f"Protocol: {manifest['protocol_id']}",
            f"Trajectory hash: {trajectory_hash}",
            "Manifest: outputs/reproduction/v0_3/manifest.json",
            f"Commands failed: {', '.join(failed_commands) if failed_commands else 'none'}",
            f"Missing artifacts: {', '.join(missing_artifacts) if missing_artifacts else 'none'}",
            f"Independent reviewer: {manifest['independent_reviewer']}",
            "No live APIs or private fills were used.",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _failed_command_ids(manifest: dict[str, Any]) -> list[str]:
    commands = manifest.get("commands", []) if isinstance(manifest.get("commands"), list) else []
    return [str(command.get("id", "")) for command in commands if command.get("returncode") not in {0, None}]


def _missing_artifact_paths(manifest: dict[str, Any]) -> list[str]:
    artifacts = manifest.get("artifacts", []) if isinstance(manifest.get("artifacts"), list) else []
    return [str(artifact.get("path", "")) for artifact in artifacts if not artifact.get("exists")]


def _trajectory_reproducibility_hash(manifest: dict[str, Any]) -> str:
    trajectory_hash = manifest.get("trajectory_hash", {})
    if not isinstance(trajectory_hash, dict):
        return ""
    return str(trajectory_hash.get("reproducibility_hash", ""))


def _default_environment_class() -> str:
    system = platform.system().lower()
    if system in {"windows", "darwin"}:
        return "windows_or_macos"
    return "linux"


def _public_argv(argv: list[Any]) -> list[str]:
    public = [str(item) for item in argv]
    if public and Path(public[0]) == Path(sys.executable):
        public[0] = "python"
    return public


def _public_python_executable() -> str:
    return Path(sys.executable).name or "python"


def _git(args: list[str]) -> str:
    try:
        result = subprocess.run(_git_command(args), cwd=ROOT, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return ""


def _git_command(args: list[str]) -> list[str]:
    return ["git", "-c", f"safe.directory={ROOT.as_posix()}", *args]


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _command_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
