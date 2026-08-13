from __future__ import annotations

import csv
from pathlib import Path

from tradearena.core.serialization import write_json
from tradearena.factory import build_default_system

OUTPUT_DIR = Path("outputs/examples")
SYMBOLS = ("SYN", "ALT", "DEF", "GHI", "JKL", "MNO")


def main() -> int:
    cases = [
        ("buy_and_hold", {"strategy_name": "buy-and-hold", "risk_name": "max-position", "max_position_weight": 0.18}),
        ("signal_weighted", {"strategy_name": "signal-weighted", "risk_name": "max-position", "max_position_weight": 0.18}),
        ("markowitz_mvo", {"strategy_name": "mean-variance", "risk_name": "max-position", "max_position_weight": 0.18}),
    ]
    rows = []
    for name, overrides in cases:
        trajectory, metrics = build_default_system(
            name=f"portfolio_baseline_{name}",
            symbols=SYMBOLS,
            periods=55,
            seed=31,
            execution_mode="realistic",
            participation_rate=0.04,
            market_impact=0.20,
            **overrides,
        ).run()
        last_weights = [abs(float(decision.get("target_weight", 0.0))) for decision in trajectory.steps[-1].approved_decisions]
        herfindahl = sum(weight * weight for weight in last_weights)
        rows.append(
            {
                "case": name,
                "total_return": metrics["total_return"],
                "max_drawdown": metrics["max_drawdown"],
                "sharpe": metrics["sharpe"],
                "fill_rate": metrics["execution_fill_rate"],
                "risk_clipped_decisions": metrics["risk_clipped_decisions"],
                "last_step_herfindahl": herfindahl,
                "last_step_active_positions": sum(1 for weight in last_weights if weight > 1e-6),
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "portfolio_markowitz_summary.json", {"rows": rows})
    _write_csv(OUTPUT_DIR / "portfolio_markowitz.csv", rows)
    _write_svg(OUTPUT_DIR / "portfolio_markowitz.svg", rows)

    print("Portfolio baseline / Markowitz demo")
    for row in rows:
        print(
            f"  {row['case']}: return={row['total_return']:.4f} "
            f"dd={row['max_drawdown']:.4f} H={row['last_step_herfindahl']:.3f}"
        )
    print(f"\nWrote {OUTPUT_DIR / 'portfolio_markowitz.svg'}")
    return 0


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_svg(path: Path, rows: list[dict[str, object]]) -> None:
    width, height = 820, 340
    max_return = max(0.001, max(abs(float(row["total_return"])) for row in rows))
    max_h = max(0.001, max(float(row["last_step_herfindahl"]) for row in rows))
    colors = {"buy_and_hold": "#2563eb", "signal_weighted": "#059669", "markowitz_mvo": "#7c3aed"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Portfolio Markowitz baseline demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 44, "Portfolio baselines expose allocation behavior", 22, "#0f172a", 800),
        _text(36, 72, "Same data and simulator, replace only the strategy: passive, signal-weighted, rolling Markowitz/MVO.", 13, "#64748b", 400),
        '<line x1="92" y1="260" x2="760" y2="260" stroke="#cbd5e1"/>',
        '<line x1="92" y1="112" x2="92" y2="260" stroke="#cbd5e1"/>',
        _text(94, 286, "return", 12, "#64748b", 500),
        _text(36, 126, "concentration", 12, "#64748b", 500),
    ]
    for row in rows:
        ret = float(row["total_return"])
        h = float(row["last_step_herfindahl"])
        x = 110 + (ret / max_return + 1.0) * 300
        y = 260 - h / max_h * 130
        case = str(row["case"])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{colors.get(case, "#334155")}"/>')
        parts.append(_text(x + 18, y + 4, case.replace("_", " "), 12, "#0f172a", 700))
    parts.append(_text(92, 316, "Lower vertical position means lower Herfindahl concentration; horizontal position tracks return.", 12, "#64748b", 500))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{value}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
