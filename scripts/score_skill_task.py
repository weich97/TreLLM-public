from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS_DIR = ROOT / "examples" / "skill_tasks"
ANSWER_SET_SCHEMA = "tradearena_skill_answer_set_v0.1"
ABILITY_LABELS = {
    "audit_accuracy": "Audit accuracy",
    "risk_understanding": "Risk-gate understanding",
    "execution_boundary_awareness": "Execution-boundary awareness",
    "claim_discipline": "Claim discipline",
    "reproduction_awareness": "Reproduction awareness",
    "plugin_engineering": "Plugin engineering",
}
DEFAULT_HARD_FAIL_TERMS = (
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
    "does not",
    "cannot",
    "never",
    "must not",
    "should not",
    "not use",
    "without",
    "avoid",
    "reject",
    "rejects",
    "not support",
    "unsupported",
)


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: str
    description: str
    points: int
    earned: int


@dataclass(frozen=True)
class TaskScore:
    task_id: str
    skill: str
    ability: str
    metric: str
    score: int
    max_score: int
    pass_threshold: int
    passed: bool
    hard_failed: bool
    hard_fail_hits: tuple[str, ...]
    criteria: tuple[CriterionResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "skill": self.skill,
            "ability": self.ability,
            "metric": self.metric,
            "score": self.score,
            "max_score": self.max_score,
            "pass_threshold": self.pass_threshold,
            "passed": self.passed,
            "hard_failed": self.hard_failed,
            "hard_fail_hits": list(self.hard_fail_hits),
            "criteria": [result.__dict__ for result in self.criteria],
        }


@dataclass(frozen=True)
class AnswerSetManifest:
    answer_set_id: str
    evaluator_type: str
    model_name: str
    provider: str
    prompt_version: str
    skill_commit_or_version: str
    task_inputs_commit_or_version: str
    skill_files_used: bool
    hidden_artifacts_used: bool
    task_ids: tuple[str, ...]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_set_id": self.answer_set_id,
            "evaluator_type": self.evaluator_type,
            "model_name": self.model_name,
            "provider": self.provider,
            "prompt_version": self.prompt_version,
            "skill_commit_or_version": self.skill_commit_or_version,
            "task_inputs_commit_or_version": self.task_inputs_commit_or_version,
            "skill_files_used": self.skill_files_used,
            "hidden_artifacts_used": self.hidden_artifacts_used,
            "task_ids": list(self.task_ids),
            "notes": self.notes,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or score TreLLM skill task rubrics.")
    parser.add_argument("task", nargs="?", help="Single skill task directory to score or validate.")
    parser.add_argument("--tasks-dir", default=str(DEFAULT_TASKS_DIR), help="Directory containing skill task folders.")
    parser.add_argument("--answer", help="Markdown/text answer for a single task.")
    parser.add_argument("--answers-dir", help="Directory containing <task_id>.md answers for batch scoring.")
    parser.add_argument("--validate-only", action="store_true", help="Validate rubric shape without scoring answers.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown-like text.")
    args = parser.parse_args(argv)

    task_paths = _select_task_paths(Path(args.task) if args.task else None, Path(args.tasks_dir))
    failures = validate_tasks(task_paths)
    if failures:
        _emit({"status": "failed", "failures": failures}, as_json=args.json)
        return 1
    if args.validate_only or (not args.answer and not args.answers_dir):
        coverage = _ability_coverage(task_paths)
        if not args.task:
            missing = [ABILITY_LABELS[ability] for ability, count in coverage.items() if count == 0]
            if missing:
                _emit({"status": "failed", "failures": [f"missing ability coverage: {name}" for name in missing]}, as_json=args.json)
                return 1
        _emit({"status": "ok", "tasks": len(task_paths), "ability_coverage": coverage}, as_json=args.json)
        return 0

    scores = []
    manifest: AnswerSetManifest | None = None
    if args.answer:
        if len(task_paths) != 1:
            raise SystemExit("--answer requires exactly one task path")
        scores.append(score_task(task_paths[0], Path(args.answer).read_text(encoding="utf-8")))
    else:
        scores, manifest, answer_failures = score_answer_directory(task_paths, Path(args.answers_dir))
        failures.extend(answer_failures)
    if failures:
        _emit({"status": "failed", "failures": failures}, as_json=args.json)
        return 1

    payload: dict[str, Any] = {
        "status": "ok",
        "scores": [score.to_dict() for score in scores],
        "ability_summary": summarize_by_ability(scores),
    }
    if manifest:
        payload["answer_set"] = manifest.to_dict()
    _emit(payload, as_json=args.json)
    return 0 if all(score.passed for score in scores) else 1


