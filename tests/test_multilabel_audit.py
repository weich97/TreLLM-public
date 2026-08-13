from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tradearena.evaluation.defect_injection import score_findings
from tradearena.evaluation.toolaudit import generate_trajectory

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load_script("generate_multilabel_audit_tasks")
RUN = _load_script("run_multilabel_audit_eval")
ANALYZE = _load_script("analyze_multilabel_audit")


def _trading_source(*, blocked: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    intent = 0.0 if blocked else 0.8
    original_approved = 0.0 if blocked else 0.35
    metadata = {"strategy": "test"}
    risk_violations: list[dict[str, Any]] = []
    if blocked:
        metadata["risk_blocked"] = "low_confidence"
        risk_violations = [
            {"constraint": "min_confidence", "symbol": "SYN"},
            {"constraint": "min_confidence", "symbol": "ALT"},
        ]
    confidence = 0.01 if blocked else 0.4
    trajectory = {
        "steps": [
            {
                "observation": {"prices": {}},
                "decisions": [
                    {
                        "symbol": "SYN",
                        "side": "hold" if blocked else "buy",
                        "target_weight": intent,
                        "confidence": confidence,
                        "metadata": {"strategy": "test"},
                    }
                ],
                "approved_decisions": [
                    {
                        "symbol": "SYN",
                        "side": "hold" if blocked else "buy",
                        "target_weight": 0.8,
                        "confidence": confidence,
                        "metadata": metadata,
                    }
                ],
                "fills": [],
                "risk_violations": risk_violations,
                "reproducibility_state": {"model_version": "model-v1"},
            }
        ]
    }
    truth = {
        "task_id": "source",
        "kind": "unclipped_position",
        "step_index": 0,
        "source_seed": 1,
        "detail": {"symbol": "SYN", "original_target_weight": original_approved},
    }
    return trajectory, truth


@pytest.mark.parametrize("blocked", [False, True])
def test_trading_triplet_has_exact_zero_one_two_labels(blocked: bool) -> None:
    trajectory, truth = _trading_source(blocked=blocked)
    variants = GEN.build_trading_triplet(trajectory, truth)

    assert [len(variants[condition][1]) for condition in GEN.CONDITIONS] == [0, 1, 2]
    for condition, (candidate, defects) in variants.items():
        expected = {(defect["step_index"], defect["kind"]) for defect in defects}
        assert GEN.trading_rule_oracle(candidate) == expected, condition

    single = variants["violation_only"][0]
    dual = variants["violation_plus_edit"][0]
    assert single["steps"][0]["decisions"][0]["side"] == "buy"
    assert dual["steps"][0]["decisions"][0]["side"] == "buy"
    assert single["steps"][0]["decisions"][0]["confidence"] >= 0.4
    if blocked:
        assert [row["symbol"] for row in single["steps"][0]["risk_violations"]] == ["ALT"]
        zero = variants["zero"][0]
        assert zero["steps"][0]["approved_decisions"][0]["target_weight"] == 0.0
        assert zero["steps"][0]["approved_decisions"][0]["metadata"]["risk_blocked"] == "low_confidence"


def test_tool_triplet_has_exact_zero_one_two_labels_and_one_field_pair() -> None:
    trajectory = generate_trajectory(9000)
    step_index = GEN._tool_target_step(trajectory, 9000)
    variants = GEN.build_tool_triplet(trajectory, step_index)
    assert [len(variants[condition][1]) for condition in GEN.CONDITIONS] == [0, 1, 2]
    for condition, (candidate, defects) in variants.items():
        expected = {(defect["step_index"], defect["kind"]) for defect in defects}
        assert GEN.tool_rule_oracle(candidate) == expected, condition

    single = copy.deepcopy(variants["violation_only"][0])
    dual = variants["violation_plus_edit"][0]
    step = single["steps"][step_index]
    tool = step["tool"]
    argument = trajectory["caps"][tool]["arg"]
    step["requested_args"][argument] = dual["steps"][step_index]["requested_args"][argument]
    assert single == dual


def test_prompts_disclose_unknown_cardinality_without_fixed_count() -> None:
    prompts = {"trading": GEN.TRADING_PROMPT, "tooluse": GEN.TOOL_PROMPT}
    for domain, prompt in prompts.items():
        normalized = " ".join(prompt.lower().split())
        assert "zero, one, or multiple" in normalized
        assert "multiple defects may coexist" in normalized
        assert "exactly one" not in normalized
        assert "single injected defect" not in normalized
        assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == ANALYZE.FROZEN_PROMPT_SHA256[domain]


def test_strict_parser_never_salvages_arbitrary_prose() -> None:
    allowed = {"unclipped_position", "silent_risk_edit"}
    assert RUN.parse_findings_strict("[]", allowed) == (True, [], "")
    assert RUN.parse_findings_strict("```json\n[]\n```", allowed) == (True, [], "")
    assert RUN.parse_findings_strict("answer: []", allowed) == (False, [], "invalid_json")
    ok, findings, error = RUN.parse_findings_strict(
        '[{"step_index": 2, "kind": "unknown"}]', allowed
    )
    assert not ok
    assert findings == [{"step_index": 2, "kind": "unknown"}]
    assert error == "item_0_unknown_kind"


def test_request_fingerprint_covers_decoding_and_system_prompt() -> None:
    base = RUN.request_fingerprint("deepseek", "m", "prompt")
    warmer = RUN.request_fingerprint("deepseek", "m", "prompt", temperature=0.1)
    other_system = RUN.request_fingerprint("deepseek", "m", "prompt", system_prompt="other")
    object_mode = RUN.request_fingerprint("deepseek", "m", "prompt", use_response_format=True)
    assert len({base["request_hash"], warmer["request_hash"], other_system["request_hash"], object_mode["request_hash"]}) == 4


def test_score_findings_supports_empty_and_same_step_multilabel_truth() -> None:
    empty = score_findings([], [])
    assert empty["true_positives"] == 0
    truth = [
        {"step_index": 4, "kind": "unclipped_position"},
        {"step_index": 4, "kind": "silent_risk_edit"},
    ]
    findings = [
        {"step_index": 4, "kind": "unclipped_position"},
        {"step_index": 4, "kind": "silent_risk_edit"},
    ]
    scored = score_findings(findings, truth)
    assert scored["true_positives"] == 2
    assert scored["precision"] == 1.0
    assert scored["recall"] == 1.0


def test_holm_and_exact_mcnemar() -> None:
    assert ANALYZE.holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert ANALYZE.exact_mcnemar_p(0, 0) == 1.0
    assert ANALYZE.exact_mcnemar_p(5, 0) == pytest.approx(0.0625)


def _mini_dataset(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    trajectory = generate_trajectory(9000)
    step_index = GEN._tool_target_step(trajectory, 9000)
    variants = GEN.build_tool_triplet(trajectory, step_index)
    tasks_dir = root / "tasks"
    tasks_dir.mkdir(parents=True)
    triple_id = GEN.opaque_id("tr", GEN.SCHEMA_VERSION, "tooluse", 9000)
    truth_rows: list[dict[str, Any]] = []
    manifest_tasks: list[dict[str, Any]] = []
    for condition, (candidate, defects) in variants.items():
        task_id = GEN.opaque_id("ml", triple_id, condition)
        task_dir = tasks_dir / task_id
        task_dir.mkdir()
        trajectory_path = task_dir / "trajectory.json"
        prompt_path = task_dir / "prompt.md"
        trajectory_path.write_text(GEN.canonical_json(candidate, indent=2), encoding="utf-8")
        prompt_path.write_bytes(GEN.TOOL_PROMPT.encode("utf-8"))
        manifest_tasks.append(
            {
                "task_id": task_id,
                "domain": "tooluse",
                "producer": "rule_based_tool",
                "trajectory_sha256": hashlib.sha256(trajectory_path.read_bytes()).hexdigest(),
                "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
            }
        )
        truth_rows.append(
            {
                "schema_version": GEN.SCHEMA_VERSION,
                "task_id": task_id,
                "triple_id": triple_id,
                "domain": "tooluse",
                "producer": "rule_based_tool",
                "source_task_id": "tool_source_9000",
                "source_seed": 9000,
                "condition": condition,
                "target_step_index": step_index,
                "defects": defects,
            }
        )
    plan = {"schema_version": "finaudit.multilabel.plan.v1"}
    plan_path = root / "analysis_plan.json"
    plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema_version": GEN.SCHEMA_VERSION,
        "task_count": 3,
        "analysis_plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "tasks": manifest_tasks,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "ground_truth.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in truth_rows), encoding="utf-8"
    )
    return {str(row["task_id"]): row for row in truth_rows}, truth_rows


