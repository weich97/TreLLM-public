from __future__ import annotations

import json
from pathlib import Path

from tradearena.core.serialization import to_jsonable, write_json
from tradearena.evaluation import BenchmarkCase, BenchmarkRunner
from tradearena.factory import build_default_system

OUTPUT_DIR = Path("outputs/examples")


def main() -> int:
    cases = [
        BenchmarkCase(
            name="risk_aware_realistic",
            build_system=lambda: build_default_system(
                name="risk_aware_realistic",
                symbols=("SYN", "ALT", "DEF"),
                periods=80,
                seed=7,
                strategy_name="signal-weighted",
                risk_name="max-position",
                execution_mode="realistic",
            ),
            description="Momentum plus macro/news signals, risk gate, and realistic execution.",
        ),
        BenchmarkCase(
            name="buy_and_hold_realistic",
            build_system=lambda: build_default_system(
                name="buy_and_hold_realistic",
                symbols=("SYN", "ALT", "DEF"),
                periods=80,
                seed=7,
                strategy_name="buy-and-hold",
                risk_name="max-position",
                execution_mode="realistic",
            ),
            description="Equal-weight buy-and-hold under the same execution simulator.",
        ),
    ]

    results = BenchmarkRunner(cases).run()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "quickstart_core_metrics.json", results)

    print("case,total_return,max_drawdown,fill_rate,clipped,rejected")
    for name, metrics in results.items():
        print(
            ",".join(
                [
                    name,
                    f"{float(metrics['total_return']):.4f}",
                    f"{float(metrics['max_drawdown']):.4f}",
                    f"{float(metrics['execution_fill_rate']):.3f}",
                    str(metrics["risk_clipped_decisions"]),
                    str(metrics["rejected_order_count"]),
                ]
            )
        )
    print(f"\nWrote {OUTPUT_DIR / 'quickstart_core_metrics.json'}")
    print(json.dumps(to_jsonable({"examples_next": "Run examples/audit_trajectory_walkthrough.py"}), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
