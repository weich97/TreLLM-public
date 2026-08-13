from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deterministic_baseline_quickstart_explains_external_evidence_tags():
    raw_text = (ROOT / "docs" / "deterministic_baseline_submission_quickstart.md").read_text(encoding="utf-8")
    text = " ".join(raw_text.split())

    assert "`external-submitted` only when the row comes from a non-maintainer" in text
    assert "`fully-auditable` only when the public manifest links enough artifacts" in text
    assert "Keep maintainer-generated refreshes separate from external evidence" in text


def test_claim_boundary_quickstart_matches_external_review_acceptance_fields():
    raw_text = (ROOT / "docs" / "claim_boundary_review_quickstart.md").read_text(encoding="utf-8")
    text = " ".join(raw_text.split())

    assert "Current supporting evidence:" in raw_text
    assert "Recommended action: weaken, strengthen, or leave unchanged" in text
    assert "Runnable verification command or artifact path:" in raw_text
