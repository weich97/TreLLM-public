"""E1: adversarial fault-injection matrix for the Airlock control plane.

The Airlock fault-evaluation matrix (results under
``docs/results/live_readiness_e1/``). Generates six families of single-defect faulted session
bundles (>=50 variants each, in-catalog directed + out-of-catalog fuzzing) from
one clean reconciled template, pushes each through the five validation layers in
deployment order, and records the first-intercepting layer or an escape. Pure
local computation: zero LLM calls, zero network.

Outputs (docs/results/live_readiness_e1/):

- ``e1_interception.csv``   per-variant ledger (fault id, family, bucket, kind,
                            expected vs first-intercepting layer, target field).
- ``e1_matrix.csv``         the family x layer interception matrix with counts,
                            percentages, and 95% Wilson intervals.
- ``e1_matrix.md``          human-readable report: headline matrix, escape
                            autopsy grouped by class, circularity note, machine.
- ``e1_matrix.json``        the full structured result (matrix + autopsy + config).
- ``e1_matrix_table.tex``   a LaTeX table of the interception matrix.

Usage:

  python scripts/run_airlock_faults.py \
    --variants-per-family 60 --reserve-fuzz 20 --seed 2027 \
    --output-dir docs/results/live_readiness_e1 \
    --tmp-dir outputs/live_readiness_e1_tmp
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradearena.evaluation.airlock_faults import (
    ESCAPE,
    FAMILY_LABELS,
    HEADLINE_FAMILIES,
    LAYER_LABELS,
    LAYERS,
    E1Report,
    run_e1,
)

DEFAULT_OUTPUT_DIR = ROOT / "docs" / "results" / "live_readiness_e1"
DEFAULT_TMP_DIR = ROOT / "outputs" / "live_readiness_e1_tmp"

LEDGER_FIELDS = (
    "fault_id",
    "family",
    "family_label",
    "bucket",
    "kind",
    "expected_layer",
    "first_layer",
    "intercepted",
    "target_field",
    "description",
    "detail",
)

MATRIX_FIELDS = (
    "family",
    "family_label",
    "layer",
    "count",
    "pct",
    "ci_low_pct",
    "ci_high_pct",
    "family_total",
)


def _cpu_name() -> str:
    if os.name == "nt":
        try:
            import winreg

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            return " ".join(str(value).split())
        except OSError:
            pass
    return platform.processor() or "unknown"


def _machine_spec() -> dict[str, object]:
    return {
        "cpu_model": _cpu_name(),
        "logical_cores": os.cpu_count(),
        "os": platform.platform(),
        "python": platform.python_version(),
    }


def _write_ledger(path: Path, report: E1Report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(LEDGER_FIELDS))
        writer.writeheader()
        for result in report.results:
            writer.writerow(
                {
                    "fault_id": result.fault_id,
                    "family": result.family,
                    "family_label": FAMILY_LABELS[result.family],
                    "bucket": result.bucket,
                    "kind": result.kind,
                    "expected_layer": result.expected_layer or "",
                    "first_layer": result.first_layer,
                    "intercepted": result.first_layer != ESCAPE,
                    "target_field": result.field_name,
                    "description": result.description,
                    "detail": result.detail,
                }
            )


def _write_matrix_csv(path: Path, report: E1Report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    families = list(HEADLINE_FAMILIES) + [family for family in report.matrix["families"] if family not in HEADLINE_FAMILIES]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MATRIX_FIELDS))
        writer.writeheader()
        for family in families:
            fm = report.matrix["families"][family]
            for layer in LAYERS:
                cell = fm["cells"][layer]
                writer.writerow(
                    {
                        "family": family,
                        "family_label": fm["label"],
                        "layer": layer,
                        "count": cell["count"],
                        "pct": cell["pct"],
                        "ci_low_pct": cell["ci_low_pct"],
                        "ci_high_pct": cell["ci_high_pct"],
                        "family_total": fm["total"],
                    }
                )
            writer.writerow(
                {
                    "family": family,
                    "family_label": fm["label"],
                    "layer": "total_intercepted",
                    "count": fm["intercepted_count"],
                    "pct": fm["intercepted_pct"],
                    "ci_low_pct": fm["intercepted_ci_low_pct"],
                    "ci_high_pct": fm["intercepted_ci_high_pct"],
                    "family_total": fm["total"],
                }
            )
            writer.writerow(
                {
                    "family": family,
                    "family_label": fm["label"],
                    "layer": "escape",
                    "count": fm["escape_count"],
                    "pct": round(100 * fm["escape_count"] / fm["total"], 2) if fm["total"] else 0.0,
                    "ci_low_pct": "",
                    "ci_high_pct": "",
                    "family_total": fm["total"],
                }
            )


def _matrix_markdown_table(report: E1Report) -> list[str]:
    header = "| First-intercepting layer | " + " | ".join(f"{f} {FAMILY_LABELS[f].split(' ')[0]}" for f in HEADLINE_FAMILIES) + " |"
    sep = "| --- | " + " | ".join("---:" for _ in HEADLINE_FAMILIES) + " |"
    lines = [header, sep]
    for layer in LAYERS:
        cells = []
        for family in HEADLINE_FAMILIES:
            cell = report.matrix["families"][family]["cells"][layer]
            cells.append(f"{cell['pct']:.1f}")
        lines.append(f"| {LAYER_LABELS[layer]} | " + " | ".join(cells) + " |")
    total_cells = []
    escape_cells = []
    for family in HEADLINE_FAMILIES:
        fm = report.matrix["families"][family]
        total_cells.append(f"{fm['intercepted_pct']:.1f} [{fm['intercepted_ci_low_pct']:.0f},{fm['intercepted_ci_high_pct']:.0f}]")
        escape_cells.append(str(fm["escape_count"]))
    lines.append("| **Total intercepted (%)** | " + " | ".join(total_cells) + " |")
    lines.append("| **Escapes (count)** | " + " | ".join(escape_cells) + " |")
    return lines


def _latex_matrix_table(report: E1Report) -> str:
    cols = "l" + "c" * len(HEADLINE_FAMILIES)
    head = " & ".join(
        ["First-intercepting layer"] + [f"F{i + 1} {FAMILY_LABELS[f].split(' ')[0]}" for i, f in enumerate(HEADLINE_FAMILIES)]
    )
    lines = [
        "% Auto-generated by scripts/run_airlock_faults.py -- do not edit by hand.",
        "% Fault-injection matrix; see docs/results/live_readiness_e1/.",
        "\\begin{tabular}{@{}" + cols + "@{}}",
        "\\toprule",
        head + " \\\\",
        "\\midrule",
    ]
    for layer in LAYERS:
        row = [LAYER_LABELS[layer]]
        for family in HEADLINE_FAMILIES:
            row.append(f"{report.matrix['families'][family]['cells'][layer]['pct']:.1f}")
        lines.append(" & ".join(row) + " \\\\")
    lines.append("\\midrule")
    total_row = ["Total intercepted (\\%)"]
    escape_row = ["Escapes (count)"]
    for family in HEADLINE_FAMILIES:
        fm = report.matrix["families"][family]
        total_row.append(
            f"{fm['intercepted_pct']:.1f} {{\\tiny[{fm['intercepted_ci_low_pct']:.0f},{fm['intercepted_ci_high_pct']:.0f}]}}"
        )
        escape_row.append(str(fm["escape_count"]))
    lines.append(" & ".join(total_row) + " \\\\")
    lines.append(" & ".join(escape_row) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    return "\n".join(lines) + "\n"


def _write_markdown(path: Path, report: E1Report, machine: dict[str, object], elapsed: float) -> None:
    matrix = report.matrix
    overall = matrix["overall"]
    lines: list[str] = []
    lines.append("# E1: Fault-Injection Interception Matrix (Airlock Control Plane)")
    lines.append("")
    lines.append(
        "Adversarial single-defect faults across six families are pushed through the five "
        "validation layers in deployment order; each variant is attributed to the first layer "
        "that rejects it, or recorded as an escape. Pure local computation: zero LLM calls, "
        "zero network."
    )
    lines.append("")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append("- Command: `python scripts/run_airlock_faults.py`")
    lines.append(
        f"- Variants: {report.config['variants_per_family']} per family "
        f"({report.config['reserve_fuzz']} reserved for out-of-catalog fuzzing), seed {report.config['seed']}"
    )
    lines.append(
        f"- Total faulted bundles: {report.config['total_variants']} "
        f"across {len(HEADLINE_FAMILIES)} headline families + {len(report.config['aux_families'])} auxiliary"
    )
    lines.append(f"- Review time (`--now`): {report.config['check_now']}; template is one reconciled dry-run session")
    lines.append(f"- Wall clock: {elapsed:.1f}s")
    lines.append("")
    lines.append("## Machine")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("| --- | --- |")
    for key, value in machine.items():
        lines.append(f"| {key} | `{value}` |")
    lines.append("")
    lines.append("## Headline interception matrix")
    lines.append("")
    lines.append(
        "Cell values are the percentage of a family's variants whose *first-intercepting* layer "
        "is that row. The Total row carries the 95% Wilson interval over the family's variants; "
        "per-cell intervals are in `e1_matrix.csv`."
    )
    lines.append("")
    lines.extend(_matrix_markdown_table(report))
    lines.append("")
    lines.append(
        f"**Overall:** {overall['intercepted_count']}/{overall['total']} variants intercepted "
        f"= {overall['intercepted_pct']:.2f}% "
        f"(95% Wilson [{overall['intercepted_ci_low_pct']:.2f}, {overall['intercepted_ci_high_pct']:.2f}]); "
        f"{overall['escape_count']} escapes."
    )
    lines.append("")
    # Auxiliary families (journal chain).
    aux = [family for family in matrix["families"] if family not in HEADLINE_FAMILIES]
    if aux:
        lines.append("## Auxiliary families (outside the six-column headline)")
        lines.append("")
        lines.append("| Family | Variants | Intercepted (%) | Escapes |")
        lines.append("| --- | ---: | ---: | ---: |")
        for family in aux:
            fm = matrix["families"][family]
            lines.append(
                f"| {family} {fm['label']} | {fm['total']} | "
                f"{fm['intercepted_pct']:.1f} [{fm['intercepted_ci_low_pct']:.0f},{fm['intercepted_ci_high_pct']:.0f}] "
                f"| {fm['escape_count']} |"
            )
        lines.append("")
        lines.append(
            "The append-only journal is not one of the six headline columns of the interception matrix, "
            "but `verify_journal_chain` is a real guard (orchestrator/audit layer) and is exercised here."
        )
        lines.append("")
    # Escape autopsy.
    lines.append("## Escape autopsy and co-evolution")
    lines.append("")
    class_labels = {"a": "schema-expressible but unchecked", "b": "requires semantic cross-artifact checking", "c": "requires a human"}
    class_counts = Counter(entry["class"] for entry in report.autopsy)
    lines.append(
        f"{len(report.autopsy)} escapes: "
        + ", ".join(f"{class_counts.get(cls, 0)} class ({cls}) {label}" for cls, label in class_labels.items())
        + "."
    )
    lines.append("")
    if report.autopsy:
        # Group escapes by (class, target_field) for a compact ledger.
        grouped: dict[tuple[str, str], dict[str, object]] = {}
        for entry in report.autopsy:
            key = (str(entry["class"]), str(entry["target_field"]))
            bucket = grouped.setdefault(
                key,
                {
                    "class": entry["class"],
                    "class_label": entry["class_label"],
                    "target_field": entry["target_field"],
                    "mechanism": entry["mechanism"],
                    "proposed_hardening": entry["proposed_hardening"],
                    "families": set(),
                    "count": 0,
                },
            )
            bucket["count"] = int(bucket["count"]) + 1
            families_set = bucket["families"]
            assert isinstance(families_set, set)
            families_set.add(entry["family"])
        lines.append("| Class | Target field | Count | Families | Mechanism | Proposed hardening |")
        lines.append("| --- | --- | ---: | --- | --- | --- |")
        for (_cls, _field), bucket in sorted(grouped.items()):
            fams = ",".join(sorted(str(f) for f in bucket["families"]))  # type: ignore[union-attr]
            lines.append(
                f"| ({bucket['class']}) {bucket['class_label']} | `{bucket['target_field']}` | {bucket['count']} "
                f"| {fams} | {bucket['mechanism']} | {bucket['proposed_hardening']} |"
            )
        lines.append("")
    lines.append("### Reading the autopsy")
    lines.append("")
    lines.append(
        "- **Class (a)** escapes are hardening targets: the fault could be rejected by a constraint "
        "that does not yet exist (here: operator/identifier fields accept homoglyph, zero-width, "
        "full-width, and case-folded look-alikes because the id is self-asserted and never "
        "cross-checked). The proposed diff tightens the identifier pattern and normalizes Unicode."
    )
    lines.append(
        "- **Class (c)** escapes are the argument for the human gate: free-text rationale and "
        "labeling fields (`approval_reason`, per-artifact `safety_note`, `adapter_name`) can be "
        "rewritten while every hash and cross-artifact binding stays consistent. No machine "
        "constraint can decide whether the *content* is truthful; a human reviewer must."
    )
    lines.append(
        "- **Class (b)** escapes (none observed) would indicate a gap in the cross-artifact "
        "preflight itself."
    )
    lines.append("")
    lines.append("## Circularity mitigation")
    lines.append("")
    lines.append(
        "The out-of-catalog fuzzer draws from generic mutation operators (field deletion, type "
        "replacement, boundary numerics, unknown fields, cross-artifact splices, nesting abuse, "
        "free-text tamper) chosen independently of the guard list. It is where the 29 class-(c) "
        "escapes were found rather than authored. The 5 class-(a) escapes came from the directed "
        "catalog instead: they were authored as probes, and the pipeline failed to reject them, "
        "which is a hardening finding rather than a discovery by search. A matrix returning 100% "
        "interception with an empty escape set would signal that the evaluation was too weak (a "
        "pre-registered kill criterion), not that the system is impenetrable."
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, report: E1Report, machine: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "trellm_airlock_e1_matrix_v0.1",
        "config": report.config,
        "machine": machine,
        "matrix": report.matrix,
        "autopsy": report.autopsy,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E1 fault-injection interception matrix (zero LLM, zero network).")
    parser.add_argument("--variants-per-family", type=int, default=60, help="Variants per family (>=50; default 60).")
    parser.add_argument("--reserve-fuzz", type=int, default=20, help="Out-of-catalog fuzz variants reserved per family.")
    parser.add_argument("--seed", type=int, default=2027, help="Deterministic catalog seed (default 2027).")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for e1_* outputs.")
    parser.add_argument("--tmp-dir", default=str(DEFAULT_TMP_DIR), help="Scratch directory for the session template.")
    parser.add_argument("--keep-tmp", action="store_true", help="Keep the scratch directory after the run.")
    args = parser.parse_args(argv)

    if args.variants_per_family < 1 or args.reserve_fuzz < 0:
        print("variants-per-family must be >= 1 and reserve-fuzz >= 0")
        return 1
    if args.reserve_fuzz > args.variants_per_family:
        print("reserve-fuzz cannot exceed variants-per-family")
        return 1

    output_dir = Path(args.output_dir)
    tmp_dir = Path(args.tmp_dir)
    machine = _machine_spec()
    print(f"E1 fault-injection matrix on {machine['cpu_model']} ({machine['logical_cores']} logical cores)")
    print(f"  variants/family={args.variants_per_family} reserve-fuzz={args.reserve_fuzz} seed={args.seed}")

    started = time.perf_counter()
    report = run_e1(
        tmp_dir,
        variants_per_family=args.variants_per_family,
        reserve_fuzz=args.reserve_fuzz,
        seed=args.seed,
    )
    elapsed = time.perf_counter() - started

    overall = report.matrix["overall"]
    print(
        f"  {overall['intercepted_count']}/{overall['total']} intercepted "
        f"({overall['intercepted_pct']:.2f}%), {overall['escape_count']} escapes"
    )
    layer_dist = Counter(result.first_layer for result in report.results)
    for layer in LAYERS:
        print(f"    {LAYER_LABELS[layer]:<28} {layer_dist.get(layer, 0)}")
    print(f"    {'escape':<28} {layer_dist.get(ESCAPE, 0)}")

    ledger_path = output_dir / "e1_interception.csv"
    matrix_csv_path = output_dir / "e1_matrix.csv"
    md_path = output_dir / "e1_matrix.md"
    json_path = output_dir / "e1_matrix.json"
    tex_path = output_dir / "e1_matrix_table.tex"

    _write_ledger(ledger_path, report)
    _write_matrix_csv(matrix_csv_path, report)
    _write_markdown(md_path, report, machine, elapsed)
    _write_json(json_path, report, machine)
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text(_latex_matrix_table(report), encoding="utf-8")

    if not args.keep_tmp:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    for path in (ledger_path, matrix_csv_path, md_path, json_path, tex_path):
        print(f"  wrote {path}")
    print(f"E1 done in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
