"""Windows share controller compatibility facade.

Implementation is split under tool.maintenance.controllers.windows_share.* modules.
"""

from .windows_share.mount_ops import (
    mount_windows_share,
    mount_windows_share_impl,
)
from .windows_share.unmount_ops import (
    unmount_windows_share,
    unmount_windows_share_impl,
)
from .windows_share.status_ops import (
    check_mount_status,
    check_mount_status_impl,
)

__all__ = [
    "mount_windows_share",
    "mount_windows_share_impl",
    "unmount_windows_share",
    "unmount_windows_share_impl",
    "check_mount_status",
    "check_mount_status_impl",
]

