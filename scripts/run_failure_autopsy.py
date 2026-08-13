from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tradearena.evaluation.autopsy import autopsy_trajectory


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify TreLLM trajectory failure modes.")
    parser.add_argument("--trajectory", default="outputs/examples/audit_walkthrough_trajectory.json")
    parser.add_argument("--output-json", default="outputs/examples/failure_autopsy.json")
    parser.add_argument("--output-md", default="outputs/examples/failure_autopsy.md")
    args = parser.parse_args()

    trajectory_path = Path(args.trajectory)
    payload = json.loads(trajectory_path.read_text(encoding="utf-8"))
    autopsy = autopsy_trajectory(payload)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(autopsy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(_render_markdown(autopsy, trajectory_path), encoding="utf-8")

    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")
    return 0


def _render_markdown(autopsy: dict[str, Any], trajectory_path: Path) -> str:
    lines = [
        "# Failure Autopsy",
        "",
        f"Trajectory: `{trajectory_path}`",
        "",
        "| Failure mode | Count |",
        "| --- | ---: |",
    ]
    for mode, count in autopsy["failure_mode_counts"].items():
        lines.append(f"| `{mode}` | {count} |")
    lines.extend(
        [
            "",
            "## Flagged Steps",
            "",
            "| Step | Timestamp | Failure modes | Evidence |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for step in autopsy["steps"]:
        evidence = step.get("evidence", {})
        compact = ", ".join(
            f"{key}={value}"
            for key, value in evidence.items()
            if value not in (0, 0.0, "", None)
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(step["step"]),
                    str(step.get("timestamp", "")),
                    ", ".join(f"`{mode}`" for mode in step.get("failure_modes", [])),
                    compact,
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
