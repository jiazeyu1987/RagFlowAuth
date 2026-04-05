"""Release helper compatibility facade.

Implementation is split across event_ops/sync_ops/onlyoffice_deploy_ops.
"""

from .event_ops import (
    extract_version_from_release_log,
    format_version_info,
    guard_ragflow_base_url,
    record_release_event,
    release_generate_version,
    release_version_arg,
)
from .sync_ops import sync_local_backup_to_test
from .onlyoffice_deploy_ops import deploy_onlyoffice_to_server

__all__ = [
    "extract_version_from_release_log",
    "record_release_event",
    "release_generate_version",
    "release_version_arg",
    "format_version_info",
    "guard_ragflow_base_url",
    "sync_local_backup_to_test",
    "deploy_onlyoffice_to_server",
]
