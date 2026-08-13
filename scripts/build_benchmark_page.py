from __future__ import annotations

import argparse
import csv
import html
import json
import statistics
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CRISIS_CSV = ROOT / "docs/results/crisis/crisis_summary.csv"
REPRESENTATION_CSV = ROOT / "docs/results/representation/embedding_robustness.csv"
INTRADAY_CSV = ROOT / "docs/results/intraday/intraday_complex.csv"
CLASSICAL_COMPARISON_CSV = ROOT / "docs/results/classical_baselines/classical_vs_llm_comparison.csv"
CLASSICAL_AGGREGATE_CSV = ROOT / "docs/results/classical_baselines/classical_baseline_aggregate.csv"
QUALITY_AGGREGATE_CSV = ROOT / "docs/results/quality_decomposition/quality_decomposition_aggregate.csv"
QUALITY_RADAR_SVG = ROOT / "docs/results/quality_decomposition/decision_execution_radar.svg"
QUICKSTART_JSON = ROOT / "outputs/examples/quickstart_core_metrics.json"
CALIBRATION_REPORTS = [
    ("fixture", ROOT / "docs/results/execution_quote_fill_calibration_sample.json"),
    ("public Binance BTCUSDT perpetual sample", ROOT / "docs/results/execution_quote_fill_calibration_binance_sample.json"),
]
RELEASE_TAG = "v0.2.0"
BENCHMARK_VERSION = "v0.2"
BENCHMARK_TITLE = "TradeArena v0.2 Benchmark Card"
LEGACY_MARKDOWN = ROOT / "docs/results/benchmark_v0_1.md"
LEGACY_HTML = ROOT / "outputs/examples/benchmark-v0.1.html"
POLICY_LABELS = {
    "gpt-5.5": "frontier-policy-A (redacted)",
    "claude-opus-4.7": "frontier-policy-B (redacted)",
    "gemini-3.1-pro": "frontier-policy-C (redacted)",
    "deepseek-v4-pro": "frontier-policy-D (redacted)",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the TradeArena v0.2 benchmark result page.")
    parser.add_argument("--markdown", default="docs/results/benchmark_v0_2.md")
    parser.add_argument("--html", default="outputs/examples/benchmark-v0.2.html")
    args = parser.parse_args()

    crisis_rows = _read_csv(CRISIS_CSV)
    representation_rows = _read_csv(REPRESENTATION_CSV)
    intraday_rows = _read_csv(INTRADAY_CSV) if INTRADAY_CSV.exists() else []
    classical_comparison_rows = _read_csv(CLASSICAL_COMPARISON_CSV) if CLASSICAL_COMPARISON_CSV.exists() else []
    classical_aggregate_rows = _read_csv(CLASSICAL_AGGREGATE_CSV) if CLASSICAL_AGGREGATE_CSV.exists() else []
    quality_rows = _read_csv(QUALITY_AGGREGATE_CSV) if QUALITY_AGGREGATE_CSV.exists() else []
    quickstart_rows = _read_quickstart_rows(QUICKSTART_JSON) if QUICKSTART_JSON.exists() else []
    calibration_rows = _read_calibration_rows(CALIBRATION_REPORTS)

    crisis_summary = _summarize_crisis(crisis_rows)
    crisis_true_rows = [row for row in crisis_rows if row.get("feedback") == "true"]
    representation_summary = _summarize_representation(representation_rows)

    md = _markdown(
        quickstart_rows,
        crisis_summary,
        crisis_true_rows,
        intraday_rows,
        classical_comparison_rows,
        classical_aggregate_rows,
        quality_rows,
        representation_summary,
        calibration_rows,
    )
    html_text = _html(
        quickstart_rows,
        crisis_summary,
        crisis_true_rows,
        intraday_rows,
        classical_comparison_rows,
        classical_aggregate_rows,
        quality_rows,
        representation_summary,
        calibration_rows,
    )

    markdown_path = ROOT / args.markdown
    html_path = ROOT / args.html
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(md, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    if markdown_path.relative_to(ROOT).as_posix() == "docs/results/benchmark_v0_2.md":
        LEGACY_MARKDOWN.write_text(_legacy_markdown_alias(), encoding="utf-8")
    if html_path.relative_to(ROOT).as_posix() == "outputs/examples/benchmark-v0.2.html":
        LEGACY_HTML.parent.mkdir(parents=True, exist_ok=True)
        LEGACY_HTML.write_text(_legacy_html_alias(), encoding="utf-8")

    print(f"Wrote {markdown_path.relative_to(ROOT)}")
    print(f"Wrote {html_path.relative_to(ROOT)}")
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_quickstart_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for case, metrics in sorted(data.items()):
        rows.append(
            {
                "scenario": "deterministic quickstart",
                "agent": case,
                "return": float(metrics.get("total_return", 0.0)),
                "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
                "fill_rate": float(metrics.get("execution_fill_rate", metrics.get("fill_rate", 0.0))),
                "rejection_rate": _safe_ratio(float(metrics.get("rejected_order_count", 0.0)), float(metrics.get("order_count", 0.0))),
                "risk_edits": int(float(metrics.get("risk_clipped_decisions", 0.0))),
                "audit_completeness": float(metrics.get("trajectory_reproducibility_coverage", 1.0)),
            }
        )
    return rows


def _read_calibration_rows(reports: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, path in reports:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        params = data["fitted_parameters"]
        quality = data["fit_quality"]
        stress = data.get("stress_only_comparison", {})
        rows.append(
            {
                "label": label,
                "aligned_rows": data["input"]["aligned_rows"],
                "spread_p50_bps": params["spread_bps_median"],
                "spread_p90_bps": params["spread_bps_p90"],
                "shortfall_p50_bps": quality["median_shortfall_bps"],
                "shortfall_p90_bps": quality["p90_shortfall_bps"],
                "stress_mae_bps": stress.get("residual_mae_bps"),
                "calibrated_mae_bps": quality["residual_mae_bps"],
            }
        )
    return rows


def _summarize_crisis(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["scene"], row["feedback"]), []).append(row)

    result: list[dict[str, Any]] = []
    for (scene, feedback), group in sorted(groups.items()):
        result.append(
            {
                "scenario": scene,
                "agent": f"LLM policies ({feedback} feedback)",
                "return": _mean(group, "total_return"),
                "max_drawdown": _mean(group, "max_drawdown"),
                "fill_rate": _mean(group, "execution_fill_rate"),
                "rejection_rate": 1.0 - _mean(group, "execution_fill_rate"),
                "risk_edits": round(_mean(group, "risk_clipped_decisions")),
                "audit_completeness": 1.0,
                "calibration": _mean(group, "mean_calibration_score"),
                "models": len(group),
            }
        )
    return result


def _summarize_representation(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keep = []
    for row in rows:
        if row.get("cohort") != "all_llm":
            continue
        if row.get("view") not in {"plan", "fused"}:
            continue
        keep.append(
            {
                "embedding": row["embedding"],
                "view": row["view"],
                "anchors": int(float(row["anchors"])),
                "pre_steps": int(float(row["pre_steps"])),
                "rank_delta": float(row["mean_effective_rank_delta"]),
                "contraction_rate": float(row["rank_contraction_rate"]),
                "mean_pre_shift": float(row["mean_pre_shift"]),
            }
        )
    return sorted(keep, key=lambda item: (item["view"], item["embedding"]))


def _markdown(
    quickstart_rows: list[dict[str, Any]],
    crisis_summary: list[dict[str, Any]],
    crisis_true_rows: list[dict[str, str]],
    intraday_rows: list[dict[str, str]],
    classical_comparison_rows: list[dict[str, str]],
    classical_aggregate_rows: list[dict[str, str]],
    quality_rows: list[dict[str, str]],
    representation_summary: list[dict[str, Any]],
    calibration_rows: list[dict[str, Any]],
) -> str:
    lines = [
        f"# {BENCHMARK_TITLE}",
        "",
        _wrap(
            "TreLLM is a financial-agent reliability audit and control system. TradeArena is the "
            "public leaderboard module and benchmark-card layer inside that system, not the whole "
            "project identity and not a profitability claim. This page gives a compact, "
            "citable snapshot of what the v0.2 artifacts show under execution realism, risk "
            "gates, and replayable intent-to-execution trajectories."
        ),
        "",
        "## One-Sentence Finding",
        "",
        _wrap(
            "Execution realism and risk gates materially change autonomous "
            "financial-agent evaluation: intended allocations can look very "
            "different after spread, slippage, latency, liquidity limits, "
            "partial fills, rejected orders, and pre-trade risk edits."
        ),
        "",
        "## Result Provenance",
        "",
        "> **Execution mode: `realistic-stress`, not calibrated transaction-cost prediction.** "
        "The default simulator uses shared stress assumptions for spread, slippage, latency, "
        "liquidity caps, partial fills, and rejections. Rows on this card should not be read "
        "as calibrated execution-cost estimates unless they attach quote/order-book/fill provenance.",
        "",
        f"- Software release: {RELEASE_TAG}.",
        f"- Benchmark snapshot lineage: {BENCHMARK_VERSION}.",
        "- Benchmark card source: tracked snapshots under `docs/results/`.",
        "- Reproduction command:",
        "",
        "  ```bash",
        "  python -m pip install -e \".[dev]\"",
        "  python scripts/run_showcase.py",
        "  python scripts/build_benchmark_page.py",
        "  ```",
        "",
        "- Data: tracked synthetic, timestamp-masked, and redacted artifacts.",
        "- Live model calls: not required for first-run reproduction.",
        "- Raw prompt/response caches: not included.",
        "- Intended use: agent reliability and audit research, not trading advice.",
        "",
        "## Claim Badges And Validation Status",
        "",
        _md_table(
            ["Surface", "Badge / status", "Evidence boundary"],
            _claim_status_rows(),
        ),
        "",
        "## What Is Measured",
        "",
        "- Return and max drawdown.",
        "- Fill rate, rejection rate, spread, latency, slippage, and partial fills.",
        "- Risk edits, clipped decisions, violations, and audit completeness.",
        "- Concentration / Herfindahl for portfolio probes.",
        "- Calibration and representation robustness diagnostics.",
        "",
        "## How To Reproduce",
        "",
        "```bash",
        "python -m pip install -e \".[dev]\"",
        "python scripts/run_showcase.py",
        "python scripts/build_benchmark_page.py",
        "```",
        "",
        _wrap(
            "The page uses tracked CSV snapshots under `docs/results/` plus "
            "deterministic first-run artifacts under `outputs/examples/`. "
            "Live model calls are not required for first-run reproduction."
        ),
        "",
    ]

    if quickstart_rows:
        lines += [
            "## First-Run Execution Benchmark",
            "",
            _md_table(
                ["Scenario", "Agent / baseline", "Return", "Max drawdown", "Fill rate", "Rejection rate", "Risk edits", "Audit completeness"],
                [
                    [
                        row["scenario"],
                        row["agent"],
                        _pct(row["return"]),
                        _pct(row["max_drawdown"]),
                        _pct(row["fill_rate"]),
                        _pct(row["rejection_rate"]),
                        str(row["risk_edits"]),
                        _pct(row["audit_completeness"]),
                    ]
                    for row in quickstart_rows
                ],
            ),
            "",
        ]

    if calibration_rows:
        lines += [
            "## Execution Calibration Evidence",
            "",
            _wrap(
                "These rows are not the default leaderboard mode. They show what "
                "must be attached before a result can move from stress-only "
                "execution assumptions toward calibrated transaction-cost evidence."
            ),
            "",
            _md_table(
                [
                    "Evidence",
                    "Aligned fills",
                    "Median spread",
                    "P90 spread",
                    "Median shortfall",
                    "P90 shortfall",
                    "Stress MAE",
                    "Calibrated MAE",
                ],
                [
                    [
                        row["label"],
                        str(row["aligned_rows"]),
                        _bps(row["spread_p50_bps"]),
                        _bps(row["spread_p90_bps"]),
                        _bps(row["shortfall_p50_bps"]),
                        _bps(row["shortfall_p90_bps"]),
                        _bps(row["stress_mae_bps"]),
                        _bps(row["calibrated_mae_bps"]),
                    ]
                    for row in calibration_rows
                ],
            ),
            "",
        ]

    if classical_comparison_rows:
        lines += [
            "## Non-LLM Classical Baseline Check",
            "",
            _wrap(
                "The synthetic and real-market matrices include deterministic "
                "non-LLM baselines so the benchmark can ask whether an LLM "
                "policy beats fixed non-LLM strategies, not only other LLMs."
            ),
            "",
            _md_table(
                ["Universe", "Scenario", "Best classical", "Classical return", "Best LLM", "LLM return", "Return gap", "LLM wins?"],
                [
                    [
                        row["universe"],
                        row["scenario_label"],
                        row["best_classical"],
                        _pct(float(row["best_classical_return"])),
                        f"{row['best_llm_provider']}:{row['best_llm_model']}" if row.get("best_llm_model") else "no LLM row",
                        _pct(float(row["best_llm_return"])),
                        _pct(float(row["llm_return_minus_classical"])) if row.get("llm_return_minus_classical") not in {"", None} else "",
                        _yes_no(row["llm_outperforms_classical_return"]),
                    ]
                    for row in classical_comparison_rows
                ],
            ),
            "",
        ]
    if classical_aggregate_rows:
        lines += [
            "## Classical Baseline Aggregate",
            "",
            _md_table(
                ["Universe", "Baseline", "Scenarios", "Avg return", "Worst DD", "Avg Sharpe", "Avg fill", "Rejected", "Risk edits"],
                [
                    [
                        row["universe"],
                        row["baseline_label"],
                        row["scenario_count"],
                        _pct(float(row["avg_return"])),
                        _pct(float(row["worst_drawdown"])),
                        f"{float(row['avg_sharpe']):.3f}",
                        _pct(float(row["avg_fill_rate"])),
                        row["total_rejected_orders"],
                        row["total_risk_edits"],
                    ]
                    for row in classical_aggregate_rows
                ],
            ),
            "",
        ]
    if quality_rows:
        lines += [
            "## Decision Quality vs Execution Quality",
            "",
            _wrap(
                "Return alone hides whether a row had useful pre-risk intent, "
                "good risk discipline, or robust execution. The three-axis "
                "diagnostic separates alpha quality, risk discipline, and "
                "execution robustness."
            ),
            "",
            "![Decision quality radar](quality_decomposition/decision_execution_radar.svg)",
            "",
            _md_table(
                ["Family", "Rows", "Alpha", "Risk", "Execution", "Pre-risk alpha return", "Realized return", "Fill rate"],
                [
                    [
                        row["family_label"],
                        row["rows"],
                        f"{float(row['alpha_quality_score']):.3f}",
                        f"{float(row['risk_discipline_score']):.3f}",
                        f"{float(row['execution_robustness_score']):.3f}",
                        _pct(float(row["alpha_pre_risk_total_return"])),
                        _pct(float(row["total_return"])),
                        _pct(float(row["execution_fill_rate"])),
                    ]
                    for row in quality_rows
                ],
            ),
            "",
        ]

    lines += [
        "## Key Result 1: Risk Gates Are Active, Not Cosmetic",
        "",
        _wrap(
            "Across the crisis and intraday rows, risk gates repeatedly edit "
            "or clip intended allocations before execution. The benchmark "
            "therefore reports risk edits alongside return, instead of "
            "treating risk control as a post-hoc metric."
        ),
        "",
        "## Crisis-Scene LLM Benchmark",
        "",
        _wrap(
            "The crisis snapshot aggregates timestamp-masked 2022 Tech/Rates "
            "and 2023 SVB-style stress paths. Rows below average across the "
            "tracked model policies for each feedback mode."
        ),
        "",
        _md_table(
            ["Scenario", "Agent / baseline", "Return", "Max drawdown", "Fill rate", "Rejection rate", "Risk edits", "Audit completeness"],
            [
                [
                    row["scenario"],
                    row["agent"],
                    _pct(row["return"]),
                    _pct(row["max_drawdown"]),
                    _pct(row["fill_rate"]),
                    _pct(row["rejection_rate"]),
                    str(row["risk_edits"]),
                    _pct(row["audit_completeness"]),
                ]
                for row in crisis_summary
            ],
        ),
        "",
        "## True-Feedback Model Rows",
        "",
        _wrap(
            "Model names are redacted or normalized labels for benchmark "
            "policies. Raw provider prompts and responses are not shipped."
        ),
        "",
        _md_table(
            ["Scenario", "Policy label", "Return", "Max drawdown", "Fill rate", "Risk edits", "Violations", "Calibration"],
            [
                [
                    row["scene"],
                    _policy_label(row["model"]),
                    _pct(float(row["total_return"])),
                    _pct(float(row["max_drawdown"])),
                    _pct(float(row["execution_fill_rate"])),
                    row["risk_clipped_decisions"],
                    row["risk_violation_count"],
                    f"{float(row['mean_calibration_score']):.3f}",
                ]
                for row in crisis_true_rows
            ],
        ),
        "",
    ]

    if intraday_rows:
        lines += [
            "## Key Result 2: Execution Assumptions Change Realized Exposure",
            "",
            _wrap(
                "The 51-stock hourly probe shows that low-liquidity and "
                "latency stress rows do not behave like ideal fills. Fill "
                "rate, rejected orders, and realized exposure become part of "
                "the benchmark outcome."
            ),
            "",
            "## 51-Stock Intraday Portfolio Probe",
            "",
            _wrap(
                "The intraday snapshot compares passive, deterministic, "
                "Markowitz/MVO, execution-stress, and redacted LLM policy "
                "rows on the same 51-stock hourly panel."
            ),
            "",
            _md_table(
                ["Agent / baseline", "Return", "Max drawdown", "Fill rate", "Rejected", "Risk edits", "Herfindahl", "Audit completeness"],
                [
                    [
                        _pretty_case(row["case"]),
                        _pct(float(row["total_return"])),
                        _pct(float(row["max_drawdown"])),
                        _pct(float(row["execution_fill_rate"])),
                        row["rejected_order_count"],
                        row["risk_clipped_decisions"],
                        f"{float(row['mean_herfindahl']):.3f}",
                        _pct(float(row["trajectory_reproducibility_coverage"])),
                    ]
                    for row in intraday_rows
                ],
            ),
            "",
        ]

    lines += [
        "## Key Result 3: Audit Completeness Is A Benchmark Dimension",
        "",
        _wrap(
            "Every result row should be traceable to a trajectory rather "
            "than only to a return curve. TradeArena therefore reports audit "
            "completeness and keeps compact, redacted result manifests."
        ),
        "",
        "## Representation Robustness Snapshot",
        "",
        _wrap(
            "A result is more useful when the diagnostic survives multiple "
            "representation views. The v0.2 tracked snapshot includes 80 "
            "rolling failure anchors and 320 pre-failure steps across eight "
            "LLM trajectories."
        ),
        "",
        _md_table(
            ["Embedding", "View", "Anchors", "Pre-failure steps", "Mean rank delta", "Contraction rate", "Mean pre-shift"],
            [
                [
                    row["embedding"],
                    row["view"],
                    str(row["anchors"]),
                    str(row["pre_steps"]),
                    f"{row['rank_delta']:.3f}",
                    _pct(row["contraction_rate"]),
                    f"{row['mean_pre_shift']:.3f}",
                ]
                for row in representation_summary
            ],
        ),
        "",
        "## Limitations",
        "",
        "- This is a benchmark and audit artifact, not financial advice.",
        "- It is not a live-trading system and does not promise profitability.",
        "- First-run reproduction uses tracked artifacts, not live provider calls.",
        "- Public rows use redacted or normalized policy labels.",
        "- Raw provider prompts, responses, credentials, and caches are not shipped.",
        "",
    ]
    return "\n".join(lines)


def _html(
    quickstart_rows: list[dict[str, Any]],
    crisis_summary: list[dict[str, Any]],
    crisis_true_rows: list[dict[str, str]],
    intraday_rows: list[dict[str, str]],
    classical_comparison_rows: list[dict[str, str]],
    classical_aggregate_rows: list[dict[str, str]],
    quality_rows: list[dict[str, str]],
    representation_summary: list[dict[str, Any]],
    calibration_rows: list[dict[str, Any]],
) -> str:
    provenance = _provenance_rows()
    claim_status_section = _section(
        "Claim Badges And Validation Status",
        "Rows are evidence-ranked before they are ranked by performance.",
        _html_table(["Surface", "Badge / status", "Evidence boundary"], _claim_status_rows()),
    )
    quickstart = ""
    if quickstart_rows:
        quickstart = _section(
            "First-Run Execution Benchmark",
            "Deterministic, local benchmark cases generated by the quickstart path.",
            _html_table(
                ["Scenario", "Agent / baseline", "Return", "Max drawdown", "Fill rate", "Rejection rate", "Risk edits", "Audit completeness"],
                [
                    [
                        row["scenario"],
                        row["agent"],
                        _pct(row["return"]),
                        _pct(row["max_drawdown"]),
                        _pct(row["fill_rate"]),
                        _pct(row["rejection_rate"]),
                        str(row["risk_edits"]),
                        _pct(row["audit_completeness"]),
                    ]
                    for row in quickstart_rows
                ],
            ),
        )

    classical = ""
    if classical_comparison_rows:
        classical = _section(
            "Non-LLM Classical Baseline Check",
            "Deterministic baselines answer whether LLM policies outperform fixed non-LLM strategies, not only other LLMs.",
            _html_table(
                ["Universe", "Scenario", "Best classical", "Classical return", "Best LLM", "LLM return", "Return gap", "LLM wins?"],
                [
                    [
                        row["universe"],
                        row["scenario_label"],
                        row["best_classical"],
                        _pct(float(row["best_classical_return"])),
                        f"{row['best_llm_provider']}:{row['best_llm_model']}" if row.get("best_llm_model") else "no LLM row",
                        _pct(float(row["best_llm_return"])),
                        _pct(float(row["llm_return_minus_classical"])) if row.get("llm_return_minus_classical") not in {"", None} else "",
                        _yes_no(row["llm_outperforms_classical_return"]),
                    ]
                    for row in classical_comparison_rows
                ],
            ),
        )
    classical_aggregate = ""
    if classical_aggregate_rows:
        classical_aggregate = _section(
            "Classical Baseline Aggregate",
            "Buy-and-hold, equal weight, random, always-hold, momentum, mean reversion, risk parity, minimum variance, and Markowitz/MVO across the benchmark scenarios.",
            _html_table(
                ["Universe", "Baseline", "Scenarios", "Avg return", "Worst DD", "Avg Sharpe", "Avg fill", "Rejected", "Risk edits"],
                [
                    [
                        row["universe"],
                        row["baseline_label"],
                        row["scenario_count"],
                        _pct(float(row["avg_return"])),
                        _pct(float(row["worst_drawdown"])),
                        f"{float(row['avg_sharpe']):.3f}",
                        _pct(float(row["avg_fill_rate"])),
                        row["total_rejected_orders"],
                        row["total_risk_edits"],
                    ]
                    for row in classical_aggregate_rows
                ],
            ),
        )
    quality = ""
    if quality_rows:
        radar = QUALITY_RADAR_SVG.read_text(encoding="utf-8", errors="ignore") if QUALITY_RADAR_SVG.exists() else ""
    quality = _section(
            "Decision Quality vs Execution Quality",
            "A three-axis decomposition separates pre-risk intent, risk discipline, and execution robustness.",
            radar
            + _html_table(
                ["Family", "Rows", "Alpha", "Risk", "Execution", "Pre-risk alpha", "Realized return", "Fill rate"],
                [
                    [
                        row["family_label"],
                        row["rows"],
                        f"{float(row['alpha_quality_score']):.3f}",
                        f"{float(row['risk_discipline_score']):.3f}",
                        f"{float(row['execution_robustness_score']):.3f}",
                        _pct(float(row["alpha_pre_risk_total_return"])),
                        _pct(float(row["total_return"])),
                        _pct(float(row["execution_fill_rate"])),
                    ]
                    for row in quality_rows
                ],
            ),
        )

    crisis = _section(
        "Crisis-Scene LLM Benchmark",
        "Timestamp-masked 2022 Tech/Rates and 2023 SVB stress paths, averaged by feedback mode.",
        _html_table(
            ["Scenario", "Agent / baseline", "Return", "Max drawdown", "Fill rate", "Rejection rate", "Risk edits", "Audit completeness"],
            [
                [
                    row["scenario"],
                    row["agent"],
                    _pct(row["return"]),
                    _pct(row["max_drawdown"]),
                    _pct(row["fill_rate"]),
                    _pct(row["rejection_rate"]),
                    str(row["risk_edits"]),
                    _pct(row["audit_completeness"]),
                ]
                for row in crisis_summary
            ],
        ),
    )
    calibration = _section(
        "Execution Calibration Evidence",
        "Rows here are evidence for calibration plumbing; default benchmark rows remain realistic-stress unless they attach quote/order-book/fill provenance.",
        _html_table(
            [
                "Evidence",
                "Aligned fills",
                "Median spread",
                "P90 spread",
                "Median shortfall",
                "P90 shortfall",
                "Stress MAE",
                "Calibrated MAE",
            ],
            [
                [
                    row["label"],
                    str(row["aligned_rows"]),
                    _bps(row["spread_p50_bps"]),
                    _bps(row["spread_p90_bps"]),
                    _bps(row["shortfall_p50_bps"]),
                    _bps(row["shortfall_p90_bps"]),
                    _bps(row["stress_mae_bps"]),
                    _bps(row["calibrated_mae_bps"]),
                ]
                for row in calibration_rows
            ],
        ),
    )

    true_feedback = _section(
        "True-Feedback Model Rows",
        "Policy-level rows under structured true risk feedback. Model names are redacted or normalized labels; raw provider prompts and responses are not shipped.",
        _html_table(
            ["Scenario", "Policy label", "Return", "Max drawdown", "Fill rate", "Risk edits", "Violations", "Calibration"],
            [
                [
                    row["scene"],
                    _policy_label(row["model"]),
                    _pct(float(row["total_return"])),
                    _pct(float(row["max_drawdown"])),
                    _pct(float(row["execution_fill_rate"])),
                    row["risk_clipped_decisions"],
                    row["risk_violation_count"],
                    f"{float(row['mean_calibration_score']):.3f}",
                ]
                for row in crisis_true_rows
            ],
        ),
    )

    intraday = ""
    if intraday_rows:
        intraday = _section(
            "51-Stock Intraday Portfolio Probe",
            "Passive, deterministic, Markowitz/MVO, execution-stress, and redacted LLM policy rows on a 51-stock hourly panel.",
            _html_table(
                ["Agent / baseline", "Return", "Max drawdown", "Fill rate", "Rejected", "Risk edits", "Herfindahl", "Audit completeness"],
                [
                    [
                        _pretty_case(row["case"]),
                        _pct(float(row["total_return"])),
                        _pct(float(row["max_drawdown"])),
                        _pct(float(row["execution_fill_rate"])),
                        row["rejected_order_count"],
                        row["risk_clipped_decisions"],
                        f"{float(row['mean_herfindahl']):.3f}",
                        _pct(float(row["trajectory_reproducibility_coverage"])),
                    ]
                    for row in intraday_rows
                ],
            ),
        )

    representation = _section(
        "Representation Robustness Snapshot",
        "80 rolling failure anchors and 320 pre-failure steps across eight LLM trajectories.",
        _html_table(
            ["Embedding", "View", "Anchors", "Pre-failure steps", "Mean rank delta", "Contraction rate", "Mean pre-shift"],
            [
                [
                    row["embedding"],
                    row["view"],
                    str(row["anchors"]),
                    str(row["pre_steps"]),
                    f"{row['rank_delta']:.3f}",
                    _pct(row["contraction_rate"]),
                    f"{row['mean_pre_shift']:.3f}",
                ]
                for row in representation_summary
            ],
        ),
    )
    provenance_section = _section(
        "Result Provenance",
        "Where this benchmark card comes from and how to reproduce it.",
        _html_table(["Field", "Value"], provenance),
    )
    measured_section = _section(
        "What Is Measured",
        "The v0.2 card emphasizes audit and execution dimensions, not only return.",
        (
            "<ul>"
            "<li>Return and max drawdown.</li>"
            "<li>Fill rate, rejection rate, spread, latency, slippage, and partial fills.</li>"
            "<li>Risk edits, clipped decisions, violations, and audit completeness.</li>"
            "<li>Concentration / Herfindahl for portfolio probes.</li>"
            "<li>Calibration and representation robustness diagnostics.</li>"
            "</ul>"
        ),
    )
    risk_gate_section = _section(
        "Key Result 1: Risk Gates Are Active, Not Cosmetic",
        "Risk gates repeatedly edit or clip intended allocations before execution.",
        '<p class="note">The benchmark reports risk edits alongside return so that risk control is visible in the result card.</p>',
    )
    execution_section = _section(
        "Key Result 2: Execution Assumptions Change Realized Exposure",
        "The 51-stock hourly probe separates intended allocation from realistic execution outcomes.",
        '<p class="note">Fill rate, rejected orders, latency, and slippage become part of the benchmark outcome.</p>',
    )
    audit_section = _section(
        "Key Result 3: Audit Completeness Is A Benchmark Dimension",
        "Each row should be traceable to a trajectory, not just a return curve.",
        (
            '<p class="note">TradeArena keeps compact result snapshots and redacted '
            "manifests so users can inspect what happened without shipping raw "
            "provider text.</p>"
        ),
    )

    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{BENCHMARK_TITLE}</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; color: #0f172a; background: #f8fafc; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 42px 24px 58px; }}
a {{ color: #2563eb; }}
.hero {{ padding: 28px; background: #0f172a; color: #e2e8f0; border-radius: 12px; box-shadow: 0 22px 60px rgba(15, 23, 42, 0.18); }}
h1 {{ margin: 0 0 10px; font-size: 38px; letter-spacing: 0; }}
.lead {{ max-width: 900px; line-height: 1.56; color: #cbd5e1; margin: 0; }}
.links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
.links a {{ padding: 8px 11px; border-radius: 8px; border: 1px solid #334155; color: #ccfbf1; background: #111827; text-decoration: none; font-weight: 800; font-size: 13px; }}
.claim-banner {{ margin-top: 18px; padding: 12px 14px; border: 1px solid #f59e0b; border-radius: 8px; background: #fffbeb; color: #78350f; line-height: 1.5; font-weight: 700; }}
section {{ margin-top: 26px; padding: 20px; border: 1px solid #d8e2ed; border-radius: 10px; background: #fff; }}
h2 {{ margin: 0 0 6px; font-size: 24px; letter-spacing: 0; }}
.section-lead {{ margin: 0 0 14px; color: #64748b; line-height: 1.5; }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 9px 8px; text-align: right; white-space: nowrap; }}
th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
th {{ background: #f1f5f9; color: #334155; font-weight: 800; }}
.note {{ margin: 18px 0 0; color: #475569; line-height: 1.55; }}
code {{ background: #e2e8f0; border-radius: 5px; padding: 2px 5px; }}
</style>
<main>
  <div class="hero">
    <h1>{BENCHMARK_TITLE}</h1>
    <p class="lead">TradeArena is the public leaderboard module and benchmark-card layer inside TreLLM. This compact result page covers agent reliability and intent-to-execution audit, not profitability claims or financial advice.</p>
    <div class="links">
      <a href="showcase.html">Showcase</a>
      <a href="audit_report.html">Audit report</a>
      <a href="crisis_snapshot_gallery.html">Crisis gallery</a>
      <a href="https://github.com/weich97/TreLLM-public">GitHub</a>
    </div>
    <div class="claim-banner">Execution mode: <code>realistic-stress</code>, not calibrated transaction-cost prediction. Default results use shared stress assumptions; calibrated claims require quote/order-book/fill provenance.</div>
  </div>
  {provenance_section}
  {claim_status_section}
  {measured_section}
  {quickstart}
  {classical}
  {classical_aggregate}
  {quality}
  {calibration}
  {risk_gate_section}
  {crisis}
  {true_feedback}
  {execution_section}
  {intraday}
  {audit_section}
  {representation}
  <section>
    <h2>Limitations</h2>
    <p class="note">This page is a benchmark and audit artifact, not financial advice or a live-trading guarantee. First-run reproduction uses tracked artifacts, and public policy rows use redacted or normalized labels. Raw provider prompts, responses, credentials, and caches are not shipped.</p>
  </section>
</main>
</html>
"""


def _section(title: str, lead: str, body: str) -> str:
    return f"<section><h2>{html.escape(title)}</h2><p class=\"section-lead\">{html.escape(lead)}</p>{body}</section>"


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = "\n".join("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _provenance_rows() -> list[list[str]]:
    return [
        ["Software release", RELEASE_TAG],
        ["Benchmark lineage", f"{BENCHMARK_VERSION} snapshot"],
        ["Benchmark card source", "`docs/results/` tracked snapshots plus first-run outputs"],
        [
            "Reproduction command",
            "`python -m pip install -e \".[dev]\"`; `python scripts/run_showcase.py`; `python scripts/build_benchmark_page.py`",
        ],
        ["Data", "tracked synthetic / timestamp-masked / redacted artifacts under `docs/results/`"],
        ["Live model calls", "not required for first-run reproduction"],
        ["Raw prompt/response caches", "not included"],
        ["Intended use", "agent reliability and audit research, not trading advice"],
    ]


def _claim_status_rows() -> list[list[str]]:
    return [
        [
            "Execution mode",
            "`stress-only` by default",
            "Default rows are stress-simulator evidence, not calibrated transaction-cost prediction.",
        ],
        [
            "Calibration evidence",
            "`quote-calibrated` sample rows",
            "Fixture and public Binance samples show calibration plumbing; broader venue claims need external reports.",
        ],
        [
            "Provider rows",
            "`cached-provider` / `redacted-prompt`",
            "Useful reliability probes; not enough for strong model-skill claims without independent repetition.",
        ],
        [
            "Baselines",
            "`deterministic-baseline`",
            "Classical baselines are main anchors, not appendix rows.",
        ],
        [
            "Reproduction",
            "`fresh-environment` CI passing",
            "CI installs `tradearena-benchmark==0.2.0`, generates artifacts, hashes a run, and replays a step.",
        ],
        [
            "External validation",
            "open: macOS, Ubuntu, Colab/Binder, baseline, calibration, claim review",
            "Independent reports are requested in issues #43, #44, #45, #46, #47, and #48.",
        ],
    ]


def _legacy_markdown_alias() -> str:
    return "\n".join(
        [
            "# TradeArena v0.1 Benchmark Card",
            "",
            "The maintained benchmark card is now `docs/results/benchmark_v0_2.md`.",
            "The v0.1 path is kept as a compatibility pointer for older links.",
            "",
            "Open: [`benchmark_v0_2.md`](benchmark_v0_2.md).",
            "",
        ]
    )


def _legacy_html_alias() -> str:
    return """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=benchmark-v0.2.html">
<title>TradeArena Benchmark Card Moved</title>
<body>
<p>The benchmark card moved to <a href="benchmark-v0.2.html">benchmark-v0.2.html</a>.</p>
</body>
</html>
"""


def _mean(rows: list[dict[str, str]], field: str) -> float:
    return statistics.fmean(float(row[field]) for row in rows)


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def _bps(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f} bps"


def _yes_no(value: object) -> str:
    return "yes" if str(value).strip().lower() in {"true", "yes", "1"} else "no"


def _policy_label(model: str) -> str:
    return POLICY_LABELS.get(model, "frontier-policy (redacted)")


def _wrap(text: str) -> str:
    return textwrap.fill(text, width=88)


def _pretty_case(case: str) -> str:
    text = case.replace("intraday_50_", "").replace("_risk_aware", "").replace("_", " ")
    replacements = {
        "buy and hold": "Buy and Hold",
        "deterministic": "Deterministic Risk-Aware",
        "markowitz mvo": "Markowitz MVO",
        "low liquidity stress": "Low-Liquidity Stress",
        "latency stress": "Latency Stress",
        "llm gpt 5 5": "Frontier Policy A (redacted)",
        "llm gemini 3 1 pro": "Frontier Policy C (redacted)",
    }
    for needle, label in replacements.items():
        if text.startswith(needle):
            return label
    return text.title()


if __name__ == "__main__":
    raise SystemExit(main())
