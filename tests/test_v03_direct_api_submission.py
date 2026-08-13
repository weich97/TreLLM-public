from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_ROWS = ROOT / "docs" / "results" / "v0_3_direct_api_matrix_plan" / "direct_api_matrix_plan_rows.csv"


def _load_module(script_name: str):
    path = ROOT / "scripts" / f"{script_name}.py"
    spec = importlib.util.spec_from_file_location(script_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A fixed single-scenario fixture plan, so the counting assertions below are
# decoupled from the registered plan (which grows by amendment).
_FIXTURE_MODELS = ",".join([
    "deepseek:deepseek-v4-pro:api-pinned-2026-07-02:chat_completions:DEEPSEEK_API_KEY",
    "deepseek:deepseek-v4-flash:api-pinned-2026-07-02:chat_completions:DEEPSEEK_API_KEY",
    "glm:glm-5:api-pinned-2026-07-02:chat_completions:GLM_API_KEY",
])


def _build_packets(tmp_path: Path) -> Path:
    plan_dir = tmp_path / "plan"
    planner = _load_module("build_v03_direct_api_matrix_plan")
    assert planner.main([
        "--models", _FIXTURE_MODELS,
        "--scenarios", "synthetic_calm_trend_c0_v0_3",
        "--output-dir", str(plan_dir),
    ]) == 0
    packets_dir = tmp_path / "packets"
    builder = _load_module("build_v03_direct_api_call_packets")
    assert builder.main([
        "--plan-rows", str(plan_dir / "direct_api_matrix_plan_rows.csv"),
        "--output-dir", str(packets_dir),
    ]) == 0
    return packets_dir / "direct_api_call_packets.jsonl"


def _counting_transport(calls: list[dict], *, fail_seeds: set[int] | None = None):
    def transport(context: dict, prompt: str) -> str:
        if fail_seeds and int(context["seed"]) in fail_seeds:
            raise RuntimeError("synthetic transport failure for testing")
        calls.append(dict(context))
        payload = json.loads(prompt)
        weights = [
            {"symbol": str(bar["symbol"]), "target_weight": 0.2, "confidence": 0.7, "horizon": "1w"}
            for bar in payload.get("bars", [])
        ]
        return json.dumps({"weights": weights}, sort_keys=True)

    return transport


def test_dry_run_fixture_bundle_validates_and_stays_pilot(tmp_path: Path):
    packets_path = _build_packets(tmp_path)
    bundle = tmp_path / "bundle"
    bridge = _load_module("run_v03_direct_api_submission")
    validators = _load_module("validate_direct_provider_manifest")

    exit_code = bridge.main(
        [
            "--packets",
            str(packets_path),
            "--model",
            "deepseek-v4-pro",
            "--limit-seeds",
            "2",
            "--samples",
            "0,1",
            "--periods",
            "6",
            "--output-root",
            str(bundle),
        ]
    )
    assert exit_code == 0

    from tradearena.evaluation.submissions import validate_submission_file

    manifests = sorted((bundle / "provider_manifests").glob("*.json"))
    submissions = sorted((bundle / "submissions").glob("*.json"))
    assert len(manifests) == 4  # 2 seeds x 2 samples, single fixture scenario
    assert len(submissions) == 4
    for manifest_path in manifests:
        manifest, errors = validators.validate_direct_provider_manifest_file(manifest_path)
        assert errors == []
        assert manifest["provider"] == "deepseek"
        assert manifest["model_id"] == "deepseek-v4-pro"
        assert manifest["cache"]["cache_status"] == "cache_replay"
        assert "fixture" in manifest["evidence"]["claim_scope"].lower()
        assert manifest["sampling"] == {"temperature": 0.2, "top_p": 1.0, "max_tokens": 1200}
    for submission_path in submissions:
        submission, errors = validate_submission_file(submission_path)
        assert errors == []
        assert "protocol-fixture" in submission["evidence"]["tags"]
        assert "direct-api" in submission["evidence"]["tags"]
        assert submission["agent"]["prompt_mode"] == "weights_only"
        assert 0.0 <= submission["agent"]["parse_coverage"] <= 1.0

    with (bundle / "direct_api_submission_runs.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {row["status"] for row in rows} == {"ok"}
    assert {row["mode"] for row in rows} == {"dry-run"}
    assert {row["seed"] for row in rows} == {"7", "11"}
    assert {row["sample_index"] for row in rows} == {"0", "1"}
    assert all(int(row["llm_call_count"]) == 6 for row in rows)

    # Private call logs stay inside the bundle and hold the raw text evidence.
    call_logs = sorted((bundle / "private" / "llm_cache").glob("*.jsonl"))
    assert len(call_logs) == 4

    # The dry-run bundle must remain non-headline in the matrix gate.
    gate = _load_module("build_v03_direct_api_matrix_gate")
    gate_dir = tmp_path / "gate_dry_run"
    assert (
        gate.main(
            [
                "--output-dir",
                str(gate_dir),
                "--submission-dirs",
                str(bundle / "submissions"),
                "--provider-manifest-dirs",
                str(bundle / "provider_manifests"),
            ]
        )
        == 0
    )
    summary = json.loads((gate_dir / "direct_api_matrix_gate_summary.json").read_text(encoding="utf-8"))
    assert summary["row_count"] == 4
    assert summary["valid_row_count"] == 4
    assert summary["main_threshold_group_count"] == 0
    assert summary["headline_scientific_claim_ready"] is False


def test_injected_execute_bundle_passes_matrix_gate(tmp_path: Path):
    packets_path = _build_packets(tmp_path)
    bundle = tmp_path / "bundle"
    bridge = _load_module("run_v03_direct_api_submission")
    calls: list[dict] = []

    # The --execute code path is exercised with an injected offline transport:
    # no credential is read and no network call is possible.
    exit_code = bridge.main(
        [
            "--packets",
            str(packets_path),
            "--model",
            "deepseek-v4-pro",
            "--periods",
            "4",
            "--execute",
            "--output-root",
            str(bundle),
        ],
        transport=_counting_transport(calls),
    )
    assert exit_code == 0
    # 10 pre-registered seeds x 3 samples x 4 periods.
    assert len(calls) == 10 * 3 * 4

    submissions = sorted((bundle / "submissions").glob("*.json"))
    assert len(submissions) == 30
    sample_submission = json.loads(submissions[0].read_text(encoding="utf-8"))
    assert "protocol-fixture" not in sample_submission["evidence"]["tags"]
    assert "direct-api" in sample_submission["evidence"]["tags"]

    gate = _load_module("build_v03_direct_api_matrix_gate")
    gate_dir = tmp_path / "gate"
    assert (
        gate.main(
            [
                "--output-dir",
                str(gate_dir),
                "--submission-dirs",
                str(bundle / "submissions"),
                "--provider-manifest-dirs",
                str(bundle / "provider_manifests"),
            ]
        )
        == 0
    )
    summary = json.loads((gate_dir / "direct_api_matrix_gate_summary.json").read_text(encoding="utf-8"))
    assert summary["row_count"] == 30
    assert summary["valid_row_count"] == 30
    assert summary["main_threshold_group_count"] == 1
    assert summary["headline_scientific_claim_ready"] is True

    with (gate_dir / "direct_api_matrix_gate_coverage.csv").open(encoding="utf-8") as handle:
        coverage = list(csv.DictReader(handle))
    assert len(coverage) == 1
    assert coverage[0]["main_threshold_met"] == "true"
    assert coverage[0]["seed_count"] == "10"
    assert coverage[0]["minimum_samples_per_seed"] == "3"
    assert coverage[0]["blocking_reasons"] == ""


def test_rerun_skips_completed_seed_sample_pairs(tmp_path: Path):
    packets_path = _build_packets(tmp_path)
    bundle = tmp_path / "bundle"
    bridge = _load_module("run_v03_direct_api_submission")
    calls: list[dict] = []
    argv = [
        "--packets",
        str(packets_path),
        "--model",
        "deepseek-v4-flash",
        "--limit-seeds",
        "2",
        "--samples",
        "0,1",
        "--periods",
        "5",
        "--output-root",
        str(bundle),
    ]

    assert bridge.main(argv, transport=_counting_transport(calls)) == 0
    first_pass_calls = len(calls)
    assert first_pass_calls == 4 * 5

    assert bridge.main(argv, transport=_counting_transport(calls)) == 0
    assert len(calls) == first_pass_calls  # every completed (seed, sample) was skipped

    with (bundle / "direct_api_submission_runs.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {row["status"] for row in rows} == {"ok"}


def test_failure_rows_are_recorded_and_retried(tmp_path: Path):
    packets_path = _build_packets(tmp_path)
    bundle = tmp_path / "bundle"
    bridge = _load_module("run_v03_direct_api_submission")
    argv = [
        "--packets",
        str(packets_path),
        "--model",
        "deepseek-v4-pro",
        "--limit-seeds",
        "2",
        "--samples",
        "0",
        "--periods",
        "4",
        "--output-root",
        str(bundle),
    ]

    failing: list[dict] = []
    assert bridge.main(argv, transport=_counting_transport(failing, fail_seeds={11})) == 1
    with (bundle / "direct_api_submission_runs.csv").open(encoding="utf-8") as handle:
        rows = {row["plan_id"]: row for row in csv.DictReader(handle)}
    assert len(rows) == 2
    statuses = {row["seed"]: row["status"] for row in rows.values()}
    assert statuses == {"7": "ok", "11": "failed"}
    failed_row = next(row for row in rows.values() if row["status"] == "failed")
    assert failed_row["error_class"] == "RuntimeError"

    # A rerun retries only the failed row and heals the bundle.
    healing: list[dict] = []
    assert bridge.main(argv, transport=_counting_transport(healing)) == 0
    assert {call["seed"] for call in healing} == {11}
    with (bundle / "direct_api_submission_runs.csv").open(encoding="utf-8") as handle:
        rows_after = list(csv.DictReader(handle))
    assert {row["status"] for row in rows_after} == {"ok"}
    assert len(rows_after) == 2
