from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

from tradearena.core.reproducibility import sha256_text

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_TASK_MANIFEST = "docs/results/v0_3_finaudit_pilot/finaudit_pilot_task_manifest.csv"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_finaudit_direct_model_plan"
DEFAULT_MODEL_SPECS = ("openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",)
DEFAULT_CONDITIONS = ("cross-audit", "self-audit")
PLAN_FIELDS = [
    "protocol_id",
    "plan_id",
    "task_id",
    "condition",
    "provider",
    "model_id",
    "model_version_or_release",
    "api_endpoint_family",
    "credential_env_var",
    "credential_env_var_present",
    "scenario_id",
    "contamination_tier",
    "difficulty",
    "trajectory_sha256",
    "prompt_sha256",
    "audit_request_packet_sha256",
    "expected_private_response_path",
    "expected_public_score_path",
    "answer_key_public",
    "execution_status",
    "blocking_reasons",
    "claim_scope",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the TreLLM v0.3 FinAudit direct-model audit plan.")
    parser.add_argument("--task-manifest", default=DEFAULT_TASK_MANIFEST)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--models", default=",".join(DEFAULT_MODEL_SPECS))
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--expected-output-root", default="outputs/v0_3_finaudit_direct_model")
    args = parser.parse_args(argv)

    task_manifest = _resolve(args.task_manifest)
    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = _read_rows(task_manifest)
    models = [_parse_model_spec(spec) for spec in _parse_csv_list(args.models)]
    conditions = _parse_csv_list(args.conditions)
    rows = _plan_rows(tasks, models=models, conditions=conditions, expected_output_root=args.expected_output_root)
    coverage_rows = _coverage_rows(rows)
    summary = _summary(task_manifest, rows, coverage_rows, conditions=conditions, models=models)

    _write_csv(output_dir / "finaudit_direct_model_plan_rows.csv", rows, PLAN_FIELDS)
    _write_csv(output_dir / "finaudit_direct_model_plan_coverage.csv", coverage_rows, list(coverage_rows[0]))
    _write_json(output_dir / "finaudit_direct_model_plan_summary.json", summary)
    (output_dir / "finaudit_direct_model_plan.md").write_text(_summary_markdown(summary, coverage_rows), encoding="utf-8")

    print(f"Wrote {_display(output_dir / 'finaudit_direct_model_plan_rows.csv')}")
    print(f"Wrote {_display(output_dir / 'finaudit_direct_model_plan_coverage.csv')}")
    print(f"Wrote {_display(output_dir / 'finaudit_direct_model_plan_summary.json')}")
    print(f"Wrote {_display(output_dir / 'finaudit_direct_model_plan.md')}")
    print(f"Planned audit rows: {len(rows)}")
    print(f"Ready groups: {summary['ready_group_count']}")
    return 0


def _plan_rows(
    tasks: list[dict[str, str]],
    *,
    models: list[dict[str, str]],
    conditions: list[str],
    expected_output_root: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model in models:
        env_present = bool(os.environ.get(model["credential_env_var"]))
        for task in tasks:
            for condition in conditions:
                plan_id = _safe("__".join([model["provider"], model["model_id"], task["task_id"], condition]))
                request_packet = {
                    "task_id": task["task_id"],
                    "condition": condition,
                    "trajectory_sha256": task["trajectory_sha256"],
                    "prompt_sha256": task["prompt_sha256"],
                    "answer_key_public": False,
                    "auditor_model": model["model_id"],
                }
                blocking = [] if env_present else ["credential_env_var_missing"]
                rows.append(
                    {
                        "protocol_id": PROTOCOL_ID,
                        "plan_id": plan_id,
                        "task_id": task["task_id"],
                        "condition": condition,
                        "provider": model["provider"],
                        "model_id": model["model_id"],
                        "model_version_or_release": model["model_version_or_release"],
                        "api_endpoint_family": model["api_endpoint_family"],
                        "credential_env_var": model["credential_env_var"],
                        "credential_env_var_present": str(env_present).lower(),
                        "scenario_id": task["scenario_id"],
                        "contamination_tier": task["contamination_tier"],
                        "difficulty": task["difficulty"],
                        "trajectory_sha256": task["trajectory_sha256"],
                        "prompt_sha256": task["prompt_sha256"],
                        "audit_request_packet_sha256": sha256_text(
                            json.dumps(request_packet, sort_keys=True, separators=(",", ":"))
                        ),
                        "expected_private_response_path": f"{expected_output_root}/private_responses/{plan_id}.json",
                        "expected_public_score_path": f"{expected_output_root}/public_scores/{plan_id}.json",
                        "answer_key_public": str(task.get("answer_key_public", "False")).lower(),
                        "execution_status": "not_run",
                        "blocking_reasons": ";".join(blocking),
                        "claim_scope": (
                            "Pre-registered direct-model FinAudit auditor call. It is not evidence until a "
                            "direct-provider response is privately scored against the non-public answer key."
                        ),
                    }
                )
    return rows


def _coverage_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["provider"]), str(row["model_id"]), str(row["condition"])), []).append(row)
    output: list[dict[str, Any]] = []
    for (provider, model_id, condition), group in sorted(grouped.items()):
        task_count = len({row["task_id"] for row in group})
        credential_ready = all(row["credential_env_var_present"] == "true" for row in group)
        output.append(
            {
                "protocol_id": PROTOCOL_ID,
                "provider": provider,
                "model_id": model_id,
                "condition": condition,
                "planned_task_count": task_count,
                "planned_row_count": len(group),
                "credential_env_var": group[0]["credential_env_var"],
                "credential_env_var_present": str(credential_ready).lower(),
                "execution_status": "ready" if credential_ready else "blocked",
                "blocking_reasons": "" if credential_ready else "credential_env_var_missing",
            }
        )
    return output


