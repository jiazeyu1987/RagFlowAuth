import unittest


class TestUIBackupRestoreTabsImportUnit(unittest.TestCase):
    def test_imports(self):
        from tool.maintenance.ui.restore_tab import build_restore_tab
        from tool.maintenance.ui.replica_backups_tab import build_replica_backups_tab
        from tool.maintenance.ui.smoke_tab import build_smoke_tab
        from tool.maintenance.ui.tools_tab import build_tools_tab
        from tool.maintenance.ui.web_links_tab import build_web_links_tab
        from tool.maintenance.ui.backup_files_tab import build_backup_files_tab
        from tool.maintenance.ui.logs_tab import build_logs_tab

        self.assertTrue(callable(build_restore_tab))
        self.assertTrue(callable(build_replica_backups_tab))
        self.assertTrue(callable(build_smoke_tab))
        self.assertTrue(callable(build_tools_tab))
        self.assertTrue(callable(build_web_links_tab))
        self.assertTrue(callable(build_backup_files_tab))
        self.assertTrue(callable(build_logs_tab))
