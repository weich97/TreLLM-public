from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from validate_direct_provider_manifest import validate_direct_provider_manifest_file

from tradearena.core.reproducibility import compute_reproducibility_hash, sha256_file, sha256_text
from tradearena.evaluation.evidence import evidence_payload
from tradearena.evaluation.submissions import validate_submission_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic v0.3 C0/E1 direct-api pilot bundle without making live provider calls."
    )
    parser.add_argument("--output-dir", default="docs/results/v0_3_direct_api_pilot")
    parser.add_argument("--provider", default="fixture-direct-api")
    parser.add_argument("--model-id", default="fixture-llm-policy-v0")
    parser.add_argument("--model-version-or-release", default="fixture-2026-05-17")
    parser.add_argument("--api-endpoint-family", default="responses")
    parser.add_argument("--scenario-id", default="synthetic_calm_trend_c0_v0_3")
    parser.add_argument("--contamination-tier", choices=["C0", "C1", "C2"], default="C0")
    parser.add_argument("--execution-level", choices=["E0", "E1", "E2", "E3"], default="E1")
    parser.add_argument("--seeds", default="7,11")
    parser.add_argument("--samples", default="0,1")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    provider_dir = output_dir / "provider_manifests"
    submission_dir = output_dir / "submissions"
    provider_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    _clear_generated_jsons(provider_dir)
    _clear_generated_jsons(submission_dir)

    seeds = _parse_ints(args.seeds, "seeds")
    samples = _parse_ints(args.samples, "samples")
    rows: list[dict[str, Any]] = []
    validation_errors: list[str] = []

    for seed in seeds:
        for sample_index in samples:
            prompt_text = _fixture_prompt(args.scenario_id, seed, sample_index)
            response_text = _fixture_response(seed, sample_index)
            provider_manifest = _provider_manifest(args, seed, sample_index, prompt_text, response_text)
            provider_path = provider_dir / f"{args.scenario_id}__{args.provider}_{_safe(args.model_id)}__seed_{seed}__sample_{sample_index}.json"
            _write_json(provider_path, provider_manifest)

            _, provider_errors = validate_direct_provider_manifest_file(provider_path)
            validation_errors.extend(f"{provider_path}: {error}" for error in provider_errors)
            provider_manifest_hash = sha256_file(provider_path)

            submission = _benchmark_submission(args, seed, sample_index, provider_manifest_hash)
            submission["reproducibility_hash"] = compute_reproducibility_hash(submission)
            submission_path = submission_dir / f"{args.scenario_id}__{args.provider}_{_safe(args.model_id)}__seed_{seed}__sample_{sample_index}.json"
            _write_json(submission_path, submission)
            _, submission_errors = validate_submission_file(submission_path)
            validation_errors.extend(f"{submission_path}: {error}" for error in submission_errors)

            rows.append(
                {
                    "scenario_id": args.scenario_id,
                    "provider": args.provider,
                    "model_id": args.model_id,
                    "model_version_or_release": args.model_version_or_release,
                    "contamination_tier": args.contamination_tier,
                    "execution_level": args.execution_level,
                    "seed": seed,
                    "sample_index": sample_index,
                    "evidence_tags": ";".join(submission["evidence"]["tags"]),
                    "total_return": submission["metrics"]["total_return"],
                    "max_drawdown": submission["metrics"]["max_drawdown"],
                    "execution_fill_rate": submission["metrics"]["execution_fill_rate"],
                    "risk_clipped_decisions": submission["metrics"]["risk_clipped_decisions"],
                    "provider_manifest": _display_path(provider_path),
                    "provider_manifest_sha256": provider_manifest_hash,
                    "submission": _display_path(submission_path),
                    "reproducibility_hash": submission["reproducibility_hash"],
                }
            )

    if validation_errors:
        for error in validation_errors:
            print(error)
        return 1

    _write_rows_csv(output_dir / "direct_api_pilot_rows.csv", rows)
    summary = _summary(args, rows)
    _write_json(output_dir / "direct_api_pilot_summary.json", summary)
    (output_dir / "direct_api_pilot_summary.md").write_text(_summary_markdown(summary, rows), encoding="utf-8")
    print(f"Wrote {_display_path(output_dir / 'direct_api_pilot_rows.csv')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_pilot_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'direct_api_pilot_summary.md')}")
    print(f"Rows: {len(rows)}")
    return 0


