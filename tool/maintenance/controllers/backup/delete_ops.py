"""Backup delete compatibility facade."""

from .delete_files_ops import (
    delete_selected_backup_files,
    delete_selected_backup_files_impl,
)
from .delete_replica_ops import (
    delete_selected_replica_backup,
    delete_selected_replica_backup_impl,
)

__all__ = [
    "delete_selected_replica_backup",
    "delete_selected_replica_backup_impl",
    "delete_selected_backup_files",
    "delete_selected_backup_files_impl",
]
