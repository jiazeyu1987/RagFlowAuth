import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestServerBackupPullUnit(unittest.TestCase):
    def test_list_filters_formats_and_sorts(self) -> None:
        from tool.maintenance.features import server_backup_pull

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            self.assertIn("/opt/ragflowauth/backups", command)
            return True, "\n".join(
                [
                    "full_backup_pack_20260407_220101_001",
                    "notes",
                    "migration_pack_20260408_101343_362",
                ]
            )

        with patch.object(server_backup_pull.shutil, "which", return_value="C:\\Windows\\System32\\OpenSSH\\ssh.exe"):
            with patch.object(server_backup_pull.SSHExecutor, "execute", new=_fake_execute):
                result = server_backup_pull.list_server_backup_dirs(server_ip="172.30.30.58", server_user="root")

        self.assertTrue(result.ok)
        self.assertEqual(
            [item.name for item in result.backups],
            [
                "migration_pack_20260408_101343_362",
                "full_backup_pack_20260407_220101_001",
            ],
        )
        self.assertEqual(result.backups[0].display_name, "2026-04-08 10:13:43 (增量备份)")
        self.assertEqual(result.backups[1].display_name, "2026-04-07 22:01:01 (全量备份)")

    def test_list_reports_no_backups_when_no_valid_names(self) -> None:
        from tool.maintenance.features import server_backup_pull

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            return True, "tmp\nlogs\n"

        with patch.object(server_backup_pull.shutil, "which", return_value="C:\\Windows\\System32\\OpenSSH\\ssh.exe"):
            with patch.object(server_backup_pull.SSHExecutor, "execute", new=_fake_execute):
                result = server_backup_pull.list_server_backup_dirs(server_ip="172.30.30.58", server_user="root")

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "no_backups_found")

    def test_download_rejects_invalid_name(self) -> None:
        from tool.maintenance.features.server_backup_pull import download_server_backup_dir

        result = download_server_backup_dir(
            server_ip="172.30.30.58",
            server_user="root",
            name="../bad",
            destination_root=Path(tempfile.gettempdir()),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "invalid_name")

    def test_download_fails_when_scp_missing(self) -> None:
        from tool.maintenance.features.server_backup_pull import download_server_backup_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "tool.maintenance.features.server_backup_pull.shutil.which",
                side_effect=lambda name: "C:\\Windows\\System32\\OpenSSH\\ssh.exe" if name == "ssh" else None,
            ):
                result = download_server_backup_dir(
                    server_ip="172.30.30.58",
                    server_user="root",
                    name="migration_pack_20260408_101343_362",
                    destination_root=tmpdir,
                )

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "scp_not_found")

    def test_download_fails_when_destination_exists(self) -> None:
        from tool.maintenance.features.server_backup_pull import download_server_backup_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "migration_pack_20260408_101343_362"
            target.mkdir()

            with patch(
                "tool.maintenance.features.server_backup_pull.shutil.which",
                return_value="C:\\Windows\\System32\\OpenSSH\\ssh.exe",
            ):
                result = download_server_backup_dir(
                    server_ip="172.30.30.58",
                    server_user="root",
                    name=target.name,
                    destination_root=tmpdir,
                )

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "destination_exists")

    def test_download_uses_scp_and_moves_backup_to_destination(self) -> None:
        from tool.maintenance.features import server_backup_pull

        with tempfile.TemporaryDirectory() as tmpdir:
            local_root = Path(tmpdir) / "local"
            temp_root = Path(tmpdir) / "scp-temp"
            temp_root.mkdir()
            local_root.mkdir()

            def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
                self.assertIn("test -d 'migration_pack_20260408_101343_362'", command)
                self.assertIn("printf 'READY\\n'", command)
                return True, "READY"

            def _fake_scp(argv, capture_output, text, encoding, errors, check):  # noqa: ARG001
                downloaded_dir = temp_root / "migration_pack_20260408_101343_362"
                downloaded_dir.mkdir(exist_ok=True)
                (downloaded_dir / "auth.db").write_text("sqlite", encoding="utf-8")
                self.assertEqual(argv[0], "scp")
                self.assertIn("root@172.30.30.58:/opt/ragflowauth/backups/migration_pack_20260408_101343_362", argv)
                return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

            with patch.object(server_backup_pull.shutil, "which", return_value="C:\\Windows\\System32\\OpenSSH\\ssh.exe"):
                with patch.object(server_backup_pull, "make_temp_dir", return_value=temp_root):
                    with patch.object(server_backup_pull.SSHExecutor, "execute", new=_fake_execute):
                        result = server_backup_pull.download_server_backup_dir(
                            server_ip="172.30.30.58",
                            server_user="root",
                            name="migration_pack_20260408_101343_362",
                            destination_root=local_root,
                            scp_runner=_fake_scp,
                        )

            self.assertTrue(result.ok)
            self.assertEqual(result.message, "downloaded")
            self.assertTrue((local_root / "migration_pack_20260408_101343_362").is_dir())
            self.assertTrue((local_root / "migration_pack_20260408_101343_362" / "auth.db").is_file())
