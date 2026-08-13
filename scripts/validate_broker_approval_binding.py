from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.tools import validate_broker_approval_artifact_file, validate_broker_approval_request_binding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate that a TreLLM broker approval binds to a handoff artifact.")
    parser.add_argument("approval_artifact", help="Path to a broker approval artifact JSON file.")
    parser.add_argument("request_artifact", help="Path to a broker handoff request artifact JSON file.")
    parser.add_argument("--now", default=None, help="Optional ISO timestamp used to reject expired approval artifacts.")
    args = parser.parse_args(argv)

    approval_path = Path(args.approval_artifact)
    request_path = Path(args.request_artifact)
    approval, approval_errors = validate_broker_approval_artifact_file(approval_path, now=args.now)
    errors = approval_errors or validate_broker_approval_request_binding(approval, request_path, now=args.now)
    if errors:
        print(f"Invalid broker approval binding: {approval_path} -> {request_path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid broker approval binding: {approval_path} -> {request_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
