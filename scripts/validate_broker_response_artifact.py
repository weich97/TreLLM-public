from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.tools import validate_broker_response_artifact_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a TreLLM broker response artifact.")
    parser.add_argument("artifact", help="Path to a broker response artifact JSON file.")
    args = parser.parse_args(argv)

    path = Path(args.artifact)
    _, errors = validate_broker_response_artifact_file(path)
    if errors:
        print(f"Invalid broker response artifact: {path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid broker response artifact: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
