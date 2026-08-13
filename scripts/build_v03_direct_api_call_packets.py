from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from tradearena.core.reproducibility import sha256_text

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_PLAN_ROWS = "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_direct_api_call_packets"
MANIFEST_FIELDS = [
    "protocol_id",
    "call_packet_id",
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
    "prompt_packet_sha256",
    "expected_provider_manifest_path",
    "expected_submission_path",
    "execution_status",
    "blocking_reasons",
    "redaction_contract",
    "claim_scope",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build no-key TreLLM v0.3 direct API call packets from the pre-registered matrix plan."
    )
    parser.add_argument("--plan-rows", default=DEFAULT_PLAN_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    plan_rows_path = _resolve(args.plan_rows)
    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_rows = _read_rows(plan_rows_path)
    packets = [_call_packet(row) for row in plan_rows]
    manifest_rows = [_manifest_row(packet) for packet in packets]
    summary = _summary(plan_rows_path, packets, manifest_rows)

    _write_jsonl(output_dir / "direct_api_call_packets.jsonl", packets)
    _write_csv(output_dir / "direct_api_call_packet_manifest.csv", manifest_rows, MANIFEST_FIELDS)
    _write_json(output_dir / "direct_api_call_packets_summary.json", summary)
    (output_dir / "direct_api_call_packets.md").write_text(_summary_markdown(summary, manifest_rows), encoding="utf-8")

    print(f"Wrote {_display(output_dir / 'direct_api_call_packets.jsonl')}")
    print(f"Wrote {_display(output_dir / 'direct_api_call_packet_manifest.csv')}")
    print(f"Wrote {_display(output_dir / 'direct_api_call_packets_summary.json')}")
    print(f"Wrote {_display(output_dir / 'direct_api_call_packets.md')}")
    print(f"Call packets: {len(packets)}")
    print(f"Credential-ready packets: {summary['credential_ready_packet_count']}")
    return 0


def _call_packet(row: dict[str, str]) -> dict[str, Any]:
    call_packet_id = row["plan_id"]
    prompt_packet = {
        "prompt_template_id": row["prompt_template_id"],
        "prompt_version": row["prompt_version"],
        "scenario_id": row["scenario_id"],
        "contamination_tier": row["contamination_tier"],
        "execution_level": row["execution_level"],
        "seed": int(row["seed"]),
        "sample_index": int(row["sample_index"]),
        "raw_prompt_public": False,
        "redaction_policy": "hash-only-public-prompt-packet",
    }
    prompt_packet_sha = sha256_text(json.dumps(prompt_packet, sort_keys=True, separators=(",", ":")))
    credential_ready = row["credential_env_var_present"] == "true"
    blocking = [] if credential_ready else ["credential_env_var_missing"]
    return {
        "schema": "trellm_v0_3_direct_api_call_packet_v0.1",
        "protocol_id": PROTOCOL_ID,
        "call_packet_id": call_packet_id,
        "plan_id": row["plan_id"],
        "provider": row["provider"],
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "api_endpoint_family": row["api_endpoint_family"],
        "credential_env_var": row["credential_env_var"],
        "credential_env_var_present": credential_ready,
        "request_envelope": {
            "sampling": {
                "temperature": float(row["temperature"]),
                "top_p": float(row["top_p"]),
                "max_tokens": int(row["max_tokens"]),
            },
            "prompt_packet": prompt_packet,
            "prompt_packet_sha256": prompt_packet_sha,
            "response_format": "json_object",
            "raw_prompt_public": False,
            "raw_response_public": False,
        },
        "output_contract": {
            "expected_provider_manifest_path": row["expected_provider_manifest_path"],
            "expected_submission_path": row["expected_submission_path"],
            "provider_manifest_schema": "trellm_direct_provider_manifest_v0.1",
            "benchmark_submission_schema": "0.1",
            "privacy_scan_required": True,
            "matrix_gate_required": True,
        },
        "operator_steps": [
            "Render the private prompt from prompt_template_id and prompt_packet inputs.",
            "Call the named direct provider API with the configured sampling parameters.",
            "Store raw provider text only in private workspace storage.",
            "Publish only hash-bound provider manifests and benchmark submissions.",
            "Run the direct API matrix gate and public artifact privacy scan before citing the row.",
        ],
        "execution_status": "not_run",
        "blocking_reasons": blocking,
        "claim_scope": (
            "Executable direct API call packet. It is not evidence until a live or cache-hit direct-provider "
            "manifest and benchmark submission are produced."
        ),
    }


def _manifest_row(packet: dict[str, Any]) -> dict[str, Any]:
    envelope = packet["request_envelope"]
    prompt_packet = envelope["prompt_packet"]
    output_contract = packet["output_contract"]
    return {
        "protocol_id": packet["protocol_id"],
        "call_packet_id": packet["call_packet_id"],
        "plan_id": packet["plan_id"],
        "provider": packet["provider"],
        "model_id": packet["model_id"],
        "model_version_or_release": packet["model_version_or_release"],
        "api_endpoint_family": packet["api_endpoint_family"],
        "credential_env_var": packet["credential_env_var"],
        "credential_env_var_present": str(packet["credential_env_var_present"]).lower(),
        "scenario_id": prompt_packet["scenario_id"],
        "contamination_tier": prompt_packet["contamination_tier"],
        "execution_level": prompt_packet["execution_level"],
        "seed": prompt_packet["seed"],
        "sample_index": prompt_packet["sample_index"],
        "prompt_template_id": prompt_packet["prompt_template_id"],
        "prompt_version": prompt_packet["prompt_version"],
        "temperature": envelope["sampling"]["temperature"],
        "top_p": envelope["sampling"]["top_p"],
        "max_tokens": envelope["sampling"]["max_tokens"],
        "prompt_packet_sha256": envelope["prompt_packet_sha256"],
        "expected_provider_manifest_path": output_contract["expected_provider_manifest_path"],
        "expected_submission_path": output_contract["expected_submission_path"],
        "execution_status": packet["execution_status"],
        "blocking_reasons": ";".join(packet["blocking_reasons"]),
        "redaction_contract": "hash-only-public-manifest;raw-prompt-private;raw-response-private",
        "claim_scope": packet["claim_scope"],
    }


def _summary(plan_rows_path: Path, packets: list[dict[str, Any]], manifest_rows: list[dict[str, Any]]) -> dict[str, Any]:
    ready = [packet for packet in packets if packet["credential_env_var_present"]]
    return {
        "schema": "trellm_v0_3_direct_api_call_packets_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "direct_api_call_packets",
        "source_plan_rows": _display(plan_rows_path),
        "call_packet_count": len(packets),
        "manifest_row_count": len(manifest_rows),
        "credential_ready_packet_count": len(ready),
        "not_run_packet_count": sum(1 for packet in packets if packet["execution_status"] == "not_run"),
        "providers": sorted({packet["provider"] for packet in packets}),
        "models": sorted({packet["model_id"] for packet in packets}),
        "redaction_contract": "raw provider prompts/responses stay private; public artifacts contain hashes and manifests only",
        "claim_boundary": (
            "Call packets make the pre-registered direct API matrix executable and auditable. "
            "They do not call providers, store raw prompts, store raw responses, or support model-performance claims."
        ),
        "artifacts": [
            "direct_api_call_packets.jsonl",
            "direct_api_call_packet_manifest.csv",
            "direct_api_call_packets_summary.json",
            "direct_api_call_packets.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], manifest_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 Direct API Call Packets",
        "",
        "This artifact turns the pre-registered direct API matrix plan into hash-bound call packets.",
        "It does not make provider calls and does not publish raw prompts or raw responses.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Source plan rows: `{summary['source_plan_rows']}`",
        f"- Call packets: `{summary['call_packet_count']}`",
        f"- Credential-ready packets: `{summary['credential_ready_packet_count']}`",
        f"- Not-run packets: `{summary['not_run_packet_count']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Manifest",
        "",
        "| Provider | Model | Scenario | Seed | Sample | Credential ready | Prompt packet hash | Status | Blocking reasons |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in manifest_rows:
        lines.append(
            f"| {row['provider']} | {row['model_id']} | {row['scenario_id']} | {row['seed']} | "
            f"{row['sample_index']} | {row['credential_env_var_present']} | `{row['prompt_packet_sha256']}` | "
            f"{row['execution_status']} | {row['blocking_reasons']} |"
        )
    lines.append("")
    return "\n".join(lines)


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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
