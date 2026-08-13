from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json

OUTPUT_DIR = Path("outputs/examples/broker_capability_manifest")
MANIFEST_PATH = OUTPUT_DIR / "capability_manifest.json"
REPORT_PATH = OUTPUT_DIR / "capability_manifest.md"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "trellm_broker_adapter_capability_v0.1",
        "adapter_id": "dry-run-broker-adapter",
        "adapter_name": "Dry-run broker adapter",
        "adapter_kind": "dry_run",
        "default_mode": "offline_export",
        "supported_modes": ["offline_export", "dry_run", "paper_sandbox"],
        "account_modes": ["none", "paper"],
        "network_access": "none",
        "supports_live_submission": False,
        "live_submission_default": False,
        "requires_credentials": False,
        "credential_policy": {
            "no_credentials_in_repo": True,
            "redacted_artifacts_only": True,
            "env_vars": [],
        },
        "safety_controls": {
            "manual_approval_required": True,
            "approval_expiry_required": True,
            "request_hash_binding_required": True,
            "kill_switch_required": True,
            "reconciliation_required": True,
            "artifact_retention_required": True,
        },
        "supported_order_types": ["market", "limit"],
        "supported_time_in_force": ["day"],
        "verification_commands": [
            "python -m tradearena.cli validate-broker-capability outputs/examples/broker_capability_manifest/capability_manifest.json",
        ],
        "safety_note": (
            "This capability manifest describes an offline export and paper-review path. "
            "It does not authorize live submission, read credentials, or call a broker API."
        ),
    }
    write_json(MANIFEST_PATH, manifest)
    REPORT_PATH.write_text(_render_report(manifest), encoding="utf-8")
    print("Broker capability manifest demo")
    print(f"  adapter_id={manifest['adapter_id']}")
    print(f"  default_mode={manifest['default_mode']}")
    print(f"  supports_live_submission={manifest['supports_live_submission']}")
    print(f"  wrote={MANIFEST_PATH}")
    return 0


def _render_report(manifest: dict) -> str:
    controls = manifest["safety_controls"]
    return "\n".join(
        [
            "# TreLLM Broker Adapter Capability Manifest",
            "",
            "This public manifest records what a broker-facing adapter is allowed to do before it can be reviewed.",
            "It is a capability declaration, not permission to submit live orders.",
            "",
            "## Adapter Boundary",
            "",
            f"- Adapter: `{manifest['adapter_name']}`",
            f"- Default mode: `{manifest['default_mode']}`",
            f"- Supported modes: `{', '.join(manifest['supported_modes'])}`",
            f"- Account modes: `{', '.join(manifest['account_modes'])}`",
            f"- Network access: `{manifest['network_access']}`",
            f"- Supports live submission: `{str(manifest['supports_live_submission']).lower()}`",
            f"- Live submission by default: `{str(manifest['live_submission_default']).lower()}`",
            "",
            "## Required Controls",
            "",
            "| Control | Required |",
            "| --- | --- |",
            f"| Manual approval | `{str(controls['manual_approval_required']).lower()}` |",
            f"| Approval expiry | `{str(controls['approval_expiry_required']).lower()}` |",
            f"| Request hash binding | `{str(controls['request_hash_binding_required']).lower()}` |",
            f"| Kill switch | `{str(controls['kill_switch_required']).lower()}` |",
            f"| Reconciliation | `{str(controls['reconciliation_required']).lower()}` |",
            f"| Artifact retention | `{str(controls['artifact_retention_required']).lower()}` |",
            "",
            "## Safety Note",
            "",
            str(manifest["safety_note"]),
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
