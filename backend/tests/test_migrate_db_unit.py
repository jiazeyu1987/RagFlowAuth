from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.database.sqlite import connect_sqlite
from backend.migrate_db import migrate_database


class MigrateDbUnitTests(unittest.TestCase):
    def test_migrate_database_bootstraps_current_schema_and_copies_users(self):
        with tempfile.TemporaryDirectory(prefix="ragflowauth_migrate_db_") as temp_dir:
            root = Path(temp_dir)
            old_db = root / "legacy.db"
            new_db = root / "data" / "auth.db"

            legacy_conn = sqlite3.connect(old_db)
            try:
                legacy_conn.execute(
                    """
                    CREATE TABLE users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        email TEXT,
                        role TEXT,
                        status TEXT,
                        created_at_ms INTEGER
                    )
                    """
                )
                legacy_conn.execute(
                    """
                    INSERT INTO users (
                        user_id,
                        username,
                        password_hash,
                        email,
                        role,
                        status,
                        created_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "u-1",
                        "legacy_admin",
                        "hash-1",
                        "legacy@example.com",
                        "admin",
                        "active",
                        123456,
                    ),
                )
                legacy_conn.commit()
            finally:
                legacy_conn.close()

            ok = migrate_database(old_db, new_db)

            self.assertTrue(ok)
            self.assertTrue((old_db.with_suffix(".db.backup")).exists())

            conn = connect_sqlite(new_db)
            try:
                user = conn.execute(
                    "SELECT username, email, role, status, created_at_ms FROM users WHERE user_id = ?",
                    ("u-1",),
                ).fetchone()
                self.assertIsNotNone(user)
                self.assertEqual(user["username"], "legacy_admin")
                self.assertEqual(user["email"], "legacy@example.com")
                self.assertEqual(user["role"], "admin")
                self.assertEqual(user["status"], "active")
                self.assertEqual(user["created_at_ms"], 123456)

                group_row = conn.execute(
                    """
                    SELECT group_id
                    FROM user_permission_groups
                    WHERE user_id = ?
                    """,
                    ("u-1",),
                ).fetchone()
                self.assertIsNotNone(group_row)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
