import os
import tempfile
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.nas_task_store import NasTaskStore


class TestNasTaskStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = NasTaskStore(db_path=self.db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_create_task_persists_pending_file_control_fields(self):
        task = self.store.create_task(
            task_id="task_store_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=2,
            pending_files=["folder/a.pdf", "folder/b.pdf"],
        )

        self.assertEqual(task.pending_files, ["folder/a.pdf", "folder/b.pdf"])
        self.assertEqual(task.retry_count, 0)
        self.assertIsNone(task.cancel_requested_at_ms)

    def test_request_cancel_task_pending_marks_canceled(self):
        self.store.create_task(
            task_id="task_store_2",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            status="pending",
        )

        task = self.store.request_cancel_task("task_store_2")

        self.assertIsNotNone(task)
        self.assertEqual(task.status, "canceled")
        self.assertIsNotNone(task.cancel_requested_at_ms)

    def test_request_cancel_task_running_marks_canceling(self):
        self.store.create_task(
            task_id="task_store_3",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="running",
            pending_files=["folder/a.pdf"],
        )

        task = self.store.request_cancel_task("task_store_3")

        self.assertIsNotNone(task)
        self.assertEqual(task.status, "canceling")
        self.assertIsNotNone(task.cancel_requested_at_ms)


if __name__ == "__main__":
    unittest.main()
