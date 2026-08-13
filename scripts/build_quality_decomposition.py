from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "docs/results/quality_decomposition"
INPUTS = (
    ("llm_synthetic", "LLM synthetic", ROOT / "docs/results/model_matrix/leaderboard_model_matrix.csv"),
    ("llm_real_market", "LLM real-market", ROOT / "docs/results/real_market_matrix/real_market_model_matrix.csv"),
    ("classical_synthetic", "Classical synthetic", ROOT / "docs/results/classical_baselines/classical_baseline_matrix.csv"),
    ("classical_real_market", "Classical real-market", ROOT / "docs/results/classical_baselines/classical_baseline_matrix.csv"),
)
DIMENSIONS = (
    ("alpha_quality_score", "Alpha quality"),
    ("risk_discipline_score", "Risk discipline"),
    ("execution_robustness_score", "Execution robustness"),
)
COLORS = {
    "llm_synthetic": "#2563eb",
    "llm_real_market": "#dc2626",
    "classical_synthetic": "#059669",
    "classical_real_market": "#d97706",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Alpha/Risk/Execution quality decomposition tables and radar chart."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR.relative_to(ROOT)))
    args = parser.parse_args(argv)

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _quality_rows()
    aggregate_rows = _aggregate(rows)
    _write_csv(output_dir / "quality_decomposition_rows.csv", rows)
    _write_csv(output_dir / "quality_decomposition_aggregate.csv", aggregate_rows)
    _write_markdown(output_dir / "quality_decomposition.md", aggregate_rows)
    _write_radar_svg(output_dir / "decision_execution_radar.svg", aggregate_rows)
    print(f"Wrote {output_dir.relative_to(ROOT) / 'quality_decomposition_rows.csv'}")
    print(f"Wrote {output_dir.relative_to(ROOT) / 'quality_decomposition_aggregate.csv'}")
    print(f"Wrote {output_dir.relative_to(ROOT) / 'quality_decomposition.md'}")
    print(f"Wrote {output_dir.relative_to(ROOT) / 'decision_execution_radar.svg'}")
    return 0


def _quality_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family_key, family_label, path in INPUTS:
        if not path.exists():
            continue
        for row in _read_csv(path):
            universe = str(row.get("universe", "synthetic" if family_key.endswith("synthetic") else "real_market"))
            if family_key == "classical_synthetic" and universe != "synthetic":
                continue
            if family_key == "classical_real_market" and universe != "real_market":
                continue
            agent = row.get("baseline_label") or f"{row.get('provider', '')}:{row.get('model', '')}"
            rows.append(
                {
                    "family_key": family_key,
                    "family_label": family_label,
                    "scenario_key": row.get("scenario_key", ""),
                    "scenario_label": row.get("scenario_label", ""),
                    "agent": agent,
                    "alpha_quality_score": _score(row, "alpha_quality_score", _fallback_alpha(row)),
                    "risk_discipline_score": _score(row, "risk_discipline_score", _fallback_risk(row)),
                    "execution_robustness_score": _score(
                        row,
                        "execution_robustness_score",
                        _fallback_execution(row),
                    ),
                    "alpha_pre_risk_total_return": _float(row.get("alpha_pre_risk_total_return"), 0.0),
                    "total_return": _float(row.get("total_return"), 0.0),
                    "max_drawdown": _float(row.get("max_drawdown"), 0.0),
                    "execution_fill_rate": _float(row.get("execution_fill_rate"), 0.0),
                    "risk_clipped_decisions": int(_float(row.get("risk_clipped_decisions"), 0.0)),
                    "risk_violation_count": int(_float(row.get("risk_violation_count"), 0.0)),
                }
            )
    return rows


def _aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["family_key"]), []).append(row)
    result = []
    for family_key, group in sorted(grouped.items()):
        result.append(
            {
                "family_key": family_key,
                "family_label": str(group[0]["family_label"]),
                "rows": len(group),
                "alpha_quality_score": _avg(row["alpha_quality_score"] for row in group),
                "risk_discipline_score": _avg(row["risk_discipline_score"] for row in group),
                "execution_robustness_score": _avg(row["execution_robustness_score"] for row in group),
                "alpha_pre_risk_total_return": _avg(row["alpha_pre_risk_total_return"] for row in group),
                "total_return": _avg(row["total_return"] for row in group),
                "max_drawdown": min(float(row["max_drawdown"]) for row in group),
                "execution_fill_rate": _avg(row["execution_fill_rate"] for row in group),
                "risk_clipped_decisions": sum(int(row["risk_clipped_decisions"]) for row in group),
                "risk_violation_count": sum(int(row["risk_violation_count"]) for row in group),
            }
        )
    order = {key: index for index, (key, _, _) in enumerate(INPUTS)}
    return sorted(result, key=lambda row: order.get(str(row["family_key"]), 99))


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Decision Quality vs Execution Quality",
        "",
        "This diagnostic separates three axes that are easy to conflate in a single return table:",
        "",
        "- Alpha quality: pre-risk, pre-cost intended allocation quality.",
        "- Risk discipline: how often proposals survive the risk gate without clips, blocks, or violations.",
        "- Execution robustness: how well approved orders survive fills, liquidity, latency, rejection, and cost.",
        "",
        "![Three-axis radar chart](decision_execution_radar.svg)",
        "",
        "| Family | Rows | Alpha quality | Risk discipline | Execution robustness | Pre-risk alpha return | Realized return | Worst DD | Fill rate | Risk edits | Violations |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["family_label"]),
                    str(row["rows"]),
                    _fmt(row["alpha_quality_score"]),
                    _fmt(row["risk_discipline_score"]),
                    _fmt(row["execution_robustness_score"]),
                    _pct(row["alpha_pre_risk_total_return"]),
                    _pct(row["total_return"]),
                    _pct(row["max_drawdown"]),
                    _pct(row["execution_fill_rate"]),
                    str(row["risk_clipped_decisions"]),
                    str(row["risk_violation_count"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_radar_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    width, height = 880, 560
    cx, cy, radius = 330.0, 280.0, 170.0
    angles = (-90.0, 30.0, 150.0)
    grid = []
    for level in (0.25, 0.50, 0.75, 1.0):
        points = " ".join(_point(cx, cy, radius * level, angle) for angle in angles)
        grid.append(f'<polygon points="{points}" fill="none" stroke="#d8e2ed" stroke-width="1"/>')
    axes = []
    labels = []
    for (_, label), angle in zip(DIMENSIONS, angles):
        x, y = _xy(cx, cy, radius, angle)
        lx, ly = _xy(cx, cy, radius + 34.0, angle)
        axes.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="#94a3b8" stroke-width="1"/>')
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="#0f172a">{html.escape(label)}</text>'
        )
    polygons = []
    legend = []
    for index, row in enumerate(rows):
        color = COLORS.get(str(row["family_key"]), "#334155")
        points = " ".join(
            _point(cx, cy, radius * float(row[field]), angle)
            for (field, _), angle in zip(DIMENSIONS, angles)
        )
        polygons.append(
            f'<polygon points="{points}" fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="2.5"/>'
        )
        legend_y = 170 + index * 34
        legend.append(f'<rect x="620" y="{legend_y - 12}" width="16" height="16" rx="3" fill="{color}"/>')
        legend.append(
            f'<text x="644" y="{legend_y + 1}" font-size="14" fill="#334155">{html.escape(str(row["family_label"]))}</text>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Alpha, risk discipline, and execution robustness radar chart">
<rect width="{width}" height="{height}" fill="#ffffff"/>
<text x="34" y="44" font-size="24" font-weight="800" fill="#0f172a">Decision Quality vs Execution Quality</text>
<text x="34" y="72" font-size="14" fill="#64748b">Scores are bounded diagnostics in [0, 1]; higher is better.</text>
{"".join(grid)}
{"".join(axes)}
{"".join(labels)}
{"".join(polygons)}
<rect x="596" y="124" width="240" height="178" rx="8" fill="#f8fafc" stroke="#d8e2ed"/>
<text x="620" y="150" font-size="14" font-weight="800" fill="#0f172a">Benchmark families</text>
{"".join(legend)}
<text x="34" y="510" font-size="12" fill="#64748b">Alpha uses proposed target weights before risk edits and execution costs. Risk and execution axes summarize interventions and fill realism.</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0]) if rows else ["family_key"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _score(row: dict[str, str], field: str, fallback: float) -> float:
    return _clamp01(_float(row.get(field), fallback))


def _fallback_alpha(row: dict[str, str]) -> float:
    total_return = _float(row.get("total_return"), 0.0)
    sharpe = _float(row.get("sharpe"), 0.0)
    return _clamp01(0.55 * _clamp01(0.5 + total_return / 0.20) + 0.45 * _clamp01((sharpe + 2.0) / 6.0))


def _fallback_risk(row: dict[str, str]) -> float:
    clipped = _float(row.get("risk_clipped_decisions"), 0.0)
    violations = _float(row.get("risk_violation_count"), 0.0)
    submitted = max(1.0, _float(row.get("submitted_orders"), 0.0) or clipped + violations)
    return _clamp01(1.0 - ((0.5 * clipped + violations) / submitted))


def _fallback_execution(row: dict[str, str]) -> float:
    fill = _float(row.get("execution_fill_rate"), 0.0)
    rejected = _float(row.get("rejected_order_count"), 0.0)
    denominator = max(1.0, rejected + 1.0)
    rejection_component = 1.0 - min(1.0, rejected / denominator)
    return _clamp01(0.75 * fill + 0.25 * rejection_component)


def _point(cx: float, cy: float, radius: float, angle: float) -> str:
    x, y = _xy(cx, cy, radius, angle)
    return f"{x:.1f},{y:.1f}"


def _xy(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    import math

    radians = math.radians(angle)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def _avg(values: Any) -> float:
    numbers = [float(value) for value in values]
    return sum(numbers) / len(numbers) if numbers else 0.0


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def _fmt(value: Any) -> str:
    return f"{float(value):.3f}"


def _pct(value: Any) -> str:
    return f"{100.0 * float(value):.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
