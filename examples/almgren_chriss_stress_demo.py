from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json
from tradearena.tools import AlmgrenChrissImpactStress

OUTPUT_DIR = Path("outputs/examples/almgren_chriss_stress")


def main() -> int:
    report = build_almgren_chriss_fixture()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "summary.json", report)
    (OUTPUT_DIR / "summary.md").write_text(render_markdown(report), encoding="utf-8")
    _write_svg(OUTPUT_DIR / "almgren_chriss_stress.svg", report)
    print("Almgren-Chriss impact stress demo")
    print(f"  cases={report['summary']['case_count']} max_shortfall_bps={report['summary']['max_shortfall_bps']:.2f}")
    print(f"  wrote={OUTPUT_DIR / 'summary.json'}")
    print(f"  wrote={OUTPUT_DIR / 'summary.md'}")
    return 0


def build_almgren_chriss_fixture() -> dict[str, Any]:
    plugin = AlmgrenChrissImpactStress(eta=0.25, gamma=0.03, exponent=0.5)
    base = {
        "symbol": "SYN",
        "side": "buy",
        "quantity": 5_000.0,
        "price": 25.0,
        "volume": 50_000.0,
    }
    rows = [
        {
            "case_id": "default_linear",
            "description": "default stress baseline with no optional impact plugin",
            **base,
            "model": "none",
            "assumption_class": "default_stress_without_optional_impact",
            "paper_only": True,
            "calibration_boundary": plugin.calibration_boundary,
            "participation": base["quantity"] / base["volume"],
            "modeled_shortfall_bps": 0.0,
            "modeled_shortfall_cost": 0.0,
            "temporary_impact_cost": 0.0,
            "permanent_impact_cost": 0.0,
        },
        {
            "case_id": "linear_impact",
            "description": "linear temporary impact plus permanent participation term",
            **plugin.estimate(**base, model="linear"),
        },
        {
            "case_id": "concave_impact",
            "description": "concave temporary impact proxy for liquidity stress",
            **plugin.estimate(**base, model="concave"),
        },
    ]
    return {
        "schema": "trellm_almgren_chriss_impact_stress_v0.1",
        "paper_only": True,
        "downloads_data": False,
        "calibration_boundary": plugin.calibration_boundary,
        "discussion": {
            "linear": "temporary impact grows in direct proportion to participation",
            "concave": "temporary impact grows with participation^exponent and can stress small books more aggressively",
            "required_fixture_fields": ["symbol", "side", "quantity", "price", "volume"],
        },
        "cases": rows,
        "summary": {
            "case_count": len(rows),
            "max_shortfall_bps": max(float(row["modeled_shortfall_bps"]) for row in rows),
            "max_shortfall_cost": max(float(row["modeled_shortfall_cost"]) for row in rows),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Almgren-Chriss Impact Stress Fixture",
        "",
        "Paper-only optional market-impact stress proxy. It reports modeled shortfall without claiming broker calibration.",
        "",
        "| Case | Model | Participation | Shortfall bps | Cost | Boundary |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["cases"]:
        lines.append(
            f"| `{row['case_id']}` | `{row['model']}` | {float(row['participation']):.3f} | "
            f"{float(row['modeled_shortfall_bps']):.2f} | {float(row['modeled_shortfall_cost']):.2f} | "
            f"`{row['calibration_boundary']}` |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python examples/almgren_chriss_stress_demo.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _write_svg(path: Path, report: dict[str, Any]) -> None:
    width, height = 840, 360
    rows = report["cases"]
    max_cost = max(1.0, max(float(row["modeled_shortfall_cost"]) for row in rows))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Almgren-Chriss impact stress demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 48, "Almgren-Chriss impact stress", 22, "#0f172a", 800),
        _text(36, 78, "Optional paper-only impact proxy: default stress versus linear and concave shortfall.", 13, "#64748b", 500),
    ]
    for idx, row in enumerate(rows):
        y = 126 + idx * 66
        bar_width = 470 * float(row["modeled_shortfall_cost"]) / max_cost
        parts.append(_text(36, y + 17, row["case_id"], 13, "#0f172a", 800))
        parts.append(f'<rect x="230" y="{y}" width="470" height="22" rx="6" fill="#e2e8f0"/>')
        parts.append(f'<rect x="230" y="{y}" width="{bar_width:.1f}" height="22" rx="6" fill="#0f766e"/>')
        parts.append(_text(716, y + 17, f"{float(row['modeled_shortfall_bps']):.1f} bps", 12, "#334155", 700))
    parts.append(_text(36, 326, "Output: outputs/examples/almgren_chriss_stress/summary.json", 12, "#64748b", 400))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: object, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(str(value))}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
