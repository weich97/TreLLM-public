from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

from tradearena.core.serialization import write_json
from tradearena.factory import build_default_system

TECH_51 = (
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "GOOG",
    "TSLA",
    "AVGO",
    "JPM",
    "V",
    "MA",
    "UNH",
    "XOM",
    "COST",
    "WMT",
    "HD",
    "PG",
    "JNJ",
    "ABBV",
    "BAC",
    "KO",
    "PEP",
    "CRM",
    "NFLX",
    "ORCL",
    "AMD",
    "CSCO",
    "MRK",
    "CVX",
    "TMO",
    "ACN",
    "LIN",
    "MCD",
    "IBM",
    "GE",
    "CAT",
    "DIS",
    "QCOM",
    "INTU",
    "AMAT",
    "TXN",
    "NOW",
    "ISRG",
    "PM",
    "NEE",
    "RTX",
    "SPGI",
    "GS",
    "HON",
    "LOW",
)

SVB_SYMBOLS = (
    "JPM",
    "BAC",
    "GS",
    "SCHW",
    "C",
    "WFC",
    "MS",
    "USB",
    "PNC",
    "TFC",
    "KRE",
    "XLF",
    "GSPC",
    "BTC-USD",
    "ETH-USD",
)

SCENES = {
    "tech_rates_2022": {
        "title": "2022 Tech/Rates Drawdown",
        "start": "2022-01-03",
        "end": "2022-06-30",
        "symbols": TECH_51,
        "max_position_weight": 0.08,
        "max_turnover": 0.75,
        "participation_rate": 0.03,
        "latency_steps": 1,
        "market_impact": 0.22,
    },
    "svb_2023": {
        "title": "2023 SVB / Regional Bank Shock",
        "start": "2023-03-01",
        "end": "2023-04-14",
        "symbols": SVB_SYMBOLS,
        "max_position_weight": 0.12,
        "max_turnover": 0.85,
        "participation_rate": 0.025,
        "latency_steps": 1,
        "market_impact": 0.30,
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real-market crisis-scene experiments for TreLLM.")
    parser.add_argument("--output-dir", default="outputs/tradearena_crisis")
    parser.add_argument("--data-dir", default="data/real/yahoo_daily_2021_2026_51")
    parser.add_argument("--cache", default="data/llm_cache/deepseek_analyst.jsonl")
    parser.add_argument("--scenes", default="tech_rates_2022,svb_2023")
    parser.add_argument(
        "--models",
        default="poe:gpt-5.5,poe:gemini-3.1-pro,poe:claude-opus-4.7,deepseek:deepseek-v4-pro",
        help="Comma-separated provider:model specs.",
    )
    parser.add_argument("--feedback", default="true,hidden,placebo")
    parser.add_argument("--max-symbols", type=int, default=51)
    parser.add_argument("--max-periods", type=int, default=40)
    parser.add_argument("--microstructure-steps", type=int, default=18)
    parser.add_argument("--collect-existing", action="store_true", help="Build tables and charts from every raw JSON already present.")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--rerun-existing", action="store_true", help="Ignore existing raw crisis trajectories.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop the full suite if a single live case fails.")
    parser.add_argument("--no-live", action="store_true", help="Only use existing cached/raw rows; fail if missing.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    tables_dir = output_dir / "tables"
    charts_dir = output_dir / "charts"
    raw_dir = output_dir / "raw"
    for path in (tables_dir, charts_dir, raw_dir):
        path.mkdir(parents=True, exist_ok=True)

    scene_names = [item.strip() for item in args.scenes.split(",") if item.strip()]
    model_specs = [_parse_model_spec(item) for item in args.models.split(",") if item.strip()]
    feedback_modes = [item.strip() for item in args.feedback.split(",") if item.strip()]
    case_payloads: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []

    if args.collect_existing:
        for payload_path in sorted(raw_dir.glob("*.json")):
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            if "trajectory" not in payload or "metrics" not in payload:
                continue
            case_payloads.append(payload)
            summary_rows.append(_summary_row(payload))
            step_rows.extend(_step_rows(payload))
        if not case_payloads and _copy_tracked_crisis_snapshot(tables_dir, charts_dir):
            print(f"Copied tracked crisis snapshots under {output_dir}")
            return 0
    for scene_name in ([] if args.collect_existing else scene_names):
        if scene_name not in SCENES:
            raise ValueError(f"Unknown scene: {scene_name}")
        scene = SCENES[scene_name]
        symbols = tuple(scene["symbols"][: args.max_symbols])
        _validate_daily_data(Path(args.data_dir), symbols)
        for provider, model in model_specs:
            for feedback in feedback_modes:
                case_name = f"{scene_name}_{provider}_{_slug(model)}_{feedback}"
                payload_path = raw_dir / f"{case_name}.json"
                if payload_path.exists() and args.skip_existing and not args.rerun_existing:
                    payload = json.loads(payload_path.read_text(encoding="utf-8"))
                else:
                    if args.no_live:
                        raise FileNotFoundError(f"Missing raw crisis trajectory and --no-live was set: {payload_path}")
                    print(f"Running {case_name} ({len(symbols)} symbols, {args.max_periods} steps)")
                    try:
                        payload = _run_case(
                            case_name=case_name,
                            scene_name=scene_name,
                            scene=scene,
                            symbols=symbols,
                            provider=provider,
                            model=model,
                            feedback=feedback,
                            data_dir=args.data_dir,
                            cache_path=args.cache,
                            max_periods=args.max_periods,
                        )
                    except Exception as exc:
                        error_path = raw_dir / f"{case_name}.error.json"
                        write_json(
                            error_path,
                            {
                                "case": case_name,
                                "scene": scene_name,
                                "provider": provider,
                                "model": model,
                                "feedback": feedback,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            },
                        )
                        print(f"Skipped {case_name}: {type(exc).__name__}: {exc}")
                        if args.stop_on_error:
                            raise
                        continue
                    write_json(payload_path, payload)
                    stale_error = raw_dir / f"{case_name}.error.json"
                    if stale_error.exists():
                        stale_error.unlink()
                    print(f"Wrote {payload_path}")
                case_payloads.append(payload)
                summary_rows.append(_summary_row(payload))
                step_rows.extend(_step_rows(payload))

    if not case_payloads:
        raise RuntimeError("No usable crisis trajectories were available.")

    _write_csv(tables_dir / "crisis_summary.csv", summary_rows)
    _write_csv(tables_dir / "crisis_steps.csv", step_rows)
    _write_csv(tables_dir / "crisis_representation_summary.csv", _representation_summary_rows(case_payloads))
    _write_csv(tables_dir / "crisis_correlation_pairs.csv", _correlation_pair_rows(case_payloads, Path(args.data_dir)))
    _write_markdown(tables_dir / "crisis_summary.md", summary_rows)

    _write_representation_trajectory(charts_dir / "crisis_representation_trajectory.svg", case_payloads)
    _write_correlation_intent_heatmap(charts_dir / "crisis_correlation_intent_heatmap.svg", case_payloads, Path(args.data_dir))
    _write_learning_curves(charts_dir / "crisis_feedback_learning_curves.svg", step_rows)
    _write_exposure_waterfall(charts_dir / "crisis_exposure_waterfall.svg", case_payloads)
    _write_microstructure_waterfall(charts_dir / "crisis_microstructure_waterfall.svg", case_payloads, args.microstructure_steps)
    write_json(
        output_dir / "summary.json",
        {
            "summary_rows": summary_rows,
            "charts": {
                "representation_trajectory": str(charts_dir / "crisis_representation_trajectory.svg"),
                "correlation_intent_heatmap": str(charts_dir / "crisis_correlation_intent_heatmap.svg"),
                "feedback_learning_curves": str(charts_dir / "crisis_feedback_learning_curves.svg"),
                "exposure_waterfall": str(charts_dir / "crisis_exposure_waterfall.svg"),
                "microstructure_waterfall": str(charts_dir / "crisis_microstructure_waterfall.svg"),
            },
        },
    )
    print(f"Wrote crisis artifacts under {output_dir}")
    return 0


def _run_case(
    *,
    case_name: str,
    scene_name: str,
    scene: dict[str, Any],
    symbols: tuple[str, ...],
    provider: str,
    model: str,
    feedback: str,
    data_dir: str,
    cache_path: str,
    max_periods: int,
) -> dict[str, Any]:
    use_feedback = feedback != "hidden"
    risk_feedback_mode = "placebo" if feedback == "placebo" else "true"
    analyst_name = "poe-llm" if provider == "poe" else "deepseek-llm"
    system = build_default_system(
        name=case_name,
        symbols=symbols,
        seed=22,
        strategy_name="signal-weighted",
        risk_name="max-position",
        execution_mode="realistic",
        commission_bps=1.0,
        slippage_bps=3.0,
        participation_rate=float(scene["participation_rate"]),
        latency_steps=int(scene["latency_steps"]),
        market_impact=float(scene["market_impact"]),
        max_position_weight=float(scene["max_position_weight"]),
        max_turnover=float(scene["max_turnover"]),
        analyst_names=(analyst_name,),
        data_source="csv",
        real_data_dir=data_dir,
        real_data_frequency="daily",
        real_data_start=str(scene["start"]),
        real_data_end=str(scene["end"]),
        real_data_max_periods=max_periods,
        llm_model=model,
        llm_cache_path=cache_path,
        llm_use_risk_feedback=use_feedback,
        llm_risk_feedback_mode=risk_feedback_mode,
        llm_output_mode="rationale",
        llm_mask_timestamps=True,
    )
    trajectory, metrics = system.run()
    return {
        "case": case_name,
        "scene": scene_name,
        "scene_title": scene["title"],
        "provider": provider,
        "model": model,
        "feedback": feedback,
        "symbols": symbols,
        "metrics": metrics,
        "trajectory": trajectory.to_dict(),
    }


def _summary_row(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload["metrics"]
    rows = _step_rows(payload)
    return {
        "case": payload["case"],
        "scene": payload["scene"],
        "provider": payload["provider"],
        "model": payload["model"],
        "feedback": payload["feedback"],
        "symbols": len(payload.get("symbols", [])),
        "steps": len(rows),
        "total_return": metrics.get("total_return", 0.0),
        "sharpe": metrics.get("sharpe", 0.0),
        "max_drawdown": metrics.get("max_drawdown", 0.0),
        "risk_clipped_decisions": metrics.get("risk_clipped_decisions", 0),
        "risk_violation_count": metrics.get("risk_violation_count", 0),
        "execution_fill_rate": metrics.get("execution_fill_rate", 0.0),
        "rejected_order_count": metrics.get("rejected_order_count", 0),
        "mean_intended_abs": _mean([row["intended_abs"] for row in rows]),
        "mean_approved_abs": _mean([row["approved_abs"] for row in rows]),
        "mean_realized_abs": _mean([row["realized_abs"] for row in rows]),
        "risk_gate_rate": _mean([row["risk_gate"] for row in rows]),
        "mean_calibration_score": _mean([row["calibration_score"] for row in rows]),
    }


def _step_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    trajectory = payload["trajectory"]
    equities = [float(step.get("portfolio", {}).get("equity", 0.0) or 0.0) for step in trajectory.get("steps", [])]
    drawdowns = _drawdowns(equities)
    rows = []
    for idx, step in enumerate(trajectory.get("steps", [])):
        decisions = step.get("decisions", [])
        approved = step.get("approved_decisions", [])
        intended_abs = _abs_exposure(decisions)
        approved_abs = _abs_exposure(approved)
        realized_abs = _realized_abs(step)
        gap = _calibration_gap(decisions, approved)
        risk_report = step.get("risk_report", {})
        execution = step.get("execution_report", {})
        rows.append(
            {
                "case": payload["case"],
                "scene": payload["scene"],
                "provider": payload["provider"],
                "model": payload["model"],
                "feedback": payload["feedback"],
                "step": idx,
                "timestamp": step.get("timestamp", ""),
                "equity": equities[idx] if idx < len(equities) else 0.0,
                "drawdown": drawdowns[idx] if idx < len(drawdowns) else 0.0,
                "phase": _phase(idx, drawdowns),
                "intended_abs": intended_abs,
                "approved_abs": approved_abs,
                "realized_abs": realized_abs,
                "calibration_gap": gap,
                "calibration_score": 1.0 - min(1.0, gap / max(1.0, intended_abs)),
                "risk_gate": int(
                    int(risk_report.get("clipped_count", 0) or 0)
                    + int(risk_report.get("blocked_count", 0) or 0)
                    + len(step.get("risk_violations", []) or [])
                    > 0
                ),
                "clipped_count": int(risk_report.get("clipped_count", 0) or 0),
                "blocked_count": int(risk_report.get("blocked_count", 0) or 0),
                "pending_orders": int(execution.get("pending_orders", 0) or 0),
                "rejected_orders": int(execution.get("rejected_orders", 0) or 0),
                "partial_fills": int(execution.get("partial_fills", 0) or 0),
                "plan_text": _plan_text(step),
            }
        )
    return rows


def _write_representation_trajectory(path: Path, payloads: list[dict[str, Any]]) -> None:
    selected = [p for p in payloads if p["feedback"] == "true" and p["scene"] == "tech_rates_2022"][:4]
    panels = []
    for payload in selected:
        rows = _step_rows(payload)
        vectors = [_hash_embed(row["plan_text"]) for row in rows]
        coords = _pca2(vectors)
        panels.append((payload, rows, coords))
    width, height = 1200, 720
    out = [_svg(width, height, "Crisis representation trajectory")]
    out.append(_text(40, 46, "Representation trajectories during the 2022 Tech/Rates drawdown", 24, "#0f172a", 800))
    panel_w, panel_h = 540, 270
    for idx, (payload, rows, coords) in enumerate(panels):
        x = 40 + (idx % 2) * 590
        y = 80 + (idx // 2) * 305
        out.extend(_trajectory_panel(x, y, panel_w, panel_h, payload, rows, coords))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


def _trajectory_panel(
    x: int,
    y: int,
    width: int,
    height: int,
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
    coords: list[tuple[float, float]],
) -> list[str]:
    out = [_panel(x, y, width, height, f"{payload['provider']}:{payload['model']}")]
    if not coords:
        return out
    xs, ys = [c[0] for c in coords], [c[1] for c in coords]
    lo_x, hi_x = min(xs), max(xs)
    lo_y, hi_y = min(ys), max(ys)
    plot_x, plot_y = x + 36, y + 48
    plot_w, plot_h = width - 70, height - 78
    points = []
    for (cx, cy), row in zip(coords, rows, strict=True):
        sx = _scale(cx, lo_x, hi_x, plot_x, plot_x + plot_w)
        sy = _scale(cy, lo_y, hi_y, plot_y + plot_h, plot_y)
        points.append((sx, sy, row["phase"]))
    out.append(
        f'<polyline fill="none" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="3 4" points="{" ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in points)}"/>'
    )
    for sx, sy, phase in points:
        color = {"normal": "#2563eb", "pre_drawdown": "#d97706", "drawdown": "#dc2626"}[phase]
        radius = 4.5 if phase != "normal" else 3.0
        out.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{radius}" fill="{color}" fill-opacity="0.88"/>')
    out.append(_legend(x + width - 210, y + 24, [("normal", "#2563eb"), ("pre", "#d97706"), ("drawdown", "#dc2626")]))
    return out


def _write_correlation_intent_heatmap(path: Path, payloads: list[dict[str, Any]], data_dir: Path) -> None:
    payload = next((p for p in payloads if p["scene"] == "tech_rates_2022" and p["feedback"] == "true"), payloads[0])
    symbols = list(payload["symbols"])
    corr = _market_correlation_matrix(data_dir, symbols, "2022-01-03", "2022-06-30")
    intent = _intent_coexposure_matrix(payload, symbols)
    width, height = 1200, 620
    out = [_svg(width, height, "Market correlation vs LLM intent co-exposure")]
    out.append(_text(40, 46, "Market correlation vs LLM intent co-exposure", 24, "#0f172a", 800))
    out.extend(_heatmap_panel(55, 85, 500, 500, "Market return correlation", symbols, corr, -1.0, 1.0, diverging=True))
    out.extend(_heatmap_panel(645, 85, 500, 500, f"LLM intent co-exposure ({payload['model']})", symbols, intent, 0.0, _max_matrix(intent), diverging=False))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


def _write_learning_curves(path: Path, step_rows: list[dict[str, Any]]) -> None:
    scenes = sorted({row["scene"] for row in step_rows})
    width, height = 1200, 620
    out = [_svg(width, height, "Risk feedback learning curves")]
    out.append(_text(40, 46, "Rolling risk-gate rate and calibration score by feedback condition", 24, "#0f172a", 800))
    for idx, scene in enumerate(scenes[:2]):
        rows = [row for row in step_rows if row["scene"] == scene]
        out.extend(_curve_panel(55 + idx * 585, 90, 525, 430, scene, rows))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


def _write_exposure_waterfall(path: Path, payloads: list[dict[str, Any]]) -> None:
    candidates = [p for p in payloads if p["scene"] == "tech_rates_2022" and p["feedback"] == "true"]
    payload = candidates[0] if candidates else payloads[0]
    rows = _step_rows(payload)
    row = max(rows, key=lambda item: item["clipped_count"])
    width, height = 880, 470
    out = [_svg(width, height, "Intended vs approved vs realized exposure")]
    out.append(_text(38, 46, "Exposure waterfall: intended -> approved -> realized", 24, "#0f172a", 800))
    out.append(_text(38, 74, f"{payload['scene_title']} / {payload['provider']}:{payload['model']} / {row['timestamp']}", 13, "#64748b", 400))
    bars = [("Intended", row["intended_abs"], "#2563eb"), ("Approved", row["approved_abs"], "#059669"), ("Realized", row["realized_abs"], "#d97706")]
    max_value = max(1.0, max(item[1] for item in bars))
    for idx, (label, value, color) in enumerate(bars):
        x = 95 + idx * 245
        h = 260 * value / max_value
        y = 370 - h
        out.append(f'<rect x="{x}" y="{y:.2f}" width="110" height="{h:.2f}" rx="6" fill="{color}"/>')
        out.append(_text(x + 55, 397, label, 15, "#0f172a", 700, "middle"))
        out.append(_text(x + 55, y - 12, f"{value:.3f}", 16, "#0f172a", 800, "middle"))
    out.append(_text(42, 438, f"Risk gate clipped {row['clipped_count']} decision(s); pending orders {row['pending_orders']}, rejected orders {row['rejected_orders']}.", 13, "#475569", 400))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


def _write_microstructure_waterfall(path: Path, payloads: list[dict[str, Any]], steps: int) -> None:
    payload = next((p for p in payloads if p["feedback"] == "true"), payloads[0])
    rows = _step_rows(payload)[-steps:]
    width, height = 1100, 520
    out = [_svg(width, height, "Execution-realistic exposure stress")]
    out.append(_text(40, 46, "Execution-realistic exposure stress: intended, approved, realized", 24, "#0f172a", 800))
    out.append(_text(40, 72, "A compact microstructure proxy: slippage, latency, pending/rejected orders create a gap between model intent and realized exposure.", 13, "#64748b", 400))
    series = {
        "Intended": [(row["step"], row["intended_abs"]) for row in rows],
        "Approved": [(row["step"], row["approved_abs"]) for row in rows],
        "Realized": [(row["step"], row["realized_abs"]) for row in rows],
    }
    out.extend(_line_chart_panel(70, 105, 960, 330, series))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


def _copy_tracked_crisis_snapshot(tables_dir: Path, charts_dir: Path) -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    source_tables = repo_root / "docs" / "results" / "crisis"
    source_charts = repo_root / "docs" / "assets" / "crisis"
    if not source_tables.exists() or not source_charts.exists():
        return False
    copied = False
    for source in source_tables.glob("crisis_*"):
        shutil.copy2(source, tables_dir / source.name)
        copied = True
    for source in source_charts.glob("crisis_*.svg"):
        shutil.copy2(source, charts_dir / source.name)
        copied = True
    return copied


def _representation_summary_rows(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for payload in payloads:
        step_rows = _step_rows(payload)
        vectors = [_hash_embed(row["plan_text"]) for row in step_rows]
        normal_vectors = [vector for vector, row in zip(vectors, step_rows, strict=True) if row["phase"] == "normal"]
        stress_vectors = [vector for vector, row in zip(vectors, step_rows, strict=True) if row["phase"] != "normal"]
        coords = _pca2(vectors)
        path_length = sum(_euclidean(coords[idx], coords[idx - 1]) for idx in range(1, len(coords)))
        normal_rank = _effective_rank(normal_vectors)
        stress_rank = _effective_rank(stress_vectors)
        rows.append(
            {
                "case": payload["case"],
                "scene": payload["scene"],
                "provider": payload["provider"],
                "model": payload["model"],
                "feedback": payload["feedback"],
                "steps": len(step_rows),
                "normal_steps": len(normal_vectors),
                "stress_steps": len(stress_vectors),
                "effective_rank_all": _effective_rank(vectors),
                "effective_rank_normal": normal_rank,
                "effective_rank_stress": stress_rank,
                "rank_delta_normal_minus_stress": normal_rank - stress_rank,
                "path_length": path_length,
            }
        )
    return rows


def _correlation_pair_rows(payloads: list[dict[str, Any]], data_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    selected = [payload for payload in payloads if payload["feedback"] == "true" and payload["scene"] in SCENES]
    for payload in selected:
        scene = SCENES[payload["scene"]]
        symbols = list(payload["symbols"])
        corr = _market_correlation_matrix(data_dir, symbols, str(scene["start"]), str(scene["end"]))
        intent = _intent_coexposure_matrix(payload, symbols)
        pair_rows = []
        for i, left in enumerate(symbols):
            for j in range(i + 1, len(symbols)):
                right = symbols[j]
                score = abs(corr[i][j]) * intent[i][j]
                pair_rows.append(
                    {
                        "case": payload["case"],
                        "scene": payload["scene"],
                        "provider": payload["provider"],
                        "model": payload["model"],
                        "pair": f"{left}/{right}",
                        "market_correlation": corr[i][j],
                        "intent_coexposure": intent[i][j],
                        "correlation_intent_score": score,
                    }
                )
        rows.extend(sorted(pair_rows, key=lambda row: row["correlation_intent_score"], reverse=True)[:15])
    return rows


def _curve_panel(x: int, y: int, width: int, height: int, scene: str, rows: list[dict[str, Any]]) -> list[str]:
    out = [_panel(x, y, width, height, scene)]
    feedbacks = ["true", "placebo", "hidden"]
    colors = {"true": "#059669", "placebo": "#d97706", "hidden": "#64748b"}
    max_step = max(int(row["step"]) for row in rows) if rows else 1
    plot_x, plot_y = x + 42, y + 58
    plot_w, plot_h = width - 74, height - 102
    out.append(f'<line x1="{plot_x}" y1="{plot_y + plot_h}" x2="{plot_x + plot_w}" y2="{plot_y + plot_h}" stroke="#cbd5e1"/>')
    out.append(f'<line x1="{plot_x}" y1="{plot_y}" x2="{plot_x}" y2="{plot_y + plot_h}" stroke="#cbd5e1"/>')
    for feedback in feedbacks:
        averaged = _average_by_step([row for row in rows if row["feedback"] == feedback], "calibration_score", window=8)
        points = []
        for step, value in averaged:
            sx = _scale(step, 0, max_step, plot_x, plot_x + plot_w)
            sy = _scale(value, 0.0, 1.0, plot_y + plot_h, plot_y)
            points.append(f"{sx:.1f},{sy:.1f}")
        if points:
            out.append(f'<polyline fill="none" stroke="{colors[feedback]}" stroke-width="2.4" points="{" ".join(points)}"/>')
    out.append(_legend(x + width - 160, y + 28, [(fb, colors[fb]) for fb in feedbacks]))
    out.append(_text(plot_x, y + height - 20, "rolling calibration score", 12, "#64748b", 400))
    return out


def _line_chart_panel(x: int, y: int, width: int, height: int, series: dict[str, list[tuple[int, float]]]) -> list[str]:
    colors = {"Intended": "#2563eb", "Approved": "#059669", "Realized": "#d97706"}
    all_points = [point for values in series.values() for point in values]
    if not all_points:
        return []
    min_x, max_x = min(p[0] for p in all_points), max(p[0] for p in all_points)
    max_y = max(1.0, max(p[1] for p in all_points))
    out = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d9e2ec"/>']
    plot_x, plot_y = x + 52, y + 38
    plot_w, plot_h = width - 90, height - 76
    out.append(f'<line x1="{plot_x}" y1="{plot_y + plot_h}" x2="{plot_x + plot_w}" y2="{plot_y + plot_h}" stroke="#cbd5e1"/>')
    out.append(f'<line x1="{plot_x}" y1="{plot_y}" x2="{plot_x}" y2="{plot_y + plot_h}" stroke="#cbd5e1"/>')
    for name, points in series.items():
        coords = []
        for step, value in points:
            sx = _scale(step, min_x, max_x, plot_x, plot_x + plot_w)
            sy = _scale(value, 0.0, max_y, plot_y + plot_h, plot_y)
            coords.append(f"{sx:.1f},{sy:.1f}")
        out.append(f'<polyline fill="none" stroke="{colors[name]}" stroke-width="2.5" points="{" ".join(coords)}"/>')
    out.append(_legend(x + width - 240, y + 30, [(name, colors[name]) for name in series]))
    return out


def _heatmap_panel(
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    symbols: list[str],
    matrix: list[list[float]],
    lo: float,
    hi: float,
    *,
    diverging: bool,
) -> list[str]:
    out = [_panel(x, y, width, height, title)]
    n = len(symbols)
    cell = min((width - 80) / max(1, n), (height - 80) / max(1, n))
    start_x, start_y = x + 46, y + 48
    for i in range(n):
        for j in range(n):
            value = matrix[i][j]
            color = _diverging_color(value, lo, hi) if diverging else _sequential_color(value, lo, hi)
            out.append(f'<rect x="{start_x + j * cell:.2f}" y="{start_y + i * cell:.2f}" width="{cell + 0.2:.2f}" height="{cell + 0.2:.2f}" fill="{color}"/>')
    for idx in range(0, n, max(1, n // 8)):
        out.append(_text(start_x + idx * cell, start_y + n * cell + 16, symbols[idx], 9, "#475569", 400, "middle"))
        out.append(_text(start_x - 8, start_y + idx * cell + 4, symbols[idx], 9, "#475569", 400, "end"))
    return out


def _market_correlation_matrix(data_dir: Path, symbols: list[str], start: str, end: str) -> list[list[float]]:
    prices = {}
    for symbol in symbols:
        rows = _read_price_rows(data_dir, symbol, start, end)
        prices[symbol] = [row["close"] for row in rows]
    returns = {
        symbol: [(vals[i] / vals[i - 1]) - 1.0 for i in range(1, len(vals)) if vals[i - 1]]
        for symbol, vals in prices.items()
    }
    return [[_corr(returns[left], returns[right]) for right in symbols] for left in symbols]


def _intent_coexposure_matrix(payload: dict[str, Any], symbols: list[str]) -> list[list[float]]:
    matrix = [[0.0 for _ in symbols] for _ in symbols]
    count = 0
    for step in payload["trajectory"].get("steps", []):
        weights = {str(decision.get("symbol")): abs(_to_float(decision.get("target_weight"), 0.0)) for decision in step.get("decisions", [])}
        vector = [weights.get(symbol, 0.0) for symbol in symbols]
        for i, left in enumerate(vector):
            for j, right in enumerate(vector):
                matrix[i][j] += left * right
        count += 1
    if count:
        matrix = [[value / count for value in row] for row in matrix]
    return matrix


def _read_price_rows(data_dir: Path, symbol: str, start: str, end: str) -> list[dict[str, Any]]:
    path = data_dir / f"{_safe(symbol)}_Daily_2021_2026.csv"
    if not path.exists():
        path = data_dir / f"{_safe(symbol)}_Daily.csv"
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            date = row["Date"][:10]
            if start <= date <= end:
                rows.append({"date": date, "close": _to_float(row.get("Close"), 0.0)})
    return rows


def _validate_daily_data(data_dir: Path, symbols: tuple[str, ...]) -> None:
    missing = [symbol for symbol in symbols if not (data_dir / f"{_safe(symbol)}_Daily_2021_2026.csv").exists() and not (data_dir / f"{_safe(symbol)}_Daily.csv").exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing daily data for {len(missing)} symbol(s), e.g. {missing[:5]}. "
            f"Download with scripts/download_yahoo_daily.py into {data_dir}."
        )


def _plan_text(step: dict[str, Any]) -> str:
    chunks = []
    for signal in step.get("signals", []):
        chunks.append(str(signal.get("rationale", "")))
        chunks.append(str(signal.get("metadata", {}).get("risk_notes", "")))
    for decision in step.get("decisions", []):
        chunks.append(f"{decision.get('symbol')} {decision.get('side')} {decision.get('target_weight')} {decision.get('rationale', '')}")
    return " ".join(chunk for chunk in chunks if chunk)


def _hash_embed(text: str, dim: int = 64) -> list[float]:
    values = [0.0] * dim
    tokens = [token for token in text.lower().replace("|", " ").replace(",", " ").split() if token]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dim
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        values[idx] += sign
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def _pca2(vectors: list[list[float]]) -> list[tuple[float, float]]:
    if not vectors:
        return []
    dim = len(vectors[0])
    means = [sum(vector[i] for vector in vectors) / len(vectors) for i in range(dim)]
    centered = [[vector[i] - means[i] for i in range(dim)] for vector in vectors]
    cov = [[0.0 for _ in range(dim)] for _ in range(dim)]
    for vector in centered:
        for i in range(dim):
            for j in range(dim):
                cov[i][j] += vector[i] * vector[j]
    first = _power_vector(cov)
    first_lambda = _quad(first, cov)
    deflated = [[cov[i][j] - first_lambda * first[i] * first[j] for j in range(dim)] for i in range(dim)]
    second = _power_vector(deflated)
    return [(sum(v[i] * first[i] for i in range(dim)), sum(v[i] * second[i] for i in range(dim))) for v in centered]


def _power_vector(matrix: list[list[float]], iterations: int = 80) -> list[float]:
    dim = len(matrix)
    vector = [1.0 / math.sqrt(dim)] * dim
    for _ in range(iterations):
        nxt = [sum(matrix[i][j] * vector[j] for j in range(dim)) for i in range(dim)]
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    return vector


def _quad(vector: list[float], matrix: list[list[float]]) -> float:
    return sum(vector[i] * sum(matrix[i][j] * vector[j] for j in range(len(vector))) for i in range(len(vector)))


def _effective_rank(vectors: list[list[float]]) -> float:
    if len(vectors) < 2:
        return 0.0
    dim = len(vectors[0])
    means = [sum(vector[i] for vector in vectors) / len(vectors) for i in range(dim)]
    centered = [[vector[i] - means[i] for i in range(dim)] for vector in vectors]
    gram = [[0.0 for _ in centered] for _ in centered]
    scale = max(1, len(centered) - 1)
    for i, left in enumerate(centered):
        for j, right in enumerate(centered):
            gram[i][j] = sum(left[k] * right[k] for k in range(dim)) / scale
    eigenvalues = _top_eigenvalues(gram, min(len(gram), 12))
    positive = [value for value in eigenvalues if value > 1e-12]
    total = sum(positive)
    if not total:
        return 0.0
    entropy = -sum((value / total) * math.log(value / total) for value in positive)
    return math.exp(entropy)


def _top_eigenvalues(matrix: list[list[float]], count: int) -> list[float]:
    work = [row[:] for row in matrix]
    values = []
    for _ in range(count):
        vector = _power_vector(work, iterations=60)
        value = max(0.0, _quad(vector, work))
        if value <= 1e-12:
            break
        values.append(value)
        for i in range(len(work)):
            for j in range(len(work)):
                work[i][j] -= value * vector[i] * vector[j]
    return values


def _euclidean(left: tuple[float, float], right: tuple[float, float]) -> float:
    return math.sqrt((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2)


def _drawdowns(equities: list[float]) -> list[float]:
    peak = equities[0] if equities else 0.0
    out = []
    for equity in equities:
        peak = max(peak, equity)
        out.append((equity / peak) - 1.0 if peak else 0.0)
    return out


def _phase(idx: int, drawdowns: list[float]) -> str:
    if not drawdowns:
        return "normal"
    trough = min(range(len(drawdowns)), key=lambda i: drawdowns[i])
    if max(0, trough - 5) <= idx < trough:
        return "pre_drawdown"
    if trough <= idx <= min(len(drawdowns) - 1, trough + 5):
        return "drawdown"
    return "normal"


def _abs_exposure(decisions: list[dict[str, Any]]) -> float:
    return sum(abs(_to_float(decision.get("target_weight"), 0.0)) for decision in decisions)


def _realized_abs(step: dict[str, Any]) -> float:
    portfolio = step.get("portfolio", {})
    equity = _to_float(portfolio.get("equity"), 0.0)
    prices = portfolio.get("last_prices", {})
    positions = portfolio.get("positions", {})
    if not equity:
        return 0.0
    return sum(abs(_to_float(qty, 0.0) * _to_float(prices.get(symbol), 0.0) / equity) for symbol, qty in positions.items())


def _calibration_gap(decisions: list[dict[str, Any]], approved: list[dict[str, Any]]) -> float:
    approved_by_symbol = {str(item.get("symbol")): item for item in approved}
    gap = 0.0
    for decision in decisions:
        symbol = str(decision.get("symbol"))
        gap += abs(_to_float(approved_by_symbol.get(symbol, {}).get("target_weight"), 0.0) - _to_float(decision.get("target_weight"), 0.0))
    return gap


def _average_by_step(rows: list[dict[str, Any]], key: str, window: int) -> list[tuple[int, float]]:
    by_step: dict[int, list[float]] = {}
    for row in rows:
        by_step.setdefault(int(row["step"]), []).append(float(row[key]))
    ordered = sorted((step, _mean(values)) for step, values in by_step.items())
    smoothed = []
    for idx, (step, _) in enumerate(ordered):
        values = [value for _, value in ordered[max(0, idx - window + 1) : idx + 1]]
        smoothed.append((step, _mean(values)))
    return smoothed


def _corr(left: list[float], right: list[float]) -> float:
    n = min(len(left), len(right))
    if n < 2:
        return 0.0
    left = left[-n:]
    right = right[-n:]
    mean_l = _mean(left)
    mean_r = _mean(right)
    num = sum((l - mean_l) * (r - mean_r) for l, r in zip(left, right, strict=True))
    den_l = math.sqrt(sum((l - mean_l) ** 2 for l in left))
    den_r = math.sqrt(sum((r - mean_r) ** 2 for r in right))
    return num / (den_l * den_r) if den_l and den_r else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _parse_model_spec(value: str) -> tuple[str, str]:
    if ":" not in value:
        return ("poe", value.strip())
    provider, model = value.split(":", 1)
    return provider.strip(), model.strip()


def _safe(symbol: str) -> str:
    return symbol.replace("^", "").replace("/", "-")


def _slug(value: str) -> str:
    return value.replace("-", "_").replace(".", "_")


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _max_matrix(matrix: list[list[float]]) -> float:
    return max([value for row in matrix for value in row] or [1.0]) or 1.0


def _scale(value: float, old_min: float, old_max: float, new_min: float, new_max: float) -> float:
    if math.isclose(old_min, old_max):
        return (new_min + new_max) / 2
    return new_min + (value - old_min) * (new_max - new_min) / (old_max - old_min)


def _diverging_color(value: float, lo: float, hi: float) -> str:
    mid = 0.0
    if value >= mid:
        t = min(1.0, value / max(1e-12, hi))
        return _mix((255, 255, 255), (220, 38, 38), t)
    t = min(1.0, abs(value / min(-1e-12, lo)))
    return _mix((255, 255, 255), (37, 99, 235), t)


def _sequential_color(value: float, lo: float, hi: float) -> str:
    t = min(1.0, max(0.0, (value - lo) / max(1e-12, hi - lo)))
    return _mix((240, 253, 250), (15, 118, 110), t)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    rgb = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return "#" + "".join(f"{value:02x}" for value in rgb)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "scene",
        "provider",
        "model",
        "feedback",
        "steps",
        "total_return",
        "max_drawdown",
        "risk_gate_rate",
        "mean_calibration_score",
        "execution_fill_rate",
    ]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(column, "")) for column in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _svg(width: int, height: int, title: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(title)}"><rect width="100%" height="100%" fill="#f8fafc"/>'


def _panel(x: int, y: int, width: int, height: int, title: str) -> str:
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d9e2ec"/>{_text(x + 18, y + 28, title, 15, "#0f172a", 800)}'


def _text(x: float, y: float, value: str, size: int, color: str, weight: int = 400, anchor: str = "start") -> str:
    return f'<text x="{x:.2f}" y="{y:.2f}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{_esc(value)}</text>'


def _legend(x: float, y: float, items: list[tuple[str, str]]) -> str:
    parts = []
    for idx, (label, color) in enumerate(items):
        yy = y + idx * 18
        parts.append(f'<rect x="{x}" y="{yy - 10}" width="10" height="10" fill="{color}"/>')
        parts.append(_text(x + 16, yy, label, 11, "#334155", 400))
    return "".join(parts)


def _esc(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


if __name__ == "__main__":
    raise SystemExit(main())
