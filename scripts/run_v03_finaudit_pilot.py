from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.defect_injection import DEFECT_KINDS, inject_defect, score_findings
from tradearena.factory import build_default_system

SCENARIO_ID = "synthetic_finaudit_c0_v0_3"
CONTAMINATION_TIER = "C0"
PROTOCOL_ID = "trellm-v0.3-protocol"
TASK_FIELDS = [
    "protocol_id",
    "task_id",
    "scenario_id",
    "contamination_tier",
    "source_seed",
    "difficulty",
    "trajectory_sha256",
    "prompt_sha256",
    "answer_key_public",
]
SCORE_FIELDS = [
    "protocol_id",
    "task_id",
    "condition",
    "auditor_id",
    "difficulty",
    "findings",
    "defects",
    "true_positives",
    "precision",
    "recall",
    "f1",
]
BREAKDOWN_FIELDS = [
    "protocol_id",
    "condition",
    "auditor_id",
    "difficulty",
    "tasks",
    "findings",
    "defects",
    "true_positives",
    "precision",
    "precision_wilson_low",
    "precision_wilson_high",
    "recall",
    "recall_wilson_low",
    "recall_wilson_high",
    "f1",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the TreLLM v0.3 FinAudit injected-defect pilot report."
    )
    parser.add_argument("--output-dir", default="docs/results/v0_3_finaudit_pilot")
    parser.add_argument("--tasks", type=int, default=8)
    parser.add_argument("--periods", type=int, default=24)
    parser.add_argument("--base-seed", type=int, default=310)
    parser.add_argument("--strategy", default="signal-weighted")
    parser.add_argument("--symbols", default="SYN,ALT")
    args = parser.parse_args(argv)

    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    symbols = tuple(_parse_list(args.symbols, "symbols"))
    tasks, answer_key = _generate_tasks(
        task_count=args.tasks,
        periods=args.periods,
        base_seed=args.base_seed,
        strategy=args.strategy,
        symbols=symbols,
    )
    score_rows = _score_fixture_auditors(tasks, answer_key)
    breakdown_rows = _breakdown_rows(score_rows)
    summary = _summary(
        tasks,
        answer_key,
        score_rows,
        breakdown_rows,
        task_count=args.tasks,
        periods=args.periods,
        base_seed=args.base_seed,
        strategy=args.strategy,
        symbols=symbols,
    )

    _write_csv(output_dir / "finaudit_pilot_task_manifest.csv", tasks, TASK_FIELDS)
    _write_csv(output_dir / "finaudit_pilot_scores.csv", score_rows, SCORE_FIELDS)
    _write_csv(output_dir / "finaudit_pilot_difficulty_breakdown.csv", breakdown_rows, BREAKDOWN_FIELDS)
    _write_json(output_dir / "finaudit_pilot_summary.json", summary)
    (output_dir / "finaudit_pilot_summary.md").write_text(
        _summary_markdown(summary, breakdown_rows),
        encoding="utf-8",
    )
    print(f"Wrote {_display_path(output_dir / 'finaudit_pilot_task_manifest.csv')}")
    print(f"Wrote {_display_path(output_dir / 'finaudit_pilot_scores.csv')}")
    print(f"Wrote {_display_path(output_dir / 'finaudit_pilot_difficulty_breakdown.csv')}")
    print(f"Wrote {_display_path(output_dir / 'finaudit_pilot_summary.json')}")
    print(f"Wrote {_display_path(output_dir / 'finaudit_pilot_summary.md')}")
    print(f"Tasks: {len(tasks)}")
    return 0


