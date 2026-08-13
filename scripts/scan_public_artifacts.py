from __future__ import annotations

import argparse
from pathlib import Path

from tradearena.core.redaction import scan_public_artifact_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan public TreLLM artifacts for raw prompt/response or secret leakage.")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan.")
    args = parser.parse_args()

    findings = scan_public_artifact_paths([Path(path) for path in args.paths])
    if findings:
        print("Public artifact privacy scan failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Public artifact privacy scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
