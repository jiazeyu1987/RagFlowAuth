"""Restore controller compatibility facade.

Business logic is split across tool.maintenance.controllers.restore.* modules.
"""

from .restore.ui_bridge import (
    append_restore_log,
    append_restore_log_impl,
    on_restore_backup_selected,
    on_restore_backup_selected_impl,
    refresh_local_restore_list,
    refresh_local_restore_list_impl,
    select_restore_folder,
    select_restore_folder_impl,
    stop_restore_progress,
    stop_restore_progress_impl,
    update_restore_status,
    update_restore_status_impl,
)
from .restore.precheck import (
    validate_restore_folder,
    validate_restore_folder_impl,
)
from .restore.apply import (
    restore_data,
    restore_data_impl,
)
from .restore.transfer import execute_restore_impl
from .restore.postcheck import run_restore_postcheck

__all__ = [
    "append_restore_log",
    "append_restore_log_impl",
    "refresh_local_restore_list",
    "refresh_local_restore_list_impl",
    "on_restore_backup_selected",
    "on_restore_backup_selected_impl",
    "select_restore_folder",
    "select_restore_folder_impl",
    "update_restore_status",
    "update_restore_status_impl",
    "stop_restore_progress",
    "stop_restore_progress_impl",
    "validate_restore_folder",
    "validate_restore_folder_impl",
    "restore_data",
    "restore_data_impl",
    "execute_restore_impl",
    "run_restore_postcheck",
]
