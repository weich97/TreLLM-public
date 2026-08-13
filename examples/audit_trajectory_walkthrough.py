from __future__ import annotations

from pathlib import Path

from tradearena.core.serialization import write_json
from tradearena.factory import build_default_system

OUTPUT_DIR = Path("outputs/examples")


def main() -> int:
    system = build_default_system(
        name="audit_walkthrough",
        symbols=("SYN", "ALT", "DEF"),
        periods=90,
        seed=11,
        strategy_name="signal-weighted",
        risk_name="max-position",
        execution_mode="realistic",
        max_position_weight=0.22,
        participation_rate=0.01,
        latency_steps=2,
        market_impact=0.35,
    )
    trajectory, metrics = system.run()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "audit_walkthrough_trajectory.json"
    write_json(output_path, trajectory.to_dict())

    step = _first_interesting_step(trajectory.steps)
    print("One auditable decision step")
    print(f"  timestamp: {step.timestamp.isoformat()}")
    print(f"  prices: {step.observation['prices']}")
    print(f"  proposed decisions: {len(step.decisions)}")
    print(f"  approved decisions: {len(step.approved_decisions)}")
    print(f"  submitted orders: {len(step.orders)}")
    print(f"  fills: {len(step.fills)}")
    print(f"  risk clipped: {step.risk_report.get('clipped_count', 0)}")
    print(f"  risk blocked: {step.risk_report.get('blocked_count', 0)}")
    print(f"  pending orders: {step.execution_report.get('pending_orders', 0)}")
    print(f"  rejected orders: {step.execution_report.get('rejected_orders', 0)}")
    print(f"  memory events recorded: {len(step.memory_events)}")
    print("\nReproducibility fingerprint")
    repro = step.reproducibility_state
    print(f"  prompt_version: {repro.get('prompt_version')}")
    print(f"  model_version: {repro.get('model_version')}")
    print(f"  memory_digest: {repro.get('memory_digest')}")
    print(f"  random_seed: {repro.get('random_seed')}")
    print("\nRun metrics")
    print(f"  total_return={float(metrics['total_return']):.4f}")
    print(f"  max_drawdown={float(metrics['max_drawdown']):.4f}")
    print(f"  fill_rate={float(metrics['execution_fill_rate']):.3f}")
    print(f"\nWrote replayable trajectory to {output_path}")
    return 0


def _first_interesting_step(steps):
    for step in steps:
        if step.risk_report.get("clipped_count", 0) or step.execution_report.get("pending_orders", 0):
            return step
    return steps[-1]


if __name__ == "__main__":
    raise SystemExit(main())
