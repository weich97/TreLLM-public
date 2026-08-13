from __future__ import annotations

import argparse
import math
import shutil
from pathlib import Path

from tradearena.core.serialization import write_json

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - exercised only when optional dev deps are missing.
    raise SystemExit(
        "The visual tour demo requires Pillow. Install it with: python -m pip install -e \".[dev]\""
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs/examples"
README_ASSET_DIR = ROOT / "docs/assets"

WIDTH = 900
HEIGHT = 430

BG = (248, 250, 252)
INK = (15, 23, 42)
MUTED = (100, 116, 139)
BLUE = (37, 99, 235)
CYAN = (2, 132, 199)
GREEN = (5, 150, 105)
AMBER = (217, 119, 6)
RED = (220, 38, 38)
PURPLE = (124, 58, 237)
SLATE = (51, 65, 85)
WHITE = (255, 255, 255)
LINE = (203, 213, 225)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate animated offline TreLLM visual-tour artifacts.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--sync-readme-assets",
        action="store_true",
        help="Also copy generated GIFs into docs/assets/readme_*.gif for maintainers.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "audit_lifecycle": output_dir / "visual_tour_audit_lifecycle.gif",
        "execution_realism": output_dir / "visual_tour_execution_realism.gif",
        "diagnostics_loop": output_dir / "visual_tour_diagnostics_loop.gif",
    }
    _write_audit_lifecycle(artifacts["audit_lifecycle"])
    _write_execution_realism(artifacts["execution_realism"])
    _write_diagnostics_loop(artifacts["diagnostics_loop"])
    index = output_dir / "visual_tour_index.html"
    _write_index(index, artifacts)

    summary = {
        "api_free": True,
        "requires_live_market_data": False,
        "concepts": [
            "observe-plan-risk-act-reflect audit lifecycle",
            "execution realism under fees, slippage, latency, liquidity, partial fills, and rejections",
            "representation, feedback, and concentration diagnostics beyond headline return",
        ],
        "artifacts": {
            name: {
                "path": _relative(path),
                "bytes": path.stat().st_size,
            }
            for name, path in artifacts.items()
        }
        | {"html_index": {"path": _relative(index), "bytes": index.stat().st_size}},
    }
    write_json(output_dir / "visual_tour_summary.json", summary)

    if args.sync_readme_assets:
        _sync_readme_assets(artifacts)

    print("Visual tour demo")
    for name, path in artifacts.items():
        print(f"  {name}: {_relative(path)} ({path.stat().st_size} bytes)")
    print(f"  index: {_relative(index)}")
    print(f"\nWrote {_relative(output_dir / 'visual_tour_summary.json')}")
    return 0


