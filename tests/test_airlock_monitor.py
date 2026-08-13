"""Tests for the Airlock LLM-monitor triage eval set (E6)."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradearena.evaluation.airlock_monitor import (
    TIERS,
    build_monitor_items,
    build_prompt,
    monitor_view,
    parse_monitor_findings,
    score_monitor,
)


def _items():
    return build_monitor_items(Path(tempfile.mkdtemp(prefix="airlock_mon_test_")))


def test_eval_set_has_all_tiers_and_is_labeled():
    items = _items()
    tiers = {i.tier for i in items}
    assert tiers == set(TIERS)
    # clean items are not faulted; the other tiers are.
    for i in items:
        assert i.is_faulted == (i.tier != "clean")
        if i.is_faulted:
            assert i.faulted_artifact and i.faulted_field


def test_view_omits_schema_constant_boilerplate():
    item = next(i for i in _items() if i.tier == "clean")
    view = monitor_view(item)
    assert "account_mode" not in view["approval"]  # schema-const, would be a phantom
    assert set(view) == {"capability", "handoff", "approval", "response", "runbook"}


def test_parse_monitor_findings_shapes():
    # bare array
    assert len(parse_monitor_findings('[{"artifact":"approval","field":"x","issue":"y"}]')) == 1
    # wrapper object
    assert len(parse_monitor_findings('{"artifacts":[{"artifact":"a","field":"f"}]}')) == 1
    # empty / non-json / prose
    assert parse_monitor_findings("[]") == []
    assert parse_monitor_findings("no issues found") == []
    # entries without artifact/field are dropped
    assert parse_monitor_findings('[{"note":"hi"}]') == []


def test_scoring_rewards_correct_action():
    items = _items()
    faulted = next(i for i in items if i.tier == "semantic")
    clean = next(i for i in items if i.tier == "clean")
    hit = [{"artifact": faulted.faulted_artifact, "field": faulted.faulted_field, "issue": "x"}]
    assert score_monitor(hit, faulted)["flagged"] is True
    assert score_monitor(hit, faulted)["field_hit"] is True
    assert score_monitor([], clean)["flagged"] is False  # silence on clean is correct


def test_prompt_is_wellformed_and_hides_boilerplate():
    import json
    item = next(i for i in _items() if i.tier == "semantic")
    prompt = build_prompt(item)
    assert "JSON array" in prompt
    # the approval's schema-const account_mode is omitted; the handoff's real
    # account_mode content stays.
    view = monitor_view(item)
    assert "account_mode" not in json.dumps(view["approval"])
    assert "account_mode" in json.dumps(view["handoff"])
