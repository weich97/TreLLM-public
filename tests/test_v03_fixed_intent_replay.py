from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_v03_fixed_intent_replay.py"
SPEC = importlib.util.spec_from_file_location("run_v03_fixed_intent_replay_test", SCRIPT)
assert SPEC and SPEC.loader
REPLAY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPLAY
SPEC.loader.exec_module(REPLAY)


def test_frozen_analyst_consumes_only_the_in_memory_tape() -> None:
    analyst = REPLAY.FrozenResponseSequenceAnalyst(
        provider="deepseek",
        model="deepseek-v4-pro",
        sample_index=0,
        responses=("first", "second"),
    )

    assert analyst._cache() == {}
    assert analyst._call_deepseek("prompt-1") == "first"
    assert analyst._call_deepseek("prompt-2") == "second"
    assert analyst.generated_prompt_hashes == [
        REPLAY.sha256_text("prompt-1"),
        REPLAY.sha256_text("prompt-2"),
    ]
    with pytest.raises(REPLAY.IntegrityError, match="tape exhausted"):
        analyst._call_deepseek("prompt-3")


def test_source_snapshot_requires_an_exact_closed_file_set(tmp_path: Path) -> None:
    plan_id = "row_001"
    layouts = (
        (tmp_path / "runs", ".json"),
        (tmp_path / "provider_manifests", ".json"),
        (tmp_path / "submissions", ".json"),
        (tmp_path / "private" / "llm_cache", ".jsonl"),
    )
    for directory, suffix in layouts:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{plan_id}{suffix}").write_text("{}\n", encoding="utf-8")

    snapshot = REPLAY._source_snapshot(tmp_path, {plan_id})
    assert set(snapshot) == {
        "run_records_set",
        "provider_manifests_set",
        "submissions_set",
        "private_call_logs_set",
    }

    (tmp_path / "runs" / "unplanned.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(REPLAY.IntegrityError, match="file set differs"):
        REPLAY._source_snapshot(tmp_path, {plan_id})


def test_text_source_hash_is_portable_across_line_endings(tmp_path: Path) -> None:
    lf_path = tmp_path / "lf.txt"
    crlf_path = tmp_path / "crlf.txt"
    lf_path.write_bytes(b"alpha\nbeta\n")
    crlf_path.write_bytes(b"alpha\r\nbeta\r\n")

    assert REPLAY._sha256_lf_text(lf_path) == REPLAY._sha256_lf_text(crlf_path)


def test_invalid_private_numeric_signal_is_not_echoed() -> None:
    sentinel = "PRIVATE-RESPONSE-SENTINEL"

    class Parser:
        def _parse_response(self, response: str) -> dict[str, str]:
            return {"response": response}

        def _signal_items(self, parsed: object) -> list[dict[str, str]]:
            del parsed
            return [{"symbol": "S", "target_weight": sentinel}]

    with pytest.raises(REPLAY.IntegrityError) as exc_info:
        REPLAY._parsed_response_path([{"response_text": sentinel}], Parser())
    assert sentinel not in str(exc_info.value)


@pytest.mark.skipif(
    os.environ.get("TRADEARENA_RUN_PRIVATE_V03_REPLAY_TEST") != "1",
    reason="requires the explicit private v0.3 source-matrix integration-test opt-in",
)
def test_production_gate_and_one_pair_replay_are_closed_and_reproducible() -> None:
    plan = REPLAY._read_json(
        ROOT / "docs" / "results" / "v0_3_fixed_intent_replay" / "analysis_plan.json"
    )
    records, groups, snapshot = REPLAY.validate_source_matrix(
        plan,
        ROOT
        / "docs"
        / "results"
        / "v0_3_direct_api_matrix_plan"
        / "direct_api_matrix_plan_rows.csv",
        ROOT
        / "docs"
        / "results"
        / "v0_3_direct_api_call_packets"
        / "direct_api_call_packets.jsonl",
        ROOT / "outputs" / "v0_3_direct_api_matrix",
    )
    assert len(records) == 900
    assert len(groups) == 450
    assert snapshot == plan["source_set_sha256"]

    base_key = sorted(groups)[0]
    returned_key, rows = REPLAY._replay_group((base_key, groups[base_key]))
    assert returned_key == base_key
    assert len(rows) == 4
    assert sum(row["diagonal_check_applicable"] for row in rows) == 2
    assert all(
        row["diagonal_reproduction_pass"] is True
        for row in rows
        if row["diagonal_check_applicable"]
    )
    assert all(
        row["diagonal_reproduction_pass"] is None
        for row in rows
        if not row["diagonal_check_applicable"]
    )
    for origin in REPLAY.EXECUTION_LEVELS:
        by_origin = [row for row in rows if row["intent_origin_execution"] == origin]
        assert len({row["decision_path_sha256"] for row in by_origin}) == 1
    forbidden = {"prompt", "response", "response_text", "api_key", "cache_path"}
    assert not forbidden.intersection(rows[0])
