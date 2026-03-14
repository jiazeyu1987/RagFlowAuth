import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.nas_task_store import NasTaskStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestNasTaskStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_nas_task")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = NasTaskStore(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_create_task_persists_pending_file_control_fields(self):
        task = self.store.create_task(
            task_id="task_store_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=2,
            pending_files=["folder/a.pdf", "folder/b.pdf"],
        )

        self.assertEqual(task.pending_files, ["folder/a.pdf", "folder/b.pdf"])
        self.assertEqual(task.priority, 100)
        self.assertEqual(task.retry_count, 0)
        self.assertIsNone(task.cancel_requested_at_ms)
        self.assertEqual(task.created_by_user_id, "")

    def test_create_task_persists_priority(self):
        task = self.store.create_task(
            task_id="task_store_priority",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            priority=25,
        )

        self.assertEqual(task.priority, 25)

    def test_create_task_persists_created_by_user(self):
        task = self.store.create_task(
            task_id="task_store_owner",
            folder_path="folder",
            kb_ref="kb",
            created_by_user_id="u_admin",
            total_files=1,
            pending_files=["folder/a.pdf"],
        )

        self.assertEqual(task.created_by_user_id, "u_admin")

    def test_list_tasks_by_statuses_returns_ordered_tasks(self):
        self.store.create_task(
            task_id="task_store_status_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="failed",
            pending_files=[],
        )
        self.store.create_task(
            task_id="task_store_status_2",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="pending",
            pending_files=["folder/a.pdf"],
        )

        tasks = self.store.list_tasks_by_statuses(["pending", "running"], limit=10)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].task_id, "task_store_status_2")

    def test_list_tasks_supports_status_filter_and_latest_first(self):
        self.store.create_task(
            task_id="task_store_list_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="pending",
            pending_files=["folder/a.pdf"],
        )
        self.store.create_task(
            task_id="task_store_list_2",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="running",
            pending_files=["folder/b.pdf"],
        )

        # Touch task 1 so it becomes the latest by updated_at_ms.
        self.store.update_task("task_store_list_1", status="running")

        all_tasks = self.store.list_tasks(limit=10)
        self.assertGreaterEqual(len(all_tasks), 2)
        self.assertEqual(all_tasks[0].task_id, "task_store_list_1")

        pending_tasks = self.store.list_tasks(limit=10, statuses=["pending"])
        self.assertEqual(len(pending_tasks), 0)

        running_tasks = self.store.list_tasks(limit=10, statuses=["running"])
        running_ids = {task.task_id for task in running_tasks}
        self.assertIn("task_store_list_1", running_ids)
        self.assertIn("task_store_list_2", running_ids)

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

    def test_request_pause_task_running_marks_pausing(self):
        self.store.create_task(
            task_id="task_store_4",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="running",
            pending_files=["folder/a.pdf"],
        )

        task = self.store.request_pause_task("task_store_4")

        self.assertIsNotNone(task)
        self.assertEqual(task.status, "pausing")

    def test_request_resume_task_paused_marks_pending(self):
        self.store.create_task(
            task_id="task_store_5",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="paused",
            pending_files=["folder/a.pdf"],
        )

        task = self.store.request_resume_task("task_store_5")

        self.assertIsNotNone(task)
        self.assertEqual(task.status, "pending")


if __name__ == "__main__":
    unittest.main()
