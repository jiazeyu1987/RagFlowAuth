from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tool.maintenance.features.local_backup_catalog import list_local_backups


class TestLocalBackupCatalogUnit(unittest.TestCase):
    def test_lists_only_dirs_with_auth_db_and_sorts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="ragflowauth_backups_"))

        (root / "migration_pack_20260130_112315_160").mkdir()
        (root / "migration_pack_20260130_112315_160" / "auth.db").write_bytes(b"x")

        (root / "migration_pack_20260129_101344").mkdir()
        (root / "migration_pack_20260129_101344" / "auth.db").write_bytes(b"x")

        (root / "not_a_pack").mkdir()
        # missing auth.db -> excluded

        entries = list_local_backups(root)
        self.assertEqual(len(entries), 2)
        # Newest first
        self.assertEqual(entries[0].path.name, "migration_pack_20260130_112315_160")
        self.assertTrue(entries[0].label.startswith("2026-01-30 11:23:15"))
        self.assertEqual(entries[1].path.name, "migration_pack_20260129_101344")

