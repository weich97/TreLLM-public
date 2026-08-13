"""Compatibility re-exports for execution simulators.

Prefer importing new code from `tradearena.execution`. This module remains so
existing scripts and notebooks do not break when the execution package is split
into simple, stress, quote-replay, fill-replay, and calibration surfaces.
"""

from tradearena.execution import (
    EXECUTION_CALIBRATED,
    EXECUTION_FILL_REPLAY,
    EXECUTION_QUOTE_REPLAY,
    EXECUTION_STRESS,
    CalibratedOrderSimulator,
    FillReplayOrderSimulator,
    QuoteReplayOrderSimulator,
    RealisticOrderSimulator,
    SimpleOrderSimulator,
    load_replay_fills_csv,
)

__all__ = [
    "EXECUTION_CALIBRATED",
    "EXECUTION_FILL_REPLAY",
    "EXECUTION_QUOTE_REPLAY",
    "EXECUTION_STRESS",
    "CalibratedOrderSimulator",
    "FillReplayOrderSimulator",
    "QuoteReplayOrderSimulator",
    "RealisticOrderSimulator",
    "SimpleOrderSimulator",
    "load_replay_fills_csv",
]
