from __future__ import annotations


class RagflowAuthToolWindowsShareDelegateMixin:
    def mount_windows_share(self, *args, **kwargs):
        from tool.maintenance.controllers.windows_share_controller import mount_windows_share as controller_mount_windows_share

        return controller_mount_windows_share(self, *args, **kwargs)

    def _mount_windows_share_impl(self):
        from tool.maintenance.controllers.windows_share_controller import mount_windows_share_impl as controller_mount_windows_share_impl

        return controller_mount_windows_share_impl(self)
    

    def _pre_mount_diagnostic(self):
        from tool.maintenance.controllers.windows_share_diagnostics import pre_mount_diagnostic_impl

        return pre_mount_diagnostic_impl(self)

    def _get_mount_diagnostic_info(self):
        from tool.maintenance.controllers.windows_share_diagnostics import get_mount_diagnostic_info_impl

        return get_mount_diagnostic_info_impl(self)

    def unmount_windows_share(self, *args, **kwargs):
        from tool.maintenance.controllers.windows_share_controller import unmount_windows_share as controller_unmount_windows_share

        return controller_unmount_windows_share(self, *args, **kwargs)

    def _unmount_windows_share_impl(self):
        from tool.maintenance.controllers.windows_share_controller import unmount_windows_share_impl as controller_unmount_windows_share_impl

        return controller_unmount_windows_share_impl(self)
    

    def check_mount_status(self, *args, **kwargs):
        from tool.maintenance.controllers.windows_share_controller import check_mount_status as controller_check_mount_status

        return controller_check_mount_status(self, *args, **kwargs)

    def _check_mount_status_impl(self):
        from tool.maintenance.controllers.windows_share_controller import check_mount_status_impl as controller_check_mount_status_impl

        return controller_check_mount_status_impl(self)