def _provider_manifest(args: argparse.Namespace, seed: int, sample_index: int, prompt_text: str, response_text: str) -> dict[str, Any]:
    prompt_sha = sha256_text(prompt_text)
    response_sha = sha256_text(response_text)
    call_second = seed + sample_index
    return {
        "schema": "trellm_direct_provider_manifest_v0.1",
        "protocol_id": "trellm-v0.3-protocol",
        "provider_route": "direct-api",
        "provider": args.provider,
        "model_id": args.model_id,
        "model_version_or_release": args.model_version_or_release,
        "api_endpoint_family": args.api_endpoint_family,
        "call_window": {
            "call_started_at": f"2026-05-17T12:00:{call_second:02d}Z",
            "call_completed_at": f"2026-05-17T12:00:{call_second + 1:02d}Z",
            "request_id_redacted": True,
            "retry_count": 0,
        },
        "sampling": {"temperature": 0.2, "top_p": 1.0, "max_tokens": 1200},
        "prompt": {
            "prompt_template_id": "trellm-allocation-v0.3",
            "prompt_version": "v0.3.0",
            "prompt_sha256": prompt_sha,
            "system_prompt_sha256": sha256_text("trellm direct-api pilot system prompt v0.3"),
            "raw_prompt_public": False,
        },
        "response": {
            "response_sha256": response_sha,
            "response_format": "json_object",
            "parse_status": "parsed",
            "raw_response_public": False,
        },
        "redaction": {
            "provider_secrets_removed": True,
            "raw_prompt_public": False,
            "raw_response_public": False,
            "private_account_data_removed": True,
            "redaction_policy": "hash-only-public-manifest",
            "notes": "Deterministic protocol fixture; no live API call or raw provider text is stored.",
        },
        "cache": {
            "cache_status": "cache_replay",
            "cache_key_sha256": sha256_text(f"{args.provider}:{args.model_id}:{prompt_sha}:{response_sha}:{sample_index}"),
        },
        "run_binding": {
            "scenario_id": args.scenario_id,
            "contamination_tier": args.contamination_tier,
            "execution_level": args.execution_level,
            "seed": seed,
            "sample_index": sample_index,
            "trajectory_manifest_sha256": sha256_text(f"trajectory:{args.scenario_id}:{seed}:{sample_index}"),
        },
        "evidence": {
            "evidence_label": "direct-api",
            "claim_scope": "Protocol fixture for the v0.3 direct API evidence path; not a live provider or trading-profit claim.",
            "appendix_only": False,
        },
    }


def _benchmark_submission(args: argparse.Namespace, seed: int, sample_index: int, provider_manifest_hash: str) -> dict[str, Any]:
    evidence = evidence_payload(["stress-only", "direct-api", "protocol-fixture", "redacted-prompt"])
    total_return = round(((seed % 13) - 6) / 1000 + sample_index / 5000, 6)
    max_drawdown = round(-0.006 - (seed % 5) / 1000 - sample_index / 2000, 6)
    fill_rate = round(0.72 + (seed % 3) * 0.02 - sample_index * 0.01, 6)
    return {
        "schema_version": "0.1",
        "scenario_id": args.scenario_id,
        "agent": {
            "provider": args.provider,
            "agent_type": "llm_policy",
            "model_family": args.model_id,
            "model_display_name": f"{args.model_id} protocol fixture",
            "model_identifier_redacted": False,
            "prompt_mode": "weights_only",
            "risk_feedback_mode": "true",
            "parse_coverage": 1.0,
            "response_format": "json_object",
            "prompt_version": "trellm-allocation-v0.3",
            "agent_commit": "v0.3-direct-api-pilot",
        },
        "data_source": {
            "name": "trellm-synthetic-c0",
            "frequency": "weekly",
            "symbols": ["SYN"],
            "timestamp_policy": "relative_masked",
            "data_hash": sha256_text(f"data:{args.scenario_id}:{seed}"),
        },
        "execution_config": {
            "commission_bps": 1.0,
            "base_slippage_bps": 2.0,
            "spread_bps": 0.0,
            "latency_steps": 1,
            "participation_rate": 0.05,
            "market_impact": 0.15,
            "execution_level": args.execution_level,
        },
        "risk_config": {
            "risk_manager": "max-position",
            "risk_budget": {
                "max_position_weight": 0.35,
                "max_gross_exposure": 1.0,
                "max_single_step_turnover": 0.75,
                "risk_feedback_mode": "true",
            },
        },
        "metrics": {
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "sharpe": round(total_return / abs(max_drawdown), 6) if max_drawdown else 0.0,
            "execution_fill_rate": fill_rate,
            "rejected_order_count": int((seed + sample_index) % 3),
            "risk_clipped_decisions": int((seed + sample_index) % 4),
            "risk_violation_count": 0,
            "trajectory_reproducibility_coverage": 1.0,
        },
        "evidence": evidence,
        "trajectory_manifest": {
            "format": "redacted_manifest",
            "path_or_uri": "provider-manifest-bound-pilot-row",
            "raw_prompts_included": False,
            "raw_responses_included": False,
            "manifest_hash": sha256_text(f"trajectory-manifest:{args.scenario_id}:{seed}:{sample_index}"),
            "artifact_hashes": {"direct_provider_manifest": provider_manifest_hash},
        },
        "reproducibility_hash": "",
        "redaction": {
            "provider_secrets_removed": True,
            "timestamps_masked": True,
            "raw_provider_text_removed": True,
            "notes": "Protocol fixture stores only hashes and direct-provider-style metadata; no raw prompt or response text is included.",
        },
    }


