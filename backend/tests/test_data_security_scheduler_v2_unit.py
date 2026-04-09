from __future__ import annotations

import unittest
from unittest import mock

from backend.services.data_security.models import DataSecuritySettings
from backend.services.data_security_scheduler_v2 import BackupSchedulerV2


def _build_settings(**overrides) -> DataSecuritySettings:
    values = {
        "enabled": True,
        "interval_minutes": 60,
        "target_mode": "local",
        "target_ip": None,
        "target_share_name": None,
        "target_subdir": None,
        "target_local_dir": "D:/backups",
        "ragflow_compose_path": None,
        "ragflow_project_name": None,
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
        "incremental_schedule": "0 * * * *",
        "full_backup_schedule": "0 1 * * *",
        "last_incremental_backup_time_ms": None,
        "last_full_backup_time_ms": None,
        "replica_enabled": False,
        "replica_target_path": None,
        "replica_subdir_format": "flat",
    }
    values.update(overrides)
    return DataSecuritySettings(**values)


class TestDataSecuritySchedulerV2Unit(unittest.TestCase):
    def test_should_run_incremental_backup_skips_same_window_after_restart(self):
        scheduler = BackupSchedulerV2(store=mock.Mock())
        scheduler._has_running_backup = mock.Mock(return_value=False)
        scheduler._latest_scheduled_time_ms = mock.Mock(return_value=1_700_000_000_000)

        should_run, reason, scheduled_ms = scheduler._should_run_incremental_backup(
            _build_settings(
                incremental_schedule="5 0 * * *",
                last_run_at_ms=1_700_000_000_000,
                last_incremental_backup_time_ms=1_600_000_000_000,
            )
        )

        self.assertFalse(should_run)
        self.assertEqual(scheduled_ms, 1_700_000_000_000)
        self.assertTrue(str(reason).strip())

    def test_should_run_full_backup_skips_when_disabled(self):
        scheduler = BackupSchedulerV2(store=mock.Mock())
        scheduler._has_running_backup = mock.Mock(return_value=False)

        should_run, reason, scheduled_ms = scheduler._should_run_full_backup(_build_settings(full_backup_enabled=False))

        self.assertFalse(should_run)
        self.assertIsNone(scheduled_ms)
        self.assertTrue(str(reason).strip())

    def test_should_run_full_backup_uses_dataclass_flag_when_enabled(self):
        scheduler = BackupSchedulerV2(store=mock.Mock())
        scheduler._has_running_backup = mock.Mock(return_value=False)
        scheduler._latest_scheduled_time_ms = mock.Mock(return_value=1_700_000_000_000)

        should_run, reason, scheduled_ms = scheduler._should_run_full_backup(
            _build_settings(
                full_backup_enabled=True,
                full_backup_schedule="0 1 * * *",
                last_full_backup_time_ms=1_600_000_000_000,
            )
        )

        self.assertTrue(should_run)
        self.assertEqual(scheduled_ms, 1_700_000_000_000)
        self.assertTrue(str(reason).strip())

    def test_should_run_full_backup_skips_same_window_after_restart(self):
        scheduler = BackupSchedulerV2(store=mock.Mock())
        scheduler._has_running_backup = mock.Mock(return_value=False)
        scheduler._latest_scheduled_time_ms = mock.Mock(return_value=1_700_000_000_000)

        should_run, reason, scheduled_ms = scheduler._should_run_full_backup(
            _build_settings(
                full_backup_enabled=True,
                full_backup_schedule="0 1 * * *",
                last_run_at_ms=1_700_000_000_000,
                last_full_backup_time_ms=1_600_000_000_000,
            )
        )

        self.assertFalse(should_run)
        self.assertEqual(scheduled_ms, 1_700_000_000_000)
        self.assertTrue(str(reason).strip())


if __name__ == "__main__":
    unittest.main()
