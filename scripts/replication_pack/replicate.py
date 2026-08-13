"""Single-command deterministic replication entry for the TradeArena benchmark pack.

Runs the zero-API-key deterministic anchor arms of the TradeArena v0.3 protocol
(classical-agent leaderboard across the E0/E1 execution ladder with 30 seeds,
plus the power/detectable-effect statistics note and a replayable trajectory),
then compares every produced number against ``expected_results/expected_results.json``
within documented tolerances and prints a PASS/FAIL verdict.

Usage (from the pack root, Python >= 3.10, standard library only):

    python replicate.py --environment-class linux

Outputs are written under ``outputs/``:

- ``outputs/replication_report.json``  machine-readable report (intake-gate schema)
- ``outputs/REPLICATION_REPORT.md``    pre-filled human report to sign and return

No API keys, network access, or third-party packages are required. This pack
evaluates protocol reproducibility only; it makes no trading-profit claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

PACK_ID = "tradearena-replication-pack-v1"
PACK_VERSION = "1.0.0"
PROTOCOL_ID = "trellm-v0.3-protocol"
REPORT_SCHEMA = "tradearena_external_reproduction_pack_v1"
EXPECTED_SCHEMA = "tradearena_replication_pack_expected_v1"
PROTOCOL_PATH = "benchmarks/v0.3/protocol.json"
EXPECTED_PATH = ROOT / "expected_results" / "expected_results.json"
MANIFEST_PATH = ROOT / "PACK_MANIFEST.json"
ENVIRONMENT_CLASSES = ("windows_or_macos", "linux", "colab_or_binder")

# Tolerances for float comparisons. Every compared artifact float is rounded to
# 6 decimals by the generating scripts, so a one-ulp libm difference across
# platforms can move a value by at most one rounding step (1e-6). The absolute
# tolerance absorbs that step; the relative term covers larger magnitudes.
ABS_TOL = 2e-6
REL_TOL = 1e-6

LEVELS = "E0,E1"
TOP_K = 3
FULL_AGENTS = (
    "always-hold,buy-and-hold,equal-weight,random,naive-momentum,mean-reversion,"
    "sma-crossover,risk-parity,min-var,markowitz-mvo,no-trade-band,signal-weighted"
)
FULL_SEEDS = ",".join(str(seed) for seed in range(101, 131))
FULL_PERIODS = 45
QUICK_AGENTS = "signal-weighted,naive-momentum,risk-parity,random"
QUICK_SEEDS = ",".join(str(seed) for seed in range(101, 106))
QUICK_PERIODS = 24

LADDER_AGG_INT_FIELDS = ("rank", "run_count")
LADDER_AGG_FLOAT_FIELDS = (
    "sharpe_mean",
    "sharpe_std",
    "sharpe_ci_low",
    "sharpe_ci_high",
    "total_return_mean",
    "max_drawdown_mean",
    "execution_fill_rate_mean",
    "rejected_order_count_mean",
    "total_slippage_cost_mean",
    "intent_execution_gap_l1_mean",
)
STABILITY_INT_FIELDS = ("agent_count",)
STABILITY_FLOAT_FIELDS = (
    "kendall_tau",
    "top_k_jaccard",
    "mean_return_delta_vs_e0",
    "mean_fill_rate_delta_vs_e0",
    "mean_intent_execution_gap_delta_vs_e0",
    "mean_slippage_delta_vs_e0",
)
POWER_FLOAT_FIELDS = ("observed_cohens_d", "power")
DETECTABLE_FLOAT_FIELDS = ("minimum_detectable_cohens_d",)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the TradeArena deterministic replication pack.")
    parser.add_argument(
        "--environment-class",
        choices=ENVIRONMENT_CLASSES,
        default=_default_environment_class(),
        help="Environment class recorded in the report (windows_or_macos, linux, colab_or_binder).",
    )
    parser.add_argument("--quick", action="store_true", help="Fast smoke subset; not valid for a replication report.")
    parser.add_argument(
        "--write-expected",
        action="store_true",
        help="Maintainer freeze mode: run the full anchors and write expected_results/expected_results.json.",
    )
    parser.add_argument(
        "--maintainer",
        action="store_true",
        help="Mark the report as project-maintainer authored (smoke test, not independent evidence).",
    )
    parser.add_argument(
        "--repository-url",
        default=f"pack:{PACK_ID}",
        help="Where you obtained this pack (repository or release URL). Use the URL from your invitation if any.",
    )
    parser.add_argument("--reviewer-name", default="", help="Optional reviewer name for the report.")
    parser.add_argument("--affiliation", default="", help="Optional reviewer affiliation for the report.")
    parser.add_argument("--contact", default="", help="Optional reviewer contact for the report.")
    parser.add_argument("--output-dir", default="outputs", help="Output directory relative to the pack root.")
    args = parser.parse_args(argv)

    if args.write_expected and args.quick:
        raise SystemExit("--write-expected requires the full anchor configuration; drop --quick.")

    # Anchor all relative paths (including hashed trajectory paths) at the pack
    # root so reports never embed machine-specific absolute paths.
    os.chdir(ROOT)
    started = time.perf_counter()
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = "quick" if args.quick else "full"
    maintainer = bool(args.maintainer or args.write_expected)

    print(f"TradeArena replication pack {PACK_VERSION} ({mode} mode)")
    print(f"Python {platform.python_version()} on {platform.platform()}")

    checks: list[dict[str, Any]] = []
    integrity = _pack_integrity_check(skip=args.write_expected)
    if integrity is not None:
        checks.append(integrity)

    command_results = [_run_step(step) for step in _steps(quick=args.quick, output_dir=output_dir)]
    trajectory = _trajectory_facts(output_dir)
    actual = _collect_actual(output_dir, trajectory)

    if args.write_expected:
        expected = _as_expected_payload(actual)
        EXPECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXPECTED_PATH.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {EXPECTED_PATH.relative_to(ROOT).as_posix()}")
        overall_pass: bool | None = None
        strict_checks: list[dict[str, Any]] = []
    elif args.quick:
        overall_pass = None
        strict_checks = []
        print("Quick smoke mode: pipeline executed; no expected-results comparison performed.")
    else:
        expected = _load_expected()
        hard, strict_checks = _compare_all(actual, expected)
        checks.extend(hard)
        overall_pass = all(check["status"] == "PASS" for check in checks) and _commands_ok(command_results)

    report = _report_payload(
        args=args,
        mode=mode,
        maintainer=maintainer,
        command_results=command_results,
        output_dir=output_dir,
        trajectory=trajectory,
        checks=checks,
        strict_checks=strict_checks,
        overall_pass=overall_pass,
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    report_path = output_dir / "replication_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "REPLICATION_REPORT.md").write_text(_report_markdown(report), encoding="utf-8")

    _print_summary(report)
    print(f"Wrote {report_path.relative_to(ROOT).as_posix()}")
    print(f"Wrote {(output_dir / 'REPLICATION_REPORT.md').relative_to(ROOT).as_posix()}")

    if not _commands_ok(command_results):
        return 1
    if overall_pass is False:
        return 1
    return 0


def _steps(*, quick: bool, output_dir: Path) -> list[dict[str, Any]]:
    agents = QUICK_AGENTS if quick else FULL_AGENTS
    seeds = QUICK_SEEDS if quick else FULL_SEEDS
    periods = QUICK_PERIODS if quick else FULL_PERIODS
    ladder_dir = _rel(output_dir / "anchor_execution_ladder")
    power_dir = _rel(output_dir / "anchor_power_note")
    power_args = (
        ["--repeat-levels", "6,10", "--effect-sizes", "0.8", "--target-powers", "0.5", "--draws", "30", "--permutation-draws", "128", "--seed", "3"]
        if quick
        else ["--repeat-levels", "6,10", "--effect-sizes", "0.5,0.8,1.2", "--target-powers", "0.8", "--draws", "80", "--permutation-draws", "256", "--seed", "2026"]
    )
    return [
        {
            "id": "validate_protocol",
            "argv": [sys.executable, "scripts/validate_benchmark_spec.py", PROTOCOL_PATH],
            "description": "Validate the frozen v0.3 protocol contract and print its canonical hash.",
        },
        {
            "id": "deterministic_trajectory",
            "argv": [sys.executable, "examples/audit_trajectory_walkthrough.py"],
            "description": "Generate the deterministic replayable trajectory used for the reproducibility hash.",
        },
        {
            "id": "anchor_execution_ladder",
            "argv": [
                sys.executable,
                "scripts/run_v03_execution_ladder.py",
                "--output-dir",
                ladder_dir,
                "--agents",
                agents,
                "--levels",
                LEVELS,
                "--seeds",
                seeds,
                "--periods",
                str(periods),
                "--top-k",
                str(TOP_K),
            ],
            "description": "Classical-agent leaderboard across the E0/E1 execution ladder (C0 synthetic, CPU only).",
        },
        {
            "id": "anchor_power_note",
            "argv": [sys.executable, "scripts/run_v03_power_note.py", "--output-dir", power_dir, *power_args],
            "description": "Bootstrap/permutation power curves and smallest detectable effect note.",
        },
    ]


def _run_step(step: dict[str, Any]) -> dict[str, Any]:
    print(f"[{step['id']}] running ...", flush=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    started = time.perf_counter()
    result = subprocess.run(step["argv"], cwd=ROOT, env=env, capture_output=True, text=True)
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[{step['id']}] returncode={result.returncode} elapsed={elapsed}s")
    return {
        "id": step["id"],
        "description": step["description"],
        "argv": _public_argv(step["argv"]),
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def _pack_integrity_check(*, skip: bool) -> dict[str, Any] | None:
    if skip or not MANIFEST_PATH.exists():
        return None
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mismatches: list[str] = []
    for rel_path, expected_hash in sorted(manifest.get("files", {}).items()):
        path = ROOT / rel_path
        if not path.exists():
            mismatches.append(f"missing: {rel_path}")
        elif _sha256_file(path) != expected_hash:
            mismatches.append(f"modified: {rel_path}")
    return _check(
        "pack_integrity",
        passed=not mismatches,
        detail=mismatches[:10] or [f"{len(manifest.get('files', {}))} files verified"],
    )


def _trajectory_facts(output_dir: Path) -> dict[str, Any]:
    path = ROOT / "outputs" / "examples" / "audit_walkthrough_trajectory.json"
    if not path.exists():
        return {"exists": False, "path": _rel(path)}
    from tradearena.core.reproducibility import canonical_json, hash_trajectory_file, sha256_text

    payload = json.loads(path.read_text(encoding="utf-8"))
    # Hash via the pack-relative path (cwd is the pack root) so the recorded
    # trajectory manifest is identical on every machine.
    relative_path = Path(_rel(path))
    return {
        "exists": True,
        "path": _rel(path),
        "experiment_name": payload.get("experiment_name"),
        "seed": payload.get("seed"),
        "schema_version": payload.get("schema_version"),
        "step_count": len(payload.get("steps", [])),
        "canonical_content_sha256": sha256_text(canonical_json(payload)),
        "file_hash": hash_trajectory_file(relative_path),
    }


def _collect_actual(output_dir: Path, trajectory: dict[str, Any]) -> dict[str, Any]:
    from validate_benchmark_spec import canonical_spec_hash, validate_spec

    protocol_payload = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    ladder_dir = output_dir / "anchor_execution_ladder"
    power_dir = output_dir / "anchor_power_note"
    return {
        "protocol": {
            "protocol_id": protocol_payload.get("protocol_id"),
            "validation_errors": validate_spec(protocol_payload),
            "canonical_sha256": canonical_spec_hash(protocol_payload),
        },
        "trajectory": trajectory,
        "ladder_aggregate": _read_csv(ladder_dir / "execution_ladder_aggregate.csv"),
        "ladder_stability": _read_csv(ladder_dir / "execution_ladder_ranking_stability.csv"),
        "power_curves": _read_csv(power_dir / "v0_3_power_curves.csv"),
        "detectable_effects": _read_csv(power_dir / "v0_3_detectable_effects.csv"),
    }


def _as_expected_payload(actual: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": EXPECTED_SCHEMA,
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "protocol_id": PROTOCOL_ID,
        "created_at": _utc_now(),
        "source_python": platform.python_version(),
        "source_platform": platform.platform(),
        "tolerances": {"abs": ABS_TOL, "rel": REL_TOL},
        "anchor_config": {
            "agents": FULL_AGENTS.split(","),
            "levels": LEVELS.split(","),
            "seeds": [int(seed) for seed in FULL_SEEDS.split(",")],
            "periods": FULL_PERIODS,
            "top_k": TOP_K,
        },
        "protocol": {
            "protocol_id": actual["protocol"]["protocol_id"],
            "canonical_sha256": actual["protocol"]["canonical_sha256"],
        },
        "trajectory": {
            "experiment_name": actual["trajectory"].get("experiment_name"),
            "seed": actual["trajectory"].get("seed"),
            "schema_version": actual["trajectory"].get("schema_version"),
            "step_count": actual["trajectory"].get("step_count"),
            "canonical_content_sha256": actual["trajectory"].get("canonical_content_sha256"),
            "reproducibility_hash": (actual["trajectory"].get("file_hash") or {}).get("reproducibility_hash"),
        },
        "ladder_aggregate": actual["ladder_aggregate"],
        "ladder_stability": actual["ladder_stability"],
        "power_curves": actual["power_curves"],
        "detectable_effects": actual["detectable_effects"],
    }


def _load_expected() -> dict[str, Any]:
    if not EXPECTED_PATH.exists():
        raise SystemExit(f"Missing {_rel(EXPECTED_PATH)}; this pack was not frozen with expected results.")
    payload = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != EXPECTED_SCHEMA:
        raise SystemExit(f"Unexpected expected-results schema: {payload.get('schema')}")
    return payload


def _compare_all(actual: dict[str, Any], expected: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hard: list[dict[str, Any]] = []
    hard.append(
        _check(
            "protocol_valid",
            passed=not actual["protocol"]["validation_errors"],
            detail=actual["protocol"]["validation_errors"][:5] or ["protocol contract validates"],
        )
    )
    hard.append(
        _equal_check(
            "protocol_canonical_hash",
            actual["protocol"]["canonical_sha256"],
            expected["protocol"]["canonical_sha256"],
        )
    )
    trajectory_expected = expected["trajectory"]
    trajectory_actual = actual["trajectory"]
    structure_pairs = [
        (field, trajectory_actual.get(field), trajectory_expected.get(field))
        for field in ("experiment_name", "seed", "schema_version", "step_count")
    ]
    structure_mismatches = [
        f"{field}: actual={value!r} expected={target!r}" for field, value, target in structure_pairs if value != target
    ]
    hard.append(
        _check(
            "trajectory_structure",
            passed=trajectory_actual.get("exists", False) and not structure_mismatches,
            detail=structure_mismatches[:5] or ["experiment name, seed, schema, and step count match"],
        )
    )
    hard.append(
        _table_check(
            "ladder_aggregate",
            actual["ladder_aggregate"],
            expected["ladder_aggregate"],
            key_fields=("execution_level", "agent"),
            int_fields=LADDER_AGG_INT_FIELDS,
            float_fields=LADDER_AGG_FLOAT_FIELDS,
        )
    )
    hard.append(
        _table_check(
            "ladder_ranking_stability",
            actual["ladder_stability"],
            expected["ladder_stability"],
            key_fields=("baseline_level", "comparison_level"),
            int_fields=STABILITY_INT_FIELDS,
            float_fields=STABILITY_FLOAT_FIELDS,
        )
    )
    hard.append(
        _table_check(
            "power_curves",
            actual["power_curves"],
            expected["power_curves"],
            key_fields=("mode", "effect_label", "repeat_count"),
            int_fields=(),
            float_fields=POWER_FLOAT_FIELDS,
        )
    )
    hard.append(
        _table_check(
            "detectable_effects",
            actual["detectable_effects"],
            expected["detectable_effects"],
            key_fields=("repeat_count", "target_power"),
            int_fields=(),
            float_fields=DETECTABLE_FLOAT_FIELDS,
            str_fields=("grid_status",),
        )
    )
    strict = [
        _equal_check(
            "strict_trajectory_content_hash",
            trajectory_actual.get("canonical_content_sha256"),
            trajectory_expected.get("canonical_content_sha256"),
            strict=True,
        ),
        _equal_check(
            "strict_trajectory_file_hash",
            (trajectory_actual.get("file_hash") or {}).get("reproducibility_hash"),
            trajectory_expected.get("reproducibility_hash"),
            strict=True,
        ),
    ]
    return hard, strict


def _table_check(
    name: str,
    actual_rows: list[dict[str, Any]],
    expected_rows: list[dict[str, Any]],
    *,
    key_fields: tuple[str, ...],
    int_fields: tuple[str, ...],
    float_fields: tuple[str, ...],
    str_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    actual_by_key = {_row_key(row, key_fields): row for row in actual_rows}
    expected_by_key = {_row_key(row, key_fields): row for row in expected_rows}
    mismatches: list[str] = []
    for key in sorted(expected_by_key):
        expected_row = expected_by_key[key]
        actual_row = actual_by_key.get(key)
        if actual_row is None:
            mismatches.append(f"missing row {key}")
            continue
        for field in int_fields:
            if _as_int(actual_row.get(field)) != _as_int(expected_row.get(field)):
                mismatches.append(f"{key} {field}: actual={actual_row.get(field)} expected={expected_row.get(field)}")
        for field in float_fields:
            if not _float_close(_as_float(actual_row.get(field)), _as_float(expected_row.get(field))):
                mismatches.append(f"{key} {field}: actual={actual_row.get(field)} expected={expected_row.get(field)}")
        for field in str_fields:
            if str(actual_row.get(field, "")) != str(expected_row.get(field, "")):
                mismatches.append(f"{key} {field}: actual={actual_row.get(field)} expected={expected_row.get(field)}")
    extra = sorted(set(actual_by_key) - set(expected_by_key))
    if extra:
        mismatches.append(f"unexpected rows: {extra[:5]}")
    detail = mismatches[:10] if mismatches else [f"{len(expected_by_key)} rows compared within tolerance"]
    return _check(name, passed=not mismatches, detail=detail, mismatch_count=len(mismatches))


def _float_close(actual: float | None, expected: float | None) -> bool:
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
    return abs(actual - expected) <= max(ABS_TOL, REL_TOL * abs(expected))


def _row_key(row: dict[str, Any], key_fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "")) for field in key_fields)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _equal_check(name: str, actual: Any, expected: Any, *, strict: bool = False) -> dict[str, Any]:
    passed = actual == expected and actual is not None
    detail = ["match"] if passed else [f"actual={actual!r}", f"expected={expected!r}"]
    payload = _check(name, passed=passed, detail=detail)
    if strict:
        payload["tier"] = "strict-informational"
        payload["status"] = "STRICT_PASS" if passed else "STRICT_DIFFER"
    return payload


def _check(name: str, *, passed: bool, detail: list[str], **extra: Any) -> dict[str, Any]:
    return {"id": name, "status": "PASS" if passed else "FAIL", "detail": detail, "tier": "hard", **extra}


def _commands_ok(command_results: list[dict[str, Any]]) -> bool:
    return all(result.get("returncode") == 0 for result in command_results)


def _report_payload(
    *,
    args: argparse.Namespace,
    mode: str,
    maintainer: bool,
    command_results: list[dict[str, Any]],
    output_dir: Path,
    trajectory: dict[str, Any],
    checks: list[dict[str, Any]],
    strict_checks: list[dict[str, Any]],
    overall_pass: bool | None,
    elapsed_seconds: float,
) -> dict[str, Any]:
    manifest_hash = _sha256_file(MANIFEST_PATH) if MANIFEST_PATH.exists() else ""
    artifacts = [_artifact_record(path) for path in _artifact_paths(output_dir)]
    return {
        "schema": REPORT_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "pack_manifest_sha256": manifest_hash,
        "replication_mode": mode,
        "environment_class": args.environment_class,
        "report_author_type": "project-maintainer" if maintainer else "independent",
        "independent_reviewer": not maintainer,
        "created_at": _utc_now(),
        "repository": args.repository_url,
        "commit_or_tag": f"{PACK_ID}@{PACK_VERSION}",
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": Path(sys.executable).name or "python",
            "platform": platform.platform(),
        },
        "commands": command_results,
        "artifacts": artifacts,
        "trajectory_hash": trajectory.get("file_hash", {"error": "missing trajectory"}),
        "live_api_used": False,
        "market_data_used": "deterministic synthetic market paths generated inside the pack (contamination tier C0)",
        "private_fills_used": False,
        "verification": {
            "overall_pass": overall_pass,
            "hard_checks": checks,
            "strict_checks": strict_checks,
            "tolerances": {"abs": ABS_TOL, "rel": REL_TOL},
            "elapsed_seconds_total": elapsed_seconds,
        },
        "reviewer": {
            "name": args.reviewer_name,
            "affiliation": args.affiliation,
            "contact": args.contact,
        },
        "notes": (
            "Deterministic zero-key replication of the TradeArena v0.3 anchor arms: classical-agent "
            "leaderboard across execution levels E0/E1 with 30 seeds, statistics power note, protocol "
            "validation, and a replayable trajectory. This is protocol-reproducibility evidence only; "
            "it is not a trading-profit claim."
        ),
    }


def _artifact_paths(output_dir: Path) -> list[Path]:
    return [
        ROOT / "outputs" / "examples" / "audit_walkthrough_trajectory.json",
        output_dir / "anchor_execution_ladder" / "execution_ladder_rows.csv",
        output_dir / "anchor_execution_ladder" / "execution_ladder_aggregate.csv",
        output_dir / "anchor_execution_ladder" / "execution_ladder_ranking_stability.csv",
        output_dir / "anchor_execution_ladder" / "execution_ladder_summary.json",
        output_dir / "anchor_power_note" / "v0_3_power_curves.csv",
        output_dir / "anchor_power_note" / "v0_3_detectable_effects.csv",
        output_dir / "anchor_power_note" / "v0_3_power_note_summary.json",
    ]


def _artifact_record(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": _rel(path), "exists": False}
    return {"path": _rel(path), "exists": True, "bytes": path.stat().st_size, "sha256": _sha256_file(path)}


def _report_markdown(report: dict[str, Any]) -> str:
    verification = report["verification"]
    verdict = _verdict_label(verification["overall_pass"], report["replication_mode"])
    lines = [
        "# TradeArena Replication Pack Report",
        "",
        f"**Verdict: {verdict}**",
        "",
        f"- Pack: `{report['pack_id']}` v{report['pack_version']}",
        f"- Protocol: `{report['protocol_id']}`",
        f"- Mode: `{report['replication_mode']}`",
        f"- Environment class: `{report['environment_class']}`",
        f"- Python: `{report['python']['version']}` ({report['python']['implementation']})",
        f"- Platform: `{report['python']['platform']}`",
        f"- Created: `{report['created_at']}`",
        f"- Total wall-clock: `{verification['elapsed_seconds_total']} s`",
        f"- Live APIs used: `{report['live_api_used']}`  Private data used: `{report['private_fills_used']}`",
        "",
        "## Commands",
        "",
        "| Step | Return code | Elapsed (s) |",
        "| --- | ---: | ---: |",
    ]
    lines.extend(
        f"| `{command['id']}` | {command['returncode']} | {command['elapsed_seconds']} |"
        for command in report["commands"]
    )
    lines += ["", "## Checks (tolerance tier)", ""]
    if verification["hard_checks"]:
        lines += ["| Check | Status | Detail |", "| --- | --- | --- |"]
        lines.extend(
            f"| `{check['id']}` | {check['status']} | {'; '.join(str(item) for item in check['detail'][:3])} |"
            for check in verification["hard_checks"]
        )
    else:
        lines.append("(no expected-results comparison in this mode)")
    lines += ["", "## Strict determinism checks (informational)", ""]
    if verification["strict_checks"]:
        lines += ["| Check | Status |", "| --- | --- |"]
        lines.extend(f"| `{check['id']}` | {check['status']} |" for check in verification["strict_checks"])
        lines += [
            "",
            "Strict checks compare exact hashes. `STRICT_DIFFER` with all tolerance checks passing",
            "usually indicates last-digit libm differences across platforms and does not fail the replication.",
        ]
    else:
        lines.append("(not computed in this mode)")
    lines += [
        "",
        "## Reviewer sign-off (fill in and return with outputs/replication_report.json)",
        "",
        f"- Name: {report['reviewer']['name'] or '_______________'}",
        f"- Affiliation: {report['reviewer']['affiliation'] or '_______________'}",
        f"- Contact: {report['reviewer']['contact'] or '_______________'}",
        "- Date: _______________",
        "- How I obtained this pack (URL or note): _______________",
        "- Deviations from the README instructions (if any): none / _______________",
        "- I am not an author or maintainer of this project: yes / no",
        "- I used no API keys and no private data: yes / no",
        "- Signature: _______________",
        "",
    ]
    return "\n".join(lines)


def _print_summary(report: dict[str, Any]) -> None:
    verification = report["verification"]
    print("")
    print("=" * 60)
    for check in verification["hard_checks"]:
        print(f"  {check['status']:<6} {check['id']}")
        if check["status"] != "PASS":
            for item in check["detail"][:5]:
                print(f"         - {item}")
    for check in verification["strict_checks"]:
        print(f"  {check['status']:<13} {check['id']}")
    print("-" * 60)
    print(f"  OVERALL: {_verdict_label(verification['overall_pass'], report['replication_mode'])}")
    print(f"  Total wall-clock: {verification['elapsed_seconds_total']} s")
    print("=" * 60)


def _verdict_label(overall_pass: bool | None, mode: str) -> str:
    if overall_pass is True:
        return "PASS"
    if overall_pass is False:
        return "FAIL"
    return "SMOKE-ONLY (no verdict)" if mode == "quick" else "EXPECTED-RESULTS WRITTEN (maintainer freeze)"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _public_argv(argv: list[Any]) -> list[str]:
    public = [str(item) for item in argv]
    if public and Path(public[0]) == Path(sys.executable):
        public[0] = "python"
    return public


def _default_environment_class() -> str:
    system = platform.system().lower()
    if system in {"windows", "darwin"}:
        return "windows_or_macos"
    return "linux"


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
