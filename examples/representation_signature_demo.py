from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from tradearena.core.serialization import write_json

OUTPUT_DIR = Path("outputs/examples")
TABLE_DIR = Path("outputs/tradearena_paper/tables")
FALLBACK_TABLE_DIR = Path("docs/results/representation")


def main() -> int:
    robustness = _read_table("embedding_robustness.csv")
    dense = _read_table("transformer_embedding_probe.csv")
    lexical = _read_table("language_collapse_controls.csv")
    if not robustness:
        raise FileNotFoundError(
            "Missing embedding_robustness.csv. Run the diagnostic suite or fetch tracked docs/results tables."
        )

    summary = {
        "hash_lsa_rows": _select_rows(robustness, "cohort", "all_llm"),
        "dense_probe_rows": dense,
        "lexical_control_rows": _select_rows(lexical, "cohort", "all_llm"),
        "interpretation": (
            "Pre-failure rank contraction is checked in deterministic Hash64, LSA32, "
            "optional BGE-M3 dense embeddings, and lexical controls."
        ),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "representation_signature_summary.json", summary)
    _write_svg(OUTPUT_DIR / "representation_signature.svg", summary)

    print("Representation signature demo")
    for row in summary["hash_lsa_rows"]:
        print(
            f"  {row['embedding']}:{row['view']} rank_delta={float(row['mean_effective_rank_delta']):.3f} "
            f"contraction={float(row['rank_contraction_rate']):.3f}"
        )
    print(f"  dense_probe_rows={len(dense)} lexical_control_rows={len(summary['lexical_control_rows'])}")
    print(f"\nWrote {OUTPUT_DIR / 'representation_signature.svg'}")
    return 0


def _read_table(name: str) -> list[dict[str, Any]]:
    for directory in (TABLE_DIR, FALLBACK_TABLE_DIR):
        rows = _read_rows(directory / name)
        if rows:
            return rows
    return []


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _select_rows(rows: list[dict[str, Any]], key: str, value: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get(key) == value]


def _write_svg(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["hash_lsa_rows"]
    dense_rows = summary["dense_probe_rows"]
    lexical_rows = summary["lexical_control_rows"]
    width, height = 920, 380
    max_delta = max(1.0, max(float(row["mean_effective_rank_delta"]) for row in rows))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Representation signature summary">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(36, 44, "Representation signatures: from table to visual diagnostic", 22, "#0f172a", 800),
        _text(36, 72, "A hands-on reader can inspect rank contraction, dense embedding agreement, and lexical controls without API calls.", 13, "#64748b", 400),
    ]
    for idx, row in enumerate(rows[:6]):
        x = 72 + idx * 126
        delta = float(row["mean_effective_rank_delta"])
        contraction = float(row["rank_contraction_rate"])
        bar_h = max(0, delta) / max_delta * 150
        color = "#2563eb" if row["embedding"] == "hash64" else "#7c3aed"
        parts.append(f'<rect x="{x}" y="{250 - bar_h:.1f}" width="58" height="{bar_h:.1f}" rx="6" fill="{color}"/>')
        parts.append(_text(x + 29, 272, f"{row['embedding']}", 11, "#0f172a", 700, "middle"))
        parts.append(_text(x + 29, 288, f"{row['view']}", 11, "#64748b", 500, "middle"))
        parts.append(_text(x + 29, 306, f"CR {contraction:.2f}", 10, "#64748b", 500, "middle"))
    dense_note = f"BGE-M3 rows: {len(dense_rows)}"
    if dense_rows:
        dense_note += f"; best BA {max(float(row['mean_early_warning_ba']) for row in dense_rows):.3f}"
    lexical_note = "Lexical controls: "
    if lexical_rows:
        lexical_note += ", ".join(
            f"{row['view']} no-lexical-collapse {float(row['rank_contraction_without_lexical_collapse']):.2f}"
            for row in lexical_rows[:2]
        )
    parts.append('<rect x="620" y="110" width="250" height="92" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
    parts.append(_text(638, 140, dense_note, 13, "#0f172a", 700))
    parts.append(_text(638, 166, lexical_note[:55], 11, "#475569", 500))
    parts.append(_text(638, 184, lexical_note[55:110], 11, "#475569", 500))
    parts.append(_text(72, 346, "Bar height = mean effective-rank delta before failure. CR = contraction rate.", 12, "#64748b", 500))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _text(x: float, y: float, value: str, size: int, color: str, weight: int, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{value}</text>'


if __name__ == "__main__":
    raise SystemExit(main())
