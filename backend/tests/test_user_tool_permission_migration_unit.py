import json
import sqlite3
import unittest

from backend.database.schema.permission_groups import migrate_user_tools_from_permission_groups


def _build_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            role TEXT,
            manager_user_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE permission_groups (
            group_id INTEGER PRIMARY KEY,
            can_view_tools INTEGER,
            accessible_tools TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE user_permission_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            created_at_ms INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE user_tool_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tool_id TEXT NOT NULL,
            granted_by_user_id TEXT,
            created_at_ms INTEGER NOT NULL,
            updated_at_ms INTEGER NOT NULL,
            UNIQUE(user_id, tool_id)
        )
        """
    )
    return conn


class TestUserToolPermissionMigrationUnit(unittest.TestCase):
    def test_migration_moves_legacy_group_tools(self):
        conn = _build_conn()
        try:
            conn.executemany(
                "INSERT INTO users (user_id, role, manager_user_id) VALUES (?, ?, ?)",
                [
                    ("sub-1", "sub_admin", None),
                    ("viewer-1", "viewer", "sub-1"),
                ],
            )
            conn.executemany(
                "INSERT INTO permission_groups (group_id, can_view_tools, accessible_tools) VALUES (?, ?, ?)",
                [
                    (1, 1, json.dumps(["paper_download", "nmpa"])),
                    (2, 1, json.dumps(["paper_download"])),
                ],
            )
            conn.executemany(
                "INSERT INTO user_permission_groups (user_id, group_id, created_at_ms) VALUES (?, ?, ?)",
                [
                    ("sub-1", 1, 1),
                    ("viewer-1", 2, 1),
                ],
            )

            migrate_user_tools_from_permission_groups(conn)

            rows = conn.execute(
                """
                SELECT user_id, tool_id, granted_by_user_id
                FROM user_tool_permissions
                ORDER BY user_id, tool_id
                """
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    ("sub-1", "nmpa", "system_migration"),
                    ("sub-1", "paper_download", "system_migration"),
                    ("viewer-1", "paper_download", "sub-1"),
                ],
            )
        finally:
            conn.close()

    def test_migration_fails_fast_when_legacy_tool_id_is_unknown(self):
        conn = _build_conn()
        try:
            conn.execute("INSERT INTO users (user_id, role, manager_user_id) VALUES (?, ?, ?)", ("sub-1", "sub_admin", None))
            conn.execute(
                "INSERT INTO permission_groups (group_id, can_view_tools, accessible_tools) VALUES (?, ?, ?)",
                (1, 1, json.dumps(["ghost_tool"])),
            )
            conn.execute(
                "INSERT INTO user_permission_groups (user_id, group_id, created_at_ms) VALUES (?, ?, ?)",
                ("sub-1", 1, 1),
            )

            with self.assertRaisesRegex(ValueError, "tool_migration_invalid_tool_id:ghost_tool"):
                migrate_user_tools_from_permission_groups(conn)

            count = conn.execute("SELECT COUNT(*) FROM user_tool_permissions").fetchone()[0]
            self.assertEqual(count, 0)
        finally:
            conn.close()

    def test_migration_fails_fast_when_viewer_scope_exceeds_manager(self):
        conn = _build_conn()
        try:
            conn.executemany(
                "INSERT INTO users (user_id, role, manager_user_id) VALUES (?, ?, ?)",
                [
                    ("sub-1", "sub_admin", None),
                    ("viewer-1", "viewer", "sub-1"),
                ],
            )
            conn.executemany(
                "INSERT INTO permission_groups (group_id, can_view_tools, accessible_tools) VALUES (?, ?, ?)",
                [
                    (1, 1, json.dumps(["paper_download"])),
                    (2, 1, json.dumps(["nmpa"])),
                ],
            )
            conn.executemany(
                "INSERT INTO user_permission_groups (user_id, group_id, created_at_ms) VALUES (?, ?, ?)",
                [
                    ("sub-1", 1, 1),
                    ("viewer-1", 2, 1),
                ],
            )

            with self.assertRaisesRegex(ValueError, "tool_migration_viewer_scope_exceeds_manager:viewer-1"):
                migrate_user_tools_from_permission_groups(conn)

            count = conn.execute("SELECT COUNT(*) FROM user_tool_permissions").fetchone()[0]
            self.assertEqual(count, 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
