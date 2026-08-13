import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_five_minute_notebook_contains_benchmark_and_hash_cells():
    notebook = json.loads((ROOT / "notebooks" / "tradearena_5min_colab.ipynb").read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]

    assert any(
        "tradearena --benchmark tradearena-core --periods 30 --output outputs/examples/notebook_trajectory.json"
        in source
        for source in code_cells
    )
    assert any("tradearena hash-run outputs/examples/notebook_trajectory.json" in source for source in code_cells)


def test_getting_started_names_colab_and_binder_caveats():
    text = (ROOT / "docs" / "getting_started.md").read_text(encoding="utf-8")

    assert "Binder can take several minutes" in text
    assert "Colab runtime reset" in text
    assert "outputs/examples/notebook_trajectory.json" in text