def _result_row(model: str, truth: dict[str, Any]) -> dict[str, Any]:
    findings = [
        {"step_index": defect["step_index"], "kind": defect["kind"]} for defect in truth["defects"]
    ]
    return {
        "schema_version": RUN.OUTPUT_SCHEMA_VERSION,
        "model": model,
        "task_id": truth["task_id"],
        "sample": 0,
        "parse_ok": True,
        "parse_error": "",
        "finding_count": len(findings),
        "findings": findings,
        "response_sha256": "a" * 64,
        "request_hash": "b" * 64,
        "prompt_hash": "c" * 64,
        "decoding_hash": "d" * 64,
        "cache_key": f"auditmlv1:test:{truth['task_id']}",
    }


def test_dataset_and_result_gate_reject_missing_and_duplicate_keys(tmp_path: Path) -> None:
    truth_by_task, truth_rows = _mini_dataset(tmp_path / "dataset")
    _, loaded_truth = ANALYZE.load_dataset(tmp_path / "dataset", require_full_scale=False)
    assert set(loaded_truth) == set(truth_by_task)
    model = "deepseek:deepseek-v4-pro"
    rows = [_result_row(model, truth) for truth in truth_rows]
    result_path = tmp_path / "results.jsonl"
    result_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    validated = ANALYZE.validate_results(
        result_path,
        loaded_truth,
        [model],
        verify_cache=False,
        require_frozen_models=False,
    )
    assert len(validated) == 3

    result_path.write_text("".join(json.dumps(row) + "\n" for row in rows[:-1]), encoding="utf-8")
    with pytest.raises(ANALYZE.IncompleteGridError):
        ANALYZE.validate_results(
            result_path,
            loaded_truth,
            [model],
            verify_cache=False,
            require_frozen_models=False,
        )

    duplicated = rows + [rows[0]]
    result_path.write_text("".join(json.dumps(row) + "\n" for row in duplicated), encoding="utf-8")
    with pytest.raises(ANALYZE.IntegrityError, match="Duplicate result key"):
        ANALYZE.validate_results(
            result_path,
            loaded_truth,
            [model],
            verify_cache=False,
            require_frozen_models=False,
        )


