import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.modules.data_security import router
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _SettingsStub:
    def __init__(self, local_target: str | None, windows_target: str | None = None):
        self._local_target = local_target
        self._windows_target = windows_target

    def local_backup_target_path(self) -> str | None:
        return self._local_target

    def windows_target_path(self) -> str | None:
        return self._windows_target


class TestDataSecurityRouterStats(unittest.TestCase):
    def test_backup_pack_stats_skips_mnt_replica_scan_by_default(self):
        s = _SettingsStub("/app/data/backups", "/mnt/replica/RagflowAuth")
        with patch.object(router.settings, "DATA_SECURITY_SCAN_MOUNT_STATS", False), patch.object(
            router.Path, "exists", side_effect=AssertionError("should not stat mount path")
        ):
            data = router._backup_pack_stats(s)
        self.assertEqual(str(data.get("local_backup_target_path", "")).replace("\\", "/"), "/app/data/backups")
        self.assertEqual(str(data.get("windows_backup_target_path", "")).replace("\\", "/"), "/mnt/replica/RagflowAuth")
        self.assertEqual(data.get("local_backup_pack_count"), 0)
        self.assertEqual(data.get("windows_backup_pack_count"), 0)
        self.assertTrue(bool(data.get("windows_backup_pack_count_skipped")))

    def test_backup_pack_stats_counts_local_packs(self):
        td = make_temp_dir(prefix="ragflowauth_stats")
        try:
            base = Path(td)
            (base / "migration_pack_1").mkdir(parents=True, exist_ok=True)
            (base / "migration_pack_2").mkdir(parents=True, exist_ok=True)
            (base / "other").mkdir(parents=True, exist_ok=True)
            s = _SettingsStub(str(base))
            data = router._backup_pack_stats(s)
            self.assertEqual(data.get("local_backup_target_path"), str(base))
            self.assertEqual(data.get("local_backup_pack_count"), 2)
            self.assertEqual(data.get("windows_backup_target_path"), "")
            self.assertEqual(data.get("windows_backup_pack_count"), 0)
        finally:
            cleanup_dir(td)