def _generate_tasks(
    *,
    task_count: int,
    periods: int,
    base_seed: int,
    strategy: str,
    symbols: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks: list[dict[str, Any]] = []
    answer_key: list[dict[str, Any]] = []
    attempt = 0
    max_attempts = max(40, task_count * 20)
    while len(tasks) < task_count and attempt < max_attempts:
        kind = DEFECT_KINDS[len(tasks) % len(DEFECT_KINDS)]
        seed = base_seed + attempt
        attempt += 1
        trajectory, _ = build_default_system(
            name=f"v03_finaudit_source_{seed}",
            symbols=symbols,
            periods=periods,
            seed=seed,
            strategy_name=strategy,
            analyst_names=("momentum", "macro-news"),
        ).run()
        try:
            defective, truth = inject_defect(trajectory.to_dict(), kind, seed=seed)
        except ValueError:
            continue
        task_id = f"finaudit_{len(tasks):04d}"
        prompt = _prompt_text()
        tasks.append(
            {
                "protocol_id": PROTOCOL_ID,
                "task_id": task_id,
                "scenario_id": SCENARIO_ID,
                "contamination_tier": CONTAMINATION_TIER,
                "source_seed": seed,
                "difficulty": truth["difficulty"],
                "trajectory_sha256": _sha256_json(defective),
                "prompt_sha256": _sha256_text(prompt),
                "answer_key_public": False,
            }
        )
        answer_key.append(
            {
                "task_id": task_id,
                "source_seed": seed,
                "kind": truth["kind"],
                "difficulty": truth["difficulty"],
                "step_index": truth["step_index"],
                "detail_sha256": _sha256_json(truth["detail"]),
            }
        )
    if len(tasks) != task_count:
        raise SystemExit(f"Generated {len(tasks)} tasks after {attempt} attempts; expected {task_count}")
    return tasks, answer_key


def _score_fixture_auditors(tasks: list[dict[str, Any]], answer_key: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    key_by_task = {row["task_id"]: row for row in answer_key}
    for task in tasks:
        truth = key_by_task[task["task_id"]]
        for condition, auditor_id, findings in (
            ("cross-audit", "fixture-cross-auditor-v0", _cross_audit_fixture(truth)),
            ("self-audit", "fixture-self-auditor-v0", _self_audit_fixture(truth)),
        ):
            score = score_findings(findings, [truth])
            rows.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "task_id": task["task_id"],
                    "condition": condition,
                    "auditor_id": auditor_id,
                    "difficulty": truth["difficulty"],
                    **{key: _round(value) if isinstance(value, float) else value for key, value in score.items()},
                }
            )
    return rows


def _cross_audit_fixture(truth: dict[str, Any]) -> list[dict[str, Any]]:
    if truth["difficulty"] == "L3":
        return []
    return [{"step_index": int(truth["step_index"]), "kind": str(truth["kind"]), "explanation": "fixture hit"}]


def _self_audit_fixture(truth: dict[str, Any]) -> list[dict[str, Any]]:
    if truth["difficulty"] == "L1":
        return [{"step_index": int(truth["step_index"]), "kind": str(truth["kind"]), "explanation": "fixture hit"}]
    if truth["difficulty"] == "L2" and str(truth["kind"]) == "provenance_drift":
        return [{"step_index": int(truth["step_index"]), "kind": str(truth["kind"]), "explanation": "fixture hit"}]
    return []


