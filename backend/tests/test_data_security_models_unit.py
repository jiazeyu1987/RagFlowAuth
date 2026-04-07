import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.data_security.models import DataSecuritySettings


def _settings(**overrides) -> DataSecuritySettings:
    values = {
        "enabled": False,
        "interval_minutes": 1440,
        "target_mode": "share",
        "target_ip": "",
        "target_share_name": "",
        "target_subdir": "",
        "target_local_dir": "",
        "ragflow_compose_path": "",
        "ragflow_project_name": "",
        "ragflow_stop_services": False,
        "auth_db_path": "data/auth.db",
        "updated_at_ms": 0,
        "last_run_at_ms": None,
        "upload_after_backup": False,
        "upload_host": None,
        "upload_username": None,
        "upload_target_path": None,
        "full_backup_enabled": False,
        "full_backup_include_images": True,
        "backup_retention_max": 30,
        "incremental_schedule": None,
        "full_backup_schedule": None,
        "last_incremental_backup_time_ms": None,
        "last_full_backup_time_ms": None,
        "replica_enabled": True,
        "replica_target_path": None,
        "replica_subdir_format": "flat",
        "standard_replica_mount_active": False,
    }
    values.update(overrides)
    return DataSecuritySettings(**values)


class TestDataSecurityModelsUnit(unittest.TestCase):
    def test_local_backup_target_path_uses_repo_data_backups_on_host_runtime(self) -> None:
        expected = str((Path(r"D:\ProjectPackage\RagflowAuth\data") / "backups").resolve())
        with patch("backend.services.data_security.models._running_inside_container", return_value=False), patch(
            "backend.services.data_security.models.managed_data_root",
            return_value=Path(r"D:\ProjectPackage\RagflowAuth\data"),
        ):
            settings = _settings()
            actual = settings.local_backup_target_path()

        self.assertEqual(actual, expected)

    def test_local_backup_target_path_keeps_container_path_inside_container_runtime(self) -> None:
        with patch("backend.services.data_security.models._running_inside_container", return_value=True):
            settings = _settings()
            actual = settings.local_backup_target_path()

        self.assertEqual(str(actual).replace("\\", "/"), "/app/data/backups")

    def test_windows_target_path_uses_standard_mount_when_active(self) -> None:
        settings = _settings(
            replica_target_path="/mnt/replica/RagflowAuth",
            target_ip="10.0.0.8",
            target_share_name="BackupShare",
            target_subdir="RagflowAuth",
            standard_replica_mount_active=True,
        )

        self.assertEqual(settings.windows_target_path(), "/mnt/replica/RagflowAuth")

    def test_windows_target_path_falls_back_to_unc_when_standard_mount_inactive(self) -> None:
        settings = _settings(
            replica_target_path="/mnt/replica/RagflowAuth",
            target_ip="10.0.0.8",
            target_share_name="BackupShare",
            target_subdir="RagflowAuth",
            standard_replica_mount_active=False,
        )

        self.assertEqual(settings.windows_target_path(), r"\\10.0.0.8\BackupShare\RagflowAuth")

    def test_windows_target_path_ignores_invalid_local_mount_path_when_inactive(self) -> None:
        settings = _settings(
            target_mode="local",
            target_local_dir="/mnt/replica/RagflowAuth",
            standard_replica_mount_active=False,
        )

        self.assertIsNone(settings.windows_target_path())

    def test_windows_target_path_keeps_explicit_unc_replica_path(self) -> None:
        settings = _settings(
            replica_target_path=r"\\10.0.0.9\Backups\RagflowAuth",
            target_ip="10.0.0.8",
            target_share_name="Ignored",
            target_subdir="Ignored",
            standard_replica_mount_active=False,
        )

        self.assertEqual(settings.windows_target_path(), r"\\10.0.0.9\Backups\RagflowAuth")


if __name__ == "__main__":
    unittest.main()
