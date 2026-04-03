from __future__ import annotations

import unittest

from backend.app.core.paths import repo_root
from backend.database.paths import resolve_auth_db_path
from backend.runtime.runner import migrate_data_dir


class AuthDbPathUnitTests(unittest.TestCase):
    def test_default_database_path_resolves_to_repo_root_data_auth_db(self):
        resolved = resolve_auth_db_path()
        self.assertEqual(resolved, repo_root() / "data" / "auth.db")

    def test_relative_legacy_database_path_is_rejected(self):
        with self.assertRaises(ValueError) as cm:
            resolve_auth_db_path("backend/data/auth.db")

        self.assertIn("legacy_auth_db_path_not_supported", str(cm.exception))

    def test_absolute_legacy_database_path_is_rejected(self):
        legacy_path = repo_root() / "backend" / "data" / "auth.db"
        with self.assertRaises(ValueError) as cm:
            resolve_auth_db_path(legacy_path)

        self.assertIn("legacy_auth_db_path_not_supported", str(cm.exception))

    def test_legacy_migrate_command_is_disabled(self):
        with self.assertRaises(SystemExit) as cm:
            migrate_data_dir()

        self.assertIn("legacy_data_dir_migration_removed", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