def test_result_schema_rejects_raw_text_and_extra_finding_fields(tmp_path: Path) -> None:
    truth_by_task, truth_rows = _mini_dataset(tmp_path / "dataset")
    _, loaded_truth = ANALYZE.load_dataset(tmp_path / "dataset", require_full_scale=False)
    model = "deepseek:deepseek-v4-pro"
    rows = [_result_row(model, truth) for truth in truth_rows]
    result_path = tmp_path / "results.jsonl"

    rows[0]["raw_model_output"] = "private completion text"
    result_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    with pytest.raises(ANALYZE.IntegrityError, match="frozen public schema"):
        ANALYZE.validate_results(
            result_path,
            loaded_truth,
            [model],
            verify_cache=False,
            require_frozen_models=False,
        )
    with pytest.raises(ValueError, match="frozen result schema"):
        RUN._load_done(
            result_path,
            allowed_models={model},
            allowed_tasks=set(truth_by_task),
        )

    del rows[0]["raw_model_output"]
    assert rows[1]["findings"]
    rows[1]["findings"][0]["completion_text"] = "private completion text"
    result_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    with pytest.raises(ANALYZE.IntegrityError, match="frozen public schema"):
        ANALYZE.validate_results(
            result_path,
            loaded_truth,
            [model],
            verify_cache=False,
            require_frozen_models=False,
        )
    with pytest.raises(ValueError, match="non-canonical finding schema"):
        RUN._load_done(
            result_path,
            allowed_models={model},
            allowed_tasks=set(truth_by_task),
        )


