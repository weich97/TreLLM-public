from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Any

from tradearena.core.serialization import write_json

OUTPUT_DIR = Path("outputs/examples")
RESULTS_DIR = Path("docs/results/crisis")
ASSETS_DIR = Path("docs/assets/crisis")


def main() -> int:
    rows = _read_rows(RESULTS_DIR / "crisis_summary.csv")
    if not rows:
        raise FileNotFoundError("Missing crisis summary snapshot. Run scripts/run_crisis_scene_experiments.py --collect-existing first.")
    summary = _summary(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _copy_assets()
    write_json(OUTPUT_DIR / "crisis_snapshot_summary.json", summary)
    _write_html(OUTPUT_DIR / "crisis_snapshot_gallery.html", rows, summary)

    print("Crisis snapshot demo")
    print(f"  scenes={', '.join(summary['scenes'])}")
    print(f"  models={', '.join(summary['models'])}")
    print(f"  rows={summary['rows']} best_calibration={summary['best_calibration']['case']}")
    print(f"\nWrote {OUTPUT_DIR / 'crisis_snapshot_summary.json'}")
    print(f"Wrote {OUTPUT_DIR / 'crisis_snapshot_gallery.html'}")
    return 0


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    best_return = max(rows, key=lambda row: float(row["total_return"]))
    best_calibration = max(rows, key=lambda row: float(row["mean_calibration_score"]))
    return {
        "rows": len(rows),
        "scenes": sorted({row["scene"] for row in rows}),
        "models": sorted({row["model"] for row in rows}),
        "feedback_modes": sorted({row["feedback"] for row in rows}),
        "best_return": _compact_case(best_return),
        "best_calibration": _compact_case(best_calibration),
    }


def _compact_case(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case": row["case"],
        "scene": row["scene"],
        "model": row["model"],
        "feedback": row["feedback"],
        "total_return": float(row["total_return"]),
        "max_drawdown": float(row["max_drawdown"]),
        "mean_calibration_score": float(row["mean_calibration_score"]),
    }


def _write_html(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    cards = "\n".join(
        f'<figure><img src="assets/crisis/{name}" alt="{name}"><figcaption>{name}</figcaption></figure>'
        for name in [
            "crisis_representation_trajectory.svg",
            "crisis_correlation_intent_heatmap.svg",
            "crisis_feedback_learning_curves.svg",
            "crisis_exposure_waterfall.svg",
            "crisis_microstructure_waterfall.svg",
        ]
        if (ASSETS_DIR / name).exists()
    )
    top_rows = sorted(rows, key=lambda row: float(row["mean_calibration_score"]), reverse=True)[:8]
    table_rows = "\n".join(
        "<tr>"
        f"<td>{row['scene']}</td><td>{row['model']}</td><td>{row['feedback']}</td>"
        f"<td>{float(row['total_return']):.3f}</td><td>{float(row['max_drawdown']):.3f}</td>"
        f"<td>{float(row['mean_calibration_score']):.3f}</td>"
        "</tr>"
        for row in top_rows
    )
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>TreLLM Crisis Snapshot Gallery</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 34px; }}
h1 {{ margin: 0 0 8px; font-size: 30px; }}
p {{ color: #475569; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 18px; }}
figure {{ margin: 0; background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 14px; }}
img {{ width: 100%; height: auto; display: block; }}
figcaption {{ margin-top: 8px; color: #64748b; font-size: 13px; }}
table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9e2ec; }}
th, td {{ padding: 9px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 13px; }}
th {{ background: #eef2f7; }}
</style>
<main>
  <h1>TreLLM Crisis Snapshot Gallery</h1>
  <p>{summary['rows']} crisis rows across {len(summary['models'])} models and {len(summary['feedback_modes'])} feedback modes. This page makes no live provider calls and reads tracked table/image snapshots.</p>
  <section class="grid">{cards}</section>
  <h2>Top Calibration Rows</h2>
  <table>
    <tr><th>Scene</th><th>Model</th><th>Feedback</th><th>Return</th><th>Max DD</th><th>Calibration</th></tr>
    {table_rows}
  </table>
</main>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _copy_assets() -> None:
    target = OUTPUT_DIR / "assets/crisis"
    target.mkdir(parents=True, exist_ok=True)
    for source in ASSETS_DIR.glob("*.svg"):
        shutil.copy2(source, target / source.name)


if __name__ == "__main__":
    raise SystemExit(main())
