from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline TreLLM launch demo.")
    parser.add_argument(
        "--skip-paper-figures",
        action="store_true",
        help="Do not rebuild optional diagnostic SVG dashboards.",
    )
    args = parser.parse_args()

    print("TreLLM launch demo", flush=True)
    print("===================", flush=True)
    print("This run requires no keys and stays offline: no DeepSeek, Poe, OpenAI, or market-data calls.", flush=True)
    print(flush=True)

    _run([sys.executable, "examples/quickstart_core_benchmark.py"], "1/9 Core benchmark")
    _run([sys.executable, "examples/audit_trajectory_walkthrough.py"], "2/9 Audit trajectory")
    _run(
        [
            sys.executable,
            "scripts/render_audit_report.py",
            "--trajectory",
            "outputs/examples/audit_walkthrough_trajectory.json",
            "--output",
            "outputs/examples/audit_report.html",
        ],
        "3/9 HTML audit report",
    )
    _run(
        [
            sys.executable,
            "scripts/render_agent_autopsy_dashboard.py",
            "--trajectory",
            "outputs/examples/audit_walkthrough_trajectory.json",
            "--output",
            "outputs/examples/agent_autopsy_dashboard.html",
        ],
        "4/9 Agent autopsy dashboard",
    )
    _run([sys.executable, "examples/sidecar_data_demo.py"], "5/9 Optional data sidecars")
    _run([sys.executable, "examples/akshare_csv_reuse_demo.py"], "6/9 AkShare CSV reuse path")
    _run([sys.executable, "examples/ashare_market_rules_demo.py"], "7/9 A-share market-rule risk gate")
    _run([sys.executable, "examples/crisis_snapshot_demo.py"], "8/9 Crisis-scene visual gallery")
    _run([sys.executable, "examples/llm_cache_replay_demo.py"], "9/9 Redacted LLM cache manifest")
    figure_builder = ROOT / "scripts/build_paper_summary_figures.py"
    if not args.skip_paper_figures and figure_builder.exists() and (ROOT / "outputs/tradearena_paper/tables").exists():
        _run(
            [sys.executable, "scripts/build_paper_summary_figures.py", "--output-dir", "outputs/tradearena_paper"],
            "Optional diagnostic figure dashboards",
        )
    _write_demo_index(ROOT / "outputs/examples/index.html")

    print(flush=True)
    print("Demo artifacts", flush=True)
    print("--------------", flush=True)
    for path in [
        "outputs/examples/index.html",
        "outputs/examples/quickstart_core_metrics.json",
        "outputs/examples/audit_walkthrough_trajectory.json",
        "outputs/examples/audit_report.html",
        "outputs/examples/agent_autopsy_dashboard.html",
        "outputs/examples/sidecar_data",
        "outputs/examples/akshare_csv_reuse_summary.json",
        "outputs/examples/akshare_csv_reuse.svg",
        "outputs/examples/ashare_market_rules_summary.json",
        "outputs/examples/ashare_market_rules.svg",
        "outputs/examples/crisis_snapshot_summary.json",
        "outputs/examples/crisis_snapshot_gallery.html",
        "outputs/examples/llm_cache_replay_summary.json",
    ]:
        target = ROOT / path
        status = "ok" if target.exists() else "missing"
        print(f"[{status}] {path}", flush=True)
    return 0


def _run(command: list[str], label: str) -> None:
    print(f"\n{label}", flush=True)
    print("-" * len(label), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _write_demo_index(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cards = [
        (
            "Audit report",
            "Open one replayable observe-plan-risk-act-reflect trajectory with fills, rejections, memory, and reproducibility state.",
            "audit_report.html",
        ),
        (
            "Agent autopsy dashboard",
            "Inspect intent versus executed weights, slippage attribution, and the risk intervention timeline.",
            "agent_autopsy_dashboard.html",
        ),
        (
            "Crisis gallery",
            "Inspect representation trajectory, correlation heatmap, feedback curves, and exposure waterfall snapshots from tracked diagnostic artifacts.",
            "crisis_snapshot_gallery.html",
        ),
        (
            "AkShare CSV bridge",
            "See how A-share history is normalized into the same OHLCV CSV boundary used by every other TreLLM data provider.",
            "akshare_csv_reuse.svg",
        ),
        (
            "A-share rules",
            "See T+1, price-limit, and board-lot constraints become clipped or blocked risk-gate outcomes.",
            "ashare_market_rules.svg",
        ),
        (
            "Core benchmark JSON",
            "Compare a risk-aware realistic agent against buy-and-hold under the same execution frictions.",
            "quickstart_core_metrics.json",
        ),
        (
            "LLM cache manifest",
            "Check provider/model coverage, relative timestamp masking, prompt modes, and parsed signal counts without shipping raw prompts.",
            "llm_cache_replay_summary.json",
        ),
        (
            "Sidecar data",
            "Inspect the tiny CSV adapter example for optional news, macro, filings, and alternative-data fields.",
            "sidecar_data/",
        ),
    ]
    card_html = "\n".join(
        f'<a class="card" href="{href}"><span>{title}</span><p>{body}</p></a>' for title, body, href in cards
    )
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>TreLLM Demo Portal</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
main {{ max-width: 1040px; margin: 0 auto; padding: 42px 28px; }}
h1 {{ margin: 0 0 8px; font-size: 34px; letter-spacing: 0; }}
.lead {{ margin: 0 0 24px; max-width: 760px; color: #475569; line-height: 1.55; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
.card {{ display: block; min-height: 122px; padding: 18px; border: 1px solid #d8e2ed; border-radius: 8px; background: white; color: inherit; text-decoration: none; }}
.card:hover {{ border-color: #2563eb; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.10); transform: translateY(-1px); }}
.card span {{ display: block; font-weight: 800; font-size: 16px; margin-bottom: 8px; }}
.card p {{ margin: 0; color: #64748b; font-size: 13px; line-height: 1.45; }}
.footer {{ margin-top: 26px; color: #64748b; font-size: 13px; }}
</style>
<main>
  <h1>TreLLM Demo Portal</h1>
  <p class="lead">One offline launch path for financial-agent reliability: lifecycle traces, execution realism, hard market rules, crisis-scene visuals, and cached model replay metadata.</p>
  <section class="grid">
    {card_html}
  </section>
  <p class="footer">Generated by <code>python scripts/run_launch_demo.py</code>. None of these examples calls DeepSeek, Poe, OpenAI, or live market-data APIs.</p>
</main>
</html>
"""
    path.write_text(html, encoding="utf-8")
    print(f"\nWrote {path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
