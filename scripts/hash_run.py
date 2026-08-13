from __future__ import annotations

import argparse
import json

from tradearena.core.reproducibility import hash_trajectory_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute a reproducibility hash for a TreLLM trajectory JSON.")
    parser.add_argument("trajectory", help="Path to a trajectory JSON file.")
    args = parser.parse_args(argv)

    print(json.dumps(hash_trajectory_file(args.trajectory), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
