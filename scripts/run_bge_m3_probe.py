from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tradearena.core.trajectory import StepRecord, Trajectory
from tradearena.experiments.paper import _embed_text, _mean, _plan_text, _rolling_failure_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate TreLLM representation signatures with local BGE-family Transformer embeddings.")
    parser.add_argument(
        "--trajectory",
        nargs="+",
        default=["outputs/tradearena_paper/raw/llm_matrix_gpt_5_5_risk_aware_trajectory.json"],
        help="One or more trajectory JSON files used for the Transformer embedding probe.",
    )
    parser.add_argument("--model", default="BAAI/bge-m3", help="SentenceTransformers model name.")
    parser.add_argument(
        "--model-label",
        default="",
        help="Display label written to the output table. Useful when loading a local cached model directory.",
    )
    parser.add_argument("--output-dir", default="outputs/tradearena_paper/tables", help="Output table directory.")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--hf-endpoint",
        default=os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"),
        help="Hugging Face endpoint mirror used before model loading. Use an empty string for the official endpoint.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.hf_endpoint:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint
    trajectories = [load_trajectory(Path(path)) for path in args.trajectory]
    texts: list[str] = []
    spans: list[tuple[Trajectory, int, int]] = []
    for trajectory in trajectories:
        start = len(texts)
        texts.extend(_plan_text(step) for step in trajectory.steps)
        spans.append((trajectory, start, len(texts)))
    bge_vectors = embed_bge(args.model, texts, args.batch_size)
    hash_vectors = [_embed_text(text) for text in texts]

    rows = []
    transformer_label = embedding_label(args.model)
    display_model = args.model_label or ("BAAI/bge-m3" if transformer_label == "bge_m3" else args.model)
    for trajectory, start, end in spans:
        for embedding, vectors in ((transformer_label, bge_vectors[start:end]), ("hash64", hash_vectors[start:end])):
            events = _rolling_failure_events(trajectory.experiment_name, trajectory, vectors)
            rows.append(
                {
                    "case": trajectory.experiment_name,
                    "embedding": embedding,
                    "model": display_model if embedding != "hash64" else "deterministic_hash_64",
                    "steps": len(vectors),
                    "anchors": len(events),
                    "pre_steps": sum(int(row["pre_steps"]) for row in events),
                    "mean_pre_shift": _mean([float(row["pre_shift"]) for row in events]),
                    "mean_effective_rank_delta": _mean(
                        [float(row["effective_rank_delta"]) for row in events if row["effective_rank_delta"] != ""]
                    ),
                    "rank_contraction_rate": _mean(
                        [1.0 if float(row["effective_rank_delta"]) > 0.0 else 0.0 for row in events if row["effective_rank_delta"] != ""]
                    ),
                    "mean_early_warning_ba": _mean([float(row["early_warning_ba"]) for row in events]),
                }
            )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "transformer_embedding_probe.csv", rows)
    write_markdown(output_dir / "transformer_embedding_probe.md", rows)
    for row in rows:
        print(row)
    return 0


def embed_bge(model_name: str, texts: list[str], batch_size: int) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install the embedding extra first: python -m pip install -e .[embeddings]") from exc
    model = SentenceTransformer(model_name)
    vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)
    return [[float(value) for value in vector] for vector in vectors]


def embedding_label(model_name: str) -> str:
    normalized = str(model_name).replace("\\", "/").lower()
    if "bge-m3" in normalized or "bge_m3" in normalized:
        return "bge_m3"
    return "bge_transformer"


def load_trajectory(path: Path) -> Trajectory:
    data = json.loads(path.read_text(encoding="utf-8"))
    steps = []
    for item in data["steps"]:
        steps.append(
            StepRecord(
                timestamp=datetime.fromisoformat(item["timestamp"]),
                observation=item.get("observation", {}),
                signals=item.get("signals", []),
                decisions=item.get("decisions", []),
                approved_decisions=item.get("approved_decisions", []),
                orders=item.get("orders", []),
                fills=item.get("fills", []),
                portfolio=item.get("portfolio", {}),
                reproducibility_state=item.get("reproducibility_state", {}),
                agent_trace=item.get("agent_trace", {}),
                risk_report=item.get("risk_report", {}),
                in_trade_report=item.get("in_trade_report", {}),
                post_trade_report=item.get("post_trade_report", {}),
                execution_report=item.get("execution_report", {}),
                risk_violations=item.get("risk_violations", []),
                memory_events=item.get("memory_events", []),
            )
        )
    return Trajectory(
        experiment_name=str(data.get("experiment_name", path.stem.replace("_trajectory", ""))),
        seed=int(data.get("seed", 0)),
        steps=steps,
        metadata=data.get("metadata", {}),
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    columns = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    columns = list(rows[0])
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(format_cell(row[column]) for column in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