def validate_tasks(task_paths: list[Path]) -> list[str]:
    failures: list[str] = []
    seen_ids: set[str] = set()
    for task_path in task_paths:
        rubric_path = task_path / "rubric.json"
        input_path = task_path / "input.md"
        if not input_path.exists():
            failures.append(f"{task_path.name}: missing input.md")
        if not rubric_path.exists():
            failures.append(f"{task_path.name}: missing rubric.json")
            continue
        try:
            rubric = _load_rubric(rubric_path)
        except ValueError as exc:
            failures.append(f"{task_path.name}: {exc}")
            continue
        task_id = str(rubric.get("task_id", ""))
        if task_id != task_path.name:
            failures.append(f"{task_path.name}: task_id must match directory name")
        if task_id in seen_ids:
            failures.append(f"{task_path.name}: duplicate task_id {task_id}")
        seen_ids.add(task_id)
        if not str(rubric.get("skill", "")).startswith("tradearena-"):
            failures.append(f"{task_path.name}: skill must start with tradearena-")
        if rubric.get("ability") not in ABILITY_LABELS:
            failures.append(f"{task_path.name}: unknown ability {rubric.get('ability')!r}")
        criteria = rubric.get("criteria")
        if not isinstance(criteria, list) or len(criteria) < 4:
            failures.append(f"{task_path.name}: criteria must contain at least four items")
            continue
        total_points = 0
        for index, criterion in enumerate(criteria):
            total_points += _validate_criterion(task_path.name, index, criterion, failures)
        threshold = rubric.get("pass_threshold")
        if not isinstance(threshold, int) or threshold < 1 or threshold > total_points:
            failures.append(f"{task_path.name}: pass_threshold must be between 1 and {total_points}")
        hard_fail_terms = rubric.get("hard_fail_terms", [])
        if hard_fail_terms and not all(isinstance(term, str) and term.strip() for term in hard_fail_terms):
            failures.append(f"{task_path.name}: hard_fail_terms must be non-empty strings")
    return failures


def score_task(task_path: Path, answer_text: str) -> TaskScore:
    rubric = _load_rubric(task_path / "rubric.json")
    hard_fail_terms = tuple(dict.fromkeys((*DEFAULT_HARD_FAIL_TERMS, *rubric.get("hard_fail_terms", []))))
    hard_fail_hits = tuple(term for term in hard_fail_terms if _has_unnegated_term(answer_text, term))
    criteria = tuple(_score_criterion(criterion, answer_text, bool(hard_fail_hits)) for criterion in rubric["criteria"])
    score = sum(result.earned for result in criteria)
    max_score = sum(result.points for result in criteria)
    threshold = int(rubric["pass_threshold"])
    return TaskScore(
        task_id=str(rubric["task_id"]),
        skill=str(rubric["skill"]),
        ability=str(rubric["ability"]),
        metric=str(rubric["metric"]),
        score=score,
        max_score=max_score,
        pass_threshold=threshold,
        passed=score >= threshold and not hard_fail_hits,
        hard_failed=bool(hard_fail_hits),
        hard_fail_hits=hard_fail_hits,
        criteria=criteria,
    )


