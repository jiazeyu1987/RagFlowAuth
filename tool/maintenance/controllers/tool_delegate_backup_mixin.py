from __future__ import annotations


class RagflowAuthToolBackupDelegateMixin:
    def create_logs_tab(self):
        """日志查看页签 UI（拆分到独立模块）。"""
        from tool.maintenance.ui.logs_tab import build_logs_tab

        build_logs_tab(self)

    def create_nas_tab(self):
        """NAS 云盘页签 UI（仅管理员可见）。"""
        from tool.maintenance.ui.nas_tab import build_nas_tab

        build_nas_tab(self)

    def _is_admin_tab_user(self) -> bool:
        username = (self.user_var.get() if hasattr(self, "user_var") else self.config.user or "").strip().lower()
        return username in {"root", "admin"}

    def refresh_admin_tabs(self) -> None:
        from tool.maintenance.controllers.environment_controller import refresh_admin_tabs_impl

        return refresh_admin_tabs_impl(self)

    def create_backup_files_tab(self):
        """备份文件页签 UI（拆分到独立模块）。"""
        from tool.maintenance.ui.backup_files_tab import build_backup_files_tab

        build_backup_files_tab(self)

    def create_replica_backups_tab(self):
        """共享备份页签：查看/删除两台服务器本地 /opt/ragflowauth/data/backups 下的备份目录（测试/正式）。"""
        from tool.maintenance.ui.replica_backups_tab import build_replica_backups_tab

        build_replica_backups_tab(self)

    def refresh_backup_files(self, *args, **kwargs):
        from tool.maintenance.controllers.backup_controller import refresh_backup_files as controller_refresh_backup_files

        return controller_refresh_backup_files(self, *args, **kwargs)

    def _refresh_backup_files_impl(self):
        from tool.maintenance.controllers.backup_controller import refresh_backup_files_impl as controller_refresh_backup_files_impl

        return controller_refresh_backup_files_impl(self)

    def refresh_replica_backups(self, *args, **kwargs):
        from tool.maintenance.controllers.backup_controller import refresh_replica_backups as controller_refresh_replica_backups

        return controller_refresh_replica_backups(self, *args, **kwargs)

    def _refresh_replica_backups_impl(self):
        from tool.maintenance.controllers.backup_controller import refresh_replica_backups_impl as controller_refresh_replica_backups_impl

        return controller_refresh_replica_backups_impl(self)

    def delete_selected_replica_backup(self, *args, **kwargs):
        from tool.maintenance.controllers.backup_controller import delete_selected_replica_backup as controller_delete_selected_replica_backup

        return controller_delete_selected_replica_backup(self, *args, **kwargs)

    def _delete_selected_replica_backup_impl(self, which: str):
        from tool.maintenance.controllers.backup_controller import delete_selected_replica_backup_impl as controller_delete_selected_replica_backup_impl

        return controller_delete_selected_replica_backup_impl(self, which)

    def _get_backup_files(self, directory):
        from tool.maintenance.controllers.backup_view_controller import get_backup_files_impl

        return get_backup_files_impl(self, directory)

    def _update_file_trees(self, left_files, right_files):
        from tool.maintenance.controllers.backup_view_controller import update_file_trees_impl

        return update_file_trees_impl(self, left_files, right_files)

    def _get_file_size(self, path):
        from tool.maintenance.controllers.backup_view_controller import get_file_size_impl

        return get_file_size_impl(self, path)

    def show_backup_file_details(self, side):
        from tool.maintenance.controllers.backup_view_controller import show_backup_file_details_impl

        return show_backup_file_details_impl(self, side)

    def delete_selected_backup_files(self, *args, **kwargs):
        from tool.maintenance.controllers.backup_controller import delete_selected_backup_files as controller_delete_selected_backup_files

        return controller_delete_selected_backup_files(self, *args, **kwargs)

    def _delete_selected_backup_files_impl(self):
        from tool.maintenance.controllers.backup_controller import delete_selected_backup_files_impl as controller_delete_selected_backup_files_impl

        return controller_delete_selected_backup_files_impl(self)

    def _delete_complete(self, deleted, failed):
        from tool.maintenance.controllers.backup_view_controller import delete_complete_impl

        return delete_complete_impl(self, deleted, failed)

    def cleanup_old_backups(self, *args, **kwargs):
        from tool.maintenance.controllers.backup_controller import cleanup_old_backups as controller_cleanup_old_backups

        return controller_cleanup_old_backups(self, *args, **kwargs)

    def _cleanup_old_backups_impl(self):
        from tool.maintenance.controllers.backup_controller import cleanup_old_backups_impl as controller_cleanup_old_backups_impl

        return controller_cleanup_old_backups_impl(self)
