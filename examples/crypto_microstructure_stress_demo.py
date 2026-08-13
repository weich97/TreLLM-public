from __future__ import annotations

import html
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json
from tradearena.factory import build_default_system

OUTPUT_DIR = Path("outputs/examples/crypto_microstructure_stress")


@dataclass(frozen=True)
class CryptoExecutionPreset:
    name: str
    fee_tier_bps: float
    spread_bps: float
    slippage_bps: float
    participation_rate: float
    latency_steps: int
    market_impact: float


def main() -> int:
    summary = build_crypto_microstructure_stress_summary()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "summary.json", summary)
    _write_svg(OUTPUT_DIR / "crypto_microstructure_stress.svg", summary)
    stress = _stress_row(summary)
    print("Crypto microstructure stress demo")
    print(
        f"  fill_rate={stress['execution_fill_rate']:.3f} rejected={stress['rejected_order_count']} "
        f"slippage={stress['total_slippage_cost']:.2f}"
    )
    print(f"  wrote={OUTPUT_DIR / 'summary.json'}")
    print(f"  wrote={OUTPUT_DIR / 'crypto_microstructure_stress.svg'}")
    return 0


def build_crypto_microstructure_stress_summary(*, periods: int = 72) -> dict[str, Any]:
    presets = (
        CryptoExecutionPreset(
            name="baseline_fee_tier",
            fee_tier_bps=1.0,
            spread_bps=3.0,
            slippage_bps=4.0,
            participation_rate=0.012,
            latency_steps=1,
            market_impact=0.18,
        ),
        CryptoExecutionPreset(
            name="fee_tier_spread_shock",
            fee_tier_bps=15.0,
            spread_bps=42.0,
            slippage_bps=8.0,
            participation_rate=0.003,
            latency_steps=2,
            market_impact=0.35,
        ),
    )
    rows = [_run_preset(preset, periods=periods) for preset in presets]
    stress = next(row for row in rows if row["preset"] == "fee_tier_spread_shock")
    return {
        "schema": "trellm_crypto_microstructure_stress_v0.2",
        "scenario": "no-key synthetic crypto microstructure stress",
        "paper_only": True,
        "downloads_data": False,
        "calibration_boundary": "stress_assumption_not_venue_calibrated",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD"],
        "steps": stress["steps"],
        "reproducible_inputs": {
            "seed": 21,
            "periods": periods,
            "synthetic_volatility_scale": 3.2,
            "synthetic_tail_df": 3,
            "synthetic_jump_probability": 0.08,
            "synthetic_jump_scale": 0.10,
        },
        "presets": rows,
        "cost_delta": {
            "commission_delta": rows[1]["total_commission"] - rows[0]["total_commission"],
            "slippage_delta": rows[1]["total_slippage_cost"] - rows[0]["total_slippage_cost"],
            "fill_rate_delta": rows[1]["execution_fill_rate"] - rows[0]["execution_fill_rate"],
        },
        # Backward-compatible top-level fields used by older demo smoke checks.
        "total_return": stress["total_return"],
        "max_drawdown": stress["max_drawdown"],
        "execution_fill_rate": stress["execution_fill_rate"],
        "rejected_order_count": stress["rejected_order_count"],
        "partial_fill_count": stress["partial_fill_count"],
        "total_slippage_cost": stress["total_slippage_cost"],
        "avg_latency_steps": stress["avg_latency_steps"],
        "submitted_orders": stress["submitted_orders"],
        "pending_orders_last": stress["pending_orders_last"],
        "config": stress["config"],
    }


