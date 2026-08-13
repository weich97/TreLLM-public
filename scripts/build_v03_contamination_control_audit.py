from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "trellm-v0.3-protocol"
DEFAULT_OUTPUT_DIR = "docs/results/v0_3_contamination_control_audit"
PROTOCOL_PATH = ROOT / "benchmarks" / "v0.3" / "protocol.json"
MEMORY_SUMMARY_PATH = ROOT / "docs/results/v0_3_memory_contamination/memory_contamination_summary.json"
MEMORY_CONTROLS_PATH = ROOT / "docs/results/v0_3_memory_contamination/contamination_tier_controls.csv"
FORWARD_FREEZE_SCRIPT = ROOT / "scripts/freeze_forward_window.py"
FIELDS = [
    "protocol_id",
    "contamination_tier",
    "tier_name",
    "protocol_required_controls",
    "memory_artifact_status",
    "readiness_status",
    "claim_scope",
    "blocking_gaps",
    "verification_path",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the TreLLM v0.3 contamination-control audit artifact.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol = _load_json(PROTOCOL_PATH)
    memory_summary = _load_json(MEMORY_SUMMARY_PATH)
    memory_controls = _load_memory_controls()
    rows = _audit_rows(protocol, memory_summary, memory_controls)
    summary = _summary(rows, memory_summary)

    _write_csv(output_dir / "contamination_control_audit.csv", rows)
    _write_json(output_dir / "contamination_control_audit_summary.json", summary)
    (output_dir / "contamination_control_audit.md").write_text(_summary_markdown(summary, rows), encoding="utf-8")

    print(f"Wrote {_display(output_dir / 'contamination_control_audit.csv')}")
    print(f"Wrote {_display(output_dir / 'contamination_control_audit_summary.json')}")
    print(f"Wrote {_display(output_dir / 'contamination_control_audit.md')}")
    print(f"Contamination tiers audited: {len(rows)}")
    print(f"Scientific-ready tiers: {summary['scientific_ready_tier_count']}")
    return 0


def _audit_rows(
    protocol: dict[str, Any],
    memory_summary: dict[str, Any],
    memory_controls: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    implemented_tiers = set(memory_summary.get("implemented_tiers", []))
    rows: list[dict[str, str]] = []
    for tier in protocol.get("contamination_tiers", []):
        tier_id = str(tier.get("id", ""))
        controls = "; ".join(str(control) for control in tier.get("required_controls", []))
        memory_status = memory_controls.get(tier_id, {}).get("status_in_this_artifact", "missing")
        readiness = _readiness_status(tier_id, memory_status, implemented_tiers)
        rows.append(
            {
                "protocol_id": PROTOCOL_ID,
                "contamination_tier": tier_id,
                "tier_name": str(tier.get("name", "")),
                "protocol_required_controls": controls,
                "memory_artifact_status": memory_status,
                "readiness_status": readiness,
                "claim_scope": _claim_scope(tier_id, tier, readiness),
                "blocking_gaps": _blocking_gaps(tier_id, memory_status),
                "verification_path": _verification_path(tier_id),
            }
        )
    return rows


def _readiness_status(tier_id: str, memory_status: str, implemented_tiers: set[str]) -> str:
    if tier_id in implemented_tiers and memory_status == "implemented":
        return "fixture-mechanism-ready"
    if tier_id == "C2" and FORWARD_FREEZE_SCRIPT.exists():
        return "tooling-present-contract-only"
    if memory_status == "control-contract-only":
        return "contract-only"
    return "missing"


def _claim_scope(tier_id: str, tier: dict[str, Any], readiness: str) -> str:
    protocol_scope = str(tier.get("claim_scope", ""))
    if readiness == "fixture-mechanism-ready":
        return f"{protocol_scope}; current public artifact is C0 fixture mechanism evidence, not model-performance evidence."
    if tier_id == "C2":
        return (
            f"{protocol_scope}; freeze tooling exists, but no committed future-window result is present in v0.3 public artifacts."
        )
    return f"{protocol_scope}; control requirements are declared but not yet backed by public rows."


def _blocking_gaps(tier_id: str, memory_status: str) -> str:
    if tier_id == "C0" and memory_status == "implemented":
        return ""
    if tier_id == "C1":
        return "anonymized_real_rows_missing;memorization_probe_rows_missing"
    if tier_id == "C2":
        return "forward_window_commitment_missing;post_window_results_missing;walk_forward_provenance_missing"
    return "tier_controls_missing"


def _verification_path(tier_id: str) -> str:
    if tier_id == "C0":
        return "docs/results/v0_3_memory_contamination/memory_contamination_summary.json"
    if tier_id == "C2":
        return "scripts/freeze_forward_window.py"
    return "docs/results/v0_3_memory_contamination/contamination_tier_controls.csv"


def _summary(rows: list[dict[str, str]], memory_summary: dict[str, Any]) -> dict[str, Any]:
    scientific_ready = [row for row in rows if row["readiness_status"] == "scientific-ready"]
    contract_only = [
        row
        for row in rows
        if row["readiness_status"] in {"contract-only", "tooling-present-contract-only"}
    ]
    return {
        "schema": "trellm_v0_3_contamination_control_audit_v0.1",
        "protocol_id": PROTOCOL_ID,
        "artifact_id": "contamination_control_audit",
        "tier_count": len(rows),
        "fixture_ready_tier_count": sum(1 for row in rows if row["readiness_status"] == "fixture-mechanism-ready"),
        "contract_only_tier_count": len(contract_only),
        "scientific_ready_tier_count": len(scientific_ready),
        "forward_freeze_tooling_present": FORWARD_FREEZE_SCRIPT.exists(),
        "memory_artifact_schema": memory_summary.get("schema", ""),
        "memory_artifact_control_contract_only_tiers": memory_summary.get("control_contract_only_tiers", []),
        "claim_boundary": (
            "This audit maps v0.3 contamination tiers to current public evidence. C0 is fixture mechanism evidence; "
            "C1 and C2 remain contract-only and must not support scientific contamination-control claims yet."
        ),
        "artifacts": [
            "contamination_control_audit.csv",
            "contamination_control_audit_summary.json",
            "contamination_control_audit.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], rows: list[dict[str, str]]) -> str:
    lines = [
        "# TreLLM v0.3 Contamination Control Audit",
        "",
        "This artifact maps C0/C1/C2 contamination controls to current public evidence.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Tiers audited: `{summary['tier_count']}`",
        f"- Fixture-ready tiers: `{summary['fixture_ready_tier_count']}`",
        f"- Contract-only tiers: `{summary['contract_only_tier_count']}`",
        f"- Scientific-ready tiers: `{summary['scientific_ready_tier_count']}`",
        f"- Forward-freeze tooling present: `{summary['forward_freeze_tooling_present']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        "",
        "## Tier Readiness",
        "",
        "| Tier | Name | Readiness | Memory artifact status | Blocking gaps | Claim scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['contamination_tier']} | {row['tier_name']} | {row['readiness_status']} | "
            f"{row['memory_artifact_status']} | {row['blocking_gaps']} | {row['claim_scope']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{_display(path)} must contain a JSON object")
    return payload


def _load_memory_controls() -> dict[str, dict[str, str]]:
    with MEMORY_CONTROLS_PATH.open(newline="", encoding="utf-8") as handle:
        return {row["contamination_tier"]: row for row in csv.DictReader(handle)}


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
