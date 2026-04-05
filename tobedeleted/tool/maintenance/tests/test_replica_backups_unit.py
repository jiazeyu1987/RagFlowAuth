import unittest
from unittest.mock import patch


class TestReplicaBackupsUnit(unittest.TestCase):
    def test_list_sorts_and_filters(self) -> None:
        from tool.maintenance.features import replica_backups

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            self.assertIn("/opt/ragflowauth/data/backups", command)
            return True, "migration_pack_20260202_010006_104\n_tmp/\nmigration_pack_20260127_150556\n"

        with patch.object(replica_backups.SSHExecutor, "execute", new=_fake_execute):
            res = replica_backups.list_replica_backup_dirs(server_ip="172.30.30.58", server_user="root")

        self.assertTrue(res.ok)
        self.assertEqual(res.names[0], "migration_pack_20260202_010006_104")
        self.assertIn("_tmp", res.names)

    def test_delete_rejects_bad_names(self) -> None:
        from tool.maintenance.features.replica_backups import delete_replica_backup_dir

        res = delete_replica_backup_dir(server_ip="172.30.30.58", server_user="root", name="../oops")
        self.assertFalse(res.ok)
        self.assertEqual(res.message, "invalid_name")

    def test_delete_uses_safe_rm(self) -> None:
        from tool.maintenance.features import replica_backups

        called = {"cmd": ""}

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            called["cmd"] = command
            return True, "DELETED\n"

        with patch.object(replica_backups.SSHExecutor, "execute", new=_fake_execute):
            res = replica_backups.delete_replica_backup_dir(
                server_ip="172.30.30.58",
                server_user="root",
                name="migration_pack_20260202_010006_104",
            )

        self.assertTrue(res.ok)
        self.assertIn("cd /opt/ragflowauth/data/backups", called["cmd"])
        self.assertIn("rm -rf", called["cmd"])
