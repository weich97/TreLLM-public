from __future__ import annotations

import importlib.util
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "freeze_forward_window.py"
    spec = importlib.util.spec_from_file_location("freeze_forward_window", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_freeze_then_verify_round_trip(tmp_path: Path):
    module = _load_module()
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=100)).isoformat()
    output = tmp_path / "commitment.json"

    assert (
        module.main(["--window-start", start, "--window-end", end, "--output", str(output)])
        == 0
    )
    commitment = json.loads(output.read_text(encoding="utf-8"))
    assert commitment["declaration_hash"].startswith("sha256:")
    assert commitment["window_start"] == start

    assert module.main(["--verify", str(output)]) == 0


def test_verify_detects_tampered_declaration(tmp_path: Path):
    module = _load_module()
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=100)).isoformat()
    output = tmp_path / "commitment.json"
    module.main(["--window-start", start, "--window-end", end, "--output", str(output)])

    commitment = json.loads(output.read_text(encoding="utf-8"))
    commitment["symbols"] = ["TAMPERED"]
    output.write_text(json.dumps(commitment), encoding="utf-8")

    assert module.main(["--verify", str(output)]) == 1


def test_freeze_rejects_non_future_window(tmp_path: Path):
    module = _load_module()
    today_utc = datetime.now(timezone.utc).date()
    start = today_utc.isoformat()
    end = (today_utc + timedelta(days=30)).isoformat()

    with pytest.raises(SystemExit):
        module.main(
            ["--window-start", start, "--window-end", end, "--output", str(tmp_path / "c.json")]
        )
