"""Runtime controller compatibility facade.

Implementation is split under tool.maintenance.controllers.runtime.* modules.
"""

from .runtime.connection_ops import (
    test_connection_impl,
    update_ssh_executor_impl,
)
from .runtime.command_ops import execute_ssh_command_impl
from .runtime.log_window_ops import open_log_window_impl

__all__ = [
    "test_connection_impl",
    "update_ssh_executor_impl",
    "execute_ssh_command_impl",
    "open_log_window_impl",
]

