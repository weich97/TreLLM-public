from __future__ import annotations

from pathlib import Path

from tradearena.cli import main


def test_new_plugin_scaffold_creates_risk_plugin(tmp_path: Path) -> None:
    output = tmp_path / "plugins"

    result = main(["new-plugin", "--type", "risk", "--name", "max-drawdown-guard", "--output", str(output)])

    assert result == 0
    plugin_dir = output / "max_drawdown_guard"
    module_path = plugin_dir / "max_drawdown_guard.py"
    test_path = plugin_dir / "test_max_drawdown_guard.py"
    readme_path = plugin_dir / "README.md"

    assert module_path.exists()
    assert test_path.exists()
    assert readme_path.exists()
    assert "class MaxDrawdownGuard" in module_path.read_text(encoding="utf-8")
    assert "MaxPositionRiskManager" in module_path.read_text(encoding="utf-8")
    assert "tradearena new-plugin" in readme_path.read_text(encoding="utf-8")


def test_new_plugin_scaffold_rejects_existing_directory(tmp_path: Path) -> None:
    output = tmp_path / "plugins"
    assert main(["new-plugin", "--type", "evaluator", "--name", "audit score", "--output", str(output)]) == 0

    try:
        main(["new-plugin", "--type", "evaluator", "--name", "audit score", "--output", str(output)])
    except SystemExit as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Expected duplicate scaffold creation to fail")
