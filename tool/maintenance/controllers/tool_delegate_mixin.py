from __future__ import annotations

from tool.maintenance.controllers.tool_delegate_backup_mixin import RagflowAuthToolBackupDelegateMixin
from tool.maintenance.controllers.tool_delegate_release_mixin import RagflowAuthToolReleaseDelegateMixin
from tool.maintenance.controllers.tool_delegate_restore_mixin import RagflowAuthToolRestoreDelegateMixin
from tool.maintenance.controllers.tool_delegate_runtime_mixin import RagflowAuthToolRuntimeDelegateMixin
from tool.maintenance.controllers.tool_delegate_windows_share_mixin import RagflowAuthToolWindowsShareDelegateMixin


class RagflowAuthToolDelegateMixin(
    RagflowAuthToolReleaseDelegateMixin,
    RagflowAuthToolBackupDelegateMixin,
    RagflowAuthToolWindowsShareDelegateMixin,
    RagflowAuthToolRuntimeDelegateMixin,
    RagflowAuthToolRestoreDelegateMixin,
):
    """Compatibility aggregation mixin for RagflowAuthTool delegated methods."""

