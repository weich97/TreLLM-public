"""Smoke and invariant tests for the Airlock E1 fault-injection harness."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

from tradearena.evaluation.airlock_faults import (
    ESCAPE,
    HEADLINE_FAMILIES,
    LAYERS,
    build_clean_template,
    build_fault_catalog,
    run_e1,
    run_intercept_matrix,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_runner():
    path = ROOT / "scripts" / "run_airlock_faults.py"
    spec = importlib.util.spec_from_file_location("run_airlock_faults", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_clean_template_passes_every_layer(tmp_path: Path) -> None:
    template = build_clean_template(tmp_path / "tpl")
    # All six artifact payloads and the journal are present and non-trivial.
    for name in ("capability", "handoff", "approval", "response", "runbook", "bundle"):
        assert isinstance(template.payloads[name], dict)
    assert template.journal_lines
    # The untouched template must escape (i.e., be accepted) at CHECK_NOW, which
    # is the harness's own sanity gate inside run_intercept_matrix.
    catalog = build_fault_catalog(variants_per_family=6, reserve_fuzz=2, seed=1)
    results = run_intercept_matrix(template, catalog)
    assert results, "expected at least one fault result"


def test_each_headline_family_has_at_least_fifty_variants() -> None:
    catalog = build_fault_catalog(variants_per_family=55, reserve_fuzz=20, seed=2027)
    for family in HEADLINE_FAMILIES:
        assert len(catalog[family]) == 55, f"{family} must have exactly the requested variant count"
        buckets = {spec.bucket for spec in catalog[family]}
        assert "fuzz" in buckets, f"{family} must include out-of-catalog fuzz variants"
        assert "directed" in buckets, f"{family} must include in-catalog directed variants"


def test_run_e1_is_deterministic_and_well_formed(tmp_path: Path) -> None:
    first = run_e1(tmp_path / "a", variants_per_family=30, reserve_fuzz=10, seed=2027)
    second = run_e1(tmp_path / "b", variants_per_family=30, reserve_fuzz=10, seed=2027)

    def _fingerprint(report) -> list[tuple[str, str]]:
        return [(r.fault_id, r.first_layer) for r in report.results]

    assert _fingerprint(first) == _fingerprint(second), "same seed must give the same first-layer attribution"

    overall = first.matrix["overall"]
    assert overall["total"] == len(first.results)
    assert 0 <= overall["intercepted_pct"] <= 100
    assert overall["intercepted_count"] + overall["escape_count"] == overall["total"]

    # Every result is attributed to a known layer or an escape.
    valid = set(LAYERS) | {ESCAPE}
    assert all(r.first_layer in valid for r in first.results)


def test_matrix_cells_and_wilson_intervals(tmp_path: Path) -> None:
    report = run_e1(tmp_path / "m", variants_per_family=50, reserve_fuzz=18, seed=2027)
    for family in HEADLINE_FAMILIES:
        fm = report.matrix["families"][family]
        # Cell counts across the five layers plus escapes must sum to the family total.
        cell_sum = sum(fm["cells"][layer]["count"] for layer in LAYERS)
        assert cell_sum + fm["escape_count"] == fm["total"]
        # Wilson interval brackets the point estimate.
        assert fm["intercepted_ci_low_pct"] <= fm["intercepted_pct"] <= fm["intercepted_ci_high_pct"]
        assert fm["total"] >= 50


def test_directed_identifier_and_binding_faults_are_intercepted(tmp_path: Path) -> None:
    report = run_e1(tmp_path / "d", variants_per_family=60, reserve_fuzz=20, seed=2027)
    by_id = {r.fault_id: r for r in report.results}
    # Whitespace pollution of a hashed identifier is caught at the schema layer.
    assert by_id["F1-handoff-orders[0].symbol-lead_space"].first_layer == "schema_validation"
    # A post-approval handoff edit breaks the approval/response hash binding.
    assert by_id["F3-handoff-postapproval-quantity-x10"].first_layer == "approval_hash_binding"
    # Replaying a foreign approval is only caught by the live orchestrator.
    assert by_id["F3-orchestrator-replay-foreign-approval"].first_layer == "orchestrator_revalidation"
    # Journal tampering is caught by the append-only chain verifier.
    assert by_id["F7-journal-reorder"].first_layer == "orchestrator_revalidation"


def test_escapes_are_found_and_classified(tmp_path: Path) -> None:
    report = run_e1(tmp_path / "e", variants_per_family=60, reserve_fuzz=20, seed=2027)
    # Out-of-catalog fuzzing plus identity pollution must surface some escapes
    # (an empty escape set is a pre-registered kill criterion, not a pass).
    assert report.autopsy, "expected the fuzzer to find at least one escape"
    classes = {entry["class"] for entry in report.autopsy}
    assert classes <= {"a", "b", "c"}
    for entry in report.autopsy:
        assert entry["proposed_hardening"]
        assert entry["target_field"]


def test_runner_writes_all_artifacts(tmp_path: Path) -> None:
    module = _load_runner()
    output_dir = tmp_path / "e1_out"
    exit_code = module.main(
        [
            "--variants-per-family",
            "24",
            "--reserve-fuzz",
            "8",
            "--seed",
            "2027",
            "--output-dir",
            str(output_dir),
            "--tmp-dir",
            str(tmp_path / "e1_tmp"),
        ]
    )
    assert exit_code == 0

    ledger = _read_csv(output_dir / "e1_interception.csv")
    assert ledger
    assert {"fault_id", "family", "first_layer", "intercepted", "target_field"} <= set(ledger[0].keys())

    matrix_rows = _read_csv(output_dir / "e1_matrix.csv")
    layers_seen = {row["layer"] for row in matrix_rows}
    assert set(LAYERS) <= layers_seen
    assert "total_intercepted" in layers_seen and "escape" in layers_seen

    payload = json.loads((output_dir / "e1_matrix.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "trellm_airlock_e1_matrix_v0.1"
    assert set(HEADLINE_FAMILIES) <= set(payload["matrix"]["families"].keys())

    md_text = (output_dir / "e1_matrix.md").read_text(encoding="utf-8")
    for marker in ("Headline interception matrix", "Escape autopsy", "Circularity mitigation", "cpu_model"):
        assert marker in md_text

    tex_text = (output_dir / "e1_matrix_table.tex").read_text(encoding="utf-8")
    assert "\\begin{tabular}" in tex_text and "Total intercepted" in tex_text

    # Scratch directory is cleaned up by default.
    assert not (tmp_path / "e1_tmp").exists()
