from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
REQUIRED_HEADINGS = (
    "## Purpose",
    "## When To Use",
    "## Do Not Use",
    "## Required Inputs",
    "## Safety Boundary",
    "## Workflow",
    "## Output Contract",
    "## Validation Commands",
)
REQUIRED_BOUNDARY_TERMS = (
    "claim",
    "evidence",
    "reproduc",
    "Do not",
)
FORBIDDEN_SKILL_NAME_PARTS = (
    "alpha",
    "buy-sell",
    "live-trading",
    "profit",
    "stock-trader",
    "trader",
)
UNSAFE_DIRECTIVE_TERMS = (
    "live order",
    "broker password",
    "api key",
    "private holdings",
    "guaranteed profit",
    "buy recommendation",
    "sell recommendation",
)
NEGATION_MARKERS = (
    "do not",
    "never",
    "must not",
    "should not",
    "not use",
    "without",
    "avoid",
    "not request",
    "not expose",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate TreLLM agent skill contracts.")
    parser.add_argument("skills_dir_positional", nargs="?", help="Directory containing skill folders.")
    parser.add_argument("--skills-dir", dest="skills_dir_option", help="Directory containing skill folders.")
    args = parser.parse_args(argv)

    skills_dir = Path(args.skills_dir_option or args.skills_dir_positional or SKILLS_DIR)
    failures = validate_skills(skills_dir)
    if failures:
        print("Skill contract validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Skill contract validation passed.")
    return 0


def validate_skills(skills_dir: Path) -> list[str]:
    failures: list[str] = []
    if not skills_dir.exists():
        return [f"missing skills directory: {skills_dir}"]

    skill_dirs = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    if not skill_dirs:
        failures.append("no skill directories found")

    readme = skills_dir / "README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    if not readme_text:
        failures.append("missing skills/README.md")

    for skill_dir in skill_dirs:
        failures.extend(_validate_skill_dir(skill_dir, readme_text))
    return failures


def _validate_skill_dir(skill_dir: Path, readme_text: str) -> list[str]:
    failures: list[str] = []
    if any(part in skill_dir.name for part in FORBIDDEN_SKILL_NAME_PARTS):
        failures.append(f"{skill_dir.name}: forbidden trading-skill naming")

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return [f"{skill_dir.name}: missing SKILL.md"]
    text = skill_file.read_text(encoding="utf-8")

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            failures.append(f"{skill_dir.name}: missing heading {heading}")
    if skill_dir.name != "skill_template" and "## Do Not Use This Skill For" not in text:
        failures.append(f"{skill_dir.name}: missing Do Not Use section")
    for term in REQUIRED_BOUNDARY_TERMS:
        if term not in text:
            failures.append(f"{skill_dir.name}: missing boundary term {term!r}")
    if "```bash" not in text:
        failures.append(f"{skill_dir.name}: validation commands must use a bash code fence")
    if "buy/sell" in text.lower() or "profit-maximization" in text.lower():
        failures.append(f"{skill_dir.name}: contains disallowed trading-assistant phrasing")
    for term in UNSAFE_DIRECTIVE_TERMS:
        if _has_unnegated_term(text, term):
            failures.append(f"{skill_dir.name}: unsafe non-negated directive term {term!r}")

    resources_dir = skill_dir / "resources"
    if not resources_dir.exists():
        failures.append(f"{skill_dir.name}: missing resources directory")
    elif not any(path.is_file() for path in resources_dir.iterdir()):
        failures.append(f"{skill_dir.name}: resources directory is empty")

    if skill_dir.name != "skill_template" and skill_dir.name not in readme_text:
        failures.append(f"{skill_dir.name}: missing from skills/README.md")
    return failures


def _has_unnegated_term(text: str, term: str) -> bool:
    lines = text.lower().splitlines()
    needle = term.lower()
    for index, line in enumerate(lines):
        if needle not in line:
            continue
        context = " ".join(lines[max(0, index - 5) : index + 1])
        if not any(marker in context for marker in NEGATION_MARKERS):
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
