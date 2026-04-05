"""Restore UI bridge compatibility facade."""

from .ui_feedback_ops import (
    append_restore_log,
    append_restore_log_impl,
    stop_restore_progress,
    stop_restore_progress_impl,
    update_restore_status,
    update_restore_status_impl,
)
from .ui_list_ops import (
    refresh_local_restore_list,
    refresh_local_restore_list_impl,
    select_restore_folder,
    select_restore_folder_impl,
)
from .ui_selection_ops import (
    on_restore_backup_selected,
    on_restore_backup_selected_impl,
)

__all__ = [
    "select_restore_folder",
    "select_restore_folder_impl",
    "refresh_local_restore_list",
    "refresh_local_restore_list_impl",
    "on_restore_backup_selected",
    "on_restore_backup_selected_impl",
    "append_restore_log",
    "append_restore_log_impl",
    "update_restore_status",
    "update_restore_status_impl",
    "stop_restore_progress",
    "stop_restore_progress_impl",
]
