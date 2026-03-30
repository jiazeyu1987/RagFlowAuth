from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.nas_import_task_store import NasImportTaskStore


class TestNasImportTaskStoreUnit(unittest.TestCase):
    def test_create_and_get_task(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "auth.db"
            store = NasImportTaskStore(db_path=db_path)

            store.create_task(
                task_id="task-1",
                folder_path="folder/a",
                kb_ref="kb-x",
                total_files=3,
                skipped_count=1,
                skipped=[{"path": "folder/a/skip.txt", "reason": "unsupported_extension"}],
                status="pending",
            )

            task = store.get_task("task-1")
            self.assertIsNotNone(task)
            assert task is not None
            self.assertEqual(task["task_id"], "task-1")
            self.assertEqual(task["status"], "pending")
            self.assertEqual(task["total_files"], 3)
            self.assertEqual(task["processed_files"], 0)
            self.assertEqual(task["skipped_count"], 1)
            self.assertEqual(task["progress_percent"], 0)
            self.assertEqual(task["remaining_files"], 3)
            self.assertEqual(len(task["skipped"]), 1)

    def test_apply_outcome_updates_counts_and_caps_payload(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "auth.db"
            store = NasImportTaskStore(db_path=db_path)
            store.create_task(task_id="task-2", folder_path="folder/b", kb_ref="kb-y", total_files=80, status="running")

            for idx in range(60):
                store.apply_outcome("task-2", status="failed", payload={"path": f"f{idx}.pdf"})

            task = store.get_task("task-2")
            self.assertIsNotNone(task)
            assert task is not None
            self.assertEqual(task["processed_files"], 60)
            self.assertEqual(task["failed_count"], 60)
            self.assertEqual(len(task["failed"]), 50)

    def test_mark_running_completed_failed(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "auth.db"
            store = NasImportTaskStore(db_path=db_path)
            store.create_task(task_id="task-3", folder_path="folder/c", kb_ref="kb-z", total_files=1, status="pending")

            store.mark_running("task-3")
            self.assertEqual(store.get_task("task-3")["status"], "running")

            store.mark_failed("task-3", "boom")
            failed = store.get_task("task-3")
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["error"], "boom")

            store.mark_completed("task-3")
            completed = store.get_task("task-3")
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["current_file"], "")


if __name__ == "__main__":
    unittest.main()
