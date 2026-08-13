from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "outputs/examples"
DEFAULT_WORK_DIR = ROOT / "outputs/launch/demo_video"
DEFAULT_OUTPUT = ROOT / "outputs/launch/trellm_3min_demo.mp4"
WIDTH = 1920
HEIGHT = 1080
FPS = 30


SLIDES = [
    {
        "id": "title",
        "duration": 12,
        "title": "TreLLM in 3 Minutes",
        "subtitle": "Agent reliability, risk-aware AI systems, and intent-to-execution audit for financial decision agents.",
        "bullets": [
            "Every decision becomes a replayable trajectory.",
            "Risk gates, execution friction, memory, and diagnostics are first-class artifacts.",
            "The quickstart showcase uses tracked artifacts and requires no API keys.",
        ],
    },
    {
        "id": "terminal",
        "duration": 20,
        "title": "Start with one command",
        "subtitle": "The showcase builds a local portal from deterministic demos and tracked diagnostic snapshots.",
        "terminal": [
            "$ python scripts/run_showcase.py",
            "TreLLM showcase",
            "A one-command quickstart repo tour for new users, reviewers, and launch posts.",
            "[ok] outputs/examples/index.html",
            "[ok] outputs/examples/audit_report.html",
            "[ok] outputs/examples/extension_walkthrough.svg",
            "[ok] outputs/examples/retail_planning_report.html",
            "[ok] outputs/examples/showcase.html",
        ],
    },
    {
        "id": "showcase",
        "duration": 24,
        "title": "Open the showcase portal",
        "subtitle": "One page links to the artifacts that make an agent inspectable rather than just profitable-looking.",
        "source": EXAMPLE_DIR / "showcase.html",
        "bullets": [
            "Audit report and lifecycle traces",
            "Execution-realism and portfolio diagnostics",
            "Extension demos for contributors",
        ],
    },
    {
        "id": "audit_report",
        "duration": 30,
        "title": "Inspect the audit report",
        "subtitle": "A single decision step keeps the observation, signal, risk edit, order, fill, memory, and reproducibility fingerprint together.",
        "source": EXAMPLE_DIR / "audit_report.html",
        "bullets": [
            "Observe -> plan -> risk gate -> execute -> reflect",
            "Rejected and clipped orders are visible, not hidden",
            "Prompt version, market timestamp, seed, and memory digest are recorded",
        ],
    },
    {
        "id": "execution_realism",
        "duration": 24,
        "title": "Stress execution realism",
        "subtitle": "TreLLM separates intended allocation from what the market simulator can actually fill.",
        "source": EXAMPLE_DIR / "execution_realism_sweep.svg",
        "bullets": [
            "Fees, slippage, latency, liquidity limits",
            "Partial fills, pending orders, and rejections",
            "Idealized backtests can overstate agent quality",
        ],
    },
    {
        "id": "extension_walkthrough",
        "duration": 26,
        "title": "Swap modules without changing the runner",
        "subtitle": "Contributors can add a data adapter, analyst, strategy, risk gate, simulator, planner, or evaluator through narrow interfaces.",
        "source": EXAMPLE_DIR / "extension_walkthrough.svg",
        "bullets": [
            "Custom analyst emits standard Signal objects",
            "Custom risk manager writes structured RiskReport entries",
            "Custom evaluator reads the final Trajectory",
        ],
    },
    {
        "id": "retail_planning",
        "duration": 26,
        "title": "Use the planning sandbox safely",
        "subtitle": "The retail workflow demonstrates suitability gates, target allocation, futures margin checks, and paper-only rebalance instructions.",
        "source": EXAMPLE_DIR / "retail_planning_report.html",
        "bullets": [
            "Educational and research artifact only",
            "No live brokerage calls or automatic execution",
            "Human approval is required for paper rebalance instructions",
        ],
    },
    {
        "id": "outro",
        "duration": 18,
        "title": "What TreLLM is for",
        "subtitle": "Not another black-box trading bot: an audit and control system for financial-agent reliability. TradeArena is the public leaderboard module.",
        "bullets": [
            "Reproduce decisions, not just returns.",
            "Compare agents under the same execution and risk lifecycle.",
            "Extend TreLLM with small, reviewable plugins.",
        ],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a captioned 3-minute TreLLM demo video.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output MP4 path.")
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR), help="Temporary frame/segment directory.")
    parser.add_argument(
        "--refresh-showcase",
        action="store_true",
        help="Run the full showcase before capturing screenshots. The default reuses existing artifacts.",
    )
    parser.add_argument("--keep-work-dir", action="store_true", help="Keep generated slides and segment files.")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    _run_showcase(refresh=args.refresh_showcase)
    browser = _find_browser()
    ffmpeg = _find_ffmpeg()

    screenshot_dir = work_dir / "screenshots"
    slide_dir = work_dir / "slides"
    segment_dir = work_dir / "segments"
    for path in (screenshot_dir, slide_dir, segment_dir):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    screenshots = _capture_sources(browser, screenshot_dir)
    slides = _render_slides(screenshots, slide_dir)
    video_only = work_dir / "trellm_3min_demo_video_only.mp4"
    _render_video(ffmpeg, slides, segment_dir, video_only)
    _add_silent_audio(ffmpeg, video_only, output)

    thumbnail = output.with_name(output.stem + "_thumbnail.png")
    shutil.copyfile(slides[0]["path"], thumbnail)
    storyboard = output.with_name(output.stem + "_storyboard.json")
    storyboard.write_text(
        json.dumps(
            {
                "output": _artifact_path(output),
                "duration_seconds": sum(int(slide["duration"]) for slide in SLIDES),
                "fps": FPS,
                "slides": [
                    {
                        "id": slide["id"],
                        "duration": slide["duration"],
                        "title": slide["title"],
                        "source": _artifact_path(slide.get("source", "")),
                    }
                    for slide in SLIDES
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if not args.keep_work_dir:
        shutil.rmtree(segment_dir, ignore_errors=True)

    print(f"Wrote {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}")
    print(f"Wrote {thumbnail.relative_to(ROOT) if thumbnail.is_relative_to(ROOT) else thumbnail}")
    print(f"Wrote {storyboard.relative_to(ROOT) if storyboard.is_relative_to(ROOT) else storyboard}")
    return 0


def _artifact_path(path: object) -> str:
    if not path:
        return ""
    artifact = Path(path)
    try:
        return artifact.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _run_showcase(refresh: bool) -> None:
    command = [sys.executable, "scripts/run_showcase.py"]
    if not refresh:
        command.append("--reuse-existing")
    subprocess.run(command, cwd=ROOT, check=True)


def _find_browser() -> Path:
    candidates = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("msedge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError("Could not find Chrome, Chromium, or Edge for screenshot capture.")


def _find_ffmpeg() -> Path:
    candidates = [
        shutil.which("ffmpeg"),
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\Tecplot\Tecplot 360 EX 2022 R1\bin\ffmpeg.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError("Could not find ffmpeg. Install ffmpeg or add it to PATH.")


def _capture_sources(browser: Path, screenshot_dir: Path) -> dict[str, Path]:
    screenshots: dict[str, Path] = {}
    for slide in SLIDES:
        source = slide.get("source")
        if not source:
            continue
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        screenshot = screenshot_dir / f"{slide['id']}.png"
        _capture_screenshot(browser, source_path, screenshot)
        screenshots[slide["id"]] = screenshot
    return screenshots


def _capture_screenshot(browser: Path, source: Path, output: Path) -> None:
    url = source.resolve().as_uri()
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--no-sandbox",
        "--window-size=1600,960",
        f"--screenshot={output}",
        url,
    ]
    try:
        subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        fallback = command.copy()
        fallback[1] = "--headless"
        subprocess.run(fallback, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _render_slides(screenshots: dict[str, Path], slide_dir: Path) -> list[dict[str, object]]:
    fonts = _fonts()
    rendered = []
    for idx, slide in enumerate(SLIDES):
        image = _base_canvas()
        draw = ImageDraw.Draw(image)
        _draw_header(draw, fonts, idx + 1, len(SLIDES), slide["title"], slide["subtitle"])

        if slide["id"] == "terminal":
            _draw_terminal(image, slide["terminal"], fonts)
        elif slide["id"] in screenshots:
            _draw_screenshot_panel(image, screenshots[slide["id"]], slide["bullets"], fonts)
        else:
            _draw_big_bullets(image, slide["bullets"], fonts)

        _draw_footer(draw, fonts)
        slide_path = slide_dir / f"{idx:02d}_{slide['id']}.png"
        image.save(slide_path)
        rendered.append({"path": slide_path, "duration": int(slide["duration"])})
    return rendered


def _base_canvas() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f8fafc")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 150), fill="#0f172a")
    draw.rectangle((0, 150, WIDTH, 156), fill="#14b8a6")
    for i in range(12):
        x = 1260 + i * 70
        y = 28 + int(18 * math.sin(i))
        draw.ellipse((x, y, x + 10, y + 10), fill="#334155")
    return image


def _draw_header(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
    current: int,
    total: int,
    title: str,
    subtitle: str,
) -> None:
    draw.text((72, 36), "TreLLM", fill="#ccfbf1", font=fonts["brand"])
    draw.text((72, 82), title, fill="#ffffff", font=fonts["title"])
    draw.text((72, 128), subtitle, fill="#cbd5e1", font=fonts["subtitle"])
    draw.rounded_rectangle((1695, 42, 1848, 92), radius=24, outline="#475569", width=2, fill="#111827")
    draw.text((1734, 55), f"{current}/{total}", fill="#e2e8f0", font=fonts["pill"])


def _draw_footer(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]) -> None:
    draw.text(
        (72, HEIGHT - 58),
        "Quickstart showcase: no API keys or live provider calls. Advanced model/data APIs are optional.",
        fill="#64748b",
        font=fonts["small"],
    )


def _draw_terminal(
    image: Image.Image,
    lines: list[str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    draw = ImageDraw.Draw(image)
    panel = (120, 245, 1800, 850)
    draw.rounded_rectangle(panel, radius=18, fill="#020617")
    draw.ellipse((154, 277, 176, 299), fill="#ef4444")
    draw.ellipse((190, 277, 212, 299), fill="#f59e0b")
    draw.ellipse((226, 277, 248, 299), fill="#22c55e")
    y = 340
    for line in lines:
        color = "#93c5fd" if line.startswith("$") else "#d1fae5" if line.startswith("[ok]") else "#e2e8f0"
        draw.text((160, y), line, fill=color, font=fonts["mono"])
        y += 56


def _draw_screenshot_panel(
    image: Image.Image,
    screenshot_path: Path,
    bullets: list[str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    draw = ImageDraw.Draw(image)
    screen_area = (70, 215, 1288, 865)
    note_area = (1326, 238, 1848, 820)

    screenshot = Image.open(screenshot_path).convert("RGB")
    fitted = ImageOps.contain(screenshot, (screen_area[2] - screen_area[0], screen_area[3] - screen_area[1]))
    shadow = (screen_area[0] + 12, screen_area[1] + 16, screen_area[2] + 12, screen_area[3] + 16)
    draw.rounded_rectangle(shadow, radius=18, fill="#cbd5e1")
    draw.rounded_rectangle(screen_area, radius=18, fill="#ffffff", outline="#cbd5e1", width=2)
    x = screen_area[0] + ((screen_area[2] - screen_area[0]) - fitted.width) // 2
    y = screen_area[1] + ((screen_area[3] - screen_area[1]) - fitted.height) // 2
    image.paste(fitted, (x, y))

    draw.rounded_rectangle(note_area, radius=18, fill="#ffffff", outline="#d8e2ed", width=2)
    draw.text((note_area[0] + 28, note_area[1] + 30), "What to notice", fill="#0f172a", font=fonts["section"])
    y = note_area[1] + 92
    for bullet in bullets:
        draw.ellipse((note_area[0] + 32, y + 9, note_area[0] + 44, y + 21), fill="#14b8a6")
        y = _draw_wrapped(draw, bullet, (note_area[0] + 60, y), 430, fonts["body"], "#334155") + 22


def _draw_big_bullets(
    image: Image.Image,
    bullets: list[str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    draw = ImageDraw.Draw(image)
    panel = (210, 250, 1710, 820)
    draw.rounded_rectangle(panel, radius=24, fill="#ffffff", outline="#d8e2ed", width=2)
    y = 330
    for bullet in bullets:
        draw.ellipse((292, y + 13, 316, y + 37), fill="#0f766e")
        y = _draw_wrapped(draw, bullet, (360, y), 1190, fonts["big_body"], "#0f172a") + 44


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    max_width: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    line_height = int(font.size * 1.34) if hasattr(font, "size") else 28
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += line_height
    return y


def _fonts() -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    def load(names: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for name in names:
            path = Path(name)
            if path.exists():
                return ImageFont.truetype(str(path), size)
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()

    return {
        "brand": load([r"C:\Windows\Fonts\segoeuib.ttf"], 28),
        "title": load([r"C:\Windows\Fonts\segoeuib.ttf"], 38),
        "subtitle": load([r"C:\Windows\Fonts\segoeui.ttf"], 22),
        "pill": load([r"C:\Windows\Fonts\segoeuib.ttf"], 24),
        "section": load([r"C:\Windows\Fonts\segoeuib.ttf"], 30),
        "body": load([r"C:\Windows\Fonts\segoeui.ttf"], 25),
        "big_body": load([r"C:\Windows\Fonts\segoeui.ttf"], 38),
        "check": load([r"C:\Windows\Fonts\segoeuib.ttf"], 26),
        "mono": load([r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\consolab.ttf"], 30),
        "small": load([r"C:\Windows\Fonts\segoeui.ttf"], 20),
    }


def _render_video(ffmpeg: Path, slides: list[dict[str, object]], segment_dir: Path, output: Path) -> None:
    segment_paths = []
    for idx, slide in enumerate(slides):
        segment = segment_dir / f"segment_{idx:02d}.mp4"
        command = [
            str(ffmpeg),
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-t",
            str(slide["duration"]),
            "-i",
            str(slide["path"]),
            "-vf",
            f"scale={WIDTH}:{HEIGHT}:flags=lanczos,fps={FPS},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            str(segment),
        ]
        subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        segment_paths.append(segment)

    concat = segment_dir / "segments.txt"
    concat.write_text("".join(f"file '{path.as_posix()}'\n" for path in segment_paths), encoding="utf-8")
    subprocess.run(
        [str(ffmpeg), "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _add_silent_audio(ffmpeg: Path, video_only: Path, output: Path) -> None:
    total = sum(int(slide["duration"]) for slide in SLIDES)
    command = [
        str(ffmpeg),
        "-y",
        "-i",
        str(video_only),
        "-f",
        "lavfi",
        "-t",
        str(total),
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    raise SystemExit(main())
