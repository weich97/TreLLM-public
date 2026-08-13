from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


DEMOS = [
    (
        "Execution Realism",
        "Same agent under ideal fills, realistic fills, high spread, low liquidity, and high latency.",
        "examples/execution_realism_sweep_demo.py",
        "execution_realism_sweep.svg",
    ),
    (
        "Portfolio Baselines",
        "Passive, signal-weighted, and rolling Markowitz/MVO strategies under the same simulator.",
        "examples/portfolio_markowitz_demo.py",
        "portfolio_markowitz.svg",
    ),
    (
        "Representation Signatures",
        "Hash, LSA, dense-embedding, and lexical-control diagnostics from tracked tables.",
        "examples/representation_signature_demo.py",
        "representation_signature.svg",
    ),
    (
        "Custom Plugin",
        "Drop in a local analyst class while reusing the existing strategy, risk, execution, memory, and evaluator stack.",
        "examples/custom_plugin_demo.py",
        "custom_plugin.svg",
    ),
]


def main() -> int:
    print("TreLLM experiment-design demo suite")
    print("===================================")
    print("Offline-friendly demos aligned with core TreLLM experiment axes.")
    for idx, (title, _, script, _) in enumerate(DEMOS, start=1):
        print(f"\n{idx}/{len(DEMOS)} {title}", flush=True)
        print("-" * (len(title) + 4), flush=True)
        subprocess.run([sys.executable, script], cwd=ROOT, check=True)
    index_path = ROOT / "outputs/examples/experiment_design_index.html"
    legacy_index_path = ROOT / "outputs/examples/paper_design_index.html"
    _write_index(index_path)
    if legacy_index_path != index_path:
        legacy_index_path.write_text(index_path.read_text(encoding="utf-8"), encoding="utf-8")
    print("\nDemo artifacts")
    print("--------------")
    for _, _, _, artifact in DEMOS:
        path = ROOT / "outputs/examples" / artifact
        print(f"[{'ok' if path.exists() else 'missing'}] outputs/examples/{artifact}")
    print("[ok] outputs/examples/experiment_design_index.html")
    return 0


def _write_index(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(
        f'<a class="card" href="{artifact}"><span>{title}</span><p>{body}</p></a>'
        for title, body, _, artifact in DEMOS
    )
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>TreLLM Experiment-Design Demos</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
main {{ max-width: 1040px; margin: 0 auto; padding: 42px 28px; }}
h1 {{ margin: 0 0 8px; font-size: 32px; letter-spacing: 0; }}
.lead {{ margin: 0 0 24px; max-width: 780px; color: #475569; line-height: 1.55; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 14px; }}
.card {{ display: block; min-height: 124px; padding: 18px; border: 1px solid #d8e2ed; border-radius: 8px; background: white; color: inherit; text-decoration: none; }}
.card:hover {{ border-color: #2563eb; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.10); transform: translateY(-1px); }}
.card span {{ display: block; font-weight: 800; font-size: 16px; margin-bottom: 8px; }}
.card p {{ margin: 0; color: #64748b; font-size: 13px; line-height: 1.45; }}
</style>
<main>
  <h1>TreLLM Experiment-Design Demos</h1>
  <p class="lead">These offline-friendly hands-on examples exercise four TreLLM research axes: execution realism, quant baselines, representation diagnostics, and modular extensibility.</p>
  <section class="grid">
    {cards}
  </section>
</main>
</html>
"""
    path.write_text(html, encoding="utf-8")
    print(f"\nWrote {path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