def _summary(
    task_manifest: Path,
    rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    *,
    conditions: list[str],
    models: list[dict[str, str]],
) -> dict[str, Any]:
    ready = [row for row in coverage_rows if row["execution_status"] == "ready"]
    return {
        "schema": "trellm_v0_3_finaudit_direct_model_plan_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "finaudit_direct_model_plan",
        "source_task_manifest": _display(task_manifest),
        "planned_row_count": len(rows),
        "coverage_group_count": len(coverage_rows),
        "ready_group_count": len(ready),
        "task_count": len({row["task_id"] for row in rows}),
        "conditions": conditions,
        "planned_models": [
            {
                "provider": model["provider"],
                "model_id": model["model_id"],
                "model_version_or_release": model["model_version_or_release"],
                "api_endpoint_family": model["api_endpoint_family"],
                "credential_env_var": model["credential_env_var"],
            }
            for model in models
        ],
        "answer_key_public": False,
        "all_rows_not_run": all(row["execution_status"] == "not_run" for row in rows),
        "claim_boundary": (
            "This artifact pre-registers direct-model FinAudit auditor calls. It does not call providers, "
            "publish answer keys, publish raw responses, or support model audit-performance claims."
        ),
        "artifacts": [
            "finaudit_direct_model_plan_rows.csv",
            "finaudit_direct_model_plan_coverage.csv",
            "finaudit_direct_model_plan_summary.json",
            "finaudit_direct_model_plan.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], coverage_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 FinAudit Direct-Model Plan",
        "",
        "This artifact pre-registers direct-model auditor calls for FinAudit tasks.",
        "It does not call providers, publish raw responses, or publish answer keys.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Source task manifest: `{summary['source_task_manifest']}`",
        f"- Planned rows: `{summary['planned_row_count']}`",
        f"- Task count: `{summary['task_count']}`",
        f"- Ready groups: `{summary['ready_group_count']}`",
        f"- Answer key public: `{summary['answer_key_public']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Coverage Groups",
        "",
        "| Provider | Model | Condition | Tasks | Rows | Env var | Env present | Status | Blocking reasons |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in coverage_rows:
        lines.append(
            f"| {row['provider']} | {row['model_id']} | {row['condition']} | {row['planned_task_count']} | "
            f"{row['planned_row_count']} | {row['credential_env_var']} | {row['credential_env_var_present']} | "
            f"{row['execution_status']} | {row['blocking_reasons']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _parse_model_spec(value: str) -> dict[str, str]:
    parts = value.split(":")
    if len(parts) != 5 or any(not part.strip() for part in parts):
        raise SystemExit(
            "--models entries must use provider:model_id:model_version_or_release:api_endpoint_family:credential_env_var"
        )
    provider, model_id, version, endpoint, env_var = [part.strip() for part in parts]
    return {
        "provider": provider,
        "model_id": model_id,
        "model_version_or_release": version,
        "api_endpoint_family": endpoint,
        "credential_env_var": env_var,
    }


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_csv_list(value: str) -> list[str]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    if not values:
        raise SystemExit("comma-separated values must contain at least one item")
    return values


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _safe(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
