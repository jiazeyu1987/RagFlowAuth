"""Release service compatibility facade.

Implementation is split across service_*_ops modules.
"""

from .service_history_ops import (
    copy_release_history_to_clipboard,
    copy_release_history_to_clipboard_impl,
)
from .service_restart_stop_ops import (
    restart_ragflow_and_ragflowauth,
    restart_ragflow_and_ragflowauth_impl,
    stop_ragflow_and_ragflowauth,
    stop_ragflow_and_ragflowauth_impl,
)
from .service_backup_job_ops import (
    kill_running_backup_job,
    kill_running_backup_job_impl,
)

__all__ = [
    "copy_release_history_to_clipboard",
    "copy_release_history_to_clipboard_impl",
    "restart_ragflow_and_ragflowauth",
    "restart_ragflow_and_ragflowauth_impl",
    "stop_ragflow_and_ragflowauth",
    "stop_ragflow_and_ragflowauth_impl",
    "kill_running_backup_job",
    "kill_running_backup_job_impl",
]
