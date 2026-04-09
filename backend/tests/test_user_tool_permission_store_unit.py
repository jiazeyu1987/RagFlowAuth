import tempfile
import unittest
from pathlib import Path

from backend.database.schema.ensure import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.users.store import UserStore
from backend.services.users.tool_permission_store import UserToolPermissionStore


class TestUserToolPermissionStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self._tmp.name) / "auth.db"
        ensure_schema(str(self.db_path))

    def tearDown(self):
        self._tmp.cleanup()

    def _new_store(self) -> UserToolPermissionStore:
        return UserToolPermissionStore(connection_factory=lambda: connect_sqlite(self.db_path))

    def test_replace_and_list_tool_ids(self):
        store = self._new_store()
        store.replace_tool_ids(
            "u-1",
            ["paper_download", "", "nmpa", "nmpa"],
            granted_by_user_id="admin-1",
        )

        self.assertEqual(store.list_tool_ids("u-1"), ["nmpa", "paper_download"])

        conn = connect_sqlite(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT tool_id, granted_by_user_id
                FROM user_tool_permissions
                WHERE user_id = ?
                ORDER BY tool_id
                """,
                ("u-1",),
            ).fetchall()
            normalized_rows = [(str(row[0]), str(row[1])) for row in rows]
            self.assertEqual(
                normalized_rows,
                [
                    ("nmpa", "admin-1"),
                    ("paper_download", "admin-1"),
                ],
            )
        finally:
            conn.close()

    def test_list_managed_viewer_user_ids(self):
        conn = connect_sqlite(self.db_path)
        try:
            conn.executemany(
                """
                INSERT INTO users (
                    user_id, username, password_hash, role, manager_user_id, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    ("sub-1", "sub-1", "hash", "sub_admin", None, 1),
                    ("viewer-1", "viewer-1", "hash", "viewer", "sub-1", 100),
                    ("viewer-2", "viewer-2", "hash", "viewer", "sub-1", 200),
                    ("reviewer-1", "reviewer-1", "hash", "reviewer", "sub-1", 300),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        store = self._new_store()
        self.assertEqual(store.list_managed_viewer_user_ids("sub-1"), ["viewer-2", "viewer-1"])

    def test_sync_prunes_managed_viewer_tools_when_sub_admin_scope_shrinks(self):
        user_store = UserStore(db_path=str(self.db_path))
        sub_admin = user_store.create_user(
            username="sub-admin",
            password="Pass1234",
            role="sub_admin",
            company_id=1,
            department_id=1,
        )
        viewer_a = user_store.create_user(
            username="viewer-a",
            password="Pass1234",
            role="viewer",
            manager_user_id=sub_admin.user_id,
            company_id=1,
            department_id=1,
        )
        viewer_b = user_store.create_user(
            username="viewer-b",
            password="Pass1234",
            role="viewer",
            manager_user_id=sub_admin.user_id,
            company_id=1,
            department_id=1,
        )

        user_store.set_user_tool_permissions(sub_admin.user_id, ["paper_download", "nmpa"])
        user_store.set_user_tool_permissions(viewer_a.user_id, ["paper_download", "nmpa"])
        user_store.set_user_tool_permissions(viewer_b.user_id, ["paper_download"])

        user_store.set_user_tool_permissions_with_managed_viewer_sync(
            sub_admin_user_id=sub_admin.user_id,
            tool_ids=["paper_download"],
            granted_by_user_id="admin-1",
        )

        self.assertEqual(user_store.list_user_tool_ids(sub_admin.user_id), ["paper_download"])
        self.assertEqual(user_store.list_user_tool_ids(viewer_a.user_id), ["paper_download"])
        self.assertEqual(user_store.list_user_tool_ids(viewer_b.user_id), ["paper_download"])


if __name__ == "__main__":
    unittest.main()
