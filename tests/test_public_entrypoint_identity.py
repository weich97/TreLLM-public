import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_github_templates_explain_trellm_and_tradearena_roles():
    required_snippets = {
        ".github/ISSUE_TEMPLATE/bug_report.yml": [
            "Report a reproducible TreLLM system or TradeArena leaderboard issue",
        ],
        ".github/ISSUE_TEMPLATE/research_extension.yml": [
            "Suggest an experiment that could strengthen the TreLLM system research or TradeArena leaderboard suite",
            "Paper, system, or leaderboard output",
        ],
        ".github/PULL_REQUEST_TEMPLATE.md": [
            "TreLLM system change",
            "TradeArena leaderboard or registry artifact update",
            "Live-ready contribution track:",
            "Broker capability manifest",
            "Broker adapter capability manifest validates with:",
            "Live-readiness preflight",
            "Live-readiness preflight bundle validates with:",
            "Default path cannot submit live orders",
            "Approval binding",
            "Paper-sandbox adapter",
            "Operator runbook",
        ],
        ".github/ISSUE_TEMPLATE/demo_or_adapter.yml": [
            "Live-ready contribution track",
            "Broker capability manifest",
            "Broker review export",
            "Approval binding",
            "Paper-sandbox adapter",
            "Reconciliation",
            "Operator runbook",
            "Live-readiness preflight",
            "Adapter or account mode",
            "offline_export",
            "paper_sandbox",
            "live_human_approved",
            "No default live orders",
        ],
        ".github/ISSUE_TEMPLATE/config.yml": [
            "Live-ready broker safety boundary",
            "docs/live_trading_readiness.md",
            "Check broker-review, paper-sandbox, and future live-approved contribution boundaries.",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

def test_package_docstring_uses_trellm_system_identity():
    import tradearena

    docstring = tradearena.__doc__ or ""

    assert "TreLLM: LLM-driven trading audit and control system" in docstring
    assert "TradeArena compatibility API" in docstring
    assert "TradeArena: pluggable AI trading agent research framework" not in docstring


def test_contributor_docs_keep_system_and_leaderboard_identity_separate():
    required_snippets = {
        "CONTRIBUTING.md": [
            "# Contributing to TreLLM",
            "TreLLM is designed around narrow interfaces.",
            "TradeArena leaderboard or benchmark artifacts should remain comparable, redacted, and reproducible.",
        ],
        "GOVERNANCE.md": [
            "TreLLM is maintained as an LLM-driven trading audit and live-readiness control system.",
            "TradeArena is the public leaderboard and benchmark-card surface inside TreLLM.",
        ],
        "SECURITY.md": [
            "TreLLM is an LLM-driven trading audit and live-readiness control system.",
            "TradeArena is the public leaderboard and benchmark-card surface inside TreLLM.",
            "It does not execute live trades by default",
            "Live execution is out of scope for the public TradeArena leaderboard path",
        ],
        "docs/contributor_roadmap.md": [
            "TreLLM grows best when contributions make financial AI agents easier to evaluate, audit, reproduce, control, or extend.",
            "These contributions move TreLLM from offline audit research toward human-gated, live-ready trading infrastructure.",
            "match one of the external contribution tracks",
            "These contributions strengthen the TradeArena leaderboard module and benchmark-card layer.",
        ],
        "docs/community_participation.md": [
            "TreLLM should not describe itself as community-backed until public, reviewable participation exists.",
            "TradeArena leaderboard row",
            'early-stage research prototype with a public TradeArena leaderboard module',
        ],
        "docs/community_milestones.md": [
            "Goal: make the first public TreLLM audit release easier to cite, reproduce, and review while keeping TradeArena benchmark rows comparable.",
            "New adapters: link the data, broker, or model interface you want TreLLM to support.",
        ],
        "docs/community_operations.md": [
            "We maintain TreLLM, an early-stage live-ready audit and control system for auditing",
            "TradeArena can package comparable benchmark manifests and leaderboard evidence",
        ],
        "docs/launch/discussion_seeds.md": [
            "We want community leaderboard submissions without exposing raw provider prompts or",
            "Reply with the fields you would be comfortable sharing in a public leaderboard row.",
        ],
        "docs/launch/issue_backlog.md": [
            "How should community leaderboard submissions redact provider prompts/responses?",
        ],
        "docs/community_tasks.md": [
            "## Broker And Live-Ready Tracks",
            "Each task should remain offline export, dry run, or paper sandbox by default.",
            "## Completed Live-Ready Capability Map",
            "Broker adapter capability manifest",
            "Live-readiness preflight consistency check",
            "Approval-binding edge-case coverage",
            "Paper-sandbox adapter skeleton",
        ],
        "docs/live_trading_readiness.md": [
            "Capability manifest, `submit_live=false`",
            "Stages 4 and 5 are not part of the public TradeArena leaderboard claim.",
            "a schema-valid broker adapter capability manifest declares supported modes",
            "a live-readiness preflight bundle validates the capability manifest",
            "Broker capability manifest",
            "Live-readiness preflight",
        ],
        "docs/broker_adapter_contract.md": [
            "Before a broker-facing adapter is reviewed, it should publish a capability manifest",
            "tradearena validate-broker-capability outputs/examples/broker_capability_manifest/capability_manifest.json",
            "tradearena validate-live-readiness outputs/examples/live_readiness_preflight/preflight_bundle.json",
            "validate_broker_adapter_capability",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    contributor_text = _normalized(_read_text("docs/contributor_roadmap.md"))
    assert "TradeArena is the public leaderboard and benchmark module inside that system" not in contributor_text
    assert "These contributions strengthen the TradeArena leaderboard and benchmark module." not in contributor_text

    contributing_text = _normalized(_read_text("CONTRIBUTING.md"))
    assert "TradeArena is designed around narrow interfaces." not in contributing_text

    governance_text = _normalized(_read_text("GOVERNANCE.md"))
    assert "TradeArena is maintained as an open benchmark, audit framework" not in governance_text
    assert "These contributions move TreLLM from benchmark research toward human-gated" not in contributor_text

    security_text = _normalized(_read_text("SECURITY.md"))
    assert "TradeArena is an audit, benchmark, and live-readiness framework." not in security_text
    assert "Live execution is out of scope for the public benchmark" not in security_text

    live_readiness_text = _normalized(_read_text("docs/live_trading_readiness.md"))
    assert "Stages 4 and 5 are not part of the public benchmark claim." not in live_readiness_text


def test_external_validation_task_tables_include_colab_binder_reproduction():
    required_snippets = {
        "README.md": [
            "Run the v0.2 reproduction pack on Colab/Binder",
            "https://github.com/weich97/TreLLM-public/issues/45",
        ],
        "docs/community_tasks.md": [
            "Run v0.2 reproduction pack on Colab/Binder",
            "https://github.com/weich97/TreLLM-public/issues/45",
        ],
        "docs/community_participation.md": [
            "Run the v0.2 reproduction pack on Colab/Binder",
            "https://github.com/weich97/TreLLM-public/issues/45",
        ],
        "docs/external_validation.md": [
            "Run v0.2 reproduction pack on Colab/Binder",
            "https://github.com/weich97/TreLLM-public/issues/45",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text


def test_community_task_tables_separate_open_and_completed_issue_links():
    text = _normalized(_read_text("docs/community_tasks.md"))

    required_open_issue_links = [
        "https://github.com/weich97/TreLLM-public/issues/43",
        "https://github.com/weich97/TreLLM-public/issues/44",
        "https://github.com/weich97/TreLLM-public/issues/45",
        "https://github.com/weich97/TreLLM-public/issues/46",
        "https://github.com/weich97/TreLLM-public/issues/47",
        "https://github.com/weich97/TreLLM-public/issues/48",
    ]
    for issue_link in required_open_issue_links:
        assert issue_link in text

    live_ready_section = text.split("## Broker And Live-Ready Tracks", 1)[1].split("## Completed Live-Ready Capability Map", 1)[0]
    completed_section = text.split("## Completed Live-Ready Capability Map", 1)[1].split("## Benchmark Flywheel", 1)[0]
    completed_issue_links = [
        "https://github.com/weich97/TreLLM-public/issues/57",
        "https://github.com/weich97/TreLLM-public/issues/58",
        "https://github.com/weich97/TreLLM-public/issues/59",
        "https://github.com/weich97/TreLLM-public/issues/60",
        "https://github.com/weich97/TreLLM-public/issues/61",
        "https://github.com/weich97/TreLLM-public/issues/62",
    ]
    for issue_link in completed_issue_links:
        assert issue_link not in live_ready_section
        assert issue_link in completed_section

    good_first_section = text.split("## Good First Issues", 1)[1].split("## Completed Good-First Fixture Map", 1)[0]
    completed_good_first_section = text.split("## Completed Good-First Fixture Map", 1)[1].split(
        "## Finance And Market Realism", 1
    )[0]
    anonymous_manifest_link = "https://github.com/weich97/TreLLM-public/issues/29"
    assert anonymous_manifest_link not in good_first_section
    assert anonymous_manifest_link in completed_good_first_section
    assert "https://github.com/weich97/TreLLM-public/issues/41" not in good_first_section
    assert "https://github.com/weich97/TreLLM-public/issues/41" in completed_good_first_section
    for snippet in [
        "examples/benchmark_submissions/anonymous_entry_redacted_submission.json",
        "test_anonymous_redacted_submission_validates_and_uses_entry_id_boundary",
        "docs/results/community_registry.html",
        "plugins/examples/sector_concentration_guard",
        "tests/test_plugin_examples.py",
    ]:
        assert snippet in completed_good_first_section

    active_task_sections = {
        "good_first": text.split("## Good First Issues", 1)[1].split("## Completed Good-First Fixture Map", 1)[0],
        "market_realism": text.split("## Finance And Market Realism", 1)[1].split(
            "## Completed Market Realism Map", 1
        )[0],
        "benchmark_flywheel": text.split("## Benchmark Flywheel", 1)[1].split(
            "## Completed Benchmark Flywheel Map", 1
        )[0],
        "observability": text.split("## Observability", 1)[1].split("## Completed Observability Map", 1)[0],
    }
    completed_maps = text.split("## Completed Good-First Fixture Map", 1)[1]
    closed_non_external_issue_links = [
        "https://github.com/weich97/TreLLM-public/issues/27",
        "https://github.com/weich97/TreLLM-public/issues/31",
        "https://github.com/weich97/TreLLM-public/issues/32",
        "https://github.com/weich97/TreLLM-public/issues/33",
        "https://github.com/weich97/TreLLM-public/issues/34",
        "https://github.com/weich97/TreLLM-public/issues/35",
        "https://github.com/weich97/TreLLM-public/issues/36",
        "https://github.com/weich97/TreLLM-public/issues/37",
        "https://github.com/weich97/TreLLM-public/issues/38",
        "https://github.com/weich97/TreLLM-public/issues/39",
        "https://github.com/weich97/TreLLM-public/issues/40",
        "https://github.com/weich97/TreLLM-public/issues/41",
    ]
    for issue_link in closed_non_external_issue_links:
        for active_section in active_task_sections.values():
            assert issue_link not in active_section
        assert issue_link in completed_maps
    for evidence_snippet in [
        "tests/test_sma_strategy.py",
        "examples/ashare_market_rules_demo.py",
        "examples/hk_market_rules_demo.py",
        "examples/crypto_microstructure_stress_demo.py",
        "examples/almgren_chriss_stress_demo.py",
        "examples/liquidity_halt_demo.py",
        "docs/results/community_registry.html",
        "tests/test_trace_export.py",
        "tests/test_observability_export.py",
        "tests/test_trace_schema_export.py",
        "tests/test_notebook_quickstart.py",
        "plugins/examples/sector_concentration_guard",
        "tests/test_plugin_examples.py",
    ]:
        assert evidence_snippet in completed_maps

    required_rows = [
        "| Add a drawdown recovery chart to the showcase | `good first issue`, `risk`, `docs` |",
        "| Add a quarterly challenge seed file | `help wanted`, `benchmark` |",
        "| Add a redacted citation entry template | `good first issue`, `docs` |",
    ]
    for row in required_rows:
        assert _normalized(row) in text

    assert "Add an Ollama local-model config example" not in text


def test_completed_live_ready_backlog_rows_point_to_current_artifacts():
    text = _normalized(_read_text("docs/community_tasks.md"))
    live_ready_section = text.split("## Broker And Live-Ready Tracks", 1)[1].split(
        "## Completed Live-Ready Capability Map", 1
    )[0]
    completed_section = text.split("## Completed Live-Ready Capability Map", 1)[1].split("## Benchmark Flywheel", 1)[0]

    completed_capabilities = {
        "Live-readiness safety-control mismatch fixture": [
            "outputs/examples/live_readiness_preflight/preflight_bundle.json",
            "safety controls",
        ],
        "Broker-specific paper sandbox client fixture": [
            "outputs/examples/mock_paper_sandbox_client/paper_sandbox_response_artifact.json",
            "mock-paper sandbox fixture",
        ],
        "Incident-response drill artifact": [
            "outputs/examples/operator_runbook/summary.json",
            "incident_response_drill",
        ],
        "Broker-response reconciliation edge cases": [
            "outputs/examples/broker_response_reconciliation/broker_response_artifact.json",
            "outputs/examples/broker_response_artifact/response_artifact.json",
            "responses[1].client_order_id duplicates an earlier response",
        ],
    }
    for capability, evidence_snippets in completed_capabilities.items():
        assert capability not in live_ready_section
        assert capability in completed_section
        for evidence_snippet in evidence_snippets:
            assert evidence_snippet in completed_section


def test_claim_and_validation_docs_use_trellm_for_system_claims():
    required_snippets = {
        "docs/benchmark_maturity.md": [
            "TreLLM should be presented as an early-stage research prototype until three forms of evidence exist in public:",
            "TreLLM can credibly describe itself as externally validated, and TradeArena can credibly describe its leaderboard module as a niche benchmark",
        ],
        "docs/claim_boundaries.md": [
            "TreLLM separates three kinds of claims.",
            "The TradeArena leaderboard rows carry explicit evidence labels:",
        ],
        "docs/external_validation_quickstart.md": [
            "TreLLM needs external evidence",
            "TradeArena leaderboard rows",
            "TreLLM should not claim community validation",
        ],
        "docs/external_validation.md": [
            "External validation is the evidence that makes TreLLM more than a maintainer-run demo.",
            "accepted validations can be linked from the TradeArena leaderboard registry or release notes.",
        ],
        "docs/execution_calibration_quickstart.md": [
            "contributors who want to strengthen TreLLM execution evidence",
            "the TreLLM calibration pipeline was run on this public BTCUSDT sample",
        ],
        "docs/demo_matrix.md": [
            "This matrix maps TreLLM capabilities to hands-on repository artifacts.",
            "one runnable example for each TreLLM system surface",
            "### Broker Capability Manifest",
            "how TreLLM should progress from paper research to broker-review exports",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    calibration_text = _normalized(_read_text("docs/execution_calibration_quickstart.md"))
    assert "strengthen TradeArena's execution evidence" not in calibration_text
    assert "the TradeArena calibration pipeline was run" not in calibration_text

    readme_text = _normalized(_read_text("README.md"))
    assert "This makes the system relevant to LLM trading agents" in readme_text
    assert "This makes the framework relevant to LLM trading agents" not in readme_text

    demo_matrix_text = _normalized(_read_text("docs/demo_matrix.md"))
    assert "one runnable example for each framework surface" not in demo_matrix_text


def test_skill_experiment_docs_assign_audit_research_to_trellm():
    required_snippets = {
        "docs/agent_skills.md": [
            "The task suite measures TreLLM-specific financial-audit ability rather than trading ability:",
        ],
        "docs/poe_skill_task_experiments.md": [
            "TreLLM already has synthetic, real-market, execution-shock, classical-baseline, and calibration snapshots, with TradeArena providing the comparable leaderboard surface.",
        ],
    }
    forbidden_snippets = {
        "docs/agent_skills.md": [
            "The task suite measures TradeArena-specific audit ability rather than trading ability:",
        ],
        "docs/poe_skill_task_experiments.md": [
            "TradeArena already has synthetic, real-market, execution-shock, classical-baseline, and calibration snapshots.",
        ],
    }

    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    for path, snippets in forbidden_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) not in text


def test_claim_review_examples_assign_recording_claims_to_trellm():
    required_snippets = {
        "docs/claim_boundary_review_quickstart.md": [
            '"TreLLM records replayable trajectory artifacts with hashes; TradeArena can publish the resulting leaderboard evidence."',
        ],
        "examples/skill_tasks/claim_boundary_001/candidate_claims.md": [
            "TreLLM records every agent decision as a replayable intent-to-execution trajectory.",
        ],
        "examples/skill_tasks/claim_boundary_provider_drift_001/candidate_claims.md": [
            '"TreLLM records model intent, risk edits, simulated fills, and replay hashes for paper-only benchmark runs summarized in TradeArena rows."',
        ],
        "examples/skill_task_answers/reference/claim_boundary_001.md": [
            "that TreLLM can record a trajectory from intent to risk and execution state.",
            "TradeArena can present the resulting evidence as a leaderboard artifact.",
            "The single-run profitability claim is unsupported and should be weakened",
        ],
        "examples/skill_task_answers/reference/claim_boundary_provider_drift_001.md": [
            "Claim 2 is an engineering claim: TreLLM records intent, risk edits, simulated fills, and replay hashes for paper-only benchmark runs.",
            "TradeArena can summarize that evidence as a leaderboard row, but the recording capability belongs to TreLLM.",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text


def test_launch_and_pages_sources_use_trellm_for_public_positioning():
    required_snippets = {
        "docs/blog/why_llm_trading_agents_need_audit_benchmarks.md": [
            "TreLLM takes a different view. It treats a financial AI agent as an auditable decision-making system:",
            "TreLLM renders this as a browser-readable audit report",
            "TradeArena is its public leaderboard and benchmark-card layer",
        ],
        "docs/launch/README.md": [
            "# TreLLM Project Metadata",
            "TreLLM's public positioning is:",
            "TreLLM turns every financial-agent decision into a traceable trajectory:",
            "TreLLM is an LLM-driven trading audit and live-readiness control system; TradeArena is its public leaderboard",
            "llm-trading",
            "trading-audit",
            "financial-ai",
            "agent-audit",
            "execution-calibration",
            "live-readiness",
            "paper-trading",
            "risk-gates",
            "trellm",
            "leaderboard",
        ],
        "docs/launch/pages_demo.md": [
            "TreLLM publishes the project landing page and quickstart showcase",
        ],
        ".github/workflows/pages.yml": [
            "TreLLM static demo generated by:",
            "github.repository == 'weich97/TreLLM-public'",
        ],
        "scripts/run_showcase.py": [
            'description="Build the public-facing TreLLM showcase."',
            "print(\"TreLLM showcase\", flush=True)",
            "while reusing the rest of the TreLLM stack.",
            "<title>TreLLM - Trading Audit And Control Showcase</title>",
            "<h1>TreLLM: LLM Trading Audit And Control</h1>",
            "<title>TreLLM 3-Minute Demo Video</title>",
            "<h1>TreLLM 3-Minute Demo Video</h1>",
            "<h1>TreLLM Showcase: Quickstart Tour</h1>",
            'aria-label="TreLLM 3-minute demo video"',
            "What TreLLM is not:",
            "TradeArena is the public leaderboard module",
            "benchmark cards used only as citable evidence snapshots",
        ],
        "scripts/build_demo_video.py": [
            'draw.text((72, 36), "TreLLM", fill="#ccfbf1", font=fonts["brand"])',
            "TradeArena is the public leaderboard module.",
            "Extend TreLLM with small, reviewable plugins.",
        ],
        "scripts/validate_demo_artifacts.py": [
            'description="Validate required TreLLM demo artifacts."',
        ],
        "scripts/run_launch_demo.py": [
            'description="Run the offline TreLLM launch demo."',
            'print("TreLLM launch demo", flush=True)',
            "<title>TreLLM Demo Portal</title>",
            "<h1>TreLLM Demo Portal</h1>",
        ],
        "scripts/run_paper_design_demos.py": [
            'print("TreLLM experiment-design demo suite")',
            "Offline-friendly demos aligned with core TreLLM experiment axes.",
            "<title>TreLLM Experiment-Design Demos</title>",
            "<h1>TreLLM Experiment-Design Demos</h1>",
            "These offline-friendly hands-on examples exercise four TreLLM research axes",
        ],
        "examples/akshare_csv_reuse_demo.py": [
            'print("AkShare -> normalized CSV -> TreLLM demo")',
            '("TreLLM", "risk + execution + trajectory")',
            "A-share data path: AkShare -> normalized CSV -> existing TreLLM runner",
        ],
        "examples/rl_policy_baseline_demo.py": [
            "A deterministic CI-safe strategy emits normal TreLLM decisions and reuses risk, execution, and evaluation.",
        ],
        "examples/visual_tour_demo.py": [
            'description="Generate animated offline TreLLM visual-tour artifacts."',
            "TreLLM turns trajectories into mechanism probes",
            "<title>TreLLM Visual Tour: Audit, Execution, Diagnostics</title>",
            "<h1>TreLLM Visual Tour: Audit, Execution, Diagnostics</h1>",
        ],
        "examples/retail_planner_demo.py": [
            "<title>TreLLM Retail Planning Demo</title>",
            "<h1>TreLLM Retail Planning Demo</h1>",
        ],
        "examples/crisis_snapshot_demo.py": [
            "<title>TreLLM Crisis Snapshot Gallery</title>",
            "<h1>TreLLM Crisis Snapshot Gallery</h1>",
        ],
        "scripts/render_audit_report.py": [
            'description="Render a TreLLM trajectory as a compact HTML audit report."',
            "Trajectory JSON written by a TreLLM run.",
            "<title>TreLLM Audit Report: Replayable Decision Trace</title>",
            "<h1>TreLLM Audit Report: Replayable Decision Trace</h1>",
            "summarized in TradeArena leaderboard artifacts",
        ],
        "scripts/render_agent_autopsy_dashboard.py": [
            "Trajectory JSON written by a TreLLM run.",
        ],
        "scripts/run_failure_autopsy.py": [
            'description="Classify TreLLM trajectory failure modes."',
        ],
        "scripts/run_bge_m3_probe.py": [
            'description="Validate TreLLM representation signatures with local BGE-family Transformer embeddings."',
        ],
        "docs/assets/audit_report_preview.svg": [
            'aria-label="TreLLM audit report preview"',
            ">TreLLM Audit Report<",
        ],
        "examples/custom_plugin_demo.py": [
            "One new plugin, the rest of TreLLM stays fixed",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    launch_metadata = _read_text("docs/launch/README.md")
    assert (
        "TreLLM is an LLM-driven trading audit and live-readiness control system; "
        "TradeArena is its public leaderboard for replayable trajectories, risk gates, "
        "execution calibration, and reproducible agent evidence."
    ) in launch_metadata
    for topic in ["trellm", "live-readiness", "execution-calibration", "risk-gates", "paper-trading"]:
        assert f"\n{topic}\n" in launch_metadata
    assert "\nagent-benchmark\n" not in launch_metadata
    assert "\nbenchmark\n" not in launch_metadata

    demo_matrix_text = _normalized(_read_text("docs/demo_matrix.md"))
    assert "reusing the rest of the TreLLM stack" in demo_matrix_text
    assert "reusing the rest of the framework" not in demo_matrix_text


def test_public_entrypoints_follow_current_trellm_repository_location():
    stale_patterns = [
        "weich97/TradeArena",
        "github.com/weich97/TradeArena",
        "github.io/TradeArena",
        "repo=weich97/TradeArena",
        "mybinder.org/v2/gh/weich97/TradeArena",
        "nbviewer.org/github/weich97/TradeArena",
        "cd TradeArena",
        "Path(\"TradeArena\")",
        "os.chdir(\"TradeArena\")",
        'Path(\\"TradeArena\\")',
        'os.chdir(\\"TradeArena\\")',
        'name != \\"TradeArena\\"',
    ]
    public_entrypoints = [
        "README.md",
        "pyproject.toml",
        "CITATION.cff",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/workflows/pages.yml",
        "docs/design/system_repositioning.md",
        "docs/getting_started.md",
        "docs/deterministic_baseline_submission_quickstart.md",
        "docs/external_validation.md",
        "docs/external_validation_quickstart.md",
        "docs/launch/README.md",
        "docs/launch/pages_demo.md",
        "docs/launch/demo_video.md",
        "scripts/run_showcase.py",
        "scripts/build_benchmark_page.py",
        "notebooks/tradearena_5min_colab.ipynb",
        "schemas/benchmark_submission.schema.json",
        "schemas/broker_adapter_capability.schema.json",
        "schemas/broker_approval_artifact.schema.json",
        "schemas/broker_handoff_artifact.schema.json",
        "schemas/broker_response_artifact.schema.json",
        "schemas/calibration_profile.schema.json",
        "schemas/demo_artifact_contract.schema.json",
        "schemas/live_readiness_preflight.schema.json",
        "schemas/operator_runbook_artifact.schema.json",
        "schemas/reproduction_report.schema.json",
        "schemas/skill_answer_set.schema.json",
        "schemas/skill_task_rubric.schema.json",
        "schemas/trajectory.schema.json",
    ]
    for path in public_entrypoints:
        text = _read_text(path)
        for pattern in stale_patterns:
            assert pattern not in text, f"{path} still points at stale repository location {pattern!r}"


def test_launch_and_generated_pages_avoid_generic_benchmark_module_framing():
    forbidden_snippets = {
        "scripts/run_showcase.py": [
            "TradeArena is the public leaderboard and benchmark module",
        ],
        "scripts/build_demo_video.py": [
            "TradeArena is the public leaderboard and benchmark module.",
        ],
        "scripts/render_audit_report.py": [
            "TradeArena benchmark module",
        ],
        "scripts/build_benchmark_page.py": [
            "public leaderboard and benchmark-card module inside that system",
        ],
        "docs/results/benchmark_v0_2.md": [
            "public leaderboard and benchmark-card module inside that system",
        ],
        "docs/launch/release_notes_v0.2.0.md": [
            "TradeArena benchmark module",
        ],
        "docs/launch/release_notes_v0.1.0.md": [
            "TradeArena benchmark module",
        ],
    }
    for path, snippets in forbidden_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) not in text


def test_developer_docs_use_trellm_for_system_surfaces():
    required_snippets = {
        "docs/artifact_portability.md": [
            "TreLLM artifacts should be easy to move between local machines",
        ],
        "docs/observability.md": [
            "TreLLM trajectories are already structured logs.",
            "| TreLLM record | OpenTelemetry-style span | Evals or trace-style field |",
        ],
        "docs/plugin_development.md": [
            "TreLLM plugins are small Python objects that implement one narrow protocol:",
        ],
        "docs/extension_walkthrough.md": [
            "TreLLM is designed around narrow protocol surfaces.",
        ],
        "docs/public_artifact_privacy.md": [
            "TreLLM separates local debugging records from public TradeArena leaderboard artifacts.",
        ],
        "docs/execution_model_boundaries.md": [
            "TreLLM separates execution assumptions into explicit import surfaces:",
        ],
        "docs/schemas.md": [
            "# TreLLM Schemas",
            "TreLLM treats a financial AI agent as an auditable reliability lifecycle",
        ],
        "docs/retail_planning.md": [
            "TreLLM includes an offline-friendly planning layer",
        ],
        "docs/market_rules.md": [
            "TreLLM's default simulator is market-agnostic.",
            "TreLLM now exposes these as testable rule-package helpers",
        ],
        "docs/financial_audit_agent_benchmark.md": [
            "TreLLM skills are evaluated as audit workflows, not as trading strategies.",
        ],
        "docs/execution_model.md": [
            "TreLLM's execution layer is a configurable paper-execution stress model.",
            "TreLLM's default `market_impact` coefficient with a fill-log estimate",
            "claiming that TreLLM explains realized transaction costs",
        ],
        "src/tradearena/agents/rl.py": [
            "TreLLM strategy interface and downstream risk/execution/evaluation stack.",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    forbidden_snippets = {
        "docs/observability.md": [
            "| TradeArena record | OpenTelemetry-style span | Evals or trace-style field |",
        ],
        "docs/execution_model.md": [
            "TradeArena's default `market_impact` coefficient",
            "claiming that TradeArena explains realized transaction costs",
        ],
        "src/tradearena/agents/rl.py": [
            "TradeArena strategy interface and downstream risk/execution/evaluation stack.",
        ],
        "src/tradearena/cli.py": [
            "TradeArena Replay:",
        ],
    }
    for path, snippets in forbidden_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) not in text


def test_utility_cli_help_uses_trellm_for_system_artifacts():
    required_snippets = {
        "scripts/render_agent_autopsy_dashboard.py": [
            'description="Render an Agent Autopsy Dashboard from a TreLLM trajectory."',
        ],
        "scripts/hash_run.py": [
            'description="Compute a reproducibility hash for a TreLLM trajectory JSON."',
        ],
        "scripts/validate_broker_approval_artifact.py": [
            'description="Validate a TreLLM broker approval artifact."',
        ],
        "scripts/validate_broker_handoff_artifact.py": [
            'description="Validate a TreLLM broker handoff artifact."',
        ],
        "scripts/validate_broker_response_artifact.py": [
            'description="Validate a TreLLM broker response artifact."',
        ],
        "scripts/validate_broker_adapter_capability.py": [
            'description="Validate a TreLLM broker adapter capability manifest."',
        ],
        "scripts/validate_live_readiness_preflight.py": [
            'description="Validate a TreLLM live-readiness preflight bundle."',
        ],
        "scripts/validate_operator_runbook_artifact.py": [
            'description="Validate a TreLLM operator runbook artifact."',
        ],
        "scripts/validate_broker_approval_binding.py": [
            'description="Validate that a TreLLM broker approval binds to a handoff artifact."',
        ],
        "scripts/hash_broker_handoff_artifact.py": [
            'description="Validate and hash a TreLLM broker handoff artifact."',
        ],
        "scripts/calibrate_execution_model.py": [
            'description="Generate OHLCV-based diagnostics for the TreLLM execution simulator."',
        ],
        "scripts/compare_execution_to_fills.py": [
            'description="Compare TreLLM execution assumptions against historical order/fill logs."',
            "against the current TreLLM execution-stress equation.",
        ],
        "scripts/calibrate_quote_fill_model.py": [
            'description="Fit TreLLM execution parameters from top-of-book quotes and realized fills."',
        ],
        "scripts/download_binance_microstructure_sample.py": [
            "This sample upgrades TreLLM from an OHLCV-only smoke test to a public quote/fill replay",
            '"User-Agent": "TreLLM-calibration-sample"',
        ],
        "scripts/download_hf_mirror_snapshot.py": [
            '"User-Agent": "TreLLM mirror downloader"',
        ],
        "scripts/download_akshare_ashare_daily.py": [
            "Volume is normalized to TreLLM-compatible CSV units",
        ],
        "data/public/binance_btcusdt_perp_2024_03_01_sample/manifest.json": [
            "This sample upgrades TreLLM from an OHLCV-only smoke test to a public quote/fill replay",
        ],
        "scripts/download_yahoo_daily.py": [
            'description="Download normalized Yahoo Finance OHLCV CSV files for TreLLM."',
        ],
        "scripts/run_crisis_scene_experiments.py": [
            'description="Run real-market crisis-scene experiments for TreLLM."',
        ],
        "scripts/run_embedding_provider_probe.py": [
            'description="Run a 10-step embedding-provider robustness probe for TreLLM."',
        ],
        "scripts/validate_reproduction_report.py": [
            'description="Validate a TreLLM external reproduction report."',
        ],
        "src/tradearena/cli.py": [
            'description="Run TreLLM experiments and TradeArena leaderboard benchmark cases."',
            'description="Compute a reproducibility hash for a TreLLM trajectory JSON."',
            'description="Replay one step from a TreLLM trajectory JSON."',
            'description="Export a TreLLM trajectory to a local trace JSON."',
            'description="Create a local TreLLM plugin skeleton."',
            'description="Validate a TreLLM broker response artifact."',
            'description="Validate a TreLLM broker handoff artifact."',
            'description="Validate a TreLLM broker approval artifact."',
            'description="Validate that a TreLLM broker approval binds to a handoff artifact."',
            'description="Validate a TreLLM broker adapter capability manifest."',
            'description="Validate a TreLLM live-readiness preflight bundle."',
            'description="Validate and hash a TreLLM broker handoff artifact."',
            'description="Validate a TreLLM operator runbook artifact."',
        ],
        "src/tradearena/evaluation/autopsy.py": [
            "Summarize failure modes from a serialized TreLLM trajectory.",
        ],
        "src/tradearena/evaluation/trace_export.py": [
            "Export a TreLLM trajectory to an OpenTelemetry-style local trace JSON.",
        ],
        "src/tradearena/tools/broker_export.py": [
            "Convert TreLLM order intent into broker handoff rows.",
            "Convert approved TreLLM orders into broker-review files.",
        ],
        "src/tradearena/tools/calibration.py": [
            "This report fits TreLLM's compact execution equation from top-of-book quotes and realized fills.",
        ],
        "docs/results/execution_quote_fill_calibration_sample.md": [
            "This report fits TreLLM's compact execution equation from top-of-book quotes and realized fills.",
        ],
        "docs/results/execution_quote_fill_calibration_binance_sample.md": [
            "This report fits TreLLM's compact execution equation from top-of-book quotes and realized fills.",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    forbidden_snippets = {
        "scripts/download_binance_microstructure_sample.py": [
            '"User-Agent": "TradeArena-calibration-sample"',
        ],
        "scripts/download_hf_mirror_snapshot.py": [
            '"User-Agent": "TradeArena mirror downloader"',
        ],
        "scripts/download_akshare_ashare_daily.py": [
            "Volume is normalized to TradeArena units",
        ],
    }
    for path, snippets in forbidden_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) not in text


def test_broker_artifact_schemas_use_trellm_system_identity():
    required_snippets = {
        "schemas/broker_handoff_artifact.schema.json": [
            '"title": "TreLLM Broker Handoff Artifact"',
        ],
        "schemas/broker_approval_artifact.schema.json": [
            '"title": "TreLLM Broker Approval Artifact"',
        ],
        "schemas/broker_response_artifact.schema.json": [
            '"title": "TreLLM Broker Response Artifact"',
        ],
        "schemas/broker_adapter_capability.schema.json": [
            '"title": "TreLLM Broker Adapter Capability Manifest"',
        ],
        "schemas/live_readiness_preflight.schema.json": [
            '"title": "TreLLM Live Readiness Preflight Bundle"',
        ],
        "schemas/operator_runbook_artifact.schema.json": [
            '"title": "TreLLM Operator Runbook Artifact"',
        ],
    }
    forbidden_snippets = {
        path: [snippet.replace("TreLLM", "TradeArena") for snippet in snippets]
        for path, snippets in required_snippets.items()
    }

    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    for path, snippets in forbidden_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) not in text

    broker_export_text = _normalized(_read_text("src/tradearena/tools/broker_export.py"))
    assert "Convert TradeArena orders into broker handoff rows." not in broker_export_text
    assert "Convert approved TradeArena orders into broker-review files." not in broker_export_text
    for path in [
        "src/tradearena/tools/calibration.py",
        "docs/results/execution_quote_fill_calibration_sample.md",
        "docs/results/execution_quote_fill_calibration_binance_sample.md",
    ]:
        assert "TradeArena's compact execution equation" not in _normalized(_read_text(path))
    assert "TradeArena execution-stress equation" not in _normalized(_read_text("scripts/compare_execution_to_fills.py"))
    for path in [
        "scripts/download_binance_microstructure_sample.py",
        "data/public/binance_btcusdt_perp_2024_03_01_sample/manifest.json",
    ]:
        assert "upgrades TradeArena from an OHLCV-only smoke test" not in _normalized(_read_text(path))
    cli_text = _normalized(_read_text("src/tradearena/cli.py"))
    assert "Validate that a broker approval artifact binds to a handoff artifact." not in cli_text
    for snippet in [
        "Run TradeArena experiments.",
        "Replay one step from a TradeArena trajectory JSON.",
        "Export a TradeArena trajectory to a local trace JSON.",
        "Create a local TradeArena plugin skeleton.",
    ]:
        assert snippet not in cli_text
    assert "serialized TradeArena trajectory" not in _normalized(_read_text("src/tradearena/evaluation/autopsy.py"))
    assert "Export a TradeArena trajectory to an OpenTelemetry-style local trace JSON." not in _normalized(
        _read_text("src/tradearena/evaluation/trace_export.py")
    )


def test_generated_public_copy_sources_use_trellm_system_identity():
    required_snippets = {
        "docs/agent_skills.md": [
            "# TreLLM Agent Skills",
            "TreLLM agent skills are repository workflow templates for audit",
        ],
        "scripts/build_demo_video.py": [
            '"title": "TreLLM in 3 Minutes"',
            "TreLLM separates intended allocation from what the market simulator can actually fill.",
            '"title": "What TreLLM is for"',
            'description="Build a captioned 3-minute TreLLM demo video."',
            '"TreLLM showcase"',
        ],
        "scripts/score_skill_task_report.py": [
            "# TreLLM Skill Task Matrix",
            "TreLLM skills help agents inspect, reproduce, audit, and extend TradeArena leaderboard artifacts.",
        ],
        "scripts/scan_public_artifacts.py": [
            "Scan public TreLLM artifacts for raw prompt/response or secret leakage.",
        ],
        "scripts/build_benchmark_page.py": [
            "TreLLM is a financial-agent reliability audit and control system. TradeArena is the",
            "public leaderboard module and benchmark-card layer inside that system",
        ],
        "docs/results/benchmark_v0_2.md": [
            "TreLLM is a financial-agent reliability audit and control system. TradeArena is the public leaderboard",
            "module and benchmark-card layer inside that system",
        ],
        "docs/benchmark_submissions.md": [
            "TradeArena accepts redacted leaderboard manifests so users can compare runs",
        ],
        "docs/schemas.md": [
            "## Redacted Leaderboard Submission Schema",
            "External TradeArena rows can be shared without exposing raw provider prompts or responses.",
            "## Operator Runbook Artifact Schema",
            "Broker adapter capability manifests can be validated against",
            "The schema fixes the public `trellm_broker_adapter_capability_v0.1` contract",
            "tradearena validate-broker-capability outputs/examples/broker_capability_manifest/capability_manifest.json",
            "the command path must name the current preflight bundle being validated",
            "## Live-Readiness Preflight Bundle Schema",
            "The schema fixes the public `trellm_live_readiness_preflight_v0.1` contract",
            "`approval_checked_at` must match the timestamp passed to `validate-live-readiness --now`",
            "tradearena validate-live-readiness outputs/examples/live_readiness_preflight/preflight_bundle.json",
            "The schema fixes the public `trellm_operator_runbook_v0.1` contract",
            "tradearena validate-operator-runbook outputs/examples/operator_runbook/summary.json",
        ],
        "docs/launch/discussion_seeds.md": [
            "TreLLM currently records observation, signals, proposed decisions, approved",
            "If you use TreLLM in a class, project, or internal evaluation",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text


def test_public_copy_avoids_community_benchmark_submission_framing():
    forbidden_snippets = {
        "docs/schemas.md": [
            "Community Benchmark Submission Schema",
            "External benchmark rows can be shared",
        ],
        "docs/launch/discussion_seeds.md": [
            "community benchmark submissions",
            "public benchmark submission",
        ],
        "docs/launch/issue_backlog.md": [
            "community benchmark submissions",
        ],
        "docs/launch/release_notes_v0.2.0.md": [
            "Redacted benchmark submissions",
        ],
    }
    for path, snippets in forbidden_snippets.items():
        text = _normalized(_read_text(path)).lower()
        for snippet in snippets:
            assert _normalized(snippet).lower() not in text


def test_release_notes_use_trellm_for_system_release_positioning():
    required_snippets = {
        "docs/launch/release_notes_v0.2.1.md": [
            "TreLLM v0.2.1 is a patch-release candidate focused on evidence quality",
            "TreLLM remains an audit and live-readiness control system.",
            "TradeArena remains the public leaderboard module and benchmark-card layer",
            "Release readiness now checks public identity boundaries before publication.",
        ],
        "docs/launch/release_notes_v0.2.0.md": [
            "TreLLM v0.2.0 is the first protocol-focused release for the TradeArena leaderboard module and benchmark-card layer.",
        ],
        "docs/launch/release_notes_v0.1.0.md": [
            "# v0.1.0: TreLLM Audit And Control Release With TradeArena Leaderboard Artifacts",
            "TreLLM v0.1.0 is the first public TreLLM release for evaluating LLM",
            "TradeArena leaderboard module and benchmark-card layer for comparable rows.",
            "TreLLM is not a live trading bot and does not promise profitable trading.",
            "It is an audit and control system with the TradeArena leaderboard module",
            "v0.1.0: TreLLM audit and control release with TradeArena leaderboard artifacts",
        ],
        "docs/launch/release_notes_v0.1.1.md": [
            "TreLLM v0.1.1 is a small maintenance release focused on making execution",
        ],
        "docs/launch/release_notes_v0.1.2.md": [
            "TreLLM v0.1.2 is the first PyPI-ready release under the",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    current_release_text = _normalized(_read_text("docs/launch/release_notes_v0.2.1.md"))
    assert "TradeArena remains the public leaderboard and benchmark module" not in current_release_text


def test_launch_backlog_uses_trellm_for_future_system_tasks():
    required_snippets = {
        "docs/launch/issue_backlog.md": [
            "Build an offline broker-review adapter that converts approved TreLLM orders",
            "wrapped as a TreLLM strategy or analyst through the `tradearena` package interfaces.",
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text


def test_extension_and_skill_surfaces_use_trellm_system_identity():
    required_snippets = {
        "examples/README.md": [
            "# TreLLM Hands-On Examples",
            "These examples are designed for the first hour after cloning TreLLM.",
            "Shows how two leaderboard cases share the same market, risk, execution, and evaluation stack.",
            "Converts approved TreLLM orders into neutral JSON/CSV rows for Alpaca-style broker review.",
        ],
        "docs/plugin_interfaces.md": [
            "# TreLLM Plugin Interfaces",
            "The TreLLM system intentionally keeps interfaces narrow.",
            "A new LLM agent, FinRL policy, broker adapter, or risk model should be able to enter by implementing only the protocol it owns.",
        ],
        "plugins/README.md": [
            "# TreLLM Plugin Registry",
            "This directory is a lightweight registry for local and contributed TreLLM plugins.",
            "copy a reviewed TreLLM pattern",
        ],
        "docs/broker_adapter_contract.md": [
            "This contract defines the minimum bar for any TreLLM adapter that touches a broker",
            "- reconciliation status against the original TreLLM order.",
        ],
        "skills/README.md": [
            "# TreLLM Agent Skills",
            "TreLLM skills are workflow templates for humans, reviewers, and coding agents",
            "| `tradearena-plugin-author` | Author or review narrow TreLLM plugins |",
            "Skills should prefer existing TreLLM validation commands over ad hoc scripts.",
        ],
        "skills/skill_template/SKILL.md": [
            "# TreLLM Skill Template",
            "- inspect a TreLLM trajectory JSON;",
            "Prefer existing TreLLM commands before inventing new scripts:",
        ],
        "skills/skill_template/resources/safety_boundary.md": [
            "TreLLM skills operate on repository artifacts and local files.",
        ],
        "skills/tradearena-claim-boundary-review/SKILL.md": [
            "# TreLLM Claim Boundary Review Skill",
        ],
        "skills/tradearena-execution-calibration/SKILL.md": [
            "# TreLLM Execution Calibration Skill",
        ],
        "skills/tradearena-plugin-author/SKILL.md": [
            "# TreLLM Plugin Author Skill",
        ],
        "skills/tradearena-reproduction-review/SKILL.md": [
            "# TreLLM Reproduction Review Skill",
        ],
        "skills/tradearena-risk-gate-review/SKILL.md": [
            "# TreLLM Risk Gate Review Skill",
            "Review TreLLM risk-manager behavior without treating return as the primary outcome.",
        ],
        "skills/tradearena-trajectory-audit/SKILL.md": [
            "# TreLLM Trajectory Audit Skill",
            "Audit a TreLLM trajectory from agent intent to risk-gated decision",
        ],
        "docs/agent_skills_index.md": [
            "# TreLLM Agent Skills Index",
            "Skills are TreLLM repository workflows for audit, reproduction, calibration,",
            "unless recorded in the TreLLM run manifest.",
            "Review TreLLM risk-manager behavior without treating return as the primary outcome.",
            "Audit a TreLLM trajectory from agent intent to risk-gated decision",
        ],
        "examples/skill_tasks/README.md": [
            "# TreLLM Skill Task Suite",
            "human reviewer or coding agent can use TreLLM skills without turning them into trading prompts.",
        ],
        "examples/skill_task_answers/README.md": [
            "# TreLLM Skill Task Answers",
        ],
        "examples/skill_tasks_challenge/README.md": [
            "# TreLLM Challenge Skill Tasks",
        ],
        "scripts/build_skill_index.py": [
            'description="Build the TreLLM agent skill index."',
            '"# TreLLM Agent Skills Index"',
        ],
        "scripts/score_skill_task.py": [
            'description="Validate or score TreLLM skill task rubrics."',
        ],
        "scripts/score_skill_task_report.py": [
            'description="Build the TreLLM skill task matrix report."',
        ],
        "scripts/run_poe_skill_task_matrix.py": [
            "Run provider-hosted models on TreLLM financial-audit skill tasks.",
        ],
        "scripts/validate_skill_contract.py": [
            'description="Validate TreLLM agent skill contracts."',
        ],
        "examples/extension_walkthrough_demo.py": [
            "This run demonstrates the TreLLM contribution path:",
            'aria-label="TreLLM extension walkthrough"',
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    skill_index_source = _normalized(_read_text("scripts/build_skill_index.py"))
    assert "unless recorded in the TreLLM run manifest." in skill_index_source
    assert "unless recorded in the TradeArena run manifest." not in skill_index_source
    assert "unless recorded in the TradeArena run manifest." not in _normalized(_read_text("docs/agent_skills_index.md"))
    assert "# TradeArena Plugin Registry" not in _normalized(_read_text("plugins/README.md"))


def test_citation_and_research_report_keep_system_and_leaderboard_identity_separate():
    required_snippets = {
        "CITATION.cff": [
            "If you use TreLLM in research, please cite the arXiv technical report.",
            "If you use TradeArena leaderboard artifacts or a specific software release",
            "title: \"TreLLM: An LLM-Driven Trading Audit and Control System with TradeArena Leaderboard Artifacts\"",
            "title: \"Representation Signatures and Risk-Feedback Alignment in LLM Trading Agents\"",
        ],
        "docs/research_report.md": [
            "The public technical report for TreLLM research claims and TradeArena leaderboard artifacts is:",
            "Use the report for research claims about representation signatures",
            "Use repository release citations for software-version-specific reproduction.",
        ],
        "README.md": [
            "If you use TreLLM in research or cite TradeArena leaderboard artifacts, please cite the technical report:",
        ],
        "pyproject.toml": [
            'description = "TreLLM: LLM trading audit system with replayable trajectories, risk gates, reproducibility artifacts, and a TradeArena leaderboard."',
            '"trellm"',
            '"llm-trading"',
            '"trading-audit"',
            '"agent-audit"',
            '"leaderboard"',
            'authors = [{ name = "TreLLM Contributors" }]',
        ],
    }
    for path, snippets in required_snippets.items():
        text = _normalized(_read_text(path))
        for snippet in snippets:
            assert _normalized(snippet) in text

    pyproject = _read_text("pyproject.toml")
    keywords_match = re.search(r"keywords = \[(?P<keywords>.*?)\]", pyproject, flags=re.S)
    assert keywords_match is not None
    keywords = set(re.findall(r'"([^"]+)"', keywords_match.group("keywords")))
    assert 'name = "tradearena-benchmark"' in pyproject
    assert 'description = "TreLLM: LLM trading audit system' in pyproject
    assert keywords >= {
        "trellm",
        "llm-trading",
        "trading-audit",
        "financial-agents",
        "agent-audit",
        "leaderboard",
    }
