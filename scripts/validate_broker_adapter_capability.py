from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.tools import validate_broker_adapter_capability_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a TreLLM broker adapter capability manifest.")
    parser.add_argument("artifact", help="Path to a broker adapter capability manifest JSON file.")
    args = parser.parse_args(argv)

    path = Path(args.artifact)
    _, errors = validate_broker_adapter_capability_file(path)
    if errors:
        print(f"Invalid broker adapter capability manifest: {path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Valid broker adapter capability manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
