"""Windows share diagnostics compatibility facade.

Implementation is split under tool.maintenance.controllers.windows_share_diag.* modules.
"""

from .windows_share_diag.info_ops import get_mount_diagnostic_info_impl
from .windows_share_diag.precheck_ops import pre_mount_diagnostic_impl

__all__ = [
    "pre_mount_diagnostic_impl",
    "get_mount_diagnostic_info_impl",
]
