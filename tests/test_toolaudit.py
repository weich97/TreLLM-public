"""Tests for the tool-use second-domain oversight benchmark (audit study)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradearena.evaluation.defect_injection import score_findings
from tradearena.evaluation.toolaudit import (
    TOOL_DEFECT_DIFFICULTY,
    TOOL_DEFECT_KINDS,
    constraints_text,
    generate_trajectory,
    inject_over_limit_pair,
    inject_tool_defect,
    tool_compact_view,
)


def test_generate_is_deterministic_and_has_clipped_steps():
    a = generate_trajectory(1234)
    assert a == generate_trajectory(1234)
    assert len(a["steps"]) == 10
    # the approval gate legitimately clips some over-cap requests, with a record
    assert any(s["approval_meta"].get("clipped_from") for s in a["steps"])


def test_clean_trajectory_has_no_anomalies():
    traj = generate_trajectory(2001)
    for s in traj["steps"]:
        assert s["result"]["total"] == sum(s["result"]["line_items"])
        assert s["tool_version"] == traj["tool_version"]
        arg = next(iter(s["approved_args"]))
        cap = traj["caps"][s["tool"]]["cap"]
        assert s["approved_args"][arg] <= cap
        if s["requested_args"][arg] != s["approved_args"][arg]:
            assert "clipped_from" in s["approval_meta"]


def test_each_defect_injects_exactly_its_family():
    traj = generate_trajectory(1000)
    for kind in TOOL_DEFECT_KINDS:
        defective, gt = inject_tool_defect(traj, kind, seed=1000)
        assert gt["kind"] == kind
        assert gt["difficulty"] == TOOL_DEFECT_DIFFICULTY[kind]
        step = defective["steps"][gt["step_index"]]
        arg = next(iter(step["approved_args"]))
        cap = defective["caps"][step["tool"]]["cap"]
        if kind == "over_limit_call":
            assert step["approved_args"][arg] > cap
            assert "clipped_from" not in step["approval_meta"]
            # must not double as a silent edit: requested == approved
            assert step["requested_args"][arg] == step["approved_args"][arg]
        elif kind == "silent_arg_edit":
            assert step["requested_args"][arg] != step["approved_args"][arg]
            assert "clipped_from" not in step["approval_meta"]
        elif kind == "version_drift":
            assert step["tool_version"] != defective["tool_version"]
        else:  # tampered_result
            assert step["result"]["total"] != sum(step["result"]["line_items"])


def test_score_findings_matches_and_rejects():
    traj = generate_trajectory(1000)
    _, gt = inject_tool_defect(traj, "over_limit_call", seed=1000)
    hit = score_findings([{"step_index": gt["step_index"], "kind": gt["kind"]}], [gt])
    assert hit["recall"] == 1.0 and hit["true_positives"] == 1
    wrong_kind = score_findings([{"step_index": gt["step_index"], "kind": "version_drift"}], [gt])
    assert wrong_kind["recall"] == 0.0


def test_over_limit_pair_differs_only_in_requested():
    traj = generate_trajectory(4242)
    (clean, gt_c), (conf, gt_a) = inject_over_limit_pair(traj, seed=4242)
    assert gt_c["step_index"] == gt_a["step_index"]
    assert gt_c["detail"]["ambiguity"] == "clean"
    assert gt_a["detail"]["ambiguity"] == "confounded"
    i = gt_c["step_index"]
    sc, sa = clean["steps"][i], conf["steps"][i]
    arg = next(iter(sc["approved_args"]))
    cap = clean["caps"][sc["tool"]]["cap"]
    # both breach the cap identically, with no clip record
    assert sc["approved_args"][arg] == sa["approved_args"][arg] > cap
    assert "clipped_from" not in sc["approval_meta"] and "clipped_from" not in sa["approval_meta"]
    # clean: unambiguous; confounded: also a silent edit (requested under cap)
    assert sc["requested_args"][arg] == sc["approved_args"][arg]
    assert sa["requested_args"][arg] != sa["approved_args"][arg]
    assert sa["requested_args"][arg] <= cap
    # the two variants differ in requested_args of that one step and nowhere else
    sa_patched = {**sa, "requested_args": sc["requested_args"]}
    assert sa_patched == sc
    assert [s for j, s in enumerate(clean["steps"]) if j != i] == [
        s for j, s in enumerate(conf["steps"]) if j != i
    ]


def test_compact_view_and_constraints_are_wellformed():
    traj = generate_trajectory(3003)
    view = tool_compact_view(traj)
    assert len(view) == len(traj["steps"])
    assert all("tool" in v and "approved_args" in v and "result" in v for v in view)
    text = constraints_text(traj)
    assert "must not exceed" in text
    assert "sum of its result.line_items" in text
