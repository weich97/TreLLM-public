from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.tools import validate_live_readiness_preflight_bundle_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a TreLLM live-readiness preflight bundle.")
    parser.add_argument("bundle", help="Path to a live-readiness preflight bundle JSON file.")
    parser.add_argument("--now", default=None, help="Optional ISO timestamp used to reject expired approval artifacts.")
    parser.add_argument("--summary-output", default="", help="Optional path to write the preflight summary JSON.")
    args = parser.parse_args(argv)

    path = Path(args.bundle)
    summary, errors = validate_live_readiness_preflight_bundle_file(path, now=args.now)
    if args.summary_output:
        output = Path(args.summary_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        print(f"Invalid live-readiness preflight bundle: {path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid live-readiness preflight bundle: {path}")
    print(f"  components={len(summary.get('components', {}))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
