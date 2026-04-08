import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestLocalBackupRestoreUnit(unittest.TestCase):
    def test_build_volume_plan_maps_suffix_to_unique_local_volume(self) -> None:
        from tool.maintenance.features.local_backup_restore import build_local_volume_restore_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            volumes_dir = Path(tmpdir)
            (volumes_dir / "ragflow_compose_mysql_data.tar.gz").write_text("x", encoding="utf-8")
            (volumes_dir / "ragflow_compose_esdata01.tar.gz").write_text("x", encoding="utf-8")

            plan, error = build_local_volume_restore_plan(
                backup_volumes_dir=volumes_dir,
                local_volume_names=["docker_mysql_data", "docker_esdata01", "other_volume"],
            )

        self.assertIsNone(error)
        self.assertEqual(
            [(item.archive_name, item.local_volume_name) for item in plan],
            [
                ("ragflow_compose_esdata01.tar.gz", "docker_esdata01"),
                ("ragflow_compose_mysql_data.tar.gz", "docker_mysql_data"),
            ],
        )

    def test_build_volume_plan_fails_when_mapping_ambiguous(self) -> None:
        from tool.maintenance.features.local_backup_restore import build_local_volume_restore_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            volumes_dir = Path(tmpdir)
            (volumes_dir / "ragflow_compose_mysql_data.tar.gz").write_text("x", encoding="utf-8")

            plan, error = build_local_volume_restore_plan(
                backup_volumes_dir=volumes_dir,
                local_volume_names=["qa_mysql_data", "prod_mysql_data"],
            )

        self.assertEqual(plan, [])
        self.assertEqual(error, "volume_mapping_ambiguous:ragflow_compose_mysql_data:prod_mysql_data,qa_mysql_data")

    def test_build_volume_plan_prefers_docker_prefix_match_for_ragflow_backup(self) -> None:
        from tool.maintenance.features.local_backup_restore import build_local_volume_restore_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            volumes_dir = Path(tmpdir)
            (volumes_dir / "ragflow_compose_redis_data.tar.gz").write_text("x", encoding="utf-8")

            plan, error = build_local_volume_restore_plan(
                backup_volumes_dir=volumes_dir,
                local_volume_names=["docker_redis_data", "timerresearch_redis_data"],
            )

        self.assertIsNone(error)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].local_volume_name, "docker_redis_data")

    def test_restore_fails_when_local_backend_running(self) -> None:
        from tool.maintenance.features.local_backup_restore import restore_downloaded_backup_to_local

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backup"
            backup_dir.mkdir()
            (backup_dir / "auth.db").write_text("backup-db", encoding="utf-8")
            target = Path(tmpdir) / "auth.db"
            target.write_text("live-db", encoding="utf-8")

            result = restore_downloaded_backup_to_local(
                backup_dir=backup_dir,
                auth_db_target=target,
                port_probe=lambda host, port: True,  # noqa: ARG005
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "local_backend_running")

    def test_restore_fails_when_docker_missing_and_volume_archives_exist(self) -> None:
        from tool.maintenance.features.local_backup_restore import restore_downloaded_backup_to_local

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backup"
            volumes_dir = backup_dir / "volumes"
            volumes_dir.mkdir(parents=True)
            (backup_dir / "auth.db").write_text("backup-db", encoding="utf-8")
            (volumes_dir / "ragflow_compose_mysql_data.tar.gz").write_text("archive", encoding="utf-8")
            target = Path(tmpdir) / "auth.db"
            target.write_text("live-db", encoding="utf-8")

            with patch("tool.maintenance.features.local_backup_restore.shutil.which", return_value=None):
                result = restore_downloaded_backup_to_local(
                    backup_dir=backup_dir,
                    auth_db_target=target,
                    port_probe=lambda host, port: False,  # noqa: ARG005
                )

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "docker_not_found")

    def test_restore_copies_auth_db_and_restores_mapped_volumes(self) -> None:
        from tool.maintenance.features import local_backup_restore

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backup"
            volumes_dir = backup_dir / "volumes"
            backup_dir.mkdir()
            volumes_dir.mkdir()
            (backup_dir / "auth.db").write_text("backup-db", encoding="utf-8")
            (volumes_dir / "ragflow_compose_mysql_data.tar.gz").write_text("archive", encoding="utf-8")
            target = Path(tmpdir) / "auth.db"
            target.write_text("live-db", encoding="utf-8")

            calls: list[list[str]] = []

            def _fake_runner(argv, capture_output, text, encoding, errors, check):  # noqa: ARG001
                calls.append(list(argv))
                if argv[:3] == ["docker", "info", "--format"]:
                    return subprocess.CompletedProcess(argv, 0, stdout="27.0.0\n", stderr="")
                if argv[:3] == ["docker", "volume", "ls"]:
                    return subprocess.CompletedProcess(argv, 0, stdout="docker_mysql_data\n", stderr="")
                if argv[:3] == ["docker", "ps", "--filter"]:
                    return subprocess.CompletedProcess(argv, 0, stdout="abc123\tdocker-mysql-1\n", stderr="")
                if argv[:2] == ["docker", "stop"]:
                    return subprocess.CompletedProcess(argv, 0, stdout="docker-mysql-1\n", stderr="")
                if argv[:2] == ["docker", "run"]:
                    self.assertIn("docker_mysql_data:/volume_data", argv)
                    return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
                if argv[:2] == ["docker", "start"]:
                    return subprocess.CompletedProcess(argv, 0, stdout="docker-mysql-1\n", stderr="")
                raise AssertionError(f"Unexpected argv: {argv}")

            with patch.object(local_backup_restore.shutil, "which", return_value="C:\\Program Files\\Docker\\docker.exe"):
                result = local_backup_restore.restore_downloaded_backup_to_local(
                    backup_dir=backup_dir,
                    auth_db_target=target,
                    docker_runner=_fake_runner,
                    port_probe=lambda host, port: False,  # noqa: ARG005
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.message, "restored")
            self.assertEqual(target.read_text(encoding="utf-8"), "backup-db")
            self.assertEqual(result.restored_volume_names, ["docker_mysql_data"])
            self.assertEqual(result.stopped_container_names, ["docker-mysql-1"])
            self.assertTrue(any(cmd[:2] == ["docker", "stop"] for cmd in calls))
            self.assertTrue(any(cmd[:2] == ["docker", "start"] for cmd in calls))
