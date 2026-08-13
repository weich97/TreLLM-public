"""Smoke tests for the live-readiness E2 latency microbenchmark and E3 frontier sweep."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(script_name: str):
    path = ROOT / "scripts" / f"{script_name}.py"
    spec = importlib.util.spec_from_file_location(script_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _run_e2_smoke(tmp_path: Path) -> Path:
    module = _load_module("run_live_readiness_e2")
    output_dir = tmp_path / "e2_out"
    exit_code = module.main(
        [
            "--iterations",
            "3",
            "--warmup",
            "1",
            "--scaling-iterations",
            "2",
            "--scaling-order-counts",
            "1,2",
            "--output-dir",
            str(output_dir),
            "--tmp-dir",
            str(tmp_path / "e2_tmp"),
        ]
    )
    assert exit_code == 0
    return output_dir


def test_e2_smoke_writes_complete_csv_and_md(tmp_path: Path) -> None:
    output_dir = _run_e2_smoke(tmp_path)
    csv_path = output_dir / "e2_latency.csv"
    md_path = output_dir / "e2_latency.md"
    assert csv_path.exists()
    assert md_path.exists()

    rows = _read_csv(csv_path)
    assert rows, "E2 CSV must contain layer rows"
    expected_fields = {
        "layer",
        "samples",
        "order_count",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "mean_ms",
        "min_ms",
        "max_ms",
    }
    assert expected_fields == set(rows[0].keys())

    layers = {row["layer"] for row in rows}
    required_layers = {
        "schema_validation_per_artifact",
        "single_artifact_validators_all_six",
        "risk_gate",
        "hash_binding_checks",
        "journal_chain_verify",
        "cross_artifact_preflight_full_bundle",
        "step_propose",
        "step_approve",
        "step_execute",
        "step_reconcile",
        "final_gate",
        "orchestrator_step",
        "full_chain_session",
        "scaling_full_chain_n1",
        "scaling_full_chain_n2",
    }
    missing = required_layers - layers
    assert not missing, f"E2 CSV is missing layers: {sorted(missing)}"

    for row in rows:
        p50, p95, p99 = float(row["p50_ms"]), float(row["p95_ms"]), float(row["p99_ms"])
        assert 0 < p50 <= p95 <= p99, f"quantiles must be ordered and positive for {row['layer']}"
        assert float(row["min_ms"]) <= p50
        assert p99 <= float(row["max_ms"])
        assert int(row["samples"]) >= 2
        assert int(row["order_count"]) >= 1

    md_text = md_path.read_text(encoding="utf-8")
    assert "cpu_model" in md_text, "machine spec must be recorded in the markdown report"
    assert "Schema validation (per artifact)" in md_text
    assert "LLM decision call (measured anchor)" in md_text
    # The scratch session directories must have been cleaned up.
    assert not (tmp_path / "e2_tmp").exists()


def _write_synthetic_e2_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["layer", "samples", "order_count", "p50_ms", "p95_ms", "p99_ms", "mean_ms", "min_ms", "max_ms"]
    rows = [
        ("full_chain_session", 5, 3, 100.0, 120.0, 130.0, 105.0, 90.0, 130.0),
        ("scaling_full_chain_n1", 5, 1, 95.0, 110.0, 115.0, 96.0, 90.0, 115.0),
        ("scaling_full_chain_n50", 5, 50, 140.0, 160.0, 170.0, 141.0, 130.0, 170.0),
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)


def test_e3_chain_compute_interpolation_and_expiry_model() -> None:
    module = _load_module("run_live_readiness_e3")
    points = [(1, 110.0), (50, 160.0)]
    assert module.chain_compute_p95_ms(points, 1) == 110.0
    assert module.chain_compute_p95_ms(points, 50) == 160.0
    assert module.chain_compute_p95_ms(points, 100) == 160.0  # clamped above
    interpolated = module.chain_compute_p95_ms(points, 25)
    assert 110.0 < interpolated < 160.0

    # Per-minute cadence, 2.2-minute reviews: queue grows 1.2 min per session,
    # so the first approval expires at session floor((1440-2.2)/1.2)+1+1 = 1200.
    assert module.session_of_first_expiry(2.2, 1.0, 1440.0) == 1200
    assert module.session_of_first_expiry(10.0, 60.0, 1440.0) is None  # sustainable
    assert module.session_of_first_expiry(2000.0, 60.0, 1440.0) == 1  # first session already expires


def test_e3_smoke_fields_defaults_and_frontier(tmp_path: Path) -> None:
    module = _load_module("run_live_readiness_e3")
    e2_csv = tmp_path / "e2_latency.csv"
    _write_synthetic_e2_csv(e2_csv)
    output_dir = tmp_path / "e3_out"
    exit_code = module.main(["--e2-csv", str(e2_csv), "--output-dir", str(output_dir)])
    assert exit_code == 0

    rows = _read_csv(output_dir / "e3_frontier.csv")
    # 4 cadences x 50 book sizes x 4 latencies.
    assert len(rows) == 4 * 50 * 4
    assert set(module.CSV_FIELDS) == set(rows[0].keys())

    def _feasible(row: dict[str, str]) -> bool:
        return row["feasible"] == "True"

    by_key = {
        (row["frequency"], int(row["n_symbols"]), float(row["approval_latency_minutes"])): row for row in rows
    }
    # Deployed operating point: weekly cadence, 3 symbols, all tested latencies feasible.
    for latency in (1.0, 5.0, 15.0, 60.0):
        assert _feasible(by_key[("weekly", 3, latency)])
    # Per-minute cadence is infeasible everywhere and reports queue-driven expiry.
    per_minute = [row for row in rows if row["frequency"] == "per-minute"]
    assert per_minute and all(not _feasible(row) for row in per_minute)
    assert any(row["session_of_first_expiry"] for row in per_minute)
    # Assumptions must be spelled out in both outputs.
    md_text = (output_dir / "e3_frontier.md").read_text(encoding="utf-8")
    for marker in ("Assumptions", "assumed", "Approval expiry", "Weekly human ops budget"):
        assert marker in md_text
    assert rows[0]["review_base_minutes"] and rows[0]["weekly_budget_minutes"]


def test_e3_feasibility_monotone_in_latency_book_size_and_cadence(tmp_path: Path) -> None:
    module = _load_module("run_live_readiness_e3")
    e2_csv = tmp_path / "e2_latency.csv"
    _write_synthetic_e2_csv(e2_csv)

    # A short expiry window makes the latency dimension strictly binding.
    output_dir = tmp_path / "e3_tight"
    exit_code = module.main(
        ["--e2-csv", str(e2_csv), "--output-dir", str(output_dir), "--expiry-minutes", "30", "--max-symbols", "20"]
    )
    assert exit_code == 0
    rows = _read_csv(output_dir / "e3_frontier.csv")

    feasible = {
        (row["frequency"], int(row["n_symbols"]), float(row["approval_latency_minutes"])): row["feasible"] == "True"
        for row in rows
    }
    frequencies = sorted({row["frequency"] for row in rows})
    latencies = sorted({float(row["approval_latency_minutes"]) for row in rows})
    book_sizes = sorted({int(row["n_symbols"]) for row in rows})

    # Monotone: growing approval latency never turns an infeasible combo feasible.
    for frequency in frequencies:
        for n_symbols in book_sizes:
            flags = [feasible[(frequency, n_symbols, latency)] for latency in latencies]
            for earlier, later in zip(flags, flags[1:]):
                assert earlier or not later, (
                    f"feasibility must be non-increasing in approval latency ({frequency}, n={n_symbols})"
                )
    # Strict at the frontier: 60-minute latency exceeds the 30-minute expiry.
    total_by_latency = [sum(1 for key, ok in feasible.items() if key[2] == latency and ok) for latency in latencies]
    assert total_by_latency[0] > total_by_latency[-1] > 0 or total_by_latency[-1] == 0
    assert total_by_latency == sorted(total_by_latency, reverse=True)

    # Monotone in book size for fixed cadence and latency.
    for frequency in frequencies:
        for latency in latencies:
            flags = [feasible[(frequency, n, latency)] for n in book_sizes]
            for earlier, later in zip(flags, flags[1:]):
                assert earlier or not later, (
                    f"feasibility must be non-increasing in book size ({frequency}, latency={latency})"
                )
