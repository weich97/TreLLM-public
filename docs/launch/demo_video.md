# Demo Video

The 3-minute demo video shows the recommended first-run path:

1. Run `python scripts/run_showcase.py`.
2. Open `outputs/examples/showcase.html`.
3. Inspect the audit report, execution-realism sweep, extension walkthrough,
   and retail planning sandbox.

Watch it in the browser:

```text
https://weich97.github.io/TreLLM/demo_video.html
```

Regenerate it locally:

```bash
python -m pip install -e ".[dev]"
python scripts/build_demo_video.py
```

The script writes:

```text
outputs/launch/trellm_3min_demo.mp4
outputs/launch/trellm_3min_demo_thumbnail.png
outputs/launch/trellm_3min_demo_storyboard.json
```

Requirements: Pillow from the `dev` extra, a local Chrome/Edge/Chromium
browser for screenshots, and `ffmpeg` for MP4 encoding.
