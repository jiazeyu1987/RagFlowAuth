"""Restore transfer phases compatibility facade."""

from .transfer_phase_1_5_ops import run_restore_phases_1_to_5
from .transfer_phase_6_7_ops import run_restore_phases_6_and_7

__all__ = [
    "run_restore_phases_1_to_5",
    "run_restore_phases_6_and_7",
]