def _run_preset(preset: CryptoExecutionPreset, *, periods: int) -> dict[str, Any]:
    system = build_default_system(
        name=f"crypto_microstructure_stress_{preset.name}",
        symbols=("BTC-USD", "ETH-USD", "SOL-USD"),
        periods=periods,
        seed=21,
        strategy_name="signal-weighted",
        analyst_names=("momentum", "macro-news"),
        execution_mode="realistic",
        commission_bps=preset.fee_tier_bps,
        spread_bps=preset.spread_bps,
        slippage_bps=preset.slippage_bps,
        participation_rate=preset.participation_rate,
        latency_steps=preset.latency_steps,
        market_impact=preset.market_impact,
        max_position_weight=0.25,
        synthetic_volatility_scale=3.2,
        synthetic_tail_df=3,
        synthetic_jump_probability=0.08,
        synthetic_jump_scale=0.10,
    )
    trajectory, metrics = system.run()
    reports = [step.execution_report for step in trajectory.steps if step.execution_report]
    return {
        "preset": preset.name,
        "steps": len(trajectory.steps),
        "total_return": metrics["total_return"],
        "max_drawdown": metrics["max_drawdown"],
        "execution_fill_rate": metrics["execution_fill_rate"],
        "rejected_order_count": metrics["rejected_order_count"],
        "partial_fill_count": metrics["partial_fill_count"],
        "total_slippage_cost": metrics["total_slippage_cost"],
        "total_commission": sum(float(report.get("total_commission", 0.0)) for report in reports),
        "avg_latency_steps": metrics["avg_latency_steps"],
        "submitted_orders": sum(int(report.get("submitted_orders", 0)) for report in reports),
        "pending_orders_last": int(reports[-1].get("pending_orders", 0)) if reports else 0,
        "fee_tier_bps": preset.fee_tier_bps,
        "spread_bps": preset.spread_bps,
        "config": {
            "fee_tier_bps": preset.fee_tier_bps,
            "spread_bps": preset.spread_bps,
            "base_slippage_bps": preset.slippage_bps,
            "participation_rate": preset.participation_rate,
            "latency_steps": preset.latency_steps,
            "market_impact": preset.market_impact,
            "synthetic_volatility_scale": 3.2,
            "synthetic_tail_df": 3,
            "synthetic_jump_probability": 0.08,
            "synthetic_jump_scale": 0.10,
        },
    }


def _stress_row(summary: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in summary["presets"] if row["preset"] == "fee_tier_spread_shock")


def _write_svg(path: Path, summary: dict[str, Any]) -> None:
    width, height = 920, 420
    stress = _stress_row(summary)
    metrics = [
        ("Fill rate", float(stress["execution_fill_rate"]), 1.0, "#2563eb"),
        ("Rejected", float(stress["rejected_order_count"]), max(1.0, float(stress["submitted_orders"])), "#dc2626"),
        ("Partial fills", float(stress["partial_fill_count"]), max(1.0, float(stress["submitted_orders"])), "#f59e0b"),
        ("Latency", float(stress["avg_latency_steps"]), 3.0, "#7c3aed"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Crypto microstructure stress demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(38, 52, "No-key crypto microstructure stress", 24, "#0f172a", 800),
        _text(38, 82, "Fee-tier and spread-shock presets over the same synthetic inputs; stress assumptions, not venue calibration.", 13, "#64748b", 500),
    ]
    y = 130
    for idx, (label, value, denom, color) in enumerate(metrics):
        yy = y + idx * 58
        width_value = min(420.0, 420.0 * value / denom)
        parts.append(f'<rect x="38" y="{yy}" width="420" height="22" rx="6" fill="#e2e8f0"/>')
        parts.append(f'<rect x="38" y="{yy}" width="{width_value:.1f}" height="22" rx="6" fill="{color}"/>')
        parts.append(_text(478, yy + 17, f"{label}: {value:.3f}", 13, "#0f172a", 800))
    parts.append('<rect x="38" y="352" width="820" height="1" fill="#cbd5e1"/>')
    parts.append(
        _text(
            38,
            382,
            f"Stress slippage: ${float(stress['total_slippage_cost']):,.2f} | "
            f"Commission delta: ${float(summary['cost_delta']['commission_delta']):,.2f}",
            13,
            "#334155",
            800,
        )
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(str(value))}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
