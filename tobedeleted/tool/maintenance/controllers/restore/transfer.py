"""Restore transfer compatibility facade.

Implementation is moved to transfer_pipeline.py.
"""

from .transfer_pipeline import execute_restore_impl

__all__ = ["execute_restore_impl"]
