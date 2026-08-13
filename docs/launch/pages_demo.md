# GitHub Pages Demo

TreLLM publishes the project landing page and quickstart showcase as a
static GitHub Pages site:

```text
https://weich97.github.io/TreLLM/
```

The Pages workflow lives in `.github/workflows/pages.yml`. On every push to
`main`, it:

1. installs the repository with `python -m pip install -e ".[dev]"`
2. runs `python scripts/run_showcase.py`
3. uploads `outputs/examples/` as the Pages artifact
4. deploys the artifact with GitHub Pages Actions

The deployed demo contains only generated HTML, SVG, GIF, CSV, and JSON
artifacts from the quickstart showcase path. It does not include raw LLM caches,
paper sources, or local credentials.

Useful entry points:

- `index.html`: landing page
- `showcase.html`: demo portal
- `benchmark-v0.2.html`: compact benchmark result page
- `audit_report.html`: replayable audit report
- `agent_autopsy_dashboard.html`: intent/execution autopsy dashboard
- `crisis_snapshot_gallery.html`: diagnostic visual gallery
- `retail_planning_report.html`: planning sandbox report

If the URL does not resolve immediately after a push, check the `Pages Demo`
workflow run in GitHub Actions. First-time Pages deployments can take a few
minutes to become visible.
