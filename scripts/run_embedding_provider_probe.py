from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tradearena.core.trajectory import StepRecord, Trajectory
from tradearena.experiments.paper import _centroid, _cosine_distance, _effective_rank, _embed_text, _plan_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a 10-step embedding-provider robustness probe for TreLLM.")
    parser.add_argument(
        "--trajectory",
        default="outputs/tradearena_paper/raw/llm_matrix_feedback_glm_5_true_trajectory.json",
        help="Trajectory JSON used for the probe.",
    )
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model name.")
    parser.add_argument("--api-key-env", default="EMBEDDING_API_KEY", help="Environment variable containing the embedding-provider API key.")
    parser.add_argument("--base-url", default="https://api.openai.com/v1/embeddings", help="Embedding endpoint URL.")
    parser.add_argument("--normal-steps", default="0,1,2,3,4,5", help="Comma-separated normal-state step indices.")
    parser.add_argument("--pre-steps", default="31,32,33,34", help="Comma-separated pre-failure step indices.")
    parser.add_argument("--output-dir", default="outputs/tradearena_paper/tables", help="Output table directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise RuntimeError(f"{args.api_key_env} is not set; no embedding request was sent.")

    trajectory = load_trajectory(Path(args.trajectory))
    normal_steps = parse_indices(args.normal_steps)
    pre_steps = parse_indices(args.pre_steps)
    selected_steps = normal_steps + pre_steps
    texts = [_plan_text(trajectory.steps[idx]) for idx in selected_steps]
    vectors = request_embeddings(args.base_url, args.model, texts, api_key)

    normal_vectors = vectors[: len(normal_steps)]
    pre_vectors = vectors[len(normal_steps) :]
    hash_vectors = [_embed_text(text) for text in texts]
    hash_normal = hash_vectors[: len(normal_steps)]
    hash_pre = hash_vectors[len(normal_steps) :]
    row = {
        "case": Path(args.trajectory).stem.replace("_trajectory", ""),
        "embedding_model": args.model,
        "sample_steps": len(selected_steps),
        "normal_steps": " ".join(str(idx) for idx in normal_steps),
        "pre_steps": " ".join(str(idx) for idx in pre_steps),
        "embedding_normal_effective_rank": _effective_rank(normal_vectors),
        "embedding_pre_effective_rank": _effective_rank(pre_vectors),
        "embedding_effective_rank_delta": float(_effective_rank(normal_vectors)) - float(_effective_rank(pre_vectors)),
        "embedding_normal_to_pre_cosine_distance": _cosine_distance(_centroid(normal_vectors), _centroid(pre_vectors)),
        "hash_normal_effective_rank": _effective_rank(hash_normal),
        "hash_pre_effective_rank": _effective_rank(hash_pre),
        "hash_effective_rank_delta": float(_effective_rank(hash_normal)) - float(_effective_rank(hash_pre)),
        "input_sha256": hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest(),
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "embedding_provider_probe.csv"
    md_path = output_dir / "embedding_provider_probe.md"
    write_csv(csv_path, [row])
    write_markdown(md_path, [row])
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    return 0


def parse_indices(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


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
        experiment_name=str(data.get("experiment_name", path.stem)),
        seed=int(data.get("seed", 0)),
        steps=steps,
        metadata=data.get("metadata", {}),
    )


def request_embeddings(base_url: str, model: str, texts: list[str], api_key: str) -> list[list[float]]:
    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        base_url,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Embedding provider HTTP error {exc.code}; response body omitted.") from exc
    embeddings = [item["embedding"] for item in sorted(payload["data"], key=lambda item: item["index"])]
    return [normalize([float(value) for value in vector]) for vector in embeddings]


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


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
