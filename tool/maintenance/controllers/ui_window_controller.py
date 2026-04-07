"""UI window controller compatibility facade.

Implementation is split under tool.maintenance.controllers.ui_window.* modules.
"""

from .ui_window.text_ops import (
    copy_to_clipboard_impl,
    insert_colored_text_impl,
    show_text_window_impl,
)
from .ui_window.result_ops import show_result_window_impl

__all__ = [
    "show_text_window_impl",
    "insert_colored_text_impl",
    "copy_to_clipboard_impl",
    "show_result_window_impl",
]