def score_answer_directory(
    task_paths: list[Path],
    answers_dir: Path,
) -> tuple[list[TaskScore], AnswerSetManifest | None, list[str]]:
    failures: list[str] = []
    manifest, manifest_failures = load_answer_set_manifest(answers_dir, [path.name for path in task_paths])
    failures.extend(manifest_failures)

    scores: list[TaskScore] = []
    for task_path in task_paths:
        answer_path = answers_dir / f"{task_path.name}.md"
        if not answer_path.exists():
            failures.append(f"missing answer file: {answer_path}")
            continue
        scores.append(score_task(task_path, answer_path.read_text(encoding="utf-8")))
    return scores, manifest, failures


def load_answer_set_manifest(
    answers_dir: Path,
    expected_task_ids: list[str],
) -> tuple[AnswerSetManifest | None, list[str]]:
    path = answers_dir / "manifest.json"
    if not path.exists():
        return None, [f"missing answer-set manifest: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"invalid answer-set manifest JSON: {path}: {exc}"]
    if not isinstance(payload, dict):
        return None, [f"answer-set manifest must be a JSON object: {path}"]
    failures = validate_answer_set_manifest(payload, expected_task_ids)
    if failures:
        return None, [f"{path}: {failure}" for failure in failures]
    return (
        AnswerSetManifest(
            answer_set_id=str(payload["answer_set_id"]),
            evaluator_type=str(payload["evaluator_type"]),
            model_name=str(payload["model_name"]),
            provider=str(payload["provider"]),
            prompt_version=str(payload["prompt_version"]),
            skill_commit_or_version=str(payload["skill_commit_or_version"]),
            task_inputs_commit_or_version=str(payload["task_inputs_commit_or_version"]),
            skill_files_used=bool(payload["skill_files_used"]),
            hidden_artifacts_used=bool(payload["hidden_artifacts_used"]),
            task_ids=tuple(str(task_id) for task_id in payload["task_ids"]),
            notes=str(payload.get("notes", "")),
        ),
        [],
    )


def validate_answer_set_manifest(payload: dict[str, Any], expected_task_ids: list[str]) -> list[str]:
    required = {
        "schema",
        "answer_set_id",
        "evaluator_type",
        "model_name",
        "provider",
        "prompt_version",
        "skill_commit_or_version",
        "task_inputs_commit_or_version",
        "skill_files_used",
        "hidden_artifacts_used",
        "task_ids",
    }
    failures: list[str] = []
    missing = sorted(required - set(payload))
    if missing:
        failures.append(f"missing required fields: {', '.join(missing)}")
    if payload.get("schema") != ANSWER_SET_SCHEMA:
        failures.append(f"schema must be {ANSWER_SET_SCHEMA}")
    if payload.get("evaluator_type") not in {"human", "llm", "coding-agent", "reference"}:
        failures.append("evaluator_type must be human, llm, coding-agent, or reference")
    for field in (
        "answer_set_id",
        "model_name",
        "provider",
        "prompt_version",
        "skill_commit_or_version",
        "task_inputs_commit_or_version",
    ):
        if field in payload and (not isinstance(payload[field], str) or not payload[field].strip()):
            failures.append(f"{field} must be a non-empty string")
    for field in ("skill_files_used", "hidden_artifacts_used"):
        if field in payload and not isinstance(payload[field], bool):
            failures.append(f"{field} must be boolean")
    task_ids = payload.get("task_ids")
    if not isinstance(task_ids, list) or not all(isinstance(task_id, str) and task_id for task_id in task_ids):
        failures.append("task_ids must be a non-empty string array")
    elif set(task_ids) != set(expected_task_ids):
        missing_tasks = sorted(set(expected_task_ids) - set(task_ids))
        extra_tasks = sorted(set(task_ids) - set(expected_task_ids))
        if missing_tasks:
            failures.append(f"task_ids missing tasks: {', '.join(missing_tasks)}")
        if extra_tasks:
            failures.append(f"task_ids include unknown tasks: {', '.join(extra_tasks)}")
    if payload.get("hidden_artifacts_used") is True:
        failures.append("hidden_artifacts_used must be false for comparable public scorecards")
    return failures


def summarize_by_ability(scores: list[TaskScore]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for ability in ABILITY_LABELS:
        ability_scores = [score for score in scores if score.ability == ability]
        if not ability_scores:
            continue
        earned = sum(score.score for score in ability_scores)
        possible = sum(score.max_score for score in ability_scores)
        passed = sum(1 for score in ability_scores if score.passed)
        summary[ability] = {
            "label": ABILITY_LABELS[ability],
            "tasks": len(ability_scores),
            "passed": passed,
            "score": earned,
            "max_score": possible,
            "score_pct": round(earned / possible, 4) if possible else 0.0,
        }
    return summary


def _select_task_paths(task: Path | None, tasks_dir: Path) -> list[Path]:
    if task:
        return [task]
    return sorted(path for path in tasks_dir.iterdir() if path.is_dir())


def _load_rubric(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("rubric.json must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("rubric.json must be a JSON object")
    return payload


def _validate_criterion(task_id: str, index: int, criterion: Any, failures: list[str]) -> int:
    prefix = f"{task_id}: criterion {index}"
    if not isinstance(criterion, dict):
        failures.append(f"{prefix} must be an object")
        return 0
    points = criterion.get("points", 1)
    if not isinstance(points, int) or points < 1:
        failures.append(f"{prefix} has invalid points")
        points = 0
    for field in ("id", "description"):
        if not isinstance(criterion.get(field), str) or not criterion[field].strip():
            failures.append(f"{prefix} missing {field}")
    any_terms = criterion.get("any_terms", [])
    all_terms = criterion.get("all_terms", [])
    if not any_terms and not all_terms:
        failures.append(f"{prefix} needs any_terms or all_terms")
    for field, terms in (("any_terms", any_terms), ("all_terms", all_terms)):
        if terms and (not isinstance(terms, list) or not all(isinstance(term, str) and term for term in terms)):
            failures.append(f"{prefix} {field} must be non-empty strings")
    return points


def _score_criterion(criterion: dict[str, Any], answer_text: str, hard_failed: bool) -> CriterionResult:
    points = int(criterion["points"])
    passed = not hard_failed and _matches_terms(answer_text, criterion)
    return CriterionResult(
        criterion_id=str(criterion["id"]),
        description=str(criterion["description"]),
        points=points,
        earned=points if passed else 0,
    )


def _matches_terms(answer_text: str, criterion: dict[str, Any]) -> bool:
    text = answer_text.lower()
    any_terms = [term.lower() for term in criterion.get("any_terms", [])]
    all_terms = [term.lower() for term in criterion.get("all_terms", [])]
    any_ok = not any_terms or any(term in text for term in any_terms)
    all_ok = all(term in text for term in all_terms)
    return any_ok and all_ok


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


def _ability_coverage(task_paths: list[Path]) -> dict[str, int]:
    coverage = dict.fromkeys(ABILITY_LABELS, 0)
    for task_path in task_paths:
        ability = str(_load_rubric(task_path / "rubric.json").get("ability", ""))
        if ability in coverage:
            coverage[ability] += 1
    return coverage


def _emit(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if payload["status"] != "ok":
        print("Skill task check failed:")
        for failure in payload["failures"]:
            print(f"  - {failure}")
        return
    if "scores" in payload:
        answer_set = payload.get("answer_set")
        if answer_set:
            print(
                f"answer_set={answer_set['answer_set_id']} "
                f"model={answer_set['model_name']} provider={answer_set['provider']}"
            )
        for score in payload["scores"]:
            print(
                f"{score['task_id']}: {score['score']}/{score['max_score']} "
                f"threshold={score['pass_threshold']} passed={score['passed']}"
            )
        print("Ability summary:")
        for ability, row in payload.get("ability_summary", {}).items():
            print(
                f"  - {ABILITY_LABELS[ability]}: {row['passed']}/{row['tasks']} "
                f"tasks, {row['score']}/{row['max_score']} points"
            )
        return
    print(f"Skill task rubrics validated: {payload['tasks']} tasks")
    for ability, count in payload["ability_coverage"].items():
        print(f"  - {ABILITY_LABELS[ability]}: {count}")


if __name__ == "__main__":
    raise SystemExit(main())
