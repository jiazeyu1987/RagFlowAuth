import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.modules.data_security import router


class _SettingsStub:
    def __init__(self, target: str | None):
        self._target = target

    def target_path(self) -> str | None:
        return self._target


class TestDataSecurityRouterStats(unittest.TestCase):
    def test_backup_pack_stats_skips_mnt_replica_scan_by_default(self):
        s = _SettingsStub("/mnt/replica/RagflowAuth")
        with patch.object(router.settings, "DATA_SECURITY_SCAN_MOUNT_STATS", False), patch.object(
            router.Path, "exists", side_effect=AssertionError("should not stat mount path")
        ):
            data = router._backup_pack_stats(s)
        self.assertEqual(str(data.get("backup_target_path", "")).replace("\\", "/"), "/mnt/replica/RagflowAuth")
        self.assertEqual(data.get("backup_pack_count"), 0)
        self.assertTrue(bool(data.get("backup_pack_count_skipped")))

    def test_backup_pack_stats_counts_local_packs(self):
        with tempfile.TemporaryDirectory(prefix="ragflowauth_stats_") as td:
            base = Path(td)
            (base / "migration_pack_1").mkdir(parents=True, exist_ok=True)
            (base / "migration_pack_2").mkdir(parents=True, exist_ok=True)
            (base / "other").mkdir(parents=True, exist_ok=True)
            s = _SettingsStub(str(base))
            data = router._backup_pack_stats(s)
        self.assertEqual(data.get("backup_target_path"), str(base))
        self.assertEqual(data.get("backup_pack_count"), 2)
