from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.submissions import validate_submission_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a redacted TradeArena benchmark submission.")
    parser.add_argument("submission", help="Path to a benchmark submission JSON file.")
    parser.add_argument(
        "--no-verify-hash",
        action="store_true",
        help="Check shape only; do not compare the reproducibility_hash field.",
    )
    args = parser.parse_args(argv)

    path = Path(args.submission)
    _, errors = validate_submission_file(path, verify_hash=not args.no_verify_hash)
    if errors:
        print(f"Invalid benchmark submission: {path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid benchmark submission: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
