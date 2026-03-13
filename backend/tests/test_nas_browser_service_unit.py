import unittest
import os
import tempfile
from types import SimpleNamespace

import backend.services.nas_browser_service as nas_browser_module
from backend.database.schema.ensure import ensure_schema
from backend.services.nas_browser_service import NasBrowserService
from backend.services.nas_task_store import NasTaskStore


class _FakeNasBrowserService(NasBrowserService):
    async def _import_single_file(self, *, source_path: str, target_filename: str, kb_ref: str, deps, ctx):
        return {
            "status": "skipped",
            "payload": {
                "path": source_path,
                "reason": "unsupported_extension",
                "detail": "unsupported extension: .exe",
            },
        }


class NasBrowserServiceUnitTests(unittest.TestCase):
    def test_collect_folder_files_sync_returns_structured_skipped_reason(self):
        service = NasBrowserService()
        service._get_smbclient = lambda: object()  # type: ignore[method-assign]
        service._register_session = lambda _client: None  # type: ignore[method-assign]
        service._walk_files_sync = lambda _client, _path: [  # type: ignore[method-assign]
            {"name": "a.pdf", "path": "folder/a.pdf"},
            {"name": "a.exe", "path": "folder/a.exe"},
        ]
        service._allowed_extensions = lambda _deps: {".pdf"}  # type: ignore[method-assign]

        supported, skipped = service._collect_folder_files_sync("folder", deps=object())

        self.assertEqual(len(supported), 1)
        self.assertEqual(supported[0]["path"], "folder/a.pdf")
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["path"], "folder/a.exe")
        self.assertEqual(skipped[0]["reason"], "unsupported_extension")
        self.assertIn(".exe", skipped[0]["detail"])


class NasBrowserServiceAsyncUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_import_file_to_kb_returns_structured_skipped_payload(self):
        service = _FakeNasBrowserService()
        result = await service.import_file_to_kb(
            relative_path="folder/a.exe",
            kb_ref="kb1",
            deps=object(),
            ctx=object(),
        )

        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["skipped"][0]["path"], "folder/a.exe")
        self.assertEqual(result["skipped"][0]["reason"], "unsupported_extension")


class NasBrowserServiceTaskControlUnitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = NasTaskStore(db_path=self.db_path)
        self.service = NasBrowserService(task_store=self.store)
        self.deps = SimpleNamespace(nas_task_store=self.store)
        self.ctx = SimpleNamespace(
            deps=self.deps,
            payload={},
            user=SimpleNamespace(),
            snapshot=SimpleNamespace(is_admin=True),
        )
        # Avoid background worker execution in unit tests.
        self.service._schedule_folder_import_task = lambda **_kwargs: None  # type: ignore[method-assign]
        nas_browser_module._ACTIVE_TASKS.clear()

    def tearDown(self):
        nas_browser_module._ACTIVE_TASKS.clear()
        self._tmp.cleanup()

    async def test_cancel_folder_import_task_marks_pending_task_as_canceled(self):
        self.store.create_task(
            task_id="task_cancel_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=2,
            pending_files=["folder/a.pdf", "folder/b.pdf"],
            status="pending",
        )

        payload = await self.service.cancel_folder_import_task("task_cancel_1", deps=self.deps)

        self.assertEqual(payload["status"], "canceled")
        self.assertTrue(payload["cancel_requested_at_ms"])

    async def test_retry_folder_import_task_resets_task_with_failed_paths(self):
        self.store.create_task(
            task_id="task_retry_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=3,
            processed_files=3,
            failed_count=1,
            status="failed",
            failed=[{"path": "folder/b.pdf", "reason": "ingestion_failed", "detail": "boom"}],
        )

        payload = await self.service.retry_folder_import_task("task_retry_1", deps=self.deps, ctx=self.ctx)
        refreshed = self.store.get_task("task_retry_1")

        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["total_files"], 1)
        self.assertEqual(payload["retry_count"], 1)
        self.assertEqual(refreshed.pending_files, ["folder/b.pdf"])
        self.assertEqual(refreshed.processed_files, 0)
        self.assertEqual(refreshed.failed_count, 0)

    async def test_retry_folder_import_task_rejects_active_status(self):
        self.store.create_task(
            task_id="task_retry_2",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="running",
            pending_files=["folder/a.pdf"],
        )

        with self.assertRaises(RuntimeError):
            await self.service.retry_folder_import_task("task_retry_2", deps=self.deps, ctx=self.ctx)


if __name__ == "__main__":
    unittest.main()
