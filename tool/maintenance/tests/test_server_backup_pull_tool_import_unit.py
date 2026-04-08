import unittest


class TestServerBackupPullToolImportUnit(unittest.TestCase):
    def test_imports(self) -> None:
        from tool.maintenance.server_backup_pull_tool import ServerBackupPullTool, main

        self.assertTrue(callable(ServerBackupPullTool))
        self.assertTrue(callable(main))