def _write_audit_lifecycle(path: Path) -> None:
    stages = [
        ("Observe", "market, news, portfolio"),
        ("Plan", "signals + intended weights"),
        ("Risk gate", "clip, block, approve"),
        ("Execute", "latency, fills, rejects"),
        ("Reflect", "memory + fingerprint"),
    ]
    frames: list[Image.Image] = []
    for i in range(36):
        image = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(image)
        _text(draw, (36, 32), "Replayable audit lifecycle", INK, _font(28, bold=True))
        _text(
            draw,
            (38, 66),
            "Every decision is reconstructed from observe -> plan -> risk -> execute -> reflect evidence.",
            MUTED,
        )
        active = (i // 6) % len(stages)
        progress = (i % 6) / 5
        centers: list[tuple[float, float, tuple[int, int, int]]] = []
        for idx, (name, desc) in enumerate(stages):
            x = 46 + idx * 170
            y = 130
            color = [BLUE, PURPLE, AMBER, CYAN, GREEN][idx]
            fill = _blend(WHITE, color, 0.18 if idx == active else (0.08 if idx < active else 0.0))
            outline = color if idx == active else (_blend(LINE, color, 0.4) if idx < active else LINE)
            _rounded(draw, (x, y, x + 145, y + 92), 14, fill, outline, 3 if idx == active else 1)
            _text(draw, (x + 18, y + 24), name, color if idx <= active else INK, _font(17, bold=True))
            _text(draw, (x + 18, y + 52), desc, MUTED, _font(12))
            centers.append((x + 72.5, y + 46, color))

        for idx in range(len(centers) - 1):
            x1, y1, color = centers[idx]
            x2, y2, _ = centers[idx + 1]
            _arrow(draw, x1 + 72, y1, x2 - 72, y2, _blend(LINE, color, 0.8 if idx < active else 0.25), 3)

        if active < len(centers) - 1:
            sx, sy, color = centers[active]
            ex, ey, _ = centers[active + 1]
            px = _lerp(sx + 72, ex - 72, progress)
            py = _lerp(sy, ey, progress)
        else:
            sx, sy, color = centers[active]
            px = sx + math.sin(progress * math.pi * 2) * 28
            py = sy + 70
        _rounded(draw, (px - 34, py - 16, px + 34, py + 16), 8, _blend(WHITE, color, 0.2), color, 2)
        _text(draw, (px, py + 4), "trace", color, _font(12), "mm")

        _rounded(draw, (58, 286, 842, 386), 12, WHITE, LINE, 1)
        _text(draw, (82, 316), "Audit record", INK, _font(17, bold=True))
        chips = [("risk_report", AMBER), ("orders", CYAN), ("fills", GREEN), ("memory_digest", PURPLE), ("seed", BLUE)]
        for idx, (label, color) in enumerate(chips):
            x = 220 + idx * 118
            _rounded(draw, (x, 306, x + 100, 338), 8, _blend(WHITE, color, 0.28 if idx <= active else 0.06), _blend(LINE, color, 0.65), 1)
            _text(draw, (x + 50, 326), label, color if idx <= active else MUTED, _font(12), "mm")
        _text(draw, (82, 356), "JSON trajectory + HTML report + reproducibility metadata", MUTED)
        frames.append(image)
    _save_gif(frames, path)


def _write_execution_realism(path: Path) -> None:
    scenarios = [
        ("Ideal fills", 1.00, 0.05, 0.02, BLUE),
        ("Realistic", 0.94, 0.45, 0.18, GREEN),
        ("High spread", 0.92, 0.88, 0.20, AMBER),
        ("Low liquidity", 0.82, 0.68, 0.34, AMBER),
        ("High latency", 0.52, 0.82, 0.70, RED),
    ]
    frames: list[Image.Image] = []
    for i in range(50):
        image = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(image)
        _text(draw, (36, 32), "Execution-realistic simulator", INK, _font(28, bold=True))
        _text(draw, (38, 66), "The same target intent is filtered through fees, spread, slippage, latency, liquidity, partial fills, and rejections.", MUTED)
        t = (math.sin(i / 49 * math.pi * 2 - math.pi / 2) + 1) / 2
        active = (i // 10) % len(scenarios)

        _rounded(draw, (48, 122, 245, 335), 14, WHITE, LINE, 1)
        _text(draw, (72, 154), "Agent intent", INK, _font(17, bold=True))
        for idx, (symbol, weight) in enumerate([("AAPL", 0.24), ("NVDA", 0.28), ("JPM", 0.18), ("XOM", 0.12)]):
            y = 190 + idx * 30
            _text(draw, (72, y), symbol, SLATE, _font(12))
            draw.rectangle((124, y - 10, 124 + int(80 * weight / 0.3), y + 5), fill=BLUE)
            _text(draw, (214, y), f"{weight:.0%}", MUTED, _font(12), "ra")

        _arrow(draw, 260, 226, 330, 226, SLATE, 3)
        _rounded(draw, (338, 122, 558, 335), 14, (255, 251, 235), AMBER, 2)
        _text(draw, (365, 154), "Order simulator", AMBER, _font(17, bold=True))
        for idx, label in enumerate(["commission", "bid-ask spread", "market impact", "latency queue", "participation cap"]):
            alpha = 0.12 + 0.18 * ((i + idx * 3) % 18) / 18
            _rounded(draw, (366, 186 + idx * 26, 526, 206 + idx * 26), 6, _blend(WHITE, AMBER, alpha), _blend(LINE, AMBER, 0.5), 1)
            _text(draw, (382, 202 + idx * 26), label, SLATE, _font(12))

        _arrow(draw, 572, 226, 640, 226, SLATE, 3)
        _rounded(draw, (650, 108, 850, 360), 14, WHITE, LINE, 1)
        name, fill_rate, slippage, rejection, color = scenarios[active]
        _text(draw, (680, 140), name, color, _font(17, bold=True))
        metrics = [("fill rate", fill_rate, GREEN), ("slippage", slippage, AMBER), ("rejections", rejection, RED)]
        for idx, (label, value, metric_color) in enumerate(metrics):
            y = 185 + idx * 52
            shown = _lerp(0.08, value, t)
            _text(draw, (680, y), label, SLATE, _font(12))
            draw.rounded_rectangle((680, y + 10, 820, y + 26), radius=8, fill=(226, 232, 240))
            draw.rounded_rectangle((680, y + 10, 680 + int(140 * shown), y + 26), radius=8, fill=metric_color)
            _text(draw, (824, y + 24), f"{value:.0%}", metric_color, _font(12))
        _text(draw, (50, 390), "Result: realistic execution can change both measured performance and observable agent behavior.", MUTED)
        frames.append(image)
    _save_gif(frames, path)


def _write_diagnostics_loop(path: Path) -> None:
    frames: list[Image.Image] = []
    for i in range(48):
        image = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(image)
        _text(draw, (36, 32), "Diagnostics beyond return", INK, _font(28, bold=True))
        _text(draw, (38, 66), "TreLLM turns trajectories into mechanism probes: representation drift, risk feedback, and portfolio concentration.", MUTED)
        phase = (i // 16) % 3
        phase_t = (i % 16) / 15
        for panel, (title, color) in enumerate([("Representation rank", BLUE), ("Risk feedback", GREEN), ("51-stock concentration", PURPLE)]):
            x = 48 + panel * 284
            y = 118
            active = panel == phase
            _rounded(draw, (x, y, x + 245, y + 235), 14, _blend(WHITE, color, 0.08 if active else 0.0), color if active else LINE, 2 if active else 1)
            _text(draw, (x + 22, y + 32), title, color if active else INK, _font(17, bold=True))
            if panel == 0:
                _draw_contracting_cloud(draw, x + 122, y + 130, phase_t if active else 0.3)
                _text(draw, (x + 24, y + 206), "effective rank contracts", MUTED, _font(12))
            elif panel == 1:
                _draw_feedback_curve(draw, x, y, phase_t if active else 0.4)
                _text(draw, (x + 24, y + 206), "truthful audit can calibrate", MUTED, _font(12))
            else:
                _draw_concentration_bars(draw, x, y, phase_t if active else 0.0)
                _text(draw, (x + 24, y + 206), "risk gate exposes pressure", MUTED, _font(12))

        title, body, color = [
            ("Pre-failure geometry", "detect drift before the final drawdown trough", BLUE),
            ("Feedback alignment", "compare true, hidden, placebo, and false-audit signals", GREEN),
            ("Portfolio reasoning", "measure concentration and covariance blind spots", PURPLE),
        ][phase]
        _rounded(draw, (170, 372, 730, 410), 12, _blend(WHITE, color, 0.12), color, 2)
        _text(draw, (190, 396), f"{title}:", color, _font(17, bold=True))
        _text(draw, (355, 396), body, SLATE)
        frames.append(image)
    _save_gif(frames, path)


def _draw_contracting_cloud(draw: ImageDraw.ImageDraw, cx: float, cy: float, amount: float) -> None:
    for idx in range(34):
        angle = idx * 2.399
        radius = (70 if idx % 2 else 52) * (1 - 0.55 * amount) + (idx % 5) * 2
        px = cx + math.cos(angle) * radius
        py = cy + math.sin(angle) * radius * 0.55
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=BLUE)


def _draw_feedback_curve(draw: ImageDraw.ImageDraw, x: float, y: float, amount: float) -> None:
    points = []
    for idx in range(8):
        px = x + 34 + idx * 24
        value = 0.25 + idx * 0.07 + 0.2 * amount
        py = y + 190 - value * 120
        points.append((px, py))
    draw.line(points, fill=GREEN, width=4)
    for px, py in points:
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=GREEN)


def _draw_concentration_bars(draw: ImageDraw.ImageDraw, x: float, y: float, amount: float) -> None:
    for idx, (label, value) in enumerate(zip(["BH", "MVO", "GPT", "Gem"], [0.019, 0.023, 0.045, 0.035], strict=True)):
        bx = x + 34 + idx * 45
        height = value / 0.055 * 112 * (1 + 0.1 * math.sin(amount * math.pi * 2 + idx))
        draw.rectangle((bx, y + 178 - height, bx + 28, y + 178), fill=PURPLE if idx >= 2 else SLATE)
        _text(draw, (bx + 14, y + 195), label, MUTED, _font(12), "mm")
    draw.line((x + 28, y + 138, x + 210, y + 138), fill=RED, width=2)


def _write_index(path: Path, artifacts: dict[str, Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cards_data = [
        (
            "Audit lifecycle",
            "Animated decision trace moving through observe, plan, risk gate, execute, and reflect stages.",
            artifacts["audit_lifecycle"],
        ),
        (
            "Execution realism",
            "Animated execution comparison using fill-rate, spread/slippage, and rejection bars.",
            artifacts["execution_realism"],
        ),
        (
            "Diagnostics beyond return",
            "Animated diagnostics dashboard for representation rank, risk feedback, and concentration.",
            artifacts["diagnostics_loop"],
        ),
    ]
    cards = "\n".join(
        f'<figure><img src="{artifact.name}" alt="{alt}"><figcaption>{title}</figcaption></figure>'
        for title, alt, artifact in cards_data
    )
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>TreLLM Visual Tour: Audit, Execution, Diagnostics</title>
<style>
body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 36px 28px 48px; }}
h1 {{ margin: 0 0 8px; font-size: 34px; letter-spacing: 0; }}
.lead {{ margin: 0 0 22px; max-width: 820px; color: #475569; line-height: 1.55; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
figure {{ margin: 0; border: 1px solid #d8e2ed; border-radius: 8px; background: white; padding: 12px; }}
img {{ width: 100%; display: block; border-radius: 6px; }}
figcaption {{ margin-top: 8px; color: #334155; font-weight: 800; font-size: 14px; }}
code {{ background: #eef2f7; padding: 2px 5px; border-radius: 5px; }}
</style>
<main>
  <h1>TreLLM Visual Tour: Audit, Execution, Diagnostics</h1>
  <p class="lead">Three offline-generated animations turn TreLLM's hands-on examples into an inspectable loop. The image alt text summarizes each animation for readers who cannot rely on motion.</p>
  <section class="grid">{cards}</section>
  <p class="lead" style="margin-top:22px">Generated by <code>python examples/visual_tour_demo.py</code>.</p>
</main>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _sync_readme_assets(artifacts: dict[str, Path]) -> None:
    README_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {
        "audit_lifecycle": "readme_audit_lifecycle.gif",
        "execution_realism": "readme_execution_realism.gif",
        "diagnostics_loop": "readme_diagnostics_loop.gif",
    }
    for key, filename in mapping.items():
        shutil.copy2(artifacts[key], README_ASSET_DIR / filename)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [r"C:\Windows\Fonts\seguisb.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
        if bold
        else [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _rounded(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float, float, float],
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    width: int,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    value: str,
    fill: tuple[int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
    anchor: str | None = None,
) -> None:
    draw.text(xy, value, fill=fill, font=font or _font(14), anchor=anchor)


def _arrow(
    draw: ImageDraw.ImageDraw,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    fill: tuple[int, int, int],
    width: int,
) -> None:
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 10
    points = [
        (x2, y2),
        (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45)),
        (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45)),
    ]
    draw.polygon(points, fill=fill)


def _save_gif(frames: list[Image.Image], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:], optimize=True, duration=85, loop=0, disposal=2)


def _blend(left: tuple[int, int, int], right: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(int(_lerp(a, b, amount)) for a, b in zip(left, right, strict=True))


def _lerp(left: float, right: float, amount: float) -> float:
    return left + (right - left) * amount


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
