"""Run the released-results consistency checks wherever the data is present.

Some inputs live under ``outputs/``, which is not in version control, so on a
clean checkout a subset of checks skip. The gate reports those by name; this
test only asserts that nothing which *can* run disagrees.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.mark.parametrize("study", ["A", "B", "C"])
def test_released_results_match_their_sources(study: str) -> None:
    import verify_released_results

    assert verify_released_results.main(["--study", study]) == 0, (
        f"Study {study} has a released value that no longer matches its source data. "
        "Either the analysis moved and the artifact must be regenerated, or the "
        "artifact moved and the value was never right."
    )
