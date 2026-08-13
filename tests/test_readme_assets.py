from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_local_images_exist_and_stay_lightweight():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    paths = set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme))
    paths.update(re.findall(r'<img[^>]+src="([^"]+)"', readme))

    local_paths = sorted(
        path
        for path in paths
        if not path.startswith(("http://", "https://", "#"))
        and not path.startswith("data:")
    )

    assert local_paths
    for relative in local_paths:
        target = ROOT / relative
        assert target.exists(), f"README image is missing: {relative}"
        assert target.stat().st_size > 0, f"README image is empty: {relative}"
        if target.suffix.lower() == ".gif":
            assert target.stat().st_size < 1_500_000, f"README GIF is too large: {relative}"


def test_readme_surfaces_live_trading_safety_contract():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    required_snippets = [
        "## Live Trading Safety Contract",
        "pre-live broker-review request hash",
        "tradearena validate-broker-handoff",
        "tradearena validate-broker-capability",
        "tradearena hash-broker-handoff",
        "tradearena validate-broker-approval",
        "tradearena validate-broker-approval-binding",
        "tradearena validate-broker-response",
        "tradearena validate-operator-runbook",
        "tradearena validate-live-readiness",
        "live_human_approved",
    ]

    for snippet in required_snippets:
        assert snippet in readme


def test_readme_surfaces_trellm_identity_split():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    required_snippets = [
        "# TreLLM",
        "docs/assets/trellm_readme_audit_system_banner_v2.svg",
        "TreLLM is an LLM-driven trading audit and control system.",
        "TradeArena is its public leaderboard for ranking auditable agent runs.",
        "The `tradearena` command and package remain the compatibility surface",
    ]

    for snippet in required_snippets:
        assert snippet in readme


def test_readme_uses_trellm_for_system_level_claims():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    required_snippets = [
        "TreLLM is looking for independent validation reports",
        "TreLLM is best read as an agent-reliability substrate",
        "| Engineering | TreLLM records replayable trajectories",
        "TreLLM is not a replacement for mature backtesting engines.",
        "## Why TreLLM?",
        "| Tool | Best fit | TreLLM / TradeArena relationship |",
        "| TreLLM + TradeArena | Live-ready financial-agent audit, risk control, execution calibration, broker-review handoff, and public leaderboard artifacts |",
        "TreLLM can wrap learned or deterministic policies as agents",
        "The default TradeArena benchmark is therefore **not** suitable as a transaction-cost prediction",
        "Animated TreLLM audit trace showing observation, plan, risk review, execution, and reflection records.",
        "TreLLM runtime architecture: market inputs feed an agent observe-plan loop, a risk gate, an execution simulator, portfolio state, memory feedback, and replayable audit artifacts.",
        "## Validate A Redacted Leaderboard Row",
        "TradeArena can validate redacted leaderboard manifests.",
        "TreLLM does not promise profitable trading",
    ]

    for snippet in required_snippets:
        assert snippet in readme


def test_system_visual_assets_use_trellm_as_system_name():
    asset_expectations = {
        "docs/assets/trellm_readme_audit_system_banner_v2.svg": [
            "TreLLM README system banner",
            "LLM Trading Audit and Control System",
            "TradeArena leaderboard",
        ],
        "docs/assets/readme_pipeline_architecture.svg": [
            "TreLLM runtime architecture",
            "TreLLM Runtime Architecture",
        ],
        "docs/assets/system_architecture.svg": [
            "TreLLM system architecture",
            "TreLLM: Trading Audit and Control Architecture",
            "TradeArena leaderboard metrics",
        ],
        "docs/assets/motivation.svg": [
            "TreLLM motivation",
            "TreLLM framing",
        ],
        "docs/assets/demo_video_thumbnail.svg": [
            "TreLLM 3-minute demo video thumbnail",
            "TreLLM quickstart demo",
        ],
    }

    banned_snippets = [
        "TradeArena Runtime Architecture",
        "TradeArena system architecture",
        "TradeArena: Auditable Agent Benchmark Architecture",
        ">TradeArena<",
        "TradeArena motivation",
        "TradeArena framing",
        "TradeArena 3-minute demo video thumbnail",
        "TradeArena quickstart demo",
    ]

    for relative, required_snippets in asset_expectations.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for snippet in required_snippets:
            assert snippet in text
        for snippet in banned_snippets:
            assert snippet not in text


def test_demo_video_assets_use_trellm_name_and_portable_storyboard():
    required_assets = [
        ROOT / "docs/assets/trellm_3min_demo.mp4",
        ROOT / "docs/assets/trellm_3min_demo_thumbnail.png",
        ROOT / "docs/assets/trellm_3min_demo_storyboard.json",
    ]
    retired_assets = [
        ROOT / "docs/assets/tradearena_3min_demo.mp4",
        ROOT / "docs/assets/tradearena_3min_demo_thumbnail.png",
    ]

    for path in required_assets:
        assert path.exists(), f"TreLLM demo asset is missing: {path.relative_to(ROOT)}"
        assert path.stat().st_size > 0, f"TreLLM demo asset is empty: {path.relative_to(ROOT)}"
    for path in retired_assets:
        assert not path.exists(), f"retired TradeArena demo asset still exists: {path.relative_to(ROOT)}"

    storyboard = json.loads((ROOT / "docs/assets/trellm_3min_demo_storyboard.json").read_text(encoding="utf-8"))
    assert storyboard["output"] == "docs/assets/trellm_3min_demo.mp4"
    assert storyboard["slides"][0]["title"] == "TreLLM in 3 Minutes"
    assert "D:" not in json.dumps(storyboard)
