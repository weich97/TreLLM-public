from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

from tradearena.core.reproducibility import hash_trajectory_file
from tradearena.core.serialization import to_jsonable, write_json
from tradearena.evaluation import BenchmarkCase, BenchmarkRunner
from tradearena.evaluation.submissions import (
    build_registry_rows,
    validate_submission_file,
    write_registry_html,
    write_registry_markdown,
)
from tradearena.evaluation.trace_export import export_trajectory_to_trace_json
from tradearena.experiments import PaperExperimentConfig, run_paper_experiment
from tradearena.factory import build_default_system, default_registry
from tradearena.tools import (
    broker_handoff_artifact_hash,
    run_live_session_cli,
    validate_broker_adapter_capability_file,
    validate_broker_approval_artifact_file,
    validate_broker_approval_request_binding,
    validate_broker_handoff_artifact_file,
    validate_broker_response_artifact_file,
    validate_live_readiness_preflight_bundle_file,
    validate_operator_runbook_artifact_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TreLLM experiments and TradeArena leaderboard benchmark cases.")
    parser.add_argument(
        "--benchmark",
        default="tradearena-core",
        choices=["tradearena-core", "momentum-vs-buyhold", "llm-smoke"],
        help="Benchmark suite. The default is a deterministic no-key smoke test; llm-smoke runs one live/cache-backed LLM analyst case.",
    )
    parser.add_argument("--symbols", default="SYN,ALT", help="Comma-separated symbols for synthetic benchmark.")
    parser.add_argument("--periods", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--analysts",
        default="momentum,macro-news",
        help="Comma-separated analyst plugins for non-paper runs. Use deepseek-llm, poe-llm, or ollama-llm for live/cache-backed LLM analyst calls.",
    )
    parser.add_argument(
        "--execution",
        default="realistic",
        choices=["realistic", "ideal", "calibrated", "quote-replay", "level2-replay", "fill-replay"],
    )
    parser.add_argument("--execution-calibration-profile-id", default="", help="Identifier for externally calibrated execution parameters.")
    parser.add_argument("--execution-replay-fills", default="", help="Private/licensed fill CSV for --execution fill-replay.")
    parser.add_argument(
        "--spread-bps",
        type=float,
        default=0.0,
        help="Full bid-ask spread in basis points for realistic execution; market orders cross half the spread.",
    )
    parser.add_argument("--risk", default="max-position", choices=["max-position", "none"])
    parser.add_argument("--data-source", default="synthetic", choices=["synthetic", "csv"], help="Data source for non-paper benchmarks.")
    parser.add_argument("--output", default="", help="Optional JSON trajectory output path.")
    parser.add_argument("--paper-output", default="", help="Run the paper-grade experiment suite and write tables/charts/artifacts to this directory.")
    parser.add_argument("--paper-seeds", default="3,7,11", help="Comma-separated seeds for --paper-output.")
    parser.add_argument("--no-stress", action="store_true", help="Skip cost/liquidity/latency stress tests in --paper-output.")
    parser.add_argument("--no-extended", action="store_true", help="Skip extended paper ablations in --paper-output.")
    parser.add_argument("--no-real-data", action="store_true", help="Skip historical Yahoo Finance experiments in --paper-output.")
    parser.add_argument("--real-data-dir", default="data/real/yahoo_daily_2021_2026", help="Directory containing normalized historical OHLCV CSV files.")
    parser.add_argument("--real-symbols", default="GSPC,BTC-USD,ETH-USD", help="Comma-separated symbols for historical CSV experiments.")
    parser.add_argument("--real-frequency", default="weekly", choices=["daily", "weekly"], help="Decision frequency for historical CSV experiments.")
    parser.add_argument("--real-start", default="", help="Optional start date for --data-source csv benchmarks.")
    parser.add_argument("--real-end", default="", help="Optional end date for --data-source csv benchmarks.")
    parser.add_argument("--real-max-periods", type=int, default=0, help="Optional max periods for --data-source csv benchmarks.")
    parser.add_argument("--no-llm", action="store_true", help="Skip direct-provider LLM analyst sanity checks in --paper-output.")
    parser.add_argument("--llm-model", default="deepseek-v4-flash", help="Direct-provider model for LLM analyst sanity checks.")
    parser.add_argument("--llm-models", default="deepseek-v4-flash,deepseek-v4-pro", help="Comma-separated direct-provider models for LLM comparison sanity checks.")
    parser.add_argument("--no-model-matrix", action="store_true", help="Skip Poe-mediated frontier model matrix risk-adaptation experiments.")
    parser.add_argument("--model-matrix-models", default="gpt-5.5,gemini-3.1-pro,kimi-k2.5,glm-5,claude-opus-4.7", help="Comma-separated Poe model/cache names for frontier model matrix experiments.")
    parser.add_argument("--llm-cache", default="data/llm_cache/deepseek_analyst.jsonl", help="JSONL cache for LLM prompts and responses.")
    parser.add_argument("--llm-output-mode", default="rationale", choices=["rationale", "weights_only"], help="LLM response mode for non-paper llm-smoke runs.")
    parser.add_argument("--llm-risk-feedback-mode", default="true", choices=["true", "placebo", "contrarian"], help="Risk-feedback mode for non-paper LLM analyst runs.")
    parser.add_argument("--no-llm-risk-feedback", action="store_true", help="Hide risk feedback from non-paper LLM analyst prompts.")
    parser.add_argument("--llm-periods", type=int, default=52, help="Most recent historical periods to use for LLM experiments.")
    parser.add_argument("--no-statistical", action="store_true", help="Skip 30-seed statistical robustness tables in --paper-output.")
    parser.add_argument("--statistical-seeds", default="1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30", help="Comma-separated seeds for statistical robustness tables.")
    parser.add_argument("--no-synthetic-market-stress", action="store_true", help="Skip heterogeneous synthetic parallel-market stress tests in --paper-output.")
    parser.add_argument("--synthetic-stress-markets", type=int, default=120, help="Number of heterogeneous synthetic parallel markets for stress testing.")
    parser.add_argument("--no-rolling-windows", action="store_true", help="Skip historical rolling-window robustness tables in --paper-output.")
    parser.add_argument("--no-representation-analysis", action="store_true", help="Skip LLM plan/reflect embedding drift analysis in --paper-output.")
    parser.add_argument("--no-hallucination-analysis", action="store_true", help="Skip LLM hallucination proxy versus risk audit analysis in --paper-output.")
    parser.add_argument("--hallucination-annotation-path", default="data/annotations/hallucination_gold.csv", help="Optional CSV with blind human labels for hallucination-proxy calibration.")
    parser.add_argument("--no-memory-learning", action="store_true", help="Skip LLM memory-learning curve analysis in --paper-output.")
    parser.add_argument("--no-intraday-complex", action="store_true", help="Skip 50-stock 1h intraday portfolio complexity tables in --paper-output.")
    parser.add_argument("--intraday-llm-probe", action="store_true", help="Include the expensive 51-stock LLM intraday probe.")
    parser.add_argument("--no-risk-feedback-ablation", action="store_true", help="Skip risk-feedback on/off LLM intent evolution ablation.")
    parser.add_argument("--no-cot-free-ablation", action="store_true", help="Skip CoT-free target-weight ablation for cached frontier Poe models.")
    parser.add_argument("--no-noise-injection", action="store_true", help="Skip representation-signature robustness under noisy OHLCV perturbations.")
    parser.add_argument("--no-contrarian-audit", action="store_true", help="Skip contrarian false-risk-report trust-calibration experiment.")
    parser.add_argument("--intraday-data-dir", default="data/real/yahoo_intraday_1h_50", help="Directory containing 1h intraday Yahoo Finance CSV files.")
    parser.add_argument("--intraday-periods", type=int, default=40, help="Most recent hourly bars for the 50-stock intraday LLM experiment.")
    parser.add_argument("--intraday-llm-steps", type=int, default=8, help="Hourly decisions for the expensive 51-stock LLM intraday probe; set to 40 for the full-week version.")
    parser.add_argument("--intraday-llm-model", default="deepseek-v4-pro", help="Direct-provider model for the 50-stock intraday experiment.")
    parser.add_argument("--intraday-llm-models", default="", help="Comma-separated model names for multiple intraday LLM probes.")
    parser.add_argument("--intraday-llm-provider", default="deepseek", choices=["deepseek", "poe"], help="Provider adapter for the intraday LLM probe.")
    parser.add_argument("--list-plugins", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {
        "validate-submission",
        "validate-broker-handoff",
        "validate-broker-approval",
        "validate-broker-approval-binding",
        "validate-broker-capability",
        "validate-broker-response",
        "validate-live-readiness",
        "validate-operator-runbook",
        "live-session",
        "build-registry",
        "hash-broker-handoff",
        "hash-run",
        "new-plugin",
        "replay",
        "export-trace",
    }:
        return _run_utility_command(argv)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_plugins:
        registry = default_registry()
        for category in registry.categories():
            print(f"{category}: {', '.join(registry.names(category))}")
        return 0

    symbols = tuple(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip())
    analyst_names = _analyst_names_for_args(args)
    benchmark_data_kwargs = {
        "data_source": args.data_source,
        "real_data_dir": args.real_data_dir,
        "real_data_frequency": args.real_frequency,
        "real_data_start": args.real_start or None,
        "real_data_end": args.real_end or None,
        "real_data_max_periods": args.real_max_periods or None,
    }
    if args.paper_output:
        seeds = tuple(int(seed.strip()) for seed in args.paper_seeds.split(",") if seed.strip())
        statistical_seeds = tuple(int(seed.strip()) for seed in args.statistical_seeds.split(",") if seed.strip())
        llm_models = tuple(model.strip() for model in args.llm_models.split(",") if model.strip())
        model_matrix_models = tuple(model.strip() for model in args.model_matrix_models.split(",") if model.strip())
        intraday_llm_models = tuple(model.strip() for model in args.intraday_llm_models.split(",") if model.strip())
        result = run_paper_experiment(
            PaperExperimentConfig(
                output_dir=args.paper_output,
                symbols=symbols,
                periods=args.periods,
                seeds=seeds,
                include_stress=not args.no_stress,
                include_extended=not args.no_extended,
                include_real_data=not args.no_real_data,
                real_data_dir=args.real_data_dir,
                real_symbols=tuple(symbol.strip() for symbol in args.real_symbols.split(",") if symbol.strip()),
                real_data_frequency=args.real_frequency,
                include_llm=not args.no_llm,
                llm_model=args.llm_model,
                llm_models=llm_models or (args.llm_model,),
                include_model_matrix=not args.no_model_matrix,
                model_matrix_models=model_matrix_models,
                llm_cache_path=args.llm_cache,
                llm_periods=args.llm_periods,
                include_statistical=not args.no_statistical,
                statistical_seeds=statistical_seeds,
                include_synthetic_market_stress=not args.no_synthetic_market_stress,
                synthetic_stress_markets=args.synthetic_stress_markets,
                include_rolling_windows=not args.no_rolling_windows,
                include_representation_analysis=not args.no_representation_analysis,
                include_hallucination_analysis=not args.no_hallucination_analysis,
                hallucination_annotation_path=args.hallucination_annotation_path,
                include_memory_learning=not args.no_memory_learning,
                include_intraday_complex=not args.no_intraday_complex,
                include_intraday_llm_probe=args.intraday_llm_probe,
                include_risk_feedback_ablation=not args.no_risk_feedback_ablation,
                include_cot_free_ablation=not args.no_cot_free_ablation,
                include_noise_injection=not args.no_noise_injection,
                include_contrarian_audit=not args.no_contrarian_audit,
                intraday_data_dir=args.intraday_data_dir,
                intraday_max_periods=args.intraday_periods,
                intraday_llm_max_periods=args.intraday_llm_steps,
                intraday_llm_model=args.intraday_llm_model,
                intraday_llm_models=intraday_llm_models,
                intraday_llm_provider=args.intraday_llm_provider,
            )
        )
        print(json.dumps(to_jsonable(result["artifacts"]), indent=2))
        return 0

    execution_kwargs = {
        "execution_calibration_profile_id": args.execution_calibration_profile_id or None,
        "execution_replay_fills_path": args.execution_replay_fills or None,
    }

    cases = [
        BenchmarkCase(
            name="risk_aware_realistic_agent",
            build_system=lambda: build_default_system(
                name="risk_aware_realistic_agent",
                symbols=symbols,
                periods=args.periods,
                seed=args.seed,
                strategy_name="signal-weighted",
                risk_name=args.risk,
                execution_mode=args.execution,
                spread_bps=args.spread_bps,
                analyst_names=analyst_names,
                llm_model=args.llm_model,
                llm_cache_path=args.llm_cache,
                llm_use_risk_feedback=not args.no_llm_risk_feedback,
                llm_risk_feedback_mode=args.llm_risk_feedback_mode,
                llm_output_mode=args.llm_output_mode,
                **execution_kwargs,
                **benchmark_data_kwargs,
            ),
            description="Deterministic or configured analyst stack with configurable risk and execution stress.",
        ),
        BenchmarkCase(
            name="buy_and_hold_realistic",
            build_system=lambda: build_default_system(
                name="buy_and_hold_realistic",
                symbols=symbols,
                periods=args.periods,
                seed=args.seed,
                strategy_name="buy-and-hold",
                risk_name=args.risk,
                execution_mode=args.execution,
                spread_bps=args.spread_bps,
                analyst_names=analyst_names,
                llm_model=args.llm_model,
                llm_cache_path=args.llm_cache,
                llm_use_risk_feedback=not args.no_llm_risk_feedback,
                llm_risk_feedback_mode=args.llm_risk_feedback_mode,
                llm_output_mode=args.llm_output_mode,
                **execution_kwargs,
                **benchmark_data_kwargs,
            ),
            description="Equal-weight buy-and-hold baseline.",
        ),
        BenchmarkCase(
            name="ideal_execution_ablation",
            build_system=lambda: build_default_system(
                name="ideal_execution_ablation",
                symbols=symbols,
                periods=args.periods,
                seed=args.seed,
                strategy_name="signal-weighted",
                risk_name=args.risk,
                execution_mode="ideal",
                spread_bps=0.0,
                analyst_names=analyst_names,
                llm_model=args.llm_model,
                llm_cache_path=args.llm_cache,
                llm_use_risk_feedback=not args.no_llm_risk_feedback,
                llm_risk_feedback_mode=args.llm_risk_feedback_mode,
                llm_output_mode=args.llm_output_mode,
                **execution_kwargs,
                **benchmark_data_kwargs,
            ),
            description="Same agent under idealized execution for cost/realism ablation.",
        ),
        BenchmarkCase(
            name="no_risk_ablation",
            build_system=lambda: build_default_system(
                name="no_risk_ablation",
                symbols=symbols,
                periods=args.periods,
                seed=args.seed,
                strategy_name="signal-weighted",
                risk_name="none",
                execution_mode=args.execution,
                spread_bps=args.spread_bps,
                analyst_names=analyst_names,
                llm_model=args.llm_model,
                llm_cache_path=args.llm_cache,
                llm_use_risk_feedback=not args.no_llm_risk_feedback,
                llm_risk_feedback_mode=args.llm_risk_feedback_mode,
                llm_output_mode=args.llm_output_mode,
                **execution_kwargs,
                **benchmark_data_kwargs,
            ),
            description="Same agent with the risk gate disabled.",
        ),
    ]
    if args.benchmark == "momentum-vs-buyhold":
        cases = cases[:2]
    elif args.benchmark == "llm-smoke":
        cases = [
            BenchmarkCase(
                name="llm_smoke_realistic_agent",
                build_system=lambda: build_default_system(
                    name="llm_smoke_realistic_agent",
                    symbols=symbols,
                    periods=args.periods,
                    seed=args.seed,
                    strategy_name="signal-weighted",
                    risk_name=args.risk,
                    execution_mode=args.execution,
                    spread_bps=args.spread_bps,
                    analyst_names=analyst_names,
                    llm_model=args.llm_model,
                    llm_cache_path=args.llm_cache,
                    llm_use_risk_feedback=not args.no_llm_risk_feedback,
                    llm_risk_feedback_mode=args.llm_risk_feedback_mode,
                    llm_output_mode=args.llm_output_mode,
                    **execution_kwargs,
                    **benchmark_data_kwargs,
                ),
                description="Single live/cache-backed LLM analyst smoke test.",
            )
        ]
    results = BenchmarkRunner(cases=cases).run()
    print(json.dumps(to_jsonable(results), indent=2))

    if args.output:
        trajectories = {}
        for case in cases:
            trajectory, metrics = case.build_system().run()
            trajectories[case.name] = {"trajectory": trajectory.to_dict(), "metrics": metrics}
        write_json(Path(args.output), trajectories)

    return 0


def _analyst_names_for_args(args: argparse.Namespace) -> tuple[str, ...]:
    names = tuple(name.strip() for name in args.analysts.split(",") if name.strip())
    if args.benchmark == "llm-smoke" and not any(_is_llm_analyst(name) for name in names):
        return ("deepseek-llm",)
    return names or ("momentum", "macro-news")


def _is_llm_analyst(name: str) -> bool:
    return name in {"deepseek-llm", "chat-completions-llm", "poe-llm", "ollama-llm"}


def _run_utility_command(argv: list[str]) -> int:
    command = argv[0]
    if command == "validate-submission":
        parser = argparse.ArgumentParser(description="Validate a redacted TradeArena benchmark submission.")
        parser.add_argument("submission")
        parser.add_argument("--no-verify-hash", action="store_true")
        args = parser.parse_args(argv[1:])
        _, errors = validate_submission_file(args.submission, verify_hash=not args.no_verify_hash)
        if errors:
            print(f"Invalid benchmark submission: {args.submission}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid benchmark submission: {args.submission}")
        return 0

    if command == "validate-broker-response":
        parser = argparse.ArgumentParser(description="Validate a TreLLM broker response artifact.")
        parser.add_argument("artifact")
        args = parser.parse_args(argv[1:])
        _, errors = validate_broker_response_artifact_file(args.artifact)
        if errors:
            print(f"Invalid broker response artifact: {args.artifact}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid broker response artifact: {args.artifact}")
        return 0

    if command == "validate-broker-capability":
        parser = argparse.ArgumentParser(description="Validate a TreLLM broker adapter capability manifest.")
        parser.add_argument("artifact")
        args = parser.parse_args(argv[1:])
        _, errors = validate_broker_adapter_capability_file(args.artifact)
        if errors:
            print(f"Invalid broker adapter capability manifest: {args.artifact}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid broker adapter capability manifest: {args.artifact}")
        return 0

    if command == "validate-live-readiness":
        parser = argparse.ArgumentParser(description="Validate a TreLLM live-readiness preflight bundle.")
        parser.add_argument("bundle")
        parser.add_argument(
            "--now",
            default=None,
            help="Optional ISO timestamp with timezone used to reject expired approval artifacts.",
        )
        args = parser.parse_args(argv[1:])
        summary, errors = validate_live_readiness_preflight_bundle_file(args.bundle, now=args.now)
        if errors:
            print(f"Invalid live-readiness preflight bundle: {args.bundle}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid live-readiness preflight bundle: {args.bundle}")
        print(f"  components={len(summary.get('components', {}))}")
        return 0

    if command == "live-session":
        return run_live_session_cli(argv[1:])

    if command == "validate-operator-runbook":
        parser = argparse.ArgumentParser(description="Validate a TreLLM operator runbook artifact.")
        parser.add_argument("artifact")
        args = parser.parse_args(argv[1:])
        _, errors = validate_operator_runbook_artifact_file(args.artifact)
        if errors:
            print(f"Invalid operator runbook artifact: {args.artifact}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid operator runbook artifact: {args.artifact}")
        return 0

    if command == "validate-broker-handoff":
        parser = argparse.ArgumentParser(description="Validate a TreLLM broker handoff artifact.")
        parser.add_argument("artifact")
        args = parser.parse_args(argv[1:])
        _, errors = validate_broker_handoff_artifact_file(args.artifact)
        if errors:
            print(f"Invalid broker handoff artifact: {args.artifact}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid broker handoff artifact: {args.artifact}")
        return 0

    if command == "validate-broker-approval":
        parser = argparse.ArgumentParser(description="Validate a TreLLM broker approval artifact.")
        parser.add_argument("artifact")
        parser.add_argument(
            "--now",
            default=None,
            help="Optional ISO timestamp with timezone used to reject expired approval artifacts.",
        )
        args = parser.parse_args(argv[1:])
        _, errors = validate_broker_approval_artifact_file(args.artifact, now=args.now)
        if errors:
            print(f"Invalid broker approval artifact: {args.artifact}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid broker approval artifact: {args.artifact}")
        return 0

    if command == "validate-broker-approval-binding":
        parser = argparse.ArgumentParser(description="Validate that a TreLLM broker approval binds to a handoff artifact.")
        parser.add_argument("approval_artifact")
        parser.add_argument("request_artifact")
        parser.add_argument(
            "--now",
            default=None,
            help="Optional ISO timestamp with timezone used to reject expired approval artifacts.",
        )
        args = parser.parse_args(argv[1:])
        approval, approval_errors = validate_broker_approval_artifact_file(args.approval_artifact, now=args.now)
        errors = approval_errors or validate_broker_approval_request_binding(approval, args.request_artifact, now=args.now)
        if errors:
            print(f"Invalid broker approval binding: {args.approval_artifact} -> {args.request_artifact}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"Valid broker approval binding: {args.approval_artifact} -> {args.request_artifact}")
        return 0

    if command == "hash-broker-handoff":
        parser = argparse.ArgumentParser(description="Validate and hash a TreLLM broker handoff artifact.")
        parser.add_argument("artifact")
        args = parser.parse_args(argv[1:])
        _, errors = validate_broker_handoff_artifact_file(args.artifact)
        if errors:
            print(f"Invalid broker handoff artifact: {args.artifact}")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(broker_handoff_artifact_hash(args.artifact))
        return 0

    if command == "build-registry":
        parser = argparse.ArgumentParser(description="Build the TradeArena leaderboard registry from redacted submissions.")
        parser.add_argument("input")
        parser.add_argument("--output", default="docs/results/community_registry.md")
        parser.add_argument("--csv-output", default="docs/results/community_registry.csv")
        parser.add_argument("--html-output", default="docs/results/community_registry.html")
        args = parser.parse_args(argv[1:])
        rows, errors = build_registry_rows(args.input)
        if errors:
            print("Benchmark registry build failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        write_registry_markdown(rows, args.output)
        _write_registry_csv(rows, args.csv_output)
        _write_registry_html(rows, args.html_output)
        print(f"Wrote {args.output}")
        print(f"Wrote {args.csv_output}")
        print(f"Wrote {args.html_output}")
        print(f"Accepted submissions: {len(rows)}")
        return 0

    if command == "hash-run":
        parser = argparse.ArgumentParser(description="Compute a reproducibility hash for a TreLLM trajectory JSON.")
        parser.add_argument("trajectory")
        args = parser.parse_args(argv[1:])
        try:
            print(json.dumps(hash_trajectory_file(args.trajectory), indent=2))
        except ValueError as exc:
            print(str(exc))
            return 1
        return 0

    if command == "replay":
        parser = argparse.ArgumentParser(description="Replay one step from a TreLLM trajectory JSON.")
        parser.add_argument("trajectory", help="Trajectory JSON, or a multi-case JSON written by --output.")
        parser.add_argument("--step", type=int, default=1, help="1-based trajectory step to render.")
        parser.add_argument("--case", default="", help="Case name when replaying a multi-case --output file.")
        parser.add_argument("--json", action="store_true", help="Emit a compact machine-readable step summary.")
        args = parser.parse_args(argv[1:])
        try:
            payload = _load_replay_payload(Path(args.trajectory), args.case)
            summary = _replay_step_summary(payload, args.step)
        except SystemExit as exc:
            if exc.code:
                print(exc.code)
                return 1
            return 0
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(_format_replay_summary(summary))
        return 0

    if command == "export-trace":
        parser = argparse.ArgumentParser(description="Export a TreLLM trajectory to a local trace JSON.")
        parser.add_argument("trajectory", help="Trajectory JSON, or a multi-case JSON written by --output.")
        parser.add_argument("--case", default="", help="Case name when exporting a multi-case --output file.")
        parser.add_argument("--format", default="opentelemetry-json", choices=["opentelemetry-json"])
        parser.add_argument("--output", required=True, help="Trace JSON output path.")
        args = parser.parse_args(argv[1:])
        export_trajectory_to_trace_json(args.trajectory, args.output, case_name=args.case)
        print(f"Wrote {args.output}")
        return 0

    if command == "new-plugin":
        parser = argparse.ArgumentParser(description="Create a local TreLLM plugin skeleton.")
        parser.add_argument("--type", required=True, choices=["data", "analyst", "strategy", "risk", "execution", "simulator", "memory", "evaluator"])
        parser.add_argument("--name", required=True, help="Human-readable plugin name, for example max-drawdown-guard.")
        parser.add_argument("--output", default="plugins/local", help="Directory where the plugin folder should be created.")
        parser.add_argument("--force", action="store_true", help="Overwrite an existing scaffold directory.")
        args = parser.parse_args(argv[1:])
        plugin_dir = _write_plugin_scaffold(
            plugin_type=args.type,
            name=args.name,
            output_dir=Path(args.output),
            force=args.force,
        )
        print(f"Wrote plugin scaffold: {plugin_dir}")
        print(f"Next: python -m pytest {plugin_dir / ('test_' + _module_name(args.name) + '.py')} -q")
        return 0

    raise AssertionError(f"Unhandled utility command: {command}")


def _write_registry_csv(rows: list[dict[str, object]], path: str | Path) -> None:
    fieldnames = list(rows[0]) if rows else ["scenario_id"]
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_registry_html(rows: list[dict[str, object]], path: str | Path) -> None:
    write_registry_html(rows, path)


def _write_plugin_scaffold(plugin_type: str, name: str, output_dir: Path, *, force: bool = False) -> Path:
    module_name = _module_name(name)
    class_name = _class_name(name)
    plugin_dir = output_dir / module_name
    if plugin_dir.exists() and not force:
        raise SystemExit(f"Plugin scaffold already exists: {plugin_dir}. Use --force to overwrite.")
    plugin_dir.mkdir(parents=True, exist_ok=True)

    (plugin_dir / f"{module_name}.py").write_text(
        _plugin_template(plugin_type, name=name, module_name=module_name, class_name=class_name),
        encoding="utf-8",
    )
    (plugin_dir / f"test_{module_name}.py").write_text(
        _plugin_test_template(module_name=module_name, class_name=class_name),
        encoding="utf-8",
    )
    (plugin_dir / "README.md").write_text(
        _plugin_readme_template(plugin_type=plugin_type, name=name, module_name=module_name, class_name=class_name),
        encoding="utf-8",
    )
    return plugin_dir


def _module_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    if not normalized:
        raise SystemExit("Plugin name must contain at least one alphanumeric character.")
    if normalized[0].isdigit():
        normalized = f"plugin_{normalized}"
    return normalized


def _class_name(name: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", name.strip())
    class_name = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not class_name:
        raise SystemExit("Plugin name must contain at least one alphanumeric character.")
    if class_name[0].isdigit():
        class_name = f"Plugin{class_name}"
    return class_name


def _plugin_template(plugin_type: str, *, name: str, module_name: str, class_name: str) -> str:
    if plugin_type == "risk":
        return f'''from __future__ import annotations

from dataclasses import dataclass

from tradearena.agents.risk import MaxPositionRiskManager
from tradearena.core.domain import Decision, MarketSnapshot, PortfolioState


@dataclass
class {class_name}(MaxPositionRiskManager):
    """Example risk plugin scaffold generated by ``tradearena new-plugin``."""

    name: str = "{name}"
    max_abs_weight: float = 0.25

    def approve(
        self,
        snapshot: MarketSnapshot,
        decisions: list[Decision],
        portfolio: PortfolioState,
        memory: object,
    ) -> list[Decision]:
        """Apply the base risk lifecycle, then add plugin-specific checks."""
        approved = super().approve(snapshot, decisions, portfolio, memory)
        return approved
'''
    return f'''from __future__ import annotations


class {class_name}:
    """{plugin_type} plugin scaffold generated by ``tradearena new-plugin``."""

    name = "{name}"

    def describe(self) -> dict[str, str]:
        return {{
            "type": "{plugin_type}",
            "module": "{module_name}",
            "name": self.name,
        }}
'''


def _plugin_test_template(*, module_name: str, class_name: str) -> str:
    return f'''from __future__ import annotations

import importlib.util
from pathlib import Path


def test_{module_name}_imports() -> None:
    path = Path(__file__).with_name("{module_name}.py")
    spec = importlib.util.spec_from_file_location("{module_name}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert getattr(module, "{class_name}")().name
'''


def _plugin_readme_template(*, plugin_type: str, name: str, module_name: str, class_name: str) -> str:
    return f'''# {name}

Type: `{plugin_type}`

Generated by:

```bash
tradearena new-plugin --type {plugin_type} --name {name}
```

## Files

- `{module_name}.py`: plugin implementation
- `test_{module_name}.py`: import smoke test

## Validate

```bash
python -m pytest test_{module_name}.py -q
```

## Next Steps

Implement the protocol for `{class_name}` and add a small deterministic fixture
before submitting a PR. Keep live API keys, raw provider text, broker files, and
private holdings out of Git.
'''


def _load_replay_payload(path: Path, case_name: str = "") -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Trajectory not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit("Trajectory file must contain valid JSON") from exc
    if isinstance(payload, dict) and isinstance(payload.get("steps"), list):
        return payload
    if not isinstance(payload, dict):
        raise SystemExit(f"Unsupported replay file: {path}")

    cases = {
        name: value
        for name, value in payload.items()
        if isinstance(value, dict) and isinstance(value.get("trajectory"), dict)
    }
    if not cases:
        raise SystemExit(f"Unsupported replay file: {path}. Expected a trajectory with steps or a multi-case output.")
    if case_name:
        if case_name not in cases:
            available = ", ".join(sorted(cases))
            raise SystemExit(f"Case not found: {case_name}. Available cases: {available}")
        return cases[case_name]["trajectory"]
    if len(cases) == 1:
        return next(iter(cases.values()))["trajectory"]
    available = ", ".join(sorted(cases))
    raise SystemExit(f"Multiple cases found. Pass --case with one of: {available}")


def _replay_step_summary(trajectory: dict[str, Any], step_number: int) -> dict[str, Any]:
    steps = trajectory.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise SystemExit("Trajectory has no replayable steps.")
    if step_number < 1 or step_number > len(steps):
        raise SystemExit(f"--step must be between 1 and {len(steps)}; got {step_number}.")
    step = steps[step_number - 1]
    risk = step.get("risk_report", {}) if isinstance(step.get("risk_report", {}), dict) else {}
    execution = step.get("execution_report", {}) if isinstance(step.get("execution_report", {}), dict) else {}
    portfolio = step.get("portfolio", {}) if isinstance(step.get("portfolio", {}), dict) else {}
    decisions = step.get("decisions", []) if isinstance(step.get("decisions", []), list) else []
    approved = step.get("approved_decisions", []) if isinstance(step.get("approved_decisions", []), list) else []
    fills = step.get("fills", []) if isinstance(step.get("fills", []), list) else []
    reproducibility = (
        step.get("reproducibility_state", {})
        if isinstance(step.get("reproducibility_state", {}), dict)
        else {}
    )
    return {
        "experiment": trajectory.get("experiment_name", ""),
        "seed": trajectory.get("seed", ""),
        "step": step_number,
        "step_count": len(steps),
        "timestamp": step.get("timestamp", ""),
        "observation": _replay_observation_summary(step.get("observation", {})),
        "signals": _replay_signal_summary(step.get("signals", [])),
        "decisions": _replay_decision_summary(decisions, approved),
        "risk": {
            "phase": risk.get("phase", ""),
            "approved_count": risk.get("approved_count", 0),
            "blocked_count": risk.get("blocked_count", 0),
            "clipped_count": risk.get("clipped_count", 0),
            "checks": _replay_check_summary(risk.get("checks", [])),
        },
        "execution": {
            "orders": len(step.get("orders", []) or []),
            "fills": len(fills),
            "submitted_orders": execution.get("submitted_orders", 0),
            "filled_orders": execution.get("filled_orders", 0),
            "partial_fills": execution.get("partial_fills", 0),
            "pending_orders": execution.get("pending_orders", 0),
            "rejected_orders": execution.get("rejected_orders", 0),
            "total_commission": execution.get("total_commission", 0.0),
            "total_slippage": execution.get("total_slippage", 0.0),
            "average_latency_steps": execution.get("average_latency_steps", 0.0),
            "first_fill": fills[0] if fills else {},
        },
        "portfolio": {
            "cash": portfolio.get("cash", 0.0),
            "equity": portfolio.get("equity", 0.0),
            "positions": portfolio.get("positions", {}),
        },
        "memory_events": len(step.get("memory_events", []) or []),
        "reproducibility": {
            "prompt_version": reproducibility.get("prompt_version", ""),
            "model_version": reproducibility.get("model_version", ""),
            "memory_digest": reproducibility.get("memory_digest", ""),
            "random_seed": reproducibility.get("random_seed", ""),
        },
    }


def _replay_observation_summary(observation: object) -> dict[str, Any]:
    if not isinstance(observation, dict):
        return {"prices": {}, "news_count": 0, "macro_count": 0, "filings_count": 0, "alt_data_count": 0}
    return {
        "prices": observation.get("prices", {}),
        "news_count": observation.get("news_count", 0),
        "macro_count": observation.get("macro_count", 0),
        "filings_count": observation.get("filings_count", 0),
        "alt_data_count": observation.get("alt_data_count", 0),
    }


def _replay_signal_summary(signals: object, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(signals, list):
        return []
    rows = []
    for signal in signals[:limit]:
        if not isinstance(signal, dict):
            continue
        rows.append(
            {
                "symbol": signal.get("symbol", ""),
                "score": signal.get("score", 0.0),
                "confidence": signal.get("confidence", 0.0),
                "analyst": signal.get("metadata", {}).get("analyst", "") if isinstance(signal.get("metadata", {}), dict) else "",
                "rationale": signal.get("rationale", ""),
            }
        )
    return rows


def _replay_decision_summary(decisions: list[object], approved: list[object]) -> list[dict[str, Any]]:
    approved_by_symbol = {
        str(item.get("symbol", "")): item
        for item in approved
        if isinstance(item, dict)
    }
    rows = []
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        symbol = str(decision.get("symbol", ""))
        approved_decision = approved_by_symbol.get(symbol, {})
        target = _to_float(decision.get("target_weight"))
        approved_target = _to_float(approved_decision.get("target_weight", target)) if isinstance(approved_decision, dict) else target
        rows.append(
            {
                "symbol": symbol,
                "side": decision.get("side", ""),
                "target_weight": target,
                "approved_weight": approved_target,
                "delta": approved_target - target,
                "rationale": decision.get("rationale", ""),
            }
        )
    return rows


def _replay_check_summary(checks: object, limit: int = 6) -> list[dict[str, Any]]:
    if not isinstance(checks, list):
        return []
    rows = []
    for check in checks[:limit]:
        if not isinstance(check, dict):
            continue
        rows.append(
            {
                "name": check.get("name", ""),
                "passed": bool(check.get("passed", False)),
                "severity": check.get("severity", ""),
                "message": check.get("message", ""),
            }
        )
    return rows


def _format_replay_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"TreLLM Replay: {summary['experiment']} step {summary['step']} / {summary['step_count']}",
        f"timestamp: {summary['timestamp']}",
        "",
        "Observation",
        f"  prices: {_format_prices(summary['observation'].get('prices', {}))}",
        (
            f"  news={summary['observation'].get('news_count', 0)} "
            f"macro={summary['observation'].get('macro_count', 0)} "
            f"filings={summary['observation'].get('filings_count', 0)} "
            f"alt={summary['observation'].get('alt_data_count', 0)}"
        ),
        "",
        "Signals",
    ]
    for signal in summary["signals"]:
        lines.append(
            "  "
            + f"{signal['symbol']}: score={_to_float(signal['score']):+.3f}, "
            + f"confidence={_to_float(signal['confidence']):.3f}, analyst={signal['analyst'] or 'unknown'}"
        )
        lines.append(f"    {_shorten(signal['rationale'])}")
    if not summary["signals"]:
        lines.append("  none")

    lines.extend(["", "Intent -> Approved"])
    for decision in summary["decisions"]:
        lines.append(
            "  "
            + f"{decision['symbol']} {decision['side']}: "
            + f"{decision['target_weight']:.3f} -> {decision['approved_weight']:.3f} "
            + f"(delta {decision['delta']:+.3f})"
        )
        lines.append(f"    {_shorten(decision['rationale'])}")
    if not summary["decisions"]:
        lines.append("  none")

    lines.extend(
        [
            "",
            "Risk Gate",
            (
                f"  phase={summary['risk']['phase']} approved={summary['risk']['approved_count']} "
                f"clipped={summary['risk']['clipped_count']} blocked={summary['risk']['blocked_count']}"
            ),
        ]
    )
    for check in summary["risk"]["checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(f"  [{status}] {check['name']} ({check['severity']}): {_shorten(check['message'])}")

    first_fill = summary["execution"].get("first_fill", {})
    fill_line = ""
    if first_fill:
        fill_line = (
            f" first_fill={first_fill.get('side', '')} {first_fill.get('symbol', '')} "
            f"qty={_to_float(first_fill.get('quantity')):.2f} price={_to_float(first_fill.get('price')):.2f}"
        )
    lines.extend(
        [
            "",
            "Execution",
            (
                f"  orders={summary['execution']['orders']} fills={summary['execution']['fills']} "
                f"submitted={summary['execution']['submitted_orders']} filled={summary['execution']['filled_orders']} "
                f"pending={summary['execution']['pending_orders']} rejected={summary['execution']['rejected_orders']} "
                f"partial={summary['execution']['partial_fills']}"
            ),
            (
                f"  commission={_money(summary['execution']['total_commission'])} "
                f"slippage={_money(summary['execution']['total_slippage'])} "
                f"latency={_to_float(summary['execution']['average_latency_steps']):.2f} steps{fill_line}"
            ),
            "",
            "Portfolio",
            f"  equity={_money(summary['portfolio']['equity'])} cash={_money(summary['portfolio']['cash'])}",
            f"  positions: {_format_positions(summary['portfolio'].get('positions', {}))}",
            "",
            "Reproducibility",
            (
                f"  model={summary['reproducibility']['model_version']} "
                f"prompt={summary['reproducibility']['prompt_version']} "
                f"memory={summary['reproducibility']['memory_digest']} "
                f"seed={summary['reproducibility']['random_seed']}"
            ),
        ]
    )
    return "\n".join(lines)


def _format_prices(prices: object) -> str:
    if not isinstance(prices, dict) or not prices:
        return "none"
    return ", ".join(f"{symbol}={_to_float(price):.2f}" for symbol, price in list(prices.items())[:8])


def _format_positions(positions: object) -> str:
    if not isinstance(positions, dict) or not positions:
        return "flat"
    return ", ".join(f"{symbol}={_to_float(quantity):.4f}" for symbol, quantity in list(positions.items())[:8])


def _shorten(value: object, width: int = 140) -> str:
    return textwrap.shorten(str(value or ""), width=width, placeholder="...")


def _to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _money(value: object) -> str:
    return f"${_to_float(value):,.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