def test_complete_resume_checkpoint_is_atomically_canonicalized(tmp_path: Path) -> None:
    _, truth_rows = _mini_dataset(tmp_path / "dataset")
    model = "deepseek:deepseek-v4-pro"
    rows = [_result_row(model, truth) for truth in truth_rows]
    resumed_order = [rows[1], rows[2], rows[0]]
    result_path = tmp_path / "results.jsonl"
    result_path.write_text(
        "".join(json.dumps(row) + "\n" for row in resumed_order), encoding="utf-8"
    )

    RUN._canonicalize_complete_results(result_path, expected_count=3)

    expected = sorted(rows, key=lambda row: (row["model"], row["task_id"], row["sample"]))
    assert result_path.read_bytes() == (
        "".join(RUN._canonical(row) + "\n" for row in expected).encode("utf-8")
    )
    assert not result_path.with_suffix(result_path.suffix + ".canonical.tmp").exists()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("triple_id", "tr_deadbeefdeadbeef", "frozen provenance"),
        ("source_task_id", "tool_source_9001", "non-deterministic source id"),
    ],
)
def test_dataset_gate_rejects_relabelled_provenance(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    dataset_root = tmp_path / "dataset"
    _, truth_rows = _mini_dataset(dataset_root)
    for row in truth_rows:
        row[field] = value
    (dataset_root / "ground_truth.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in truth_rows),
        encoding="utf-8",
    )
    with pytest.raises(ANALYZE.IntegrityError, match=message):
        ANALYZE.load_dataset(dataset_root, require_full_scale=False)


def test_strict_result_gate_replays_raw_cache_and_request_fingerprint(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    _, truth_rows = _mini_dataset(dataset_root)
    _, loaded_truth = ANALYZE.load_dataset(dataset_root, require_full_scale=False)
    model = "deepseek:deepseek-v4-pro"
    provider, api_model = model.split(":", 1)
    result_rows: list[dict[str, Any]] = []
    cache_rows: list[dict[str, Any]] = []
    for truth in truth_rows:
        findings = [
            {"step_index": defect["step_index"], "kind": defect["kind"]}
            for defect in truth["defects"]
        ]
        response = json.dumps(findings, sort_keys=True)
        prompt = RUN.build_prompt(dataset_root / "tasks" / truth["task_id"], "tooluse")
        fingerprint = RUN.request_fingerprint(provider, api_model, prompt)
        cache_key = f"auditmlv1:{provider}:{api_model}:{truth['task_id']}:{fingerprint['request_hash']}:s0"
        parse_ok, parsed, parse_error = RUN.parse_findings_strict(response, RUN.ALLOWED_KINDS["tooluse"])
        result_rows.append(
            {
                "schema_version": RUN.OUTPUT_SCHEMA_VERSION,
                "model": model,
                "task_id": truth["task_id"],
                "sample": 0,
                "parse_ok": parse_ok,
                "parse_error": parse_error,
                "finding_count": len(parsed),
                "findings": parsed,
                "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
                **fingerprint,
                "cache_key": cache_key,
            }
        )
        cache_rows.append(
            {
                "cache_key": cache_key,
                "provider": provider,
                "model": api_model,
                "task_id": truth["task_id"],
                "sample": 0,
                "prompt": prompt,
                "response_text": response,
                **fingerprint,
            }
        )
    results_path = tmp_path / "results.jsonl"
    results_path.write_text("".join(json.dumps(row) + "\n" for row in result_rows), encoding="utf-8")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_path = cache_dir / "auditml_deepseek.jsonl"
    cache_path.write_text(
        "".join(json.dumps(row) + "\n" for row in cache_rows), encoding="utf-8"
    )
    validated = ANALYZE.validate_results(
        results_path,
        loaded_truth,
        [model],
        tasks_root=dataset_root,
        cache_dir=cache_dir,
        require_frozen_models=False,
    )
    assert len(validated) == 3

    ledger_rows = []
    cache_file_sha256 = hashlib.sha256(cache_path.read_bytes()).hexdigest()
    for result, cache in zip(result_rows, cache_rows, strict=True):
        provider, api_model = result["model"].split(":", 1)
        ledger_rows.append(
            {
                "schema_version": ANALYZE.RESPONSE_LEDGER_SCHEMA_VERSION,
                "model": result["model"],
                "provider": provider,
                "api_model": api_model,
                "task_id": result["task_id"],
                "sample": result["sample"],
                "cache_key": result["cache_key"],
                "request_hash": result["request_hash"],
                "prompt_hash": result["prompt_hash"],
                "decoding_hash": result["decoding_hash"],
                "response_sha256": result["response_sha256"],
                "parse_ok": result["parse_ok"],
                "parse_error": result["parse_error"],
                "findings_sha256": hashlib.sha256(
                    json.dumps(
                        result["findings"], sort_keys=True, separators=(",", ":")
                    ).encode()
                ).hexdigest(),
                "raw_cache_record_sha256": hashlib.sha256(
                    json.dumps(cache, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                "source_cache_file": cache_path.name,
                "source_cache_file_sha256": cache_file_sha256,
            }
        )
    ledger_path = tmp_path / "response_ledger.jsonl"
    ledger_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger_rows),
        encoding="utf-8",
    )
    released = ANALYZE.validate_results(
        results_path,
        loaded_truth,
        [model],
        tasks_root=dataset_root,
        response_ledger_path=ledger_path,
        verify_cache=False,
        require_frozen_models=False,
    )
    assert released == validated

    tampered_ledger = copy.deepcopy(ledger_rows)
    tampered_ledger[0]["response_sha256"] = "0" * 64
    ledger_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in tampered_ledger),
        encoding="utf-8",
    )
    with pytest.raises(ANALYZE.IntegrityError, match="response_sha256 mismatch"):
        ANALYZE.validate_results(
            results_path,
            loaded_truth,
            [model],
            tasks_root=dataset_root,
            response_ledger_path=ledger_path,
            verify_cache=False,
            require_frozen_models=False,
        )

    tampered = copy.deepcopy(result_rows)
    tampered[0]["request_hash"] = "0" * 64
    results_path.write_text("".join(json.dumps(row) + "\n" for row in tampered), encoding="utf-8")
    with pytest.raises(ANALYZE.IntegrityError, match="request_hash"):
        ANALYZE.validate_results(
            results_path,
            loaded_truth,
            [model],
            tasks_root=dataset_root,
            cache_dir=cache_dir,
            require_frozen_models=False,
        )


def test_duplicate_correct_finding_is_not_exact_and_counts_as_false_positive() -> None:
    truth = {
        "task_id": "ml_0123456789abcdef",
        "triple_id": "tr_0123456789abcdef",
        "domain": "trading",
        "producer": "deepseek_v4_pro",
        "condition": "violation_only",
        "target_step_index": 3,
        "defects": [{"step_index": 3, "kind": "unclipped_position"}],
    }
    result = {
        "model": "deepseek:deepseek-v4-pro",
        "parse_ok": True,
        "findings": [
            {"step_index": 3, "kind": "unclipped_position"},
            {"step_index": 3, "kind": "unclipped_position"},
        ],
    }
    evaluated = ANALYZE._evaluated_row(result, truth)
    assert evaluated["tp"] == 1
    assert evaluated["fp"] == 1
    assert evaluated["duplicate_findings"] == 1
    assert not evaluated["exact_set"]
    assert not evaluated["cardinality_correct"]
