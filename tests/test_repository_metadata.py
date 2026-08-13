from pathlib import Path

from scripts.check_repository_metadata import (
    BANNED_TOPICS,
    EXPECTED_HOMEPAGE,
    expected_metadata_from_launch_readme,
    validate_repository_metadata,
)

ROOT = Path(__file__).resolve().parents[1]


def test_expected_metadata_is_parsed_from_launch_readme():
    expected = expected_metadata_from_launch_readme(ROOT / "docs/launch/README.md")

    assert expected.description.startswith("TreLLM is an LLM-driven trading audit")
    assert "TradeArena is its public leaderboard" in expected.description
    assert expected.homepage == EXPECTED_HOMEPAGE
    assert {"trellm", "live-readiness", "execution-calibration"} <= expected.topics


def test_repository_metadata_validator_rejects_legacy_about_copy():
    expected = expected_metadata_from_launch_readme(ROOT / "docs/launch/README.md")
    payload = {
        "description": "Auditable benchmark framework for LLM trading agents.",
        "homepage": "https://weich97.github.io/TradeArena/showcase",
        "topics": ["python", "benchmark", "reproducible-research"],
    }

    failures = validate_repository_metadata(payload, expected)

    assert (
        "repository description must match docs/launch/README.md Suggested Repository Description"
        in failures
    )
    assert f"repository homepage must be {EXPECTED_HOMEPAGE}" in failures
    assert "repository topic 'benchmark' is no longer allowed for TreLLM positioning" in failures
    assert BANNED_TOPICS == {"benchmark"}


def test_repository_metadata_validator_accepts_current_metadata_contract():
    expected = expected_metadata_from_launch_readme(ROOT / "docs/launch/README.md")
    payload = {
        "description": expected.description,
        "homepage": expected.homepage,
        "topics": sorted(expected.topics),
    }

    assert validate_repository_metadata(payload, expected) == []
