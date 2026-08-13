from __future__ import annotations

import json

from tradearena.core.serialization import to_jsonable
from tradearena.factory import build_default_system


def main() -> int:
    system = build_default_system(symbols=("SYN", "ALT"), periods=90, seed=11)
    trajectory, metrics = system.run()
    payload = {
        "experiment": trajectory.experiment_name,
        "metrics": metrics,
        "last_step": trajectory.steps[-1].portfolio if trajectory.steps else {},
    }
    print(json.dumps(to_jsonable(payload), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
