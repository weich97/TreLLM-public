from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.agents import max_drawdown_risk_preset
from tradearena.core.domain import Decision, PortfolioState, RiskReport, Side
from tradearena.core.serialization import write_json
from tradearena.data import SyntheticMarketDataProvider
from tradearena.memory import InMemoryResearchMemory


def main() -> int:
    report = build_max_drawdown_fixture()
    json_path = ROOT / "docs/results/max_drawdown_risk_preset.json"
    md_path = ROOT / "docs/results/max_drawdown_risk_preset.md"
    write_json(json_path, report)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path.relative_to(ROOT).as_posix()}")
    print(f"Wrote {md_path.relative_to(ROOT).as_posix()}")
    return 0


def build_max_drawdown_fixture() -> dict[str, Any]:
    snapshot = SyntheticMarketDataProvider(symbols=("SYN",), periods=1, seed=28).stream()[0]
    memory = InMemoryResearchMemory()
    memory.record("step", {"equity": 100_000.0})
    memory.record("step", {"equity": 98_000.0})
    portfolio = PortfolioState(cash=94_000.0)
    portfolio.last_prices.update({symbol: bar.close for symbol, bar in snapshot.bars.items()})
    decision = Decision(
        symbol="SYN",
        side=Side.BUY,
        target_weight=0.40,
        confidence=0.90,
        rationale="LLM attempts to add risk after a 6% rolling drawdown",
    )
    cases = [
        _case(
            case_id="block_after_drawdown",
            de_risk_weight=0.0,
            snapshot=snapshot,
            decision=decision,
            portfolio=portfolio,
            memory=memory,
        ),
        _case(
            case_id="clip_after_drawdown",
            de_risk_weight=0.10,
            snapshot=snapshot,
            decision=decision,
            portfolio=portfolio,
            memory=memory,
        ),
    ]
    return {
        "schema": "trellm_max_drawdown_risk_preset_v0.1",
        "claim_boundary": (
            "Deterministic risk-preset fixture for audit and extension tests. "
            "It demonstrates blocked or clipped decisions; it is not trading advice."
        ),
        "settings": {
            "max_drawdown": 0.05,
            "drawdown_lookback": 3,
            "observed_rolling_drawdown": -0.06,
        },
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "blocked": sum(1 for row in cases if row["approved_side"] == Side.HOLD.value and row["approved_weight"] == 0.0),
            "clipped": sum(1 for row in cases if row["approved_weight"] not in (0.0, row["requested_weight"])),
        },
    }


def _case(
    *,
    case_id: str,
    de_risk_weight: float,
    snapshot: object,
    decision: Decision,
    portfolio: PortfolioState,
    memory: InMemoryResearchMemory,
) -> dict[str, Any]:
    risk = max_drawdown_risk_preset(max_drawdown=0.05, de_risk_weight=de_risk_weight, drawdown_lookback=3)
    approved = risk.approve(snapshot, [decision], portfolio, memory)[0]
    risk_report = _risk_report_to_dict(risk.last_report)
    return {
        "case_id": case_id,
        "preset": risk.name,
        "de_risk_weight": de_risk_weight,
        "requested_side": decision.side.value,
        "requested_weight": decision.target_weight,
        "approved_side": approved.side.value,
        "approved_weight": approved.target_weight,
        "metadata": approved.metadata,
        "risk_report": risk_report,
    }


def _risk_report_to_dict(report: RiskReport | None) -> dict[str, Any]:
    if report is None:
        return {}
    return {
        "phase": report.phase.value,
        "passed": report.passed,
        "approved_count": report.approved_count,
        "blocked_count": report.blocked_count,
        "clipped_count": report.clipped_count,
        "checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "severity": check.severity,
                "message": check.message,
                "metadata": check.metadata,
            }
            for check in report.checks
        ],
        "violations": [
            {
                "constraint": violation.constraint,
                "severity": violation.severity,
                "observed": violation.observed,
                "limit": violation.limit,
                "message": violation.message,
                "metadata": violation.metadata,
            }
            for violation in report.violations
        ],
        "budget": {
            "max_drawdown": report.budget.max_drawdown if report.budget else None,
            "metadata": report.budget.metadata if report.budget else {},
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Max Drawdown Risk Preset Fixture",
        "",
        report["claim_boundary"],
        "",
        "## Settings",
        "",
        f"- Max drawdown: {report['settings']['max_drawdown']:.2%}",
        f"- Observed rolling drawdown: {report['settings']['observed_rolling_drawdown']:.2%}",
        f"- Drawdown lookback: {report['settings']['drawdown_lookback']} equity records",
        "",
        "## Cases",
        "",
        "| Case | De-risk weight | Requested | Approved | Blocked | Clipped | Violation |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in report["cases"]:
        violation = row["risk_report"]["violations"][0]["constraint"] if row["risk_report"]["violations"] else "none"
        lines.append(
            f"| `{row['case_id']}` | {row['de_risk_weight']:.2f} | {row['requested_weight']:.2f} | "
            f"{row['approved_weight']:.2f} | {row['risk_report']['blocked_count']} | "
            f"{row['risk_report']['clipped_count']} | `{violation}` |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python examples/max_drawdown_risk_preset_demo.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
