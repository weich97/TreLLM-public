"""Offline fixed-response-path 2x2 replay for the v0.3 direct-API matrix.

Each original E0/E1 response sequence is treated as one realized intent path
and replayed under both E0 and E1 execution. The script never reads provider
credentials and has no network-capable code path. It publishes only metrics
and hashes; raw prompts and responses remain under the private source root.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.agents.llm import DeepSeekLLMAnalyst
from tradearena.core.redaction import scan_public_artifact_paths, scan_public_artifact_payload
from tradearena.core.reproducibility import (
    canonical_json,
    compute_reproducibility_hash,
    sha256_file,
    sha256_text,
)
from tradearena.evaluation.submissions import validate_submission_file
from tradearena.factory import build_default_system

_bridge_path = ROOT / "scripts" / "run_v03_direct_api_submission.py"
_bridge_spec = importlib.util.spec_from_file_location("v03_direct_api_bridge_for_replay", _bridge_path)
assert _bridge_spec and _bridge_spec.loader
bridge = importlib.util.module_from_spec(_bridge_spec)
_bridge_spec.loader.exec_module(bridge)

_validator_path = ROOT / "scripts" / "validate_direct_provider_manifest.py"
_validator_spec = importlib.util.spec_from_file_location("v03_manifest_validator_for_replay", _validator_path)
assert _validator_spec and _validator_spec.loader
manifest_validator = importlib.util.module_from_spec(_validator_spec)
_validator_spec.loader.exec_module(manifest_validator)

PLAN_SCHEMA = "tradearena.fixed-intent-replay.plan.v1"
INTEGRITY_SCHEMA = "tradearena.fixed-intent-replay.integrity.v1"
PROTOCOL_ID = "trellm-v0.3-protocol"
EXPECTED_SOURCE_ROWS = 900
EXPECTED_BASE_PAIRS = 450
EXPECTED_REPLAY_ROWS = 1800
EXPECTED_PERIODS = 24
EXECUTION_LEVELS = ("E0", "E1")
SOURCE_HASH_POLICY = "sha256 of text bytes after CRLF/CR -> LF normalization"
PLAN_ROWS_SOURCE_KEY = (
    "docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv"
)
PACKETS_SOURCE_KEY = (
    "docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.jsonl"
)
REQUIRED_SOURCE_HASHES = {
    PACKETS_SOURCE_KEY,
    PLAN_ROWS_SOURCE_KEY,
    "scripts/run_v03_fixed_intent_replay.py",
    "scripts/run_v03_direct_api_submission.py",
    "scripts/validate_direct_provider_manifest.py",
    "src/tradearena/agents/llm.py",
    "src/tradearena/core/runner.py",
    "src/tradearena/factory.py",
}
PAIR_KEY_FIELDS = (
    "protocol_id",
    "provider",
    "model_id",
    "model_version_or_release",
    "api_endpoint_family",
    "scenario_id",
    "contamination_tier",
    "seed",
    "sample_index",
    "prompt_template_id",
    "prompt_version",
    "temperature",
    "top_p",
    "max_tokens",
)
FLOAT_METRICS = (
    "total_return",
    "sharpe",
    "max_drawdown",
    "execution_fill_rate",
    "total_slippage_cost",
    "trajectory_reproducibility_coverage",
)
INTEGER_METRICS = (
    "rejected_order_count",
    "risk_clipped_decisions",
    "risk_violation_count",
)
PUBLISHED_METRICS = (
    "total_return",
    "sharpe",
    "max_drawdown",
    "execution_fill_rate",
    "total_slippage_cost",
    "rejected_order_count",
    "risk_clipped_decisions",
    "risk_violation_count",
    "trajectory_reproducibility_coverage",
)
LOG_FIELDS = {
    "api_model",
    "cache_key",
    "created_at",
    "latency_ms",
    "model",
    "prompt",
    "prompt_hash",
    "provider",
    "response_text",
    "sample_index",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class IntegrityError(ValueError):
    """Raised when the frozen source matrix is not an exact, closed set."""


class DiagonalReproductionError(IntegrityError):
    """Raised when a source arm does not reproduce under its own execution."""


@dataclass(frozen=True)
class SourceRecord:
    plan: dict[str, str]
    packet: dict[str, Any]
    run: dict[str, Any]
    submission: dict[str, Any]
    log_path: Path
    base_key_sha256: str
    prompt_step_hashes: tuple[str, ...]
    response_step_hashes: tuple[str, ...]
    parsed_response_step_hashes: tuple[str, ...]
    normalized_parsed_response_path_sha256: str
    market_path_sha256: str


class FrozenResponseSequenceAnalyst(DeepSeekLLMAnalyst):
    """Original parser/prompt path with an in-memory, finite response tape."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        sample_index: int,
        responses: tuple[str, ...],
    ) -> None:
        super().__init__(
            model=model,
            api_model=model,
            provider=provider,
            cache_path="",
            api_key_env="",
            fallback_api_key_env="",
            require_api_key=False,
            use_risk_feedback=True,
            risk_feedback_mode="true",
            output_mode="weights_only",
            mask_timestamps=True,
            anonymize_symbols=False,
            sample_index=sample_index,
            temperature=0.2,
            thinking="disabled",
            use_response_format=provider != "glm",
            name="glm-llm-analyst" if provider == "glm" else "deepseek-llm-analyst",
        )
        self._responses = responses
        self._cursor = 0
        self.generated_prompt_hashes: list[str] = []

    @property
    def consumed(self) -> int:
        return self._cursor

    def _cache(self) -> dict[str, dict[str, Any]]:
        return {}

    def _append_cache(self, entry: dict[str, Any]) -> None:
        del entry

    def _call_deepseek(self, prompt: str) -> str:
        if self._cursor >= len(self._responses):
            raise IntegrityError("frozen response tape exhausted before the arena stopped")
        self.generated_prompt_hashes.append(sha256_text(prompt))
        response = self._responses[self._cursor]
        self._cursor += 1
        return response


def _sha256_hex(path: Path) -> str:
    return sha256_file(path).split(":", 1)[1]


