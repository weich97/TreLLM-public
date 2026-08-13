from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "spec_id",
    "status",
    "claim_boundary",
    "data_windows",
    "market_rules",
    "execution",
    "allowed_information",
    "model_audit",
    "seeds",
    "baselines",
    "metrics",
    "statistics",
    "failure_policy",
    "required_artifacts",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and hash a TradeArena benchmark spec JSON file.")
    parser.add_argument("spec", nargs="?", default="benchmarks/v0.2/spec.json")
    args = parser.parse_args()

    try:
        payload = _load_spec(Path(args.spec))
    except ValueError as exc:
        result = {
            "spec": args.spec,
            "valid": False,
            "spec_id": None,
            "schema_version": None,
            "canonical_sha256": None,
            "errors": [str(exc)],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    errors = validate_spec(payload)
    result = {
        "spec": args.spec,
        "valid": not errors,
        "spec_id": payload.get("spec_id") or payload.get("protocol_id"),
        "schema_version": payload.get("schema_version"),
        "canonical_sha256": canonical_spec_hash(payload),
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _load_spec(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("benchmark spec file not found") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("benchmark spec file must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("benchmark spec file must be a JSON object")
    return payload


def validate_spec(payload: dict[str, Any]) -> list[str]:
    if payload.get("schema_version") == "trellm_protocol_v0.3":
        return _validate_protocol_v03(payload)
    return _validate_benchmark_spec_v02(payload)


def _validate_benchmark_spec_v02(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_TOP_LEVEL.difference(payload)
    if missing:
        errors.append("missing top-level fields: " + ", ".join(sorted(missing)))
    if payload.get("status") != "frozen":
        errors.append("status must be 'frozen'")
    seeds = payload.get("seeds", [])
    if not isinstance(seeds, list) or len(seeds) < 5:
        errors.append("seeds must contain at least five entries")
    if "always-hold" not in payload.get("baselines", []):
        errors.append("baselines must include always-hold")
    if "random" not in payload.get("baselines", []):
        errors.append("baselines must include random")
    paired_tests = payload.get("statistics", {}).get("paired_tests", [])
    for test_name in ("paired_bootstrap", "paired_sign_flip_permutation"):
        if test_name not in paired_tests:
            errors.append(f"statistics.paired_tests must include {test_name}")
    metrics = payload.get("metrics", {})
    for metric in ("total_return", "max_drawdown", "execution_fill_rate", "trajectory_reproducibility_coverage"):
        if metric not in metrics.get("primary", []):
            errors.append(f"metrics.primary must include {metric}")
    real_windows = payload.get("data_windows", {}).get("real_market", [])
    if not real_windows:
        errors.append("data_windows.real_market must define at least one window")
    for index, window in enumerate(real_windows):
        for field in ("symbols", "start", "end", "frequency", "max_periods", "window_offset_policy"):
            if field not in window:
                errors.append(f"real_market[{index}] missing {field}")
    return errors


def _validate_protocol_v03(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "protocol_id",
        "status",
        "system_identity",
        "paper_positioning",
        "provider_protocol",
        "execution_ladder",
        "contamination_tiers",
        "metrics",
        "statistics",
        "finaudit_track",
        "claim_boundaries",
        "external_reproduction",
        "required_artifacts",
        "milestones",
    }
    missing = required.difference(payload)
    if missing:
        errors.append("missing top-level fields: " + ", ".join(sorted(missing)))

    if payload.get("status") not in {"draft", "candidate", "frozen"}:
        errors.append("status must be draft, candidate, or frozen")

    identity = payload.get("system_identity", {})
    if identity.get("system_name") != "TreLLM":
        errors.append("system_identity.system_name must be TreLLM")
    if identity.get("leaderboard_name") != "TradeArena":
        errors.append("system_identity.leaderboard_name must be TradeArena")

    headline = payload.get("provider_protocol", {}).get("headline_results", {})
    if headline.get("allow_routed_providers") is not False:
        errors.append("provider_protocol.headline_results.allow_routed_providers must be false")
    required_manifest_fields = set(payload.get("provider_protocol", {}).get("required_manifest_fields", []))
    for field in ("provider", "model_id", "model_version_or_release", "prompt_sha256", "response_sha256"):
        if field not in required_manifest_fields:
            errors.append(f"provider_protocol.required_manifest_fields must include {field}")

    execution_ids = {entry.get("id") for entry in payload.get("execution_ladder", []) if isinstance(entry, dict)}
    for level in ("E0", "E1", "E2", "E3"):
        if level not in execution_ids:
            errors.append(f"execution_ladder must include {level}")

    contamination_ids = {entry.get("id") for entry in payload.get("contamination_tiers", []) if isinstance(entry, dict)}
    for tier in ("C0", "C1", "C2"):
        if tier not in contamination_ids:
            errors.append(f"contamination_tiers must include {tier}")

    metrics = payload.get("metrics", {})
    for metric in ("intent_to_execution_gap", "memory_pollution_ratio", "memory_driven_leverage_amplification"):
        if metric not in metrics.get("mechanism", []):
            errors.append(f"metrics.mechanism must include {metric}")

    stats = payload.get("statistics", {})
    llm_stats = stats.get("llm_main_comparison", {})
    if llm_stats.get("minimum_seeds", 0) < 10:
        errors.append("statistics.llm_main_comparison.minimum_seeds must be at least 10")
    if llm_stats.get("samples_per_seed", 0) < 3:
        errors.append("statistics.llm_main_comparison.samples_per_seed must be at least 3")
    baseline_stats = stats.get("deterministic_baseline", {})
    if baseline_stats.get("minimum_seeds", 0) < 30:
        errors.append("statistics.deterministic_baseline.minimum_seeds must be at least 30")
    for method in ("BH-FDR", "effect_size", "power_curve_or_detectable_effect_note", "variance_decomposition"):
        if method not in stats.get("required_methods", []):
            errors.append(f"statistics.required_methods must include {method}")

    finaudit = payload.get("finaudit_track", {})
    if "self_audit_bias" not in finaudit.get("required_analyses", []):
        errors.append("finaudit_track.required_analyses must include self_audit_bias")
    if "f1" not in finaudit.get("required_metrics", []):
        errors.append("finaudit_track.required_metrics must include f1")

    external_reproduction = payload.get("external_reproduction", {})
    if external_reproduction.get("minimum_independent_reports", 0) < 3:
        errors.append("external_reproduction.minimum_independent_reports must be at least 3")

    artifacts = payload.get("required_artifacts", [])
    for artifact in (
        "direct-provider manifest schema or contract",
        "contamination-control readiness audit",
        "execution stress-grid report",
        "FinAudit direct-model audit plan",
        "power curve or detectable effect note",
        "variance decomposition table",
        "claim-boundary audit",
        "direct API redaction and submission checklist",
        "direct API model matrix plan",
        "direct API call packet manifest",
        "direct API model matrix gate",
        "external reproduction report gate",
        "external reproduction bundle",
    ):
        if artifact not in artifacts:
            errors.append(f"required_artifacts must include {artifact}")
    return errors


def canonical_spec_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