def _summary(args: argparse.Namespace, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "trellm_v0_3_direct_api_pilot_v0.1",
        "protocol_id": "trellm-v0.3-protocol",
        "scenario_id": args.scenario_id,
        "provider": args.provider,
        "model_id": args.model_id,
        "contamination_tier": args.contamination_tier,
        "execution_level": args.execution_level,
        "row_count": len(rows),
        "seeds": sorted({row["seed"] for row in rows}),
        "samples": sorted({row["sample_index"] for row in rows}),
        "claim_boundary": "Direct API Pilot protocol fixture for evidence-path validation; not provider-performance or return evidence.",
        "artifacts": [
            "direct_api_pilot_rows.csv",
            "direct_api_pilot_summary.json",
            "direct_api_pilot_summary.md",
            "provider_manifests/*.json",
            "submissions/*.json",
        ],
    }


def _summary_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 Direct API Pilot",
        "",
        "This fixture bundle validates the v0.3 direct API evidence path without making live provider calls.",
        "It is not a trading-profit claim.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Scenario: `{summary['scenario_id']}`",
        f"- Provider/model: `{summary['provider']}:{summary['model_id']}`",
        f"- Contamination tier: `{summary['contamination_tier']}`",
        f"- Execution level: `{summary['execution_level']}`",
        f"- Rows: {summary['row_count']}",
        "",
        "| Seed | Sample | Evidence | Return | Max DD | Fill | Provider Manifest | Submission |",
        "| ---: | ---: | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["seed"]),
                    str(row["sample_index"]),
                    f"`{row['evidence_tags']}`",
                    str(row["total_return"]),
                    str(row["max_drawdown"]),
                    str(row["execution_fill_rate"]),
                    f"`{row['provider_manifest']}`",
                    f"`{row['submission']}`",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _fixture_prompt(scenario_id: str, seed: int, sample_index: int) -> str:
    return json.dumps(
        {
            "scenario_id": scenario_id,
            "seed": seed,
            "sample_index": sample_index,
            "timestamp": f"T+{seed % 5}",
            "symbols": ["SYN"],
            "task": "Return target weights for a C0 synthetic fixture.",
        },
        sort_keys=True,
    )


def _fixture_response(seed: int, sample_index: int) -> str:
    weight = round(0.1 + (seed % 5) / 100 + sample_index / 100, 4)
    return json.dumps({"weights": [{"symbol": "SYN", "target_weight": weight, "confidence": 0.7}]}, sort_keys=True)


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clear_generated_jsons(directory: Path) -> None:
    for path in directory.glob("*.json"):
        path.unlink()


def _parse_ints(value: str, label: str) -> list[int]:
    try:
        values = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise SystemExit(f"{label} must be a comma-separated list of integers") from exc
    if not values:
        raise SystemExit(f"{label} must contain at least one integer")
    return values


def _display_path(path: Path) -> str:
    return path.as_posix()


def _safe(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