def _sha256_lf_text(path: Path) -> str:
    """Hash text deterministically across LF/CRLF working-tree policies."""

    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return sha256_text(canonical_json(value))


def _python_tree_sha256(root: Path) -> str:
    rows = [
        [path.relative_to(ROOT).as_posix(), _sha256_lf_text(path)]
        for path in sorted(root.rglob("*.py"))
        if path.is_file() and "__pycache__" not in path.parts
    ]
    if not rows:
        raise IntegrityError(f"frozen Python tree is empty: {root}")
    return _canonical_sha256(rows)


def _source_snapshot(source_root: Path, plan_ids: set[str]) -> dict[str, str]:
    layouts = {
        "run_records_set": (source_root / "runs", ".json"),
        "provider_manifests_set": (source_root / "provider_manifests", ".json"),
        "submissions_set": (source_root / "submissions", ".json"),
        "private_call_logs_set": (source_root / "private" / "llm_cache", ".jsonl"),
    }
    snapshot: dict[str, str] = {}
    for label, (directory, suffix) in layouts.items():
        if not directory.is_dir():
            raise IntegrityError(f"missing frozen source directory: {directory}")
        entries = list(directory.iterdir())
        if any(not path.is_file() or path.is_symlink() or path.suffix != suffix for path in entries):
            raise IntegrityError(f"frozen source directory contains an unexpected entry: {directory}")
        expected_names = {f"{plan_id}{suffix}" for plan_id in plan_ids}
        if {path.name for path in entries} != expected_names:
            raise IntegrityError(f"frozen source file set differs for {label}")
        snapshot[label] = _canonical_sha256(
            [[path.name, _sha256_hex(path)] for path in sorted(entries, key=lambda item: item.name)]
        )
    return snapshot


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"invalid required JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"required JSON is not an object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        handle = path.open(encoding="utf-8")
    except FileNotFoundError as exc:
        raise IntegrityError(f"missing required JSONL file: {path}") from exc
    with handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IntegrityError(f"malformed JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise IntegrityError(f"non-object JSONL row at {path}:{line_number}")
            rows.append(row)
    return rows


def _load_plan_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_SOURCE_ROWS:
        raise IntegrityError(f"plan row count differs from 900: {len(rows)}")
    plan_ids = [row.get("plan_id", "") for row in rows]
    if any(not value for value in plan_ids) or len(plan_ids) != len(set(plan_ids)):
        raise IntegrityError("plan ids are empty or duplicated")
    return rows


def _pair_key(row: dict[str, str]) -> dict[str, Any]:
    return {
        "protocol_id": row["protocol_id"],
        "provider": row["provider"],
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "api_endpoint_family": row["api_endpoint_family"],
        "scenario_id": row["scenario_id"],
        "contamination_tier": row["contamination_tier"],
        "seed": int(row["seed"]),
        "sample_index": int(row["sample_index"]),
        "prompt_template_id": row["prompt_template_id"],
        "prompt_version": row["prompt_version"],
        "temperature": float(row["temperature"]),
        "top_p": float(row["top_p"]),
        "max_tokens": int(row["max_tokens"]),
    }


def _packet_identity(row: dict[str, str], packet: dict[str, Any]) -> None:
    prompt_packet = packet.get("request_envelope", {}).get("prompt_packet", {})
    sampling = packet.get("request_envelope", {}).get("sampling", {})
    expected_top = {
        "schema": bridge.PACKET_SCHEMA,
        "protocol_id": row["protocol_id"],
        "plan_id": row["plan_id"],
        "call_packet_id": row["plan_id"],
        "provider": row["provider"],
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "api_endpoint_family": row["api_endpoint_family"],
    }
    for field, expected in expected_top.items():
        if packet.get(field) != expected:
            raise IntegrityError(f"packet identity mismatch for {row['plan_id']}: {field}")
    expected_prompt = {
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
    if prompt_packet != expected_prompt:
        raise IntegrityError(f"packet prompt identity mismatch for {row['plan_id']}")
    if packet.get("request_envelope", {}).get("prompt_packet_sha256") != _canonical_sha256(
        prompt_packet
    ):
        raise IntegrityError(f"packet prompt hash mismatch for {row['plan_id']}")
    expected_sampling = {
        "temperature": float(row["temperature"]),
        "top_p": float(row["top_p"]),
        "max_tokens": int(row["max_tokens"]),
    }
    if sampling != expected_sampling:
        raise IntegrityError(f"packet sampling mismatch for {row['plan_id']}")
    envelope = packet.get("request_envelope", {})
    if envelope.get("raw_prompt_public") is not False or envelope.get("raw_response_public") is not False:
        raise IntegrityError(f"packet privacy flags are not closed for {row['plan_id']}")


def _parsed_response_path(
    entries: list[dict[str, Any]], parser: DeepSeekLLMAnalyst
) -> tuple[tuple[str, ...], str]:
    step_hashes: list[str] = []
    normalized_path: list[list[dict[str, Any]]] = []
    for step_index, entry in enumerate(entries):
        parsed = parser._parse_response(str(entry["response_text"]))
        items = parser._signal_items(parsed)
        if not items:
            raise IntegrityError(
                f"source response step {step_index} does not parse to a weight item"
            )
        normalized = []
        for item in items:
            target = item.get("target_weight", item.get("weight"))
            try:
                target_weight = float(target)
                confidence = float(item.get("confidence", 1.0))
            except (TypeError, ValueError):
                raise IntegrityError(
                    f"source response step {step_index} has an invalid numeric signal"
                ) from None
            normalized.append(
                {
                    "symbol": str(item.get("symbol", "")),
                    "target_weight": target_weight,
                    "confidence": confidence,
                    "horizon": str(item.get("horizon", "1w")),
                }
            )
        normalized.sort(key=lambda item: item["symbol"])
        step_hashes.append(_canonical_sha256(normalized))
        normalized_path.append(normalized)
    return tuple(step_hashes), _canonical_sha256(normalized_path)


def _validate_call_log(
    plan: dict[str, str], path: Path, run: dict[str, Any]
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    str,
    str,
]:
    entries = _read_jsonl(path)
    if len(entries) != EXPECTED_PERIODS:
        raise IntegrityError(f"{plan['plan_id']}: call log has {len(entries)}/24 rows")
    prompt_hashes: list[str] = []
    response_hashes: list[str] = []
    market_steps: list[dict[str, Any]] = []
    created_at: list[int] = []
    sample = int(plan["sample_index"])
    parser = DeepSeekLLMAnalyst(output_mode="weights_only")
    for index, entry in enumerate(entries):
        if set(entry) != LOG_FIELDS:
            raise IntegrityError(f"{plan['plan_id']}: private log schema mismatch at row {index}")
        prompt = entry.get("prompt")
        response = entry.get("response_text")
        if not isinstance(prompt, str) or not isinstance(response, str):
            raise IntegrityError(f"{plan['plan_id']}: raw call fields are not strings at row {index}")
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if entry.get("prompt_hash") != prompt_hash:
            raise IntegrityError(f"{plan['plan_id']}: prompt hash mismatch at row {index}")
        expected_cache_key = f"{plan['provider']}:{plan['model_id']}:{prompt_hash}"
        if sample:
            expected_cache_key = f"{expected_cache_key}:s{sample}"
        if (
            entry.get("cache_key") != expected_cache_key
            or entry.get("provider") != plan["provider"]
            or entry.get("model") != plan["model_id"]
            or entry.get("api_model") != plan["model_id"]
            or entry.get("sample_index") != sample
        ):
            raise IntegrityError(f"{plan['plan_id']}: call provenance mismatch at row {index}")
        try:
            payload = json.loads(prompt)
        except json.JSONDecodeError as exc:
            raise IntegrityError(f"{plan['plan_id']}: prompt JSON malformed at row {index}") from exc
        if payload.get("timestamp") != f"T+{index}" or not isinstance(payload.get("bars"), list):
            raise IntegrityError(f"{plan['plan_id']}: masked time/bar contract mismatch at row {index}")
        bars = sorted(payload["bars"], key=lambda bar: str(bar.get("symbol", "")))
        expected_symbols = sorted(
            str(symbol) for symbol in bridge.SCENARIOS[plan["scenario_id"]]["symbols"]
        )
        if [str(bar.get("symbol", "")) for bar in bars] != expected_symbols:
            raise IntegrityError(f"{plan['plan_id']}: symbol contract mismatch at row {index}")
        market_steps.append({"timestamp": payload["timestamp"], "bars": bars})
        prompt_hashes.append(sha256_text(prompt))
        response_hashes.append(sha256_text(response))
        created_at.append(int(entry.get("created_at", 0)))
    if created_at != sorted(created_at):
        raise IntegrityError(f"{plan['plan_id']}: call timestamps are not nondecreasing")
    if run.get("prompt_calls_sha256") != sha256_text(canonical_json(prompt_hashes)):
        raise IntegrityError(f"{plan['plan_id']}: prompt aggregate hash mismatch")
    if run.get("response_calls_sha256") != sha256_text(canonical_json(response_hashes)):
        raise IntegrityError(f"{plan['plan_id']}: response aggregate hash mismatch")
    parsed_steps, parsed_path = _parsed_response_path(entries, parser)
    return (
        tuple(prompt_hashes),
        tuple(response_hashes),
        parsed_steps,
        parsed_path,
        _canonical_sha256(market_steps),
    )


def _validate_source_record(
    row: dict[str, str], packet: dict[str, Any], source_root: Path
) -> SourceRecord:
    plan_id = row["plan_id"]
    run_path = source_root / "runs" / f"{plan_id}.json"
    manifest_path = source_root / "provider_manifests" / f"{plan_id}.json"
    submission_path = source_root / "submissions" / f"{plan_id}.json"
    log_path = source_root / "private" / "llm_cache" / f"{plan_id}.jsonl"
    run = _read_json(run_path)
    manifest, manifest_errors = manifest_validator.validate_direct_provider_manifest_file(manifest_path)
    submission, submission_errors = validate_submission_file(submission_path)
    if manifest_errors:
        raise IntegrityError(f"{plan_id}: provider manifest validation failed")
    if submission_errors:
        raise IntegrityError(f"{plan_id}: submission validation failed")
    expected_identity: dict[str, Any] = {
        "schema": bridge.RUN_RECORD_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "plan_id": plan_id,
        "provider": row["provider"],
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "api_endpoint_family": row["api_endpoint_family"],
        "scenario_id": row["scenario_id"],
        "contamination_tier": row["contamination_tier"],
        "execution_level": row["execution_level"],
        "seed": int(row["seed"]),
        "sample_index": int(row["sample_index"]),
        "mode": "execute",
        "transport": "direct-api",
        "status": "ok",
        "periods": EXPECTED_PERIODS,
        "llm_call_count": EXPECTED_PERIODS,
        "parse_coverage": 1.0,
        "parse_status": "parsed",
        "cache_status": "live_call",
        "symbols": list(bridge.SCENARIOS[row["scenario_id"]]["symbols"]),
        "call_log_path": log_path.relative_to(ROOT).as_posix(),
        "provider_manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "submission_path": submission_path.relative_to(ROOT).as_posix(),
    }
    for field, expected in expected_identity.items():
        if run.get(field) != expected:
            raise IntegrityError(f"{plan_id}: run identity mismatch for {field}")
    if run.get("error_class") or run.get("error_message"):
        raise IntegrityError(f"{plan_id}: run records an error")
    appended_count = run.get("live_call_appended_count")
    if (
        isinstance(appended_count, bool)
        or not isinstance(appended_count, int)
        or not 0 <= appended_count <= EXPECTED_PERIODS
    ):
        raise IntegrityError(f"{plan_id}: invalid live-call append count")
    log_hash = sha256_file(log_path)
    manifest_hash = sha256_file(manifest_path)
    if run.get("call_log_sha256") != log_hash or run.get("provider_manifest_sha256") != manifest_hash:
        raise IntegrityError(f"{plan_id}: run artifact hash link mismatch")
    if manifest.get("run_binding", {}).get("trajectory_manifest_sha256") != log_hash:
        raise IntegrityError(f"{plan_id}: provider manifest does not bind the call log")
    trajectory_manifest = submission.get("trajectory_manifest", {})
    if trajectory_manifest.get("manifest_hash") != log_hash:
        raise IntegrityError(f"{plan_id}: submission does not bind the call log")
    if trajectory_manifest.get("artifact_hashes", {}).get("direct_provider_manifest") != manifest_hash:
        raise IntegrityError(f"{plan_id}: submission does not bind the provider manifest")
    if submission.get("reproducibility_hash") != compute_reproducibility_hash(submission):
        raise IntegrityError(f"{plan_id}: submission reproducibility hash mismatch")
    if run.get("reproducibility_hash") != submission.get("reproducibility_hash"):
        raise IntegrityError(f"{plan_id}: run/submission reproducibility hash mismatch")
    if run.get("metrics") != submission.get("metrics"):
        raise IntegrityError(f"{plan_id}: run/submission metric mismatch")
    scenario = bridge.SCENARIOS[row["scenario_id"]]
    level = bridge.EXECUTION_LEVELS[row["execution_level"]]
    expected_manifest = {
        "schema": "trellm_direct_provider_manifest_v0.1",
        "protocol_id": PROTOCOL_ID,
        "provider": row["provider"],
        "provider_route": "direct-api",
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "api_endpoint_family": row["api_endpoint_family"],
        "sampling": {
            "temperature": float(row["temperature"]),
            "top_p": float(row["top_p"]),
            "max_tokens": int(row["max_tokens"]),
        },
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            raise IntegrityError(f"{plan_id}: provider manifest mismatch for {field}")
    expected_prompt = {
        "prompt_template_id": row["prompt_template_id"],
        "prompt_version": row["prompt_version"],
        "prompt_sha256": run["prompt_calls_sha256"],
        "system_prompt_sha256": sha256_text(bridge._system_prompt_text()),
        "raw_prompt_public": False,
    }
    if manifest.get("prompt") != expected_prompt:
        raise IntegrityError(f"{plan_id}: provider manifest prompt binding mismatch")
    expected_response = {
        "response_sha256": run["response_calls_sha256"],
        "raw_response_public": False,
        "response_format": "json_object",
        "parse_status": "parsed",
    }
    if manifest.get("response") != expected_response:
        raise IntegrityError(f"{plan_id}: provider manifest response binding mismatch")
    expected_run_binding = {
        "scenario_id": row["scenario_id"],
        "contamination_tier": row["contamination_tier"],
        "execution_level": row["execution_level"],
        "seed": int(row["seed"]),
        "sample_index": int(row["sample_index"]),
        "trajectory_manifest_sha256": log_hash,
    }
    if manifest.get("run_binding") != expected_run_binding:
        raise IntegrityError(f"{plan_id}: provider manifest run binding mismatch")
    if manifest.get("cache", {}).get("cache_status") != "live_call":
        raise IntegrityError(f"{plan_id}: provider manifest is not direct live-call evidence")
    redaction = manifest.get("redaction", {})
    if (
        redaction.get("raw_prompt_public") is not False
        or redaction.get("raw_response_public") is not False
        or redaction.get("provider_secrets_removed") is not True
        or redaction.get("private_account_data_removed") is not True
    ):
        raise IntegrityError(f"{plan_id}: provider manifest redaction contract mismatch")
    expected_agent = {
        "provider": row["provider"],
        "agent_type": "llm_policy",
        "model_family": row["model_id"],
        "model_display_name": f"{row['model_id']} ({row['model_version_or_release']})",
        "model_identifier_redacted": False,
        "prompt_mode": "weights_only",
        "risk_feedback_mode": "true",
        "parse_coverage": 1.0,
        "response_format": "json_object",
        "prompt_version": row["prompt_template_id"],
        "agent_commit": "v0.3-direct-api-matrix",
    }
    if submission.get("scenario_id") != row["scenario_id"] or submission.get("agent") != expected_agent:
        raise IntegrityError(f"{plan_id}: submission scenario/agent identity mismatch")
    expected_data = {
        "name": scenario["data_source_name"],
        "frequency": scenario["frequency"],
        "symbols": list(scenario["symbols"]),
        "timestamp_policy": "relative_masked",
        "data_hash": sha256_text(
            canonical_json(
                {
                    "generator": "synthetic-market",
                    "scenario_id": row["scenario_id"],
                    "seed": int(row["seed"]),
                    "periods": EXPECTED_PERIODS,
                    "symbols": list(scenario["symbols"]),
                    **scenario["synthetic"],
                }
            )
        ),
    }
    if submission.get("data_source") != expected_data:
        raise IntegrityError(f"{plan_id}: submission data identity mismatch")
    expected_execution = {
        "commission_bps": float(level["commission_bps"]),
        "base_slippage_bps": float(level["slippage_bps"]),
        "spread_bps": float(level["spread_bps"]),
        "latency_steps": int(level["latency_steps"]),
        "participation_rate": float(level["participation_rate"]),
        "market_impact": float(level["market_impact"]),
        "execution_level": row["execution_level"],
    }
    if submission.get("execution_config") != expected_execution:
        raise IntegrityError(f"{plan_id}: submission execution contract mismatch")
    expected_risk = {
        "risk_manager": "max-position",
        "risk_budget": {
            "max_position_weight": 0.35,
            "max_gross_exposure": 1.0,
            "max_single_step_turnover": 0.75,
            "risk_feedback_mode": "true",
        },
    }
    if submission.get("risk_config") != expected_risk:
        raise IntegrityError(f"{plan_id}: submission risk contract mismatch")
    trajectory_manifest = submission.get("trajectory_manifest", {})
    if (
        trajectory_manifest.get("path_or_uri") != log_path.relative_to(ROOT).as_posix()
        or trajectory_manifest.get("raw_prompts_included") is not False
        or trajectory_manifest.get("raw_responses_included") is not False
    ):
        raise IntegrityError(f"{plan_id}: submission trajectory privacy/binding mismatch")
    prompt_steps, response_steps, parsed_steps, parsed_path, market_path = _validate_call_log(
        row, log_path, run
    )
    return SourceRecord(
        plan=row,
        packet=packet,
        run=run,
        submission=submission,
        log_path=log_path,
        base_key_sha256=_canonical_sha256(_pair_key(row)),
        prompt_step_hashes=prompt_steps,
        response_step_hashes=response_steps,
        parsed_response_step_hashes=parsed_steps,
        normalized_parsed_response_path_sha256=parsed_path,
        market_path_sha256=market_path,
    )


def _validate_frozen_implementation(
    plan: dict[str, Any], plan_rows_path: Path, packets_path: Path
) -> None:
    if plan.get("source_hash_policy") != SOURCE_HASH_POLICY:
        raise IntegrityError("analysis plan source hash policy differs")
    source_hashes = plan.get("source_sha256")
    if not isinstance(source_hashes, dict) or set(source_hashes) != REQUIRED_SOURCE_HASHES:
        raise IntegrityError("analysis-plan source hash key set differs")
    for relative, expected_hash in source_hashes.items():
        path = ROOT / relative
        if (
            not isinstance(expected_hash, str)
            or not HEX64.fullmatch(expected_hash)
            or not path.is_file()
            or _sha256_lf_text(path) != expected_hash
        ):
            raise IntegrityError(f"analysis-plan source hash mismatch: {relative}")
    if (
        _sha256_lf_text(plan_rows_path) != source_hashes[PLAN_ROWS_SOURCE_KEY]
        or _sha256_lf_text(packets_path) != source_hashes[PACKETS_SOURCE_KEY]
    ):
        raise IntegrityError("CLI source files differ from the frozen plan/packet text")
    implementation = plan.get("implementation_sha256") or {}
    if implementation != {
        "src_tradearena_python_tree": _python_tree_sha256(ROOT / "src" / "tradearena")
    }:
        raise IntegrityError("implementation tree differs from the frozen replay plan")


def validate_source_matrix(
    plan: dict[str, Any], plan_rows_path: Path, packets_path: Path, source_root: Path
) -> tuple[
    list[SourceRecord],
    dict[str, dict[str, SourceRecord]],
    dict[str, str],
]:
    if plan.get("schema_version") != PLAN_SCHEMA or plan.get("protocol_id") != PROTOCOL_ID:
        raise IntegrityError("analysis plan schema/protocol mismatch")
    expected = plan.get("expected", {})
    if (
        expected.get("source_rows") != EXPECTED_SOURCE_ROWS
        or expected.get("base_pairs") != EXPECTED_BASE_PAIRS
        or expected.get("replay_rows") != EXPECTED_REPLAY_ROWS
        or expected.get("intent_paths") != EXPECTED_SOURCE_ROWS
        or expected.get("periods_per_path") != EXPECTED_PERIODS
        or expected.get("samples_per_seed") != 3
        or expected.get("seeds_per_model_scenario") != 10
    ):
        raise IntegrityError("analysis plan scale differs from the frozen 900/450/1800 design")
    if expected.get("execution_levels") != list(EXECUTION_LEVELS):
        raise IntegrityError("analysis plan execution levels differ from the frozen design")
    if plan.get("pair_key_fields") != list(PAIR_KEY_FIELDS):
        raise IntegrityError("analysis plan pair key differs from the implemented pair key")
    if plan.get("metrics") != list(PUBLISHED_METRICS):
        raise IntegrityError("analysis plan metrics differ from the replay metric family")
    if plan.get("diagonal_reproduction") != {
        "float_rule": "round(new_value, 6) equals the published submission value",
        "integer_rule": "exact equality",
        "required": True,
    }:
        raise IntegrityError("analysis plan diagonal rule differs from the implemented gate")
    if plan.get("bootstrap") != {
        "draws": 10000,
        "resampling_unit": (
            "shared source seed; retain all models, scenarios, samples, origins, and destinations"
        ),
        "seed": 20260719,
    }:
        raise IntegrityError("analysis plan bootstrap contract differs from the frozen analysis")
    if plan.get("claim_boundary") != {
        "between_origin_contrast": (
            "realized response-path contrast; includes sampling, feedback, and provider-time drift"
        ),
        "causal_execution_contrast": (
            "within one frozen response tape, pre-risk decisions are verified fixed; downstream "
            "risk approval remains execution-endogenous"
        ),
        "forbidden_claim": "the original E0/E1 diagonal difference isolates execution",
        "ranking_claim_rule": (
            "claim execution-alone ranking sensitivity only when both response-origin strata "
            "agree and the seed-cluster interval is stable"
        ),
    }:
        raise IntegrityError("analysis plan claim boundary differs from the implemented estimand")
    _validate_frozen_implementation(plan, plan_rows_path, packets_path)
    rows = _load_plan_rows(plan_rows_path)
    source_snapshot = _source_snapshot(source_root, {row["plan_id"] for row in rows})
    if source_snapshot != plan.get("source_set_sha256"):
        raise IntegrityError("source artifact set differs from the frozen replay plan")
    packets = _read_jsonl(packets_path)
    packet_by_id = {str(packet.get("plan_id", "")): packet for packet in packets}
    if len(packets) != EXPECTED_SOURCE_ROWS or len(packet_by_id) != EXPECTED_SOURCE_ROWS:
        raise IntegrityError("call packet grid is not exactly 900 unique plan ids")
    records: list[SourceRecord] = []
    groups: dict[str, dict[str, SourceRecord]] = defaultdict(dict)
    for row in rows:
        if row.get("protocol_id") != PROTOCOL_ID or row.get("execution_level") not in EXECUTION_LEVELS:
            raise IntegrityError(f"invalid plan protocol/execution for {row.get('plan_id')}")
        packet = packet_by_id.get(row["plan_id"])
        if packet is None:
            raise IntegrityError(f"missing packet for {row['plan_id']}")
        _packet_identity(row, packet)
        record = _validate_source_record(row, packet, source_root)
        records.append(record)
        if row["execution_level"] in groups[record.base_key_sha256]:
            raise IntegrityError(f"duplicate origin arm for base key {record.base_key_sha256}")
        groups[record.base_key_sha256][row["execution_level"]] = record
    if set(packet_by_id) != {row["plan_id"] for row in rows}:
        raise IntegrityError("plan and packet id sets differ")
    if len(groups) != EXPECTED_BASE_PAIRS or any(set(arms) != set(EXECUTION_LEVELS) for arms in groups.values()):
        raise IntegrityError("source matrix is not exactly 450 E0/E1 pairs")
    for base_key, arms in groups.items():
        if arms["E0"].market_path_sha256 != arms["E1"].market_path_sha256:
            raise IntegrityError(f"market path differs across source arms for {base_key}")
        if arms["E0"].prompt_step_hashes[0] != arms["E1"].prompt_step_hashes[0]:
            raise IntegrityError(f"first prompt differs before execution for {base_key}")
    sampling_grid: dict[tuple[str, str, str], dict[int, dict[str, set[int]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set))
    )
    for row in rows:
        group_key = (row["provider"], row["model_id"], row["scenario_id"])
        sampling_grid[group_key][int(row["seed"])][row["execution_level"]].add(
            int(row["sample_index"])
        )
    if len(sampling_grid) != 15:
        raise IntegrityError(f"expected 15 provider-model-scenario groups, found {len(sampling_grid)}")
    expected_samples = {0, 1, 2}
    for group_key, seeds in sampling_grid.items():
        if len(seeds) != 10 or any(
            set(by_level) != set(EXECUTION_LEVELS)
            or any(samples != expected_samples for samples in by_level.values())
            for by_level in seeds.values()
        ):
            raise IntegrityError(f"seed/sample grid differs from the frozen plan for {group_key}")
    return records, dict(groups), source_snapshot


def _source_responses(record: SourceRecord) -> tuple[str, ...]:
    entries = _read_jsonl(record.log_path)
    responses = tuple(str(entry["response_text"]) for entry in entries)
    if len(responses) != EXPECTED_PERIODS:
        raise IntegrityError(f"source response tape changed for {record.plan['plan_id']}")
    if tuple(sha256_text(value) for value in responses) != record.response_step_hashes:
        raise IntegrityError(f"source response tape hash changed for {record.plan['plan_id']}")
    return responses


def _decision_path(trajectory: Any) -> tuple[str, float, float]:
    normalized: list[list[dict[str, Any]]] = []
    decision_count = 0
    hold_count = 0
    gross_exposures: list[float] = []
    for step_index, step in enumerate(trajectory.steps):
        decisions = []
        for decision in step.decisions:
            item = {
                "step_index": step_index,
                "symbol": str(decision.get("symbol", "")),
                "side": str(decision.get("side", "")),
                "target_weight": round(float(decision.get("target_weight", 0.0)), 12),
                "confidence": round(float(decision.get("confidence", 0.0)), 12),
            }
            decisions.append(item)
            decision_count += 1
            hold_count += int(item["side"] == "hold")
        decisions.sort(key=lambda item: item["symbol"])
        normalized.append(decisions)
        gross_exposures.append(sum(abs(float(item["target_weight"])) for item in decisions))
    hold_ratio = hold_count / decision_count if decision_count else 0.0
    mean_gross = sum(gross_exposures) / len(gross_exposures) if gross_exposures else 0.0
    return _canonical_sha256(normalized), hold_ratio, mean_gross


def _replay_one(record: SourceRecord, destination: str) -> dict[str, Any]:
    row = record.plan
    scenario = bridge.SCENARIOS[row["scenario_id"]]
    level = bridge.EXECUTION_LEVELS[destination]
    responses = _source_responses(record)
    analyst = FrozenResponseSequenceAnalyst(
        provider=row["provider"],
        model=row["model_id"],
        sample_index=int(row["sample_index"]),
        responses=responses,
    )
    arena = build_default_system(
        name=f"v03_direct_api_{row['plan_id']}",
        symbols=tuple(scenario["symbols"]),
        periods=EXPECTED_PERIODS,
        seed=int(row["seed"]),
        initial_cash=float(scenario["initial_cash"]),
        strategy_name="signal-weighted",
        risk_name="max-position",
        analyst_names=(),
        execution_mode=str(level["execution_mode"]),
        commission_bps=float(level["commission_bps"]),
        slippage_bps=float(level["slippage_bps"]),
        spread_bps=float(level["spread_bps"]),
        latency_steps=int(level["latency_steps"]),
        participation_rate=float(level["participation_rate"]),
        market_impact=float(level["market_impact"]),
        **scenario["synthetic"],
    )
    arena.analysts = [analyst]
    trajectory, metrics = arena.run()
    if analyst.consumed != EXPECTED_PERIODS or len(trajectory.steps) != EXPECTED_PERIODS:
        raise IntegrityError(
            f"{row['plan_id']}->{destination}: consumed {analyst.consumed} responses / "
            f"{len(trajectory.steps)} steps"
        )
    generated_prompt_aggregate = sha256_text(canonical_json(analyst.generated_prompt_hashes))
    diagonal = destination == row["execution_level"]
    if diagonal and generated_prompt_aggregate != record.run["prompt_calls_sha256"]:
        raise DiagonalReproductionError(
            f"{row['plan_id']}->{destination}: diagonal prompt path did not reproduce"
        )
    for metric in FLOAT_METRICS:
        if metric not in metrics:
            raise IntegrityError(f"{row['plan_id']}->{destination}: missing metric {metric}")
        if diagonal and round(float(metrics[metric]), 6) != round(
            float(record.submission["metrics"][metric]), 6
        ):
            raise DiagonalReproductionError(
                f"{row['plan_id']}->{destination}: diagonal metric mismatch for {metric}"
            )
    for metric in INTEGER_METRICS:
        if metric not in metrics:
            raise IntegrityError(f"{row['plan_id']}->{destination}: missing metric {metric}")
        if diagonal and int(metrics[metric]) != int(record.submission["metrics"][metric]):
            raise DiagonalReproductionError(
                f"{row['plan_id']}->{destination}: diagonal metric mismatch for {metric}"
            )
    decision_hash, hold_ratio, mean_gross = _decision_path(trajectory)
    public_metrics = {
        metric: int(metrics[metric]) if metric in INTEGER_METRICS else round(float(metrics[metric]), 12)
        for metric in PUBLISHED_METRICS
    }
    replay_id = _canonical_sha256(
        {
            "source_plan_id": row["plan_id"],
            "intent_origin_execution": row["execution_level"],
            "replay_execution_level": destination,
        }
    )
    return {
        "protocol_id": PROTOCOL_ID,
        "replay_id": replay_id,
        "base_key_sha256": record.base_key_sha256,
        "source_plan_id": row["plan_id"],
        "provider": row["provider"],
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "scenario_id": row["scenario_id"],
        "contamination_tier": row["contamination_tier"],
        "seed": int(row["seed"]),
        "sample_index": int(row["sample_index"]),
        "intent_origin_execution": row["execution_level"],
        "replay_execution_level": destination,
        "periods": EXPECTED_PERIODS,
        "response_count": len(responses),
        "response_calls_sha256": record.run["response_calls_sha256"],
        "normalized_parsed_response_path_sha256": (
            record.normalized_parsed_response_path_sha256
        ),
        "decision_path_sha256": decision_hash,
        "generated_prompt_calls_sha256": generated_prompt_aggregate,
        "diagonal": diagonal,
        "diagonal_check_applicable": diagonal,
        "diagonal_reproduction_pass": True if diagonal else None,
        "status": "ok",
        **public_metrics,
        "hold_ratio": round(hold_ratio, 12),
        "mean_gross_target_exposure": round(mean_gross, 12),
        "metrics_sha256": _canonical_sha256(public_metrics),
    }


def _intent_row(record: SourceRecord) -> dict[str, Any]:
    row = record.plan
    return {
        "protocol_id": PROTOCOL_ID,
        "base_key_sha256": record.base_key_sha256,
        "source_plan_id": row["plan_id"],
        "provider": row["provider"],
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "scenario_id": row["scenario_id"],
        "contamination_tier": row["contamination_tier"],
        "seed": int(row["seed"]),
        "sample_index": int(row["sample_index"]),
        "intent_origin_execution": row["execution_level"],
        "periods": EXPECTED_PERIODS,
        "response_count": EXPECTED_PERIODS,
        "call_log_sha256": record.run["call_log_sha256"],
        "prompt_calls_sha256": record.run["prompt_calls_sha256"],
        "response_calls_sha256": record.run["response_calls_sha256"],
        "normalized_parsed_response_path_sha256": (
            record.normalized_parsed_response_path_sha256
        ),
        "parse_coverage": record.run["parse_coverage"],
        "source_status": record.run["status"],
    }


def _divergence_row(base_key: str, arms: dict[str, SourceRecord]) -> dict[str, Any]:
    left = arms["E0"]
    right = arms["E1"]
    first_divergence = next(
        (
            index
            for index, (first, second) in enumerate(
                zip(
                    left.parsed_response_step_hashes,
                    right.parsed_response_step_hashes,
                    strict=True,
                )
            )
            if first != second
        ),
        -1,
    )
    row = left.plan
    return {
        "protocol_id": PROTOCOL_ID,
        "base_key_sha256": base_key,
        "provider": row["provider"],
        "model_id": row["model_id"],
        "model_version_or_release": row["model_version_or_release"],
        "scenario_id": row["scenario_id"],
        "contamination_tier": row["contamination_tier"],
        "seed": int(row["seed"]),
        "sample_index": int(row["sample_index"]),
        "first_prompt_equal": left.prompt_step_hashes[0] == right.prompt_step_hashes[0],
        "first_response_hash_equal": left.response_step_hashes[0] == right.response_step_hashes[0],
        "first_parsed_response_equal": (
            left.parsed_response_step_hashes[0] == right.parsed_response_step_hashes[0]
        ),
        "first_parsed_response_divergence_step": first_divergence,
        "full_response_path_equal": left.run["response_calls_sha256"]
        == right.run["response_calls_sha256"],
        "full_parsed_response_path_equal": (
            left.normalized_parsed_response_path_sha256
            == right.normalized_parsed_response_path_sha256
        ),
    }


def _replay_group(item: tuple[str, dict[str, SourceRecord]]) -> tuple[str, list[dict[str, Any]]]:
    base_key, arms = item
    rows: list[dict[str, Any]] = []
    for origin in EXECUTION_LEVELS:
        record = arms[origin]
        by_destination = {
            destination: _replay_one(record, destination) for destination in EXECUTION_LEVELS
        }
        if by_destination["E0"]["decision_path_sha256"] != by_destination["E1"][
            "decision_path_sha256"
        ]:
            raise IntegrityError(f"fixed pre-risk decisions changed for {record.plan['plan_id']}")
        rows.extend(by_destination[destination] for destination in EXECUTION_LEVELS)
    return base_key, rows


def run_replays(
    records: list[SourceRecord],
    groups: dict[str, dict[str, SourceRecord]],
    *,
    workers: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    intent_rows = [_intent_row(record) for record in sorted(records, key=lambda item: item.plan["plan_id"])]
    divergence_rows = [_divergence_row(key, groups[key]) for key in sorted(groups)]
    replay_rows: list[dict[str, Any]] = []
    work = [(base_key, groups[base_key]) for base_key in sorted(groups)]
    if workers == 1:
        completed = map(_replay_group, work)
        pool = None
    else:
        pool = ProcessPoolExecutor(max_workers=workers)
        completed = pool.map(_replay_group, work, chunksize=1)
    try:
        for index, (base_key, rows) in enumerate(completed, start=1):
            if base_key != work[index - 1][0]:
                raise IntegrityError("parallel replay result order changed")
            replay_rows.extend(rows)
            if index % 25 == 0:
                print(f"replayed {index}/{EXPECTED_BASE_PAIRS} base pairs", flush=True)
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
    if (
        len(intent_rows) != EXPECTED_SOURCE_ROWS
        or len(divergence_rows) != EXPECTED_BASE_PAIRS
        or len(replay_rows) != EXPECTED_REPLAY_ROWS
    ):
        raise IntegrityError("generated output counts differ from the frozen plan")
    replay_keys = {
        (
            row["source_plan_id"],
            row["intent_origin_execution"],
            row["replay_execution_level"],
        )
        for row in replay_rows
    }
    if len(replay_keys) != EXPECTED_REPLAY_ROWS:
        raise IntegrityError("replay output keys are duplicated")
    return intent_rows, replay_rows, divergence_rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise IntegrityError(f"refusing to write empty CSV: {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _publish(
    output_dir: Path,
    analysis_plan_path: Path,
    plan_rows_path: Path,
    packets_path: Path,
    source_root: Path,
    intent_rows: list[dict[str, Any]],
    replay_rows: list[dict[str, Any]],
    divergence_rows: list[dict[str, Any]],
    *,
    frozen_plan_sha256: str,
    source_snapshot: dict[str, str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="v03_fixed_intent_", dir=output_dir.parent) as temporary:
        stage = Path(temporary)
        csv_findings = scan_public_artifact_payload(
            {
                "intent_paths": intent_rows,
                "replay_rows": replay_rows,
                "intent_divergence": divergence_rows,
            }
        )
        if csv_findings:
            raise IntegrityError("public CSV privacy scan failed: " + csv_findings[0])
        _write_csv(stage / "intent_paths.csv", intent_rows)
        _write_csv(stage / "replay_rows.csv", replay_rows)
        _write_csv(stage / "intent_divergence.csv", divergence_rows)
        output_sha256 = {
            name: _sha256_hex(stage / name)
            for name in ("intent_paths.csv", "replay_rows.csv", "intent_divergence.csv")
        }
        plan_ids = {str(row["source_plan_id"]) for row in intent_rows}
        if _sha256_hex(analysis_plan_path) != frozen_plan_sha256:
            raise IntegrityError("analysis plan changed during replay")
        if _source_snapshot(source_root, plan_ids) != source_snapshot:
            raise IntegrityError("source artifact set changed during replay")
        current_plan = _read_json(analysis_plan_path)
        _validate_frozen_implementation(current_plan, plan_rows_path, packets_path)
        integrity = {
            "schema_version": INTEGRITY_SCHEMA,
            "protocol_id": PROTOCOL_ID,
            "analysis_plan_sha256": frozen_plan_sha256,
            "source_hash_policy": SOURCE_HASH_POLICY,
            "source_sha256": {
                "plan_rows": _sha256_lf_text(plan_rows_path),
                "call_packets": _sha256_lf_text(packets_path),
                **source_snapshot,
            },
            "output_sha256": output_sha256,
            "expected": {
                "source_rows": EXPECTED_SOURCE_ROWS,
                "base_pairs": EXPECTED_BASE_PAIRS,
                "replay_rows": EXPECTED_REPLAY_ROWS,
                "periods_per_path": EXPECTED_PERIODS,
            },
            "observed": {
                "source_rows": len(intent_rows),
                "base_pairs": len(divergence_rows),
                "replay_rows": len(replay_rows),
                "diagonal_reproductions": sum(
                    bool(row["diagonal_check_applicable"]) for row in replay_rows
                ),
            },
            "checks": {
                "analysis_plan_contract_exact": True,
                "implementation_tree_frozen": True,
                "source_file_sets_frozen": True,
                "source_grid_exact": True,
                "plan_packet_identity": True,
                "artifact_hash_chain": True,
                "source_cross_fields_bound": True,
                "private_log_hashes_and_order": True,
                "paired_market_paths": True,
                "response_tapes_consumed_exactly": True,
                "pre_risk_decisions_fixed_across_execution": True,
                "diagonal_metrics_round6": True,
                "public_privacy_scan": True,
            },
            "failed_count": 0,
            "source_ready": True,
            "raw_prompt_emitted": False,
            "raw_response_emitted": False,
        }
        _write_text_lf(
            stage / "source_integrity.json",
            json.dumps(integrity, indent=2, sort_keys=True) + "\n",
        )
        findings = scan_public_artifact_paths([stage])
        if findings:
            raise IntegrityError("public output privacy scan failed: " + findings[0])
        for name in ("intent_paths.csv", "replay_rows.csv", "intent_divergence.csv"):
            os.replace(stage / name, output_dir / name)
        os.replace(stage / "source_integrity.json", output_dir / "source_integrity.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the zero-network fixed-response-path 2x2 replay."
    )
    parser.add_argument(
        "--analysis-plan",
        default="docs/results/v0_3_fixed_intent_replay/analysis_plan.json",
    )
    parser.add_argument(
        "--plan-rows",
        default="docs/results/v0_3_direct_api_matrix_plan/direct_api_matrix_plan_rows.csv",
    )
    parser.add_argument(
        "--packets",
        default="docs/results/v0_3_direct_api_call_packets/direct_api_call_packets.jsonl",
    )
    parser.add_argument("--source-root", default="outputs/v0_3_direct_api_matrix")
    parser.add_argument("--output-dir", default="docs/results/v0_3_fixed_intent_replay")
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Local replay worker processes (1-8); provider/network calls never occur.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run the complete source gate without replaying or publishing outputs.",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    paths = [Path(value) for value in (args.analysis_plan, args.plan_rows, args.packets, args.source_root, args.output_dir)]
    analysis_plan_path, plan_rows_path, packets_path, source_root, output_dir = [
        path if path.is_absolute() else ROOT / path for path in paths
    ]
    try:
        frozen_plan_sha256 = _sha256_hex(analysis_plan_path)
        plan = _read_json(analysis_plan_path)
        records, groups, source_snapshot = validate_source_matrix(
            plan, plan_rows_path, packets_path, source_root
        )
        print(f"source gate passed: {len(records)} rows / {len(groups)} exact E0-E1 pairs", flush=True)
        if args.validate_only:
            return 0
        intent_rows, replay_rows, divergence_rows = run_replays(
            records, groups, workers=args.workers
        )
        _publish(
            output_dir,
            analysis_plan_path,
            plan_rows_path,
            packets_path,
            source_root,
            intent_rows,
            replay_rows,
            divergence_rows,
            frozen_plan_sha256=frozen_plan_sha256,
            source_snapshot=source_snapshot,
        )
    except DiagonalReproductionError as exc:
        print(f"DIAGONAL REPRODUCTION ERROR: {exc}", file=sys.stderr)
        return 3
    except (IntegrityError, KeyError, TypeError, ValueError) as exc:
        print(f"INTEGRITY ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"published {len(replay_rows)} fixed-response-path replay rows to {output_dir}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
