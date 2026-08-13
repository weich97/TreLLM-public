from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json
from tradearena.factory import build_default_system

OUTPUT_DIR = Path("outputs/examples/rl_policy_baseline")


def main() -> int:
    system = build_default_system(
        name="mock_rl_policy_baseline",
        symbols=("SYN", "ALT", "DEF"),
        periods=48,
        seed=13,
        analyst_names=(),
        strategy_name="mock-rl-policy",
        execution_mode="realistic",
        max_position_weight=0.25,
    )
    trajectory, metrics = system.run()
    last_decisions = trajectory.steps[-1].decisions if trajectory.steps else []
    summary = {
        "policy": "deterministic mock deep-RL allocation strategy",
        "trained_model_included": False,
        "integration_goal": "show StrategyAgent compatibility with risk, execution, trajectory, and evaluators",
        "steps": len(trajectory.steps),
        "total_return": metrics["total_return"],
        "max_drawdown": metrics["max_drawdown"],
        "execution_fill_rate": metrics["execution_fill_rate"],
        "risk_audit_coverage": metrics["risk_audit_coverage"],
        "last_decisions": last_decisions,
        "future_adapter_note": "Replace DeterministicRLAllocationStrategy._policy_scores with a FinRL/Qlib model output.",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "summary.json", summary)
    _write_svg(OUTPUT_DIR / "rl_policy_baseline.svg", summary)
    print("RL policy baseline demo")
    print(f"  steps={summary['steps']} fill_rate={summary['execution_fill_rate']:.3f}")
    print(f"  wrote={OUTPUT_DIR / 'summary.json'}")
    print(f"  wrote={OUTPUT_DIR / 'rl_policy_baseline.svg'}")
    return 0


def _write_svg(path: Path, summary: dict[str, object]) -> None:
    decisions = summary["last_decisions"]
    width, height = 860, 380
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="RL policy baseline demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 52, "Mock deep-RL policy wrapper", 24, "#0f172a", 800),
        _text(36, 82, "A deterministic CI-safe strategy emits normal TreLLM decisions and reuses risk, execution, and evaluation.", 13, "#64748b", 500),
    ]
    y = 126
    for idx, decision in enumerate(decisions[:6]):
        weight = float(decision.get("target_weight", 0.0))
        yy = y + idx * 42
        parts.append(f'<rect x="36" y="{yy}" width="390" height="22" rx="6" fill="#e2e8f0"/>')
        parts.append(f'<rect x="36" y="{yy}" width="{max(3.0, weight * 390):.1f}" height="22" rx="6" fill="#2563eb"/>')
        parts.append(_text(448, yy + 17, f"{decision.get('symbol')} target {weight:.1%}", 13, "#0f172a", 800))
    parts.append(_text(36, 340, "No trained model is shipped; plug in FinRL/Qlib outputs by replacing the policy-score method.", 12, "#64748b", 700))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(str(value))}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
