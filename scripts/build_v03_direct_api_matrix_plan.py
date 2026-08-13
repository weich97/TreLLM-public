from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_direct_api_matrix_plan"
DEFAULT_MODEL_SPECS = (
    "openai:gpt-5.5:fixture-2026-05-17:responses:OPENAI_API_KEY",
)
DEFAULT_SCENARIOS = ("synthetic_calm_trend_c0_v0_3",)
DEFAULT_SEEDS = (7, 11, 17, 23, 31, 37, 41, 43, 47, 53)
DEFAULT_SAMPLES = (0, 1, 2)
REQUIRED_SEEDS = 10
REQUIRED_SAMPLES_PER_SEED = 3
PLAN_FIELDS = [
    "protocol_id",
    "plan_id",
    "provider",
    "model_id",
    "model_version_or_release",
    "api_endpoint_family",
    "credential_env_var",
    "credential_env_var_present",
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "seed",
    "sample_index",
    "prompt_template_id",
    "prompt_version",
    "temperature",
    "top_p",
    "max_tokens",
    "expected_provider_manifest_path",
    "expected_submission_path",
    "claim_scope",
]
COVERAGE_FIELDS = [
    "protocol_id",
    "provider",
    "model_id",
    "scenario_id",
    "contamination_tier",
    "execution_level",
    "planned_row_count",
    "planned_seed_count",
    "planned_minimum_samples_per_seed",
    "required_seed_count",
    "required_samples_per_seed",
    "main_threshold_target_met_by_plan",
    "credential_env_var",
    "credential_env_var_present",
    "preflight_status",
    "blocking_reasons",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the TreLLM v0.3 direct API matrix plan and preflight artifact."
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--models", default=",".join(DEFAULT_MODEL_SPECS))
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS))
    parser.add_argument("--contamination-tier", choices=["C0", "C1", "C2"], default="C0")
    parser.add_argument("--execution-level", choices=["E0", "E1", "E2", "E3"], default="E1")
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--samples", default=",".join(str(sample) for sample in DEFAULT_SAMPLES))
    parser.add_argument("--prompt-template-id", default="trellm-allocation-v0.3")
    parser.add_argument("--prompt-version", default="v0.3.0")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--expected-output-root", default="outputs/v0_3_direct_api_matrix")
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models = [_parse_model_spec(spec) for spec in _parse_csv_list(args.models)]
    scenarios = _parse_csv_list(args.scenarios)
    seeds = _parse_ints(args.seeds, "seeds")
    samples = _parse_ints(args.samples, "samples")
    _validate_args(models, scenarios, seeds, samples, args.temperature, args.top_p, args.max_tokens)

    plan_rows = _plan_rows(args, models=models, scenarios=scenarios, seeds=seeds, samples=samples)
    coverage_rows = _coverage_rows(plan_rows)
    summary = _summary(
        plan_rows,
        coverage_rows,
        seeds=seeds,
        samples=samples,
        scenarios=scenarios,
        models=models,
        expected_output_root=args.expected_output_root,
    )

    _write_csv(output_dir / "direct_api_matrix_plan_rows.csv", plan_rows, PLAN_FIELDS)
    _write_csv(output_dir / "direct_api_matrix_plan_coverage.csv", coverage_rows, COVERAGE_FIELDS)
    _write_json(output_dir / "direct_api_matrix_plan_summary.json", summary)
    (output_dir / "direct_api_matrix_plan_summary.md").write_text(
        _summary_markdown(summary, coverage_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_plan_rows.csv')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_plan_coverage.csv')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_plan_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_matrix_plan_summary.md')}")
    print(f"Planned rows: {len(plan_rows)}")
    print(f"Coverage groups: {len(coverage_rows)}")
    print(f"Ready groups: {sum(1 for row in coverage_rows if row['preflight_status'] == 'ready')}")
    return 0


def _plan_rows(
    args: argparse.Namespace,
    *,
    models: list[dict[str, str]],
    scenarios: list[str],
    seeds: list[int],
    samples: list[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model in models:
        env_present = bool(os.environ.get(model["credential_env_var"]))
        for scenario_id in scenarios:
            for seed in seeds:
                for sample_index in samples:
                    plan_id = _safe(
                        "__".join(
                            [
                                model["provider"],
                                model["model_id"],
                                scenario_id,
                                args.contamination_tier,
                                args.execution_level,
                                f"seed-{seed}",
                                f"sample-{sample_index}",
                            ]
                        )
                    )
                    rows.append(
                        {
                            "protocol_id": PROTOCOL_ID,
                            "plan_id": plan_id,
                            "provider": model["provider"],
                            "model_id": model["model_id"],
                            "model_version_or_release": model["model_version_or_release"],
                            "api_endpoint_family": model["api_endpoint_family"],
                            "credential_env_var": model["credential_env_var"],
                            "credential_env_var_present": str(env_present).lower(),
                            "scenario_id": scenario_id,
                            "contamination_tier": args.contamination_tier,
                            "execution_level": args.execution_level,
                            "seed": seed,
                            "sample_index": sample_index,
                            "prompt_template_id": args.prompt_template_id,
                            "prompt_version": args.prompt_version,
                            "temperature": args.temperature,
                            "top_p": args.top_p,
                            "max_tokens": args.max_tokens,
                            "expected_provider_manifest_path": (
                                f"{args.expected_output_root}/provider_manifests/{plan_id}.json"
                            ),
                            "expected_submission_path": f"{args.expected_output_root}/submissions/{plan_id}.json",
                            "claim_scope": (
                                "Pre-registered direct API matrix call plan. This row is not evidence until a "
                                "hash-only provider manifest and benchmark submission are generated."
                            ),
                        }
                    )
    return rows


def _coverage_rows(plan_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for row in plan_rows:
        key = (
            str(row["provider"]),
            str(row["model_id"]),
            str(row["scenario_id"]),
            str(row["contamination_tier"]),
            str(row["execution_level"]),
        )
        grouped.setdefault(key, []).append(row)

    rows: list[dict[str, Any]] = []
    for (provider, model_id, scenario_id, tier, execution_level), group_rows in sorted(grouped.items()):
        samples_by_seed: dict[str, set[str]] = {}
        for row in group_rows:
            samples_by_seed.setdefault(str(row["seed"]), set()).add(str(row["sample_index"]))
        planned_seed_count = len(samples_by_seed)
        planned_minimum_samples = min((len(samples) for samples in samples_by_seed.values()), default=0)
        threshold_met = planned_seed_count >= REQUIRED_SEEDS and planned_minimum_samples >= REQUIRED_SAMPLES_PER_SEED
        env_var = str(group_rows[0]["credential_env_var"]) if group_rows else ""
        env_present = bool(group_rows and group_rows[0]["credential_env_var_present"] == "true")
        blocking: list[str] = []
        if not threshold_met:
            blocking.append("planned_matrix_below_10x3_threshold")
        if not env_present:
            blocking.append("credential_env_var_missing")
        rows.append(
            {
                "protocol_id": PROTOCOL_ID,
                "provider": provider,
                "model_id": model_id,
                "scenario_id": scenario_id,
                "contamination_tier": tier,
                "execution_level": execution_level,
                "planned_row_count": len(group_rows),
                "planned_seed_count": planned_seed_count,
                "planned_minimum_samples_per_seed": planned_minimum_samples,
                "required_seed_count": REQUIRED_SEEDS,
                "required_samples_per_seed": REQUIRED_SAMPLES_PER_SEED,
                "main_threshold_target_met_by_plan": str(threshold_met).lower(),
                "credential_env_var": env_var,
                "credential_env_var_present": str(env_present).lower(),
                "preflight_status": "ready" if threshold_met and env_present else "blocked",
                "blocking_reasons": ";".join(blocking),
            }
        )
    return rows


def _summary(
    plan_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    *,
    seeds: list[int],
    samples: list[int],
    scenarios: list[str],
    models: list[dict[str, str]],
    expected_output_root: str,
) -> dict[str, Any]:
    ready_groups = [row for row in coverage_rows if row["preflight_status"] == "ready"]
    threshold_groups = [row for row in coverage_rows if row["main_threshold_target_met_by_plan"] == "true"]
    return {
        "schema": "trellm_v0_3_direct_api_matrix_plan_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "direct_api_model_matrix_plan",
        "planned_row_count": len(plan_rows),
        "coverage_group_count": len(coverage_rows),
        "threshold_target_group_count": len(threshold_groups),
        "ready_group_count": len(ready_groups),
        "ready_to_run": len(ready_groups) == len(coverage_rows) and bool(coverage_rows),
        "required_seed_count": REQUIRED_SEEDS,
        "required_samples_per_seed": REQUIRED_SAMPLES_PER_SEED,
        "planned_seeds": seeds,
        "planned_samples": samples,
        "planned_scenarios": scenarios,
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
        "expected_output_root": expected_output_root,
        "claim_boundary": (
            "This is a pre-registered direct API matrix plan and credential preflight, not model-performance evidence. "
            "The direct_api_model_matrix gap remains open until non-fixture provider manifests and submissions pass the matrix gate."
        ),
        "artifacts": [
            "direct_api_matrix_plan_rows.csv",
            "direct_api_matrix_plan_coverage.csv",
            "direct_api_matrix_plan_summary.json",
            "direct_api_matrix_plan_summary.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], coverage_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 Direct API Matrix Plan",
        "",
        "This artifact pre-registers the direct API call matrix and checks whether required credential environment variables are present.",
        "It does not make provider calls and does not count as model-performance evidence.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Planned rows: `{summary['planned_row_count']}`",
        f"- Coverage groups: `{summary['coverage_group_count']}`",
        f"- Threshold-target groups: `{summary['threshold_target_group_count']}`",
        f"- Ready groups: `{summary['ready_group_count']}`",
        f"- Ready to run: `{summary['ready_to_run']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Coverage Groups",
        "",
        "| Provider | Model | Scenario | Tier | Execution | Rows | Seeds | Min samples/seed | Env var | Env present | Status | Blocking reasons |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in coverage_rows:
        lines.append(
            f"| {row['provider']} | {row['model_id']} | {row['scenario_id']} | {row['contamination_tier']} | "
            f"{row['execution_level']} | {row['planned_row_count']} | {row['planned_seed_count']} | "
            f"{row['planned_minimum_samples_per_seed']} | {row['credential_env_var']} | "
            f"{row['credential_env_var_present']} | {row['preflight_status']} | {row['blocking_reasons']} |"
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


def _validate_args(
    models: list[dict[str, str]],
    scenarios: list[str],
    seeds: list[int],
    samples: list[int],
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> None:
    if not models:
        raise SystemExit("--models must contain at least one model spec")
    if not scenarios:
        raise SystemExit("--scenarios must contain at least one scenario")
    if not seeds:
        raise SystemExit("--seeds must contain at least one seed")
    if not samples or any(sample < 0 for sample in samples):
        raise SystemExit("--samples must contain non-negative sample indexes")
    if temperature < 0:
        raise SystemExit("--temperature must be >= 0")
    if top_p < 0 or top_p > 1:
        raise SystemExit("--top-p must be in [0, 1]")
    if max_tokens < 1:
        raise SystemExit("--max-tokens must be >= 1")


def _parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_ints(value: str, label: str) -> list[int]:
    try:
        return [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise SystemExit(f"--{label} must be comma-separated integers") from exc


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _safe(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
