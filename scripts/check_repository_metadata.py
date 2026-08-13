from __future__ import annotations

import argparse
import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HOMEPAGE = "https://weich97.github.io/TreLLM/"
BANNED_TOPICS = {"benchmark"}


@dataclass(frozen=True)
class ExpectedRepositoryMetadata:
    description: str
    homepage: str
    topics: set[str]


def expected_metadata_from_launch_readme(path: Path) -> ExpectedRepositoryMetadata:
    text = path.read_text(encoding="utf-8")
    description = _single_line(_fenced_text_after_heading(text, "Suggested Repository Description"))
    topics = {
        line.strip().lower()
        for line in _fenced_text_after_heading(text, "GitHub Topics").splitlines()
        if line.strip()
    }
    return ExpectedRepositoryMetadata(
        description=description,
        homepage=EXPECTED_HOMEPAGE,
        topics=topics,
    )


def validate_repository_metadata(
    payload: dict[str, Any],
    expected: ExpectedRepositoryMetadata,
) -> list[str]:
    failures: list[str] = []
    description = str(payload.get("description") or "").strip()
    homepage = _normalize_url(str(payload.get("homepage") or ""))
    topics = {str(topic).strip().lower() for topic in payload.get("topics") or [] if str(topic).strip()}

    if description != expected.description:
        failures.append(
            "repository description must match docs/launch/README.md Suggested Repository Description"
        )
    if homepage != _normalize_url(expected.homepage):
        failures.append(f"repository homepage must be {expected.homepage}")

    for topic in sorted(expected.topics - topics):
        failures.append(f"repository topic missing: {topic}")
    for topic in sorted(topics & BANNED_TOPICS):
        failures.append(f"repository topic '{topic}' is no longer allowed for TreLLM positioning")

    return failures


def fetch_repository_metadata(repo: str, token: str | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "trellm-metadata-check",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check GitHub repository About metadata against TreLLM launch metadata."
    )
    parser.add_argument("repo", nargs="?", default="weich97/TreLLM-public", help="GitHub repository in owner/name form.")
    parser.add_argument(
        "--launch-readme",
        default=str(ROOT / "docs/launch/README.md"),
        help="Path to the launch metadata README.",
    )
    parser.add_argument(
        "--metadata-json",
        default="",
        help="Optional path to a saved GitHub repository JSON payload for offline checks.",
    )
    args = parser.parse_args(argv)

    expected = expected_metadata_from_launch_readme(Path(args.launch_readme))
    if args.metadata_json:
        payload = json.loads(Path(args.metadata_json).read_text(encoding="utf-8"))
    else:
        payload = fetch_repository_metadata(args.repo, token=os.environ.get("GITHUB_TOKEN"))

    failures = validate_repository_metadata(payload, expected)
    if failures:
        print("Repository metadata check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Repository metadata check passed.")
    return 0


def _fenced_text_after_heading(text: str, heading: str) -> str:
    marker = f"## {heading}"
    heading_start = text.find(marker)
    if heading_start < 0:
        raise ValueError(f"heading not found: {heading}")
    tail = text[heading_start + len(marker) :]
    fence_start = tail.find("```text")
    if fence_start < 0:
        raise ValueError(f"text fence not found after heading: {heading}")
    fence_body = tail[fence_start + len("```text") :]
    fence_end = fence_body.find("```")
    if fence_end < 0:
        raise ValueError(f"text fence is not closed after heading: {heading}")
    return fence_body[:fence_end].strip()


def _single_line(text: str) -> str:
    return " ".join(text.split())


def _normalize_url(url: str) -> str:
    stripped = url.strip()
    if stripped and not stripped.endswith("/"):
        return f"{stripped}/"
    return stripped


if __name__ == "__main__":
    raise SystemExit(main())
