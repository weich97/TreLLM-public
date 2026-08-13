from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tradearena.experiments.paper import _hallucination_calibration_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate completed human hallucination annotations.")
    parser.add_argument("--annotations", default="data/annotations/hallucination_gold.csv")
    parser.add_argument("--sample", default="outputs/tradearena_paper/tables/hallucination_annotation_sample.csv")
    parser.add_argument("--output", default="outputs/tradearena_paper/tables/hallucination_annotation_calibration.csv")
    parser.add_argument("--min-kappa", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sample_rows = read_csv(Path(args.sample))
    rows = _hallucination_calibration_rows(sample_rows, args.annotations)
    if not rows:
        raise RuntimeError("Manual labels are missing; do not release incomplete hallucination calibration.")
    row = rows[0]
    if row.get("status") != "manual_labels_loaded":
        raise RuntimeError("Manual labels are missing; do not release incomplete hallucination calibration.")
    kappa = float(row["cohen_kappa"])
    if kappa < args.min_kappa:
        raise RuntimeError(f"Cohen's kappa {kappa:.3f} is below required threshold {args.min_kappa:.3f}.")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, rows)
    print(row)
    return 0


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    columns = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