def _breakdown_rows(score_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in score_rows:
        grouped[(str(row["condition"]), str(row["auditor_id"]), str(row["difficulty"]))].append(row)
        grouped[(str(row["condition"]), str(row["auditor_id"]), "all")].append(row)
    output: list[dict[str, Any]] = []
    for (condition, auditor_id, difficulty), rows in sorted(grouped.items()):
        findings = sum(int(row["findings"]) for row in rows)
        defects = sum(int(row["defects"]) for row in rows)
        true_positives = sum(int(row["true_positives"]) for row in rows)
        precision = true_positives / findings if findings else 0.0
        recall = true_positives / defects if defects else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        precision_low, precision_high = _wilson_interval(true_positives, findings)
        recall_low, recall_high = _wilson_interval(true_positives, defects)
        output.append(
            {
                "protocol_id": PROTOCOL_ID,
                "condition": condition,
                "auditor_id": auditor_id,
                "difficulty": difficulty,
                "tasks": len(rows),
                "findings": findings,
                "defects": defects,
                "true_positives": true_positives,
                "precision": _round(precision),
                "precision_wilson_low": _round(precision_low),
                "precision_wilson_high": _round(precision_high),
                "recall": _round(recall),
                "recall_wilson_low": _round(recall_low),
                "recall_wilson_high": _round(recall_high),
                "f1": _round(f1),
            }
        )
    return output


def _summary(
    tasks: list[dict[str, Any]],
    answer_key: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
    breakdown_rows: list[dict[str, Any]],
    *,
    task_count: int,
    periods: int,
    base_seed: int,
    strategy: str,
    symbols: tuple[str, ...],
) -> dict[str, Any]:
    by_condition = {row["condition"]: row for row in breakdown_rows if row["difficulty"] == "all"}
    cross = by_condition.get("cross-audit", {})
    self_audit = by_condition.get("self-audit", {})
    return {
        "schema": "trellm_v0_3_finaudit_pilot_v0.1",
        "protocol_id": PROTOCOL_ID,
        "scenario_id": SCENARIO_ID,
        "contamination_tier": CONTAMINATION_TIER,
        "task_count": task_count,
        "score_row_count": len(score_rows),
        "difficulty_breakdown_rows": len(breakdown_rows),
        "defect_families": list(DEFECT_KINDS),
        "difficulty_levels": sorted({row["difficulty"] for row in answer_key}),
        "periods": periods,
        "base_seed": base_seed,
        "strategy": strategy,
        "symbols": list(symbols),
        "answer_key_public": False,
        "answer_key_sha256": _sha256_json(answer_key),
        "task_manifest_sha256": _sha256_json(tasks),
        "required_metrics": ["precision", "recall", "f1", "wilson_interval", "difficulty_breakdown"],
        "conditions": ["cross-audit", "self-audit"],
        "cross_audit_f1": cross.get("f1", 0.0),
        "self_audit_f1": self_audit.get("f1", 0.0),
        "self_audit_bias_recall_delta": _round(float(cross.get("recall", 0.0)) - float(self_audit.get("recall", 0.0))),
        "claim_boundary": (
            "FinAudit pilot protocol fixture for injected-defect scoring and self/cross audit plumbing; "
            "fixture auditor scores are not model-performance evidence."
        ),
        "artifacts": [
            "finaudit_pilot_task_manifest.csv",
            "finaudit_pilot_scores.csv",
            "finaudit_pilot_difficulty_breakdown.csv",
            "finaudit_pilot_summary.json",
            "finaudit_pilot_summary.md",
        ],
    }


def _summary_markdown(summary: dict[str, Any], breakdown_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# TreLLM v0.3 FinAudit Pilot",
        "",
        "This fixture bundle validates the injected-defect audit task path for the v0.3 protocol.",
        "It is not model-performance evidence.",
        "",
        f"- Protocol: `{summary['protocol_id']}`",
        f"- Scenario: `{summary['scenario_id']}`",
        f"- Contamination tier: `{summary['contamination_tier']}`",
        f"- Tasks: {summary['task_count']}",
        f"- Conditions: `{', '.join(summary['conditions'])}`",
        f"- Required metrics: `{', '.join(summary['required_metrics'])}`",
        f"- Answer key public: `{summary['answer_key_public']}`",
        f"- Answer key hash: `{summary['answer_key_sha256']}`",
        f"- Claim boundary: {summary['claim_boundary']}",
        f"- Self-audit bias recall delta: `{summary['self_audit_bias_recall_delta']}`",
        "",
        "## Difficulty Breakdown",
        "",
        "| Condition | Auditor | Difficulty | Tasks | Precision | Recall | F1 | Recall Wilson 95% CI |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in breakdown_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["condition"]),
                    str(row["auditor_id"]),
                    str(row["difficulty"]),
                    str(row["tasks"]),
                    _fmt(row["precision"]),
                    _fmt(row["recall"]),
                    _fmt(row["f1"]),
                    f"[{_fmt(row['recall_wilson_low'])}, {_fmt(row['recall_wilson_high'])}]",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _prompt_text() -> str:
    return (
        "Audit the trajectory for one injected defect. Report JSON findings with step_index, kind, and explanation. "
        "Score uses precision, recall, and F1 against a private answer key."
    )


def _wilson_interval(successes: int, total: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    phat = successes / total
    denom = 1.0 + z * z / total
    center = (phat + z * z / (2.0 * total)) / denom
    margin = z * ((phat * (1.0 - phat) + z * z / (4.0 * total)) / total) ** 0.5 / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_list(value: str, label: str) -> list[str]:
    values = [part.strip() for part in value.split(",") if part.strip()]
    if not values:
        raise SystemExit(f"{label} must contain at least one item")
    return values


def _resolve_output_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _sha256_json(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_text(text)


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _round(value: Any) -> float:
    return round(float(value or 0.0), 6)


def _fmt(value: Any) -> str:
    if value in ("", None):
        return ""
    return f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
