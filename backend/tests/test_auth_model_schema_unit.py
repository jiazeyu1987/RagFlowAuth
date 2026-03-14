import os
import sqlite3
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.users.store import UserStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestAuthModelSchemaUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_auth_model_schema")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def test_org_user_permission_group_tables_and_columns_exist(self):
        conn = self._conn()
        try:
            tables = {
                str(row["name"])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            self.assertIn("users", tables)
            self.assertIn("permission_groups", tables)
            self.assertIn("user_permission_groups", tables)
            self.assertIn("companies", tables)
            self.assertIn("departments", tables)

            user_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            self.assertIn("role", user_cols)
            self.assertIn("group_id", user_cols)
            self.assertIn("company_id", user_cols)
            self.assertIn("department_id", user_cols)
            self.assertIn("max_login_sessions", user_cols)
            self.assertIn("idle_timeout_minutes", user_cols)
            self.assertIn("status", user_cols)

            group_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(permission_groups)").fetchall()
            }
            self.assertIn("group_name", group_cols)
            self.assertIn("accessible_kbs", group_cols)
            self.assertIn("accessible_kb_nodes", group_cols)
            self.assertIn("accessible_chats", group_cols)
            self.assertIn("can_upload", group_cols)
            self.assertIn("can_review", group_cols)
            self.assertIn("can_download", group_cols)
            self.assertIn("can_delete", group_cols)

            mapping_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(user_permission_groups)").fetchall()
            }
            self.assertIn("user_id", mapping_cols)
            self.assertIn("group_id", mapping_cols)
            self.assertIn("created_at_ms", mapping_cols)
        finally:
            conn.close()

    def test_default_permission_groups_seeded(self):
        conn = self._conn()
        try:
            names = {
                str(row["group_name"])
                for row in conn.execute("SELECT group_name FROM permission_groups").fetchall()
            }
        finally:
            conn.close()

        for required in {"admin", "reviewer", "operator", "viewer", "guest"}:
            self.assertIn(required, names)

    def test_user_permission_groups_has_unique_pair_and_indexes(self):
        user_store = UserStore(self.db_path)
        user = user_store.create_user(username="matrix_user", password="Pass1234")

        conn = self._conn()
        try:
            viewer_row = conn.execute(
                "SELECT group_id FROM permission_groups WHERE group_name = ?",
                ("viewer",),
            ).fetchone()
            self.assertIsNotNone(viewer_row)
            group_id = int(viewer_row["group_id"])

            conn.execute(
                "INSERT INTO user_permission_groups (user_id, group_id, created_at_ms) VALUES (?, ?, ?)",
                (user.user_id, group_id, 1),
            )
            conn.commit()

            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO user_permission_groups (user_id, group_id, created_at_ms) VALUES (?, ?, ?)",
                    (user.user_id, group_id, 2),
                )
                conn.commit()

            index_names = {
                str(row["name"])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
            }
            self.assertIn("idx_upg_user_id", index_names)
            self.assertIn("idx_upg_group_id", index_names)
        finally:
            conn.close()

    def test_user_store_uses_user_permission_groups_as_source_of_truth(self):
        user_store = UserStore(self.db_path)
        user = user_store.create_user(username="source_user", password="Pass1234")

        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT group_id FROM permission_groups WHERE group_name IN (?, ?) ORDER BY group_name ASC",
                ("reviewer", "viewer"),
            ).fetchall()
            self.assertEqual(len(rows), 2)
            group_ids = [int(row["group_id"]) for row in rows]

            for idx, group_id in enumerate(group_ids, start=1):
                conn.execute(
                    "INSERT INTO user_permission_groups (user_id, group_id, created_at_ms) VALUES (?, ?, ?)",
                    (user.user_id, group_id, idx),
                )
            conn.commit()
        finally:
            conn.close()

        loaded = user_store.get_by_user_id(user.user_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(set(loaded.group_ids or []), set(group_ids))
        self.assertIn(loaded.group_id, group_ids)


if __name__ == "__main__":
    unittest.main()
