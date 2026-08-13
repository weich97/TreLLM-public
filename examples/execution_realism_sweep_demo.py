from __future__ import annotations

import csv
from pathlib import Path

from tradearena.core.serialization import write_json
from tradearena.factory import build_default_system

OUTPUT_DIR = Path("outputs/examples")


def main() -> int:
    cases = [
        (
            "ideal_no_friction",
            "Idealized fills with no fees, spread, latency, or liquidity caps.",
            {"execution_mode": "ideal", "commission_bps": 0.0, "slippage_bps": 0.0},
        ),
        (
            "realistic_default",
            "Baseline realistic simulator with fees, impact, latency, and participation limits.",
            {"execution_mode": "realistic"},
        ),
        (
            "high_spread",
            "Wide quoted spread: market orders cross half the spread before impact and volatility slippage.",
            {
                "execution_mode": "realistic",
                "spread_bps": 95.0,
                "slippage_bps": 4.0,
                "participation_rate": 0.04,
                "market_impact": 0.18,
            },
        ),
        (
            "low_liquidity",
            "Thin book: tighter participation cap forces partial fills and rejections.",
            {"execution_mode": "realistic", "participation_rate": 0.015, "market_impact": 0.38, "slippage_bps": 5.0},
        ),
        (
            "high_latency",
            "Delayed execution: orders enter a queue before they become eligible for fills.",
            {"execution_mode": "realistic", "latency_steps": 4, "participation_rate": 0.03, "market_impact": 0.24},
        ),
    ]
    rows = []
    for name, description, overrides in cases:
        _, metrics = build_default_system(
            name=f"execution_realism_{name}",
            symbols=("SYN", "ALT", "DEF"),
            periods=50,
            seed=19,
            strategy_name="signal-weighted",
            risk_name="max-position",
            max_position_weight=0.28,
            **overrides,
        ).run()
        rows.append(
            {
                "case": name,
                "description": description,
                "spread_bps": overrides.get("spread_bps", 0.0),
                "base_slippage_bps": overrides.get("slippage_bps", 2.0),
                "participation_rate": overrides.get("participation_rate", 0.05),
                "latency_steps": overrides.get("latency_steps", 1 if overrides.get("execution_mode") != "ideal" else 0),
                "market_impact": overrides.get(
                    "market_impact",
                    0.15 if overrides.get("execution_mode") != "ideal" else 0.0,
                ),
                "total_return": metrics["total_return"],
                "max_drawdown": metrics["max_drawdown"],
                "fill_rate": metrics["execution_fill_rate"],
                "partial_fill_rate": metrics["partial_fill_rate"],
                "rejected_orders": metrics["rejected_order_count"],
                "pending_orders": metrics["pending_order_count"],
                "slippage_cost": metrics["total_slippage_cost"],
                "commission": metrics["total_commission"],
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(
        OUTPUT_DIR / "execution_realism_sweep_summary.json",
        {
            "rows": rows,
            "interpretation": {
                "high_spread": (
                    "The high-spread preset isolates bid-ask spread as an execution friction: "
                    "fill eligibility stays close to the default case, while slippage cost rises "
                    "because every market order crosses half the quoted spread."
                )
            },
        },
    )
    _write_csv(OUTPUT_DIR / "execution_realism_sweep.csv", rows)
    _write_svg(OUTPUT_DIR / "execution_realism_sweep.svg", rows)

    print("Execution realism sweep demo")
    for row in rows:
        print(
            f"  {row['case']}: return={row['total_return']:.4f} "
            f"fill={row['fill_rate']:.3f} spread={float(row['spread_bps']):.1f}bps "
            f"slippage={row['slippage_cost']:.1f} rejected={row['rejected_orders']}"
        )
    print(f"\nWrote {OUTPUT_DIR / 'execution_realism_sweep.svg'}")
    return 0


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_svg(path: Path, rows: list[dict[str, object]]) -> None:
    width, height = 1080, 390
    max_slip = max(1.0, max(float(row["slippage_cost"]) for row in rows))
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="Execution realism sweep">'
        ),
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 44, "Execution realism changes the measured strategy", 22, "#0f172a", 800),
        _text(
            36,
            72,
            "Same agent and market, different simulator frictions: spread, liquidity, latency, slippage, rejections.",
            13,
            "#64748b",
            400,
        ),
    ]
    for idx, row in enumerate(rows):
        x = 54 + idx * 198
        ret = float(row["total_return"])
        fill = float(row["fill_rate"])
        slip = float(row["slippage_cost"])
        spread = float(row["spread_bps"])
        ret_h = min(110, abs(ret) * 170)
        fill_h = fill * 120
        slip_h = slip / max_slip * 120
        parts.append(f'<rect x="{x}" y="{255 - fill_h:.1f}" width="38" height="{fill_h:.1f}" rx="5" fill="#2563eb"/>')
        parts.append(
            f'<rect x="{x + 48}" y="{255 - slip_h:.1f}" width="38" '
            f'height="{slip_h:.1f}" rx="5" fill="#f59e0b"/>'
        )
        color = "#059669" if ret >= 0 else "#dc2626"
        y = 255 - ret_h if ret >= 0 else 255
        parts.append(f'<rect x="{x + 96}" y="{y:.1f}" width="38" height="{ret_h:.1f}" rx="5" fill="{color}"/>')
        parts.append(_text(x + 67, 294, str(row["case"]).replace("_", " "), 12, "#0f172a", 700, "middle"))
        parts.append(_text(x + 67, 315, f"spread {spread:.0f}bp", 11, "#64748b", 500, "middle"))
        parts.append(_text(x + 67, 334, f"rej {int(row['rejected_orders'])}", 11, "#64748b", 500, "middle"))
    parts.append(
        _text(
            54,
            362,
            "Blue=fill rate, amber=slippage cost scaled, green/red=absolute return magnitude",
            12,
            "#64748b",
            500,
        )
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}" '
        f'text-anchor="{anchor}">{value}</text>'
    )


if __name__ == "__main__":
    raise SystemExit(main())
