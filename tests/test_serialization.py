from tradearena.core.serialization import read_json, write_json


def test_write_json_creates_parent_directories(tmp_path):
    target = tmp_path / "outputs" / "examples" / "trajectory.json"

    write_json(target, {"ok": True})

    assert read_json(target) == {"ok": True}
