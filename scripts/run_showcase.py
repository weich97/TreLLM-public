from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs/examples"
DEMO_VIDEO_ASSET = ROOT / "docs/assets/trellm_3min_demo.mp4"
DEMO_VIDEO_POSTER = ROOT / "docs/assets/trellm_3min_demo_thumbnail.png"


SECTIONS = [
    (
        "First-run quickstart portal",
        "Start with a guided quickstart route through the main demo artifacts, their source commands, and redacted cache manifest.",
        "quickstart.html",
        "python scripts/run_launch_demo.py",
    ),
    (
        "Benchmark v0.2 card",
        "A compact result page for agent reliability, execution-aware baselines, intraday portfolio probes, and representation robustness.",
        "benchmark-v0.2.html",
        "python scripts/build_benchmark_page.py",
    ),
    (
        "TradeArena leaderboard registry",
        "A redacted benchmark-submission page that compares runs without exposing raw provider prompts or responses.",
        "community_registry.html",
        "python scripts/build_benchmark_registry.py examples/benchmark_submissions",
    ),
    (
        "Experiment-design demos",
        "Execution realism, Markowitz/MVO baselines, representation signatures, and custom plugin extensibility.",
        "experiment_design_index.html",
        "python scripts/run_paper_design_demos.py",
    ),
    (
        "Animated visual tour",
        "Regenerate the README animations and inspect what each preview conveys without relying on motion alone.",
        "visual_tour_index.html",
        "python examples/visual_tour_demo.py",
    ),
    (
        "Audit report",
        "Trace one decision from market observation through proposal, risk review, execution, and reflection.",
        "audit_report.html",
        "python scripts/render_audit_report.py",
    ),
    (
        "Agent Autopsy Dashboard",
        "Inspect intent versus executed weights, slippage attribution, and the risk intervention timeline from a replayable trajectory.",
        "agent_autopsy_dashboard.html",
        "python scripts/render_agent_autopsy_dashboard.py",
    ),
    (
        "Crisis gallery",
        "Representation trajectory, correlation/intent heatmap, feedback curves, and exposure waterfall snapshots.",
        "crisis_snapshot_gallery.html",
        "python examples/crisis_snapshot_demo.py",
    ),
    (
        "A-share rule stress",
        "T+1, price-limit, and board-lot constraints as auditable risk-gate interventions.",
        "ashare_market_rules.svg",
        "python examples/ashare_market_rules_demo.py",
    ),
    (
        "Crypto microstructure stress",
        "No-key high-volatility crypto-style stress with fill, rejection, latency, and slippage diagnostics.",
        "crypto_microstructure_stress/crypto_microstructure_stress.svg",
        "python examples/crypto_microstructure_stress_demo.py",
    ),
    (
        "Futures roll risk",
        "Contract metadata and a roll schedule produce expiry and roll-window risk reports.",
        "futures_roll_risk/futures_roll_risk.svg",
        "python examples/futures_roll_risk_demo.py",
    ),
    (
        "Mock deep-RL policy baseline",
        "A deterministic policy wrapper emits normal decisions and reuses risk, execution, trajectory, and evaluator plugins.",
        "rl_policy_baseline/rl_policy_baseline.svg",
        "python examples/rl_policy_baseline_demo.py",
    ),
    (
        "Alpaca paper export",
        "Approved orders become paper-review JSON/CSV rows without any live broker submission.",
        "alpaca_paper_export/alpaca_paper_orders.json",
        "python examples/alpaca_paper_export_demo.py",
    ),
    (
        "Dry-run broker adapter",
        "Broker request shape is validated locally without credentials, network calls, or live submission.",
        "dry_run_broker_adapter/dry_run_orders.json",
        "python examples/dry_run_broker_adapter_demo.py",
    ),
    (
        "Broker capability manifest",
        "Adapter permissions, account modes, credential policy, and live-safety controls are declared before review.",
        "broker_capability_manifest/capability_manifest.json",
        "python examples/broker_capability_manifest_demo.py",
    ),
    (
        "Broker approval safety",
        "A redacted approval artifact becomes a live-mode safety gate that allows bounded orders and blocks oversized ones.",
        "broker_approval_safety/broker_approval_artifact.json",
        "python examples/broker_approval_safety_demo.py",
    ),
    (
        "Broker response reconciliation",
        "Paper broker responses are matched back to submitted client order IDs for audit review.",
        "broker_response_reconciliation/broker_response_artifact.json",
        "python examples/broker_response_reconciliation_demo.py",
    ),
    (
        "Operator runbook checklist",
        "Human-gated live-readiness controls are written as an offline checklist artifact.",
        "operator_runbook/operator_runbook.md",
        "python examples/operator_runbook_demo.py",
    ),
    (
        "Live-readiness preflight bundle",
        "Capability, handoff, approval binding, response reconciliation, and runbook artifacts are checked together.",
        "live_readiness_preflight/preflight_summary.json",
        "python examples/live_readiness_preflight_demo.py",
    ),
    (
        "Holdings CSV import",
        "A tiny holdings CSV fixture feeds the retail planning sandbox and paper rebalance diagnostics.",
        "holdings_csv_import/summary.json",
        "python examples/holdings_csv_import_demo.py",
    ),
    (
        "Custom plugin extension",
        "A local analyst plugin running through the same strategy, risk, execution, memory, and evaluator stack.",
        "custom_plugin.svg",
        "python examples/custom_plugin_demo.py",
    ),
    (
        "Contributor extension walkthrough",
        "Swap in a custom analyst, risk manager, and evaluator while reusing the rest of the TreLLM stack.",
        "extension_walkthrough.svg",
        "python examples/extension_walkthrough_demo.py",
    ),
    (
        "Retail planning sandbox",
        "Review investor profiles, suitability checks, target allocations, futures margin estimates, and paper rebalance orders.",
        "retail_planning_report.html",
        "python examples/retail_planner_demo.py",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public-facing TreLLM showcase.")
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Only write the showcase index from existing artifacts; do not rerun demos.",
    )
    args = parser.parse_args()

    print("TreLLM showcase", flush=True)
    print("================", flush=True)
    print("A one-command quickstart repo tour for new users, reviewers, and launch posts.", flush=True)

    if not args.reuse_existing:
        _run([sys.executable, "scripts/run_launch_demo.py", "--skip-paper-figures"], "Launch demo portal")
        _preserve_launch_portal()
        _run([sys.executable, "scripts/build_quality_decomposition.py"], "Decision/execution quality radar")
        _run([sys.executable, "scripts/build_benchmark_page.py"], "Benchmark v0.2 result page")
        _run([sys.executable, "scripts/build_benchmark_registry.py", "examples/benchmark_submissions"], "TradeArena leaderboard registry")
        _run([sys.executable, "scripts/run_paper_design_demos.py"], "Experiment-design demo suite")
        _run([sys.executable, "examples/visual_tour_demo.py"], "Animated visual tour")
        _run([sys.executable, "examples/crypto_microstructure_stress_demo.py"], "Crypto microstructure stress")
        _run([sys.executable, "examples/futures_roll_risk_demo.py"], "Futures roll risk")
        _run([sys.executable, "examples/rl_policy_baseline_demo.py"], "Mock deep-RL policy baseline")
        _run([sys.executable, "examples/alpaca_paper_export_demo.py"], "Alpaca paper export")
        _run([sys.executable, "examples/dry_run_broker_adapter_demo.py"], "Dry-run broker adapter")
        _run([sys.executable, "examples/broker_capability_manifest_demo.py"], "Broker capability manifest")
        _run([sys.executable, "examples/broker_approval_safety_demo.py"], "Broker approval safety")
        _run([sys.executable, "examples/broker_response_reconciliation_demo.py"], "Broker response reconciliation")
        _run([sys.executable, "examples/operator_runbook_demo.py"], "Operator runbook checklist")
        _run([sys.executable, "examples/live_readiness_preflight_demo.py"], "Live-readiness preflight bundle")
        _run([sys.executable, "examples/holdings_csv_import_demo.py"], "Holdings CSV import")
        _run([sys.executable, "examples/extension_walkthrough_demo.py"], "Contributor extension walkthrough")
        _run([sys.executable, "examples/retail_planner_demo.py"], "Retail planning sandbox")
    else:
        _preserve_launch_portal()
        _maybe_render_agent_autopsy()
        _run(
            [
                sys.executable,
                "scripts/build_benchmark_page.py",
                "--markdown",
                "outputs/examples/benchmark-v0.2.md",
                "--html",
                "outputs/examples/benchmark-v0.2.html",
            ],
            "Benchmark v0.2 result page",
        )
        _run([sys.executable, "scripts/build_benchmark_registry.py", "examples/benchmark_submissions"], "TradeArena leaderboard registry")

    _copy_pages_assets()
    _copy_registry_page()
    _write_demo_video_page()
    _write_landing_page(OUTPUT_DIR / "index.html")
    _write_showcase_index(OUTPUT_DIR / "showcase.html")
    print("\nShowcase artifacts", flush=True)
    print("------------------", flush=True)
    print(f"[{'ok' if (OUTPUT_DIR / 'index.html').exists() else 'missing'}] outputs/examples/index.html", flush=True)
    for _, _, href, _ in SECTIONS:
        path = OUTPUT_DIR / href
        print(f"[{'ok' if path.exists() else 'missing'}] outputs/examples/{href}", flush=True)
    print(f"[{'ok' if (OUTPUT_DIR / 'demo_video.html').exists() else 'missing'}] outputs/examples/demo_video.html", flush=True)
    print(f"[{'ok' if (OUTPUT_DIR / 'trellm_3min_demo.mp4').exists() else 'missing'}] outputs/examples/trellm_3min_demo.mp4", flush=True)
    print("[ok] outputs/examples/showcase.html", flush=True)
    return 0


def _run(command: list[str], label: str) -> None:
    print(f"\n{label}", flush=True)
    print("-" * len(label), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _preserve_launch_portal() -> None:
    source = OUTPUT_DIR / "index.html"
    target = OUTPUT_DIR / "quickstart.html"
    if not source.exists():
        return
    text = source.read_text(encoding="utf-8", errors="ignore")
    if "TreLLM launch demo" in text or "One offline launch path" in text:
        shutil.copy2(source, target)


def _copy_pages_assets() -> None:
    source = ROOT / "docs/assets"
    target = OUTPUT_DIR / "assets"
    if not source.exists():
        return
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _copy_registry_page() -> None:
    for filename in ("community_registry.md", "community_registry.html", "community_registry.csv"):
        source = ROOT / "docs/results" / filename
        if source.exists():
            shutil.copy2(source, OUTPUT_DIR / filename)


def _maybe_render_agent_autopsy() -> None:
    trajectory = OUTPUT_DIR / "audit_walkthrough_trajectory.json"
    if not trajectory.exists():
        return
    _run(
        [
            sys.executable,
            "scripts/render_agent_autopsy_dashboard.py",
            "--trajectory",
            str(trajectory.relative_to(ROOT)),
            "--output",
            "outputs/examples/agent_autopsy_dashboard.html",
        ],
        "Agent autopsy dashboard",
    )


def _write_demo_video_page() -> None:
    if not DEMO_VIDEO_ASSET.exists():
        raise FileNotFoundError(
            f"Missing demo video asset: {DEMO_VIDEO_ASSET}. Run python scripts/build_demo_video.py first."
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEMO_VIDEO_ASSET, OUTPUT_DIR / "trellm_3min_demo.mp4")
    poster_html = ""
    if DEMO_VIDEO_POSTER.exists():
        shutil.copy2(DEMO_VIDEO_POSTER, OUTPUT_DIR / "trellm_3min_demo_thumbnail.png")
        poster_html = ' poster="trellm_3min_demo_thumbnail.png"'
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TreLLM 3-Minute Demo Video</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #0f172a; color: #e2e8f0; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 40px 24px 54px; }}
a {{ color: #67e8f9; }}
h1 {{ margin: 0 0 8px; font-size: 38px; letter-spacing: 0; }}
.lead {{ margin: 0 0 22px; max-width: 850px; color: #cbd5e1; line-height: 1.55; }}
.video-wrap {{ border: 1px solid #334155; border-radius: 12px; overflow: hidden; background: #020617; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35); }}
video {{ display: block; width: 100%; height: auto; background: #020617; }}
.links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
.links a {{ display: inline-block; padding: 9px 12px; border: 1px solid #334155; border-radius: 8px; background: #111827; text-decoration: none; font-weight: 700; }}
</style>
<main>
  <h1>TreLLM 3-Minute Demo Video</h1>
  <p class="lead">A captioned walkthrough of the quickstart command, showcase portal, audit report, execution realism, extension walkthrough, and retail planning sandbox. This static Pages video plays in the browser and does not require downloading a release asset.</p>
  <div class="video-wrap">
    <video controls preload="metadata"{poster_html}>
      <source src="trellm_3min_demo.mp4" type="video/mp4">
      Your browser does not support embedded MP4 video. Open <a href="trellm_3min_demo.mp4">the MP4 file</a>.
    </video>
  </div>
  <div class="links">
    <a href="showcase.html">Back to showcase</a>
    <a href="audit_report.html">Audit report</a>
    <a href="extension_walkthrough.svg">Extension walkthrough</a>
    <a href="retail_planning_report.html">Retail planning</a>
  </div>
</main>
</html>
"""
    (OUTPUT_DIR / "demo_video.html").write_text(html, encoding="utf-8")


def _write_landing_page(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    html = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TreLLM - Trading Audit And Control Showcase</title>
<style>
body { margin: 0; font-family: Inter, Arial, sans-serif; background: #f8fafc; color: #0f172a; }
main { max-width: 1160px; margin: 0 auto; padding: 42px 24px 58px; }
a { color: #2563eb; }
.hero { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr); gap: 26px; align-items: center; padding: 30px; background: #0f172a; color: #e2e8f0; border-radius: 14px; box-shadow: 0 24px 62px rgba(15, 23, 42, 0.20); }
h1 { margin: 0 0 12px; font-size: 42px; line-height: 1.06; letter-spacing: 0; }
.lead { margin: 0; color: #cbd5e1; line-height: 1.58; font-size: 17px; }
.cta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
.cta a { display: inline-block; padding: 10px 13px; border-radius: 8px; text-decoration: none; font-weight: 800; border: 1px solid #334155; color: #ccfbf1; background: #111827; }
.terminal { padding: 18px; border-radius: 10px; background: #020617; border: 1px solid #334155; color: #e5e7eb; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 13px; line-height: 1.6; overflow-x: auto; }
.strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 22px; }
.panel { padding: 18px; border: 1px solid #d8e2ed; border-radius: 10px; background: #fff; }
.panel h2 { margin: 0 0 8px; font-size: 18px; letter-spacing: 0; }
.panel p { margin: 0; color: #64748b; line-height: 1.5; font-size: 14px; }
.flow { margin: 24px 0; padding: 18px; border: 1px solid #d8e2ed; border-radius: 10px; background: #fff; }
.flow-row { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; }
.step { padding: 12px 8px; border-radius: 8px; background: #eff6ff; color: #1e3a8a; text-align: center; font-weight: 800; font-size: 13px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-top: 18px; }
.card { display: block; min-height: 128px; padding: 18px; border: 1px solid #d8e2ed; border-radius: 10px; background: #fff; color: inherit; text-decoration: none; }
.card:hover { border-color: #2563eb; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.10); }
.card strong { display: block; margin-bottom: 8px; }
.card span { display: block; color: #64748b; line-height: 1.45; font-size: 14px; }
.note { margin-top: 22px; padding: 16px; border-left: 4px solid #0f766e; background: #ecfdf5; color: #115e59; line-height: 1.5; }
@media (max-width: 840px) { .hero, .strip, .flow-row { grid-template-columns: 1fr; } h1 { font-size: 34px; } }
</style>
<main>
  <section class="hero">
    <div>
      <h1>TreLLM: LLM Trading Audit And Control</h1>
      <p class="lead">The showcase path validates the deterministic runner, risk gate, execution simulator, and trajectory artifacts without live provider calls. TreLLM also includes opt-in live or cache-backed LLM analyst runs through the same reliability lifecycle: observation -> signal -> intended allocation -> risk gate -> order -> fill/rejection -> portfolio state -> diagnostic report. TradeArena is the public leaderboard module for reviewed rows, with benchmark cards used only as citable evidence snapshots.</p>
      <div class="cta">
        <a href="showcase.html">Open showcase</a>
        <a href="benchmark-v0.2.html">Benchmark v0.2</a>
        <a href="demo_video.html">Watch demo</a>
        <a href="https://github.com/weich97/TreLLM-public">GitHub</a>
      </div>
    </div>
    <pre class="terminal">python -m pip install -e ".[dev]"
python scripts/run_showcase.py

# Open outputs/examples/index.html
# First-run path uses deterministic agents,
# tracked snapshots, and no live provider calls.</pre>
  </section>
  <section class="strip" aria-label="Use cases">
    <div class="panel"><h2>Agent Reliability</h2><p>Run deterministic, live, or cache-backed agents, then compare return, drawdown, risk edits, rejection rate, reproducibility, and audit coverage.</p></div>
    <div class="panel"><h2>Risk-aware AI Systems</h2><p>Inspect how structured risk reports, spread, slippage, latency, liquidity limits, partial fills, and rejected orders change realized exposure.</p></div>
    <div class="panel"><h2>Intent-to-Execution Audit</h2><p>Plug in data adapters, analysts, strategies, risk gates, execution simulators, memory, and evaluators while preserving the full action trail.</p></div>
  </section>
  <section class="flow">
    <div class="flow-row">
      <div class="step">Observe</div>
      <div class="step">Plan</div>
      <div class="step">Risk Gate</div>
      <div class="step">Execute</div>
      <div class="step">Reflect</div>
      <div class="step">Audit</div>
    </div>
  </section>
  <section class="grid">
    <a class="card" href="benchmark-v0.2.html"><strong>Benchmark result page</strong><span>Agent reliability, intraday portfolio probes, and representation robustness in one compact snapshot.</span></a>
    <a class="card" href="community_registry.html"><strong>TradeArena leaderboard registry</strong><span>Validate redacted leaderboard submissions and compare runs without raw provider text.</span></a>
    <a class="card" href="audit_report.html"><strong>Replayable audit report</strong><span>Trace one decision through observation, proposal, risk revision, execution, memory, and reproducibility fields.</span></a>
    <a class="card" href="agent_autopsy_dashboard.html"><strong>Agent Autopsy Dashboard</strong><span>Compare intent, risk-approved exposure, executed weights, slippage attribution, and intervention timing.</span></a>
    <a class="card" href="crisis_snapshot_gallery.html"><strong>Crisis-scene visual probes</strong><span>Inspect representation trajectories, correlation/intent heatmaps, feedback curves, and exposure waterfalls.</span></a>
    <a class="card" href="extension_walkthrough.svg"><strong>Contributor extension path</strong><span>See how custom analysts, risk managers, and evaluators plug into the fixed protocol stack.</span></a>
  </section>
  <p class="note"><strong>What TreLLM is not:</strong> it is not financial advice, not a live trading bot, and not a promise of profitable trading. TreLLM is an audit and control system for financial AI agent reliability; TradeArena is the public leaderboard module.</p>
</main>
</html>
"""
    path.write_text(html, encoding="utf-8")
    print(f"\nWrote {path.relative_to(ROOT)}", flush=True)


def _write_showcase_index(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(_card_html(title, body, href, command) for title, body, href, command in SECTIONS)
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>TreLLM Showcase: Quickstart Tour</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
main {{ max-width: 1080px; margin: 0 auto; padding: 44px 28px 54px; }}
h1 {{ margin: 0 0 8px; font-size: 36px; letter-spacing: 0; }}
.lead {{ margin: 0 0 18px; max-width: 820px; color: #475569; line-height: 1.58; }}
.strip {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 26px; }}
.pill {{ border: 1px solid #cbd5e1; border-radius: 999px; padding: 6px 10px; background: #ffffff; color: #334155; font-size: 12px; font-weight: 700; }}
.video-spotlight {{ display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(260px, 0.75fr); gap: 18px; align-items: stretch; margin: 0 0 22px; padding: 18px; border: 1px solid #cbd5e1; border-radius: 10px; background: #0f172a; color: #e2e8f0; box-shadow: 0 20px 48px rgba(15, 23, 42, 0.16); }}
.video-spotlight video {{ display: block; width: 100%; height: auto; border-radius: 8px; background: #020617; }}
.video-copy {{ padding: 4px 4px 0; }}
.video-copy h2 {{ margin: 0 0 8px; font-size: 24px; letter-spacing: 0; color: #ffffff; }}
.video-copy p {{ margin: 0 0 14px; color: #cbd5e1; line-height: 1.5; font-size: 14px; }}
.video-links {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.video-links a {{ display: inline-block; padding: 8px 10px; border-radius: 7px; border: 1px solid #334155; background: #111827; color: #ccfbf1; text-decoration: none; font-size: 12px; font-weight: 800; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 14px; }}
.card {{ display: block; min-height: 154px; padding: 18px; border: 1px solid #d8e2ed; border-radius: 8px; background: white; color: inherit; text-decoration: none; }}
.card:hover {{ border-color: #2563eb; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.10); transform: translateY(-1px); }}
.card span {{ display: block; font-weight: 800; font-size: 16px; margin-bottom: 8px; }}
.card p {{ margin: 0 0 12px; color: #64748b; font-size: 13px; line-height: 1.45; }}
.command {{ display: inline-block; padding: 6px 8px; border-radius: 6px; background: #f1f5f9; color: #334155; font-size: 12px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
.footer {{ margin-top: 26px; color: #64748b; font-size: 13px; line-height: 1.5; }}
@media (max-width: 820px) {{ .video-spotlight {{ grid-template-columns: 1fr; }} }}
</style>
<main>
  <h1>TreLLM Showcase: Quickstart Tour</h1>
  <p class="lead">Run one command, open one page, and inspect the artifacts that demonstrate agent reliability, realistic execution, risk-aware action filters, diagnostic visuals, and extensible plugins. Each card names the artifact and the command that regenerates it; the first-run path uses deterministic agents, tracked snapshots, and no live provider calls.</p>
  <div class="strip">
    <span class="pill">First run: no provider key</span>
    <span class="pill">Execution realism</span>
    <span class="pill">Risk lifecycle</span>
    <span class="pill">Replayable trajectories</span>
    <span class="pill">Extensible plugins</span>
  </div>
  <section class="video-spotlight" aria-label="TreLLM 3-minute demo video">
    <video controls preload="metadata" poster="trellm_3min_demo_thumbnail.png">
      <source src="trellm_3min_demo.mp4" type="video/mp4">
      Your browser does not support embedded MP4 video. Open <a href="trellm_3min_demo.mp4">the MP4 file</a>.
    </video>
    <div class="video-copy">
      <h2>3-Minute Demo Video</h2>
      <p>Watch the quickstart command, showcase portal, audit report, execution realism, extension walkthrough, and retail planning sandbox without leaving this page.</p>
      <div class="video-links">
        <a href="demo_video.html">Open theater view</a>
        <a href="trellm_3min_demo.mp4">Open MP4</a>
      </div>
    </div>
  </section>
  <section class="grid">
    {cards}
  </section>
  <p class="footer">Generated by <code>python scripts/run_showcase.py</code>. Large model calls and live market-data downloads are intentionally outside the first-run path.</p>
</main>
</html>
"""
    path.write_text(html, encoding="utf-8")
    print(f"\nWrote {path.relative_to(ROOT)}", flush=True)


def _card_html(title: str, body: str, href: str, command: str) -> str:
    status = "ready" if (OUTPUT_DIR / href).exists() else "generate first"
    return (
        f'<a class="card" href="{href}">'
        f"<span>{title}</span>"
        f"<p>{body}</p>"
        f'<code class="command">{command}</code>'
        f'<p style="margin-top:10px">Artifact status: {status}</p>'
        "</a>"
    )


if __name__ == "__main__":
    raise SystemExit(main())
