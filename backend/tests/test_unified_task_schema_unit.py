import os
import sqlite3
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestUnifiedTaskSchemaUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_unified_task_schema")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def test_unified_task_tables_created(self):
        conn = self._conn()
        try:
            names = {
                str(row["name"])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            self.assertIn("unified_tasks", names)
            self.assertIn("unified_task_jobs", names)
            self.assertIn("unified_task_events", names)

            task_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(unified_tasks)").fetchall()
            }
            self.assertIn("task_id", task_columns)
            self.assertIn("task_kind", task_columns)
            self.assertIn("status", task_columns)
            self.assertIn("priority", task_columns)
            self.assertIn("created_at_ms", task_columns)
            self.assertIn("updated_at_ms", task_columns)

            job_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(unified_task_jobs)").fetchall()
            }
            self.assertIn("task_id", job_columns)
            self.assertIn("attempt_no", job_columns)
            self.assertIn("status", job_columns)
            self.assertIn("queue_name", job_columns)

            event_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(unified_task_events)").fetchall()
            }
            self.assertIn("task_id", event_columns)
            self.assertIn("event_type", event_columns)
            self.assertIn("created_at_ms", event_columns)
        finally:
            conn.close()

    def test_unified_task_indexes_created(self):
        conn = self._conn()
        try:
            index_names = {
                str(row["name"])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
            }
        finally:
            conn.close()

        expected = {
            "idx_unified_tasks_kind_status_priority",
            "idx_unified_tasks_owner_status",
            "idx_unified_tasks_updated_at",
            "idx_unified_task_jobs_task_attempt",
            "idx_unified_task_jobs_status_queue",
            "idx_unified_task_jobs_queued_at",
            "idx_unified_task_events_task_created",
            "idx_unified_task_events_type_created",
            "idx_unified_task_events_job_created",
        }
        for index_name in expected:
            self.assertIn(index_name, index_names)

    def test_ensure_schema_idempotent_for_unified_task_tables(self):
        ensure_schema(self.db_path)

        conn = self._conn()
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM sqlite_master WHERE type = 'table' AND name = 'unified_tasks'").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(int(row["c"] or 0), 1)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
