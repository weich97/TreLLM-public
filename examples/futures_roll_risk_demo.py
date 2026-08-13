from __future__ import annotations

import html
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.core.serialization import write_json
from tradearena.tools import FuturesContractMetadata, FuturesRollRiskEngine

OUTPUT_DIR = Path("outputs/examples/futures_roll_risk")


def main() -> int:
    timestamp = datetime(2026, 6, 14, 9, 30)
    contracts = (
        FuturesContractMetadata(
            symbol="MESM26",
            root_symbol="MES",
            expiry=date(2026, 6, 19),
            roll_start=date(2026, 6, 12),
            roll_end=date(2026, 6, 17),
            contract_multiplier=5.0,
            initial_margin_rate=0.08,
            description="Micro E-mini S&P 500 June 2026, paper metadata",
        ),
        FuturesContractMetadata(
            symbol="MESU26",
            root_symbol="MES",
            expiry=date(2026, 9, 18),
            roll_start=date(2026, 9, 11),
            roll_end=date(2026, 9, 16),
            contract_multiplier=5.0,
            initial_margin_rate=0.08,
            description="Micro E-mini S&P 500 September 2026, next contract",
        ),
    )
    positions = {"MESM26": 2.0, "MESU26": 0.0}
    report = FuturesRollRiskEngine(expiry_warning_days=7).review(timestamp=timestamp, contracts=contracts, positions=positions)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "paper_only": True,
        "timestamp": timestamp.isoformat(),
        "positions": positions,
        "contracts": [{**asdict(item), "expiry": item.expiry.isoformat(), "roll_start": item.roll_start.isoformat(), "roll_end": item.roll_end.isoformat()} for item in contracts],
        "risk_report": _risk_report_dict(report),
        "roll_flagged": any(item.constraint == "futures_roll_window" for item in report.violations),
        "manual_approval_required": True,
    }
    write_json(OUTPUT_DIR / "summary.json", summary)
    _write_svg(OUTPUT_DIR / "futures_roll_risk.svg", summary)
    print("Futures roll risk demo")
    print(f"  violations={len(report.violations)} roll_flagged={summary['roll_flagged']}")
    print(f"  wrote={OUTPUT_DIR / 'summary.json'}")
    print(f"  wrote={OUTPUT_DIR / 'futures_roll_risk.svg'}")
    return 0


def _risk_report_dict(report) -> dict[str, object]:
    return {
        "phase": report.phase.value,
        "approved_count": report.approved_count,
        "blocked_count": report.blocked_count,
        "checks": [asdict(item) for item in report.checks],
        "violations": [asdict(item) for item in report.violations],
    }


def _write_svg(path: Path, summary: dict[str, object]) -> None:
    width, height = 900, 360
    checks = summary["risk_report"]["checks"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Futures roll risk demo">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 52, "Futures expiry and roll-window risk", 24, "#0f172a", 800),
        _text(36, 82, "Paper-only metadata flags positions that need human review before contract expiry.", 13, "#64748b", 500),
    ]
    y = 120
    for idx, check in enumerate(checks):
        color = "#dc2626" if check["severity"] == "error" else "#f59e0b" if check["severity"] == "warning" else "#059669"
        parts.append(f'<rect x="36" y="{y + idx * 68}" width="828" height="48" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
        parts.append(f'<circle cx="62" cy="{y + idx * 68 + 24}" r="9" fill="{color}"/>')
        parts.append(_text(84, y + idx * 68 + 20, check["name"], 14, "#0f172a", 800))
        parts.append(_text(84, y + idx * 68 + 38, check["message"], 12, "#475569", 500))
    parts.append(_text(36, 326, "No live orders are submitted; all roll decisions require human approval.", 12, "#64748b", 700))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int) -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(str(value))}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
