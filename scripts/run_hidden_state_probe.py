from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tradearena.core.trajectory import StepRecord, Trajectory
from tradearena.experiments.paper import _lsa_doc_embeddings, _mean, _plan_text, _rolling_failure_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a white-box last-hidden-state collapse probe on recorded LLM trading trajectories.")
    parser.add_argument(
        "--trajectory",
        nargs="+",
        default=[
            "outputs/tradearena_paper/raw/llm_matrix_gpt_5_5_risk_aware_trajectory.json",
            "outputs/tradearena_paper/raw/llm_matrix_gemini_3_1_pro_risk_aware_trajectory.json",
        ],
    )
    parser.add_argument("--model", default=".tmp/qwen2.5-0.5b", help="Local Hugging Face causal-LM model directory or repo id.")
    parser.add_argument("--model-label", default="Qwen2.5-0.5B-Instruct")
    parser.add_argument("--output-dir", default="outputs/tradearena_paper/tables")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument(
        "--hf-endpoint",
        default=os.environ.get("HF_ENDPOINT", ""),
        help="Optional Hugging Face endpoint. Leave empty when using a local model directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.hf_endpoint:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint
    trajectories = [load_trajectory(Path(path)) for path in args.trajectory]
    documents: list[str] = []
    spans: list[tuple[Trajectory, int, int]] = []
    for trajectory in trajectories:
        start = len(documents)
        documents.extend(decision_text(step) for step in trajectory.steps)
        spans.append((trajectory, start, len(documents)))

    hidden_vectors = hidden_state_embeddings(args.model, documents, args.batch_size, args.max_length)
    lsa_vectors = _lsa_doc_embeddings(documents, dims=32)
    if not lsa_vectors:
        raise RuntimeError("LSA embeddings could not be computed for the hidden-state probe documents.")

    rows: list[dict[str, Any]] = []
    for trajectory, start, end in spans:
        hidden_events = _rolling_failure_events(trajectory.experiment_name, trajectory, hidden_vectors[start:end])
        lsa_events = _rolling_failure_events(trajectory.experiment_name, trajectory, lsa_vectors[start:end])
        hidden_by_anchor = {int(row["anchor"]): row for row in hidden_events}
        lsa_by_anchor = {int(row["anchor"]): row for row in lsa_events}
        shared = sorted(set(hidden_by_anchor) & set(lsa_by_anchor))
        hidden_rank = [float(hidden_by_anchor[anchor]["effective_rank_delta"]) for anchor in shared if hidden_by_anchor[anchor]["effective_rank_delta"] != ""]
        lsa_rank = [float(lsa_by_anchor[anchor]["effective_rank_delta"]) for anchor in shared if lsa_by_anchor[anchor]["effective_rank_delta"] != ""]
        rows.append(
            summary_row(
                trajectory.experiment_name,
                args.model_label,
                "last_hidden_mean",
                len(trajectory.steps),
                hidden_events,
                shared,
                hidden_rank,
                lsa_rank,
            )
        )
        rows.append(
            summary_row(
                trajectory.experiment_name,
                "LSA32 decision text",
                "lsa32_decision_text",
                len(trajectory.steps),
                lsa_events,
                shared,
                lsa_rank,
                hidden_rank,
            )
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "whitebox_hidden_state_probe.csv", rows)
    write_markdown(output_dir / "whitebox_hidden_state_probe.md", rows)
    for row in rows:
        print(row)
    return 0


def decision_text(step: StepRecord) -> str:
    targets = []
    for decision in step.decisions:
        symbol = str(decision.get("symbol", ""))
        target = decision.get("target_weight", decision.get("target_percent", decision.get("weight", "")))
        if target != "":
            targets.append(f"{symbol}:{target}")
    target_text = " ".join(targets)
    return f"{_plan_text(step)} TARGET_WEIGHTS {target_text}".strip()


def hidden_state_embeddings(model_name: str, documents: list[str], batch_size: int, max_length: int) -> list[list[float]]:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Install torch and transformers to run the white-box hidden-state probe.") from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    try:
        model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, dtype=torch.float32)
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, torch_dtype=torch.float32)
    model.to(device)
    model.eval()

    vectors: list[list[float]] = []
    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        encoded = tokenizer(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            outputs = model(**encoded, output_hidden_states=True, use_cache=False)
        hidden = outputs.hidden_states[-1]
        mask = encoded["attention_mask"].unsqueeze(-1).to(hidden.dtype)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)
        pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        vectors.extend([[float(value) for value in row.detach().cpu().tolist()] for row in pooled])
    return vectors


def summary_row(
    case_name: str,
    model: str,
    representation: str,
    steps: int,
    events: list[dict[str, Any]],
    shared_anchors: list[int],
    primary_rank: list[float],
    paired_rank: list[float],
) -> dict[str, Any]:
    contraction_rate = _mean(
        [1.0 if float(row["effective_rank_delta"]) > 0.0 else 0.0 for row in events if row["effective_rank_delta"] != ""]
    )
    sign_agreement = _mean(
        [1.0 if (left > 0.0) == (right > 0.0) else 0.0 for left, right in zip(primary_rank, paired_rank, strict=False)]
    )
    return {
        "case": case_name,
        "model": model,
        "representation": representation,
        "steps": steps,
        "anchors": len(events),
        "shared_anchors": len(shared_anchors),
        "mean_pre_shift": _mean([float(row["pre_shift"]) for row in events]),
        "mean_effective_rank_delta": _mean(
            [float(row["effective_rank_delta"]) for row in events if row["effective_rank_delta"] != ""]
        ),
        "rank_contraction_rate": contraction_rate,
        "mean_early_warning_ba": _mean([float(row["early_warning_ba"]) for row in events]),
        "rank_delta_sign_agreement": sign_agreement,
        "rank_delta_pearson": pearson(primary_rank, paired_rank),
    }


def pearson(left: list[float], right: list[float]) -> float | str:
    if len(left) != len(right) or len(left) < 2:
        return ""
    left_mean = _mean(left)
    right_mean = _mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    denom = (left_var * right_var) ** 0.5
    return numerator / denom if denom else ""


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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
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
