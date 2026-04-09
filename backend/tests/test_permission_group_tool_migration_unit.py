from __future__ import annotations

import sqlite3
import time
import unittest

from backend.app.core.tool_catalog import ASSIGNABLE_TOOL_IDS
from backend.database.schema.permission_groups import (
    ensure_permission_groups_table,
    ensure_user_permission_groups_table,
    ensure_user_tool_permissions_table,
    migrate_user_tools_from_permission_groups,
)
from backend.database.schema.users import ensure_users_table
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestPermissionGroupToolMigrationUnit(unittest.TestCase):
    def test_migrates_legacy_viewer_without_manager_as_system_grant(self) -> None:
        td = make_temp_dir(prefix="ragflowauth_permission_tool_migration")
        try:
            db_path = td / "auth.db"
            conn = sqlite3.connect(db_path)
            try:
                ensure_users_table(conn)
                ensure_permission_groups_table(conn)
                ensure_user_permission_groups_table(conn)
                ensure_user_tool_permissions_table(conn)

                now_ms = int(time.time() * 1000)
                conn.execute(
                    """
                    INSERT INTO users (user_id, username, password_hash, role, created_at_ms)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("viewer-1", "viewer_1", "hash", "viewer", now_ms),
                )
                conn.execute(
                    """
                    INSERT INTO permission_groups (
                        group_id, group_name, accessible_tools, can_view_tools, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (100, "legacy-viewer", "[]", 1),
                )
                conn.execute(
                    """
                    INSERT INTO user_permission_groups (user_id, group_id, created_at_ms)
                    VALUES (?, ?, ?)
                    """,
                    ("viewer-1", 100, now_ms),
                )
                conn.commit()

                migrate_user_tools_from_permission_groups(conn)
                conn.commit()

                rows = conn.execute(
                    """
                    SELECT tool_id, granted_by_user_id
                    FROM user_tool_permissions
                    WHERE user_id = ?
                    ORDER BY tool_id
                    """,
                    ("viewer-1",),
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual([row[0] for row in rows], sorted(ASSIGNABLE_TOOL_IDS))
            self.assertEqual({row[1] for row in rows}, {"system_migration"})
        finally:
            cleanup_dir(td)

    def test_migrates_managed_viewer_with_sub_admin_grant(self) -> None:
        td = make_temp_dir(prefix="ragflowauth_permission_tool_migration")
        try:
            db_path = td / "auth.db"
            conn = sqlite3.connect(db_path)
            try:
                ensure_users_table(conn)
                ensure_permission_groups_table(conn)
                ensure_user_permission_groups_table(conn)
                ensure_user_tool_permissions_table(conn)

                now_ms = int(time.time() * 1000)
                conn.execute(
                    """
                    INSERT INTO users (user_id, username, password_hash, role, created_at_ms, company_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("sub-1", "sub_1", "hash", "sub_admin", now_ms, 1),
                )
                conn.execute(
                    """
                    INSERT INTO users (user_id, username, password_hash, role, manager_user_id, created_at_ms, company_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("viewer-1", "viewer_1", "hash", "viewer", "sub-1", now_ms, 1),
                )
                conn.execute(
                    """
                    INSERT INTO permission_groups (
                        group_id, group_name, accessible_tools, can_view_tools, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (101, "managed-tools", '["paper_download","patent_download"]', 1),
                )
                conn.executemany(
                    """
                    INSERT INTO user_permission_groups (user_id, group_id, created_at_ms)
                    VALUES (?, ?, ?)
                    """,
                    [
                        ("sub-1", 101, now_ms),
                        ("viewer-1", 101, now_ms),
                    ],
                )
                conn.commit()

                migrate_user_tools_from_permission_groups(conn)
                conn.commit()

                rows = conn.execute(
                    """
                    SELECT user_id, tool_id, granted_by_user_id
                    FROM user_tool_permissions
                    ORDER BY user_id, tool_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(
                rows,
                [
                    ("sub-1", "paper_download", "system_migration"),
                    ("sub-1", "patent_download", "system_migration"),
                    ("viewer-1", "paper_download", "sub-1"),
                    ("viewer-1", "patent_download", "sub-1"),
                ],
            )
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
