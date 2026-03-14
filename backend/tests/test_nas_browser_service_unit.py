import asyncio
import heapq
import unittest
import os
from types import SimpleNamespace
from unittest.mock import patch

import backend.services.nas_browser_service as nas_browser_module
from backend.database.schema.ensure import ensure_schema
from backend.services.nas_browser_service import NasBrowserService
from backend.services.nas_task_store import NasTaskStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


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
        self._tmp = make_temp_dir(prefix="ragflowauth_nas_service")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
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
        self._orig_schedule = nas_browser_module.NasBrowserService._schedule_folder_import_task
        self._orig_max_concurrency = nas_browser_module._MAX_CONCURRENT_IMPORTS
        self._orig_max_per_user = nas_browser_module._MAX_CONCURRENT_IMPORTS_PER_USER
        self._orig_max_nas = nas_browser_module._MAX_CONCURRENT_NAS_IMPORTS
        # Avoid background worker execution in unit tests.
        self.service._schedule_folder_import_task = lambda **_kwargs: None  # type: ignore[method-assign]
        nas_browser_module._ACTIVE_TASKS.clear()
        nas_browser_module._RUNNING_TASK_META.clear()
        nas_browser_module._QUEUED_TASK_IDS.clear()
        nas_browser_module._QUEUED_TASK_HEAP.clear()

    def tearDown(self):
        nas_browser_module._MAX_CONCURRENT_IMPORTS = self._orig_max_concurrency
        nas_browser_module._MAX_CONCURRENT_IMPORTS_PER_USER = self._orig_max_per_user
        nas_browser_module._MAX_CONCURRENT_NAS_IMPORTS = self._orig_max_nas
        nas_browser_module.NasBrowserService._schedule_folder_import_task = self._orig_schedule
        nas_browser_module._ACTIVE_TASKS.clear()
        nas_browser_module._RUNNING_TASK_META.clear()
        nas_browser_module._QUEUED_TASK_IDS.clear()
        nas_browser_module._QUEUED_TASK_HEAP.clear()
        cleanup_dir(self._tmp)

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

    async def test_pause_folder_import_task_marks_pending_task_as_paused(self):
        self.store.create_task(
            task_id="task_pause_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=2,
            pending_files=["folder/a.pdf", "folder/b.pdf"],
            status="pending",
        )

        payload = await self.service.pause_folder_import_task("task_pause_1", deps=self.deps)

        self.assertEqual(payload["status"], "paused")
        self.assertTrue(payload["can_resume"])

    async def test_resume_folder_import_task_marks_paused_task_as_pending(self):
        self.store.create_task(
            task_id="task_resume_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            status="paused",
        )

        payload = await self.service.resume_folder_import_task("task_resume_1", deps=self.deps, ctx=self.ctx)
        refreshed = self.store.get_task("task_resume_1")

        self.assertEqual(payload["status"], "pending")
        self.assertTrue(payload["can_pause"])
        self.assertEqual(refreshed.status, "pending")

    async def test_queue_orders_pending_tasks_by_priority(self):
        nas_browser_module._MAX_CONCURRENT_IMPORTS = 0
        self.service._schedule_folder_import_task = self._orig_schedule.__get__(  # type: ignore[method-assign]
            self.service, nas_browser_module.NasBrowserService
        )

        self.store.create_task(
            task_id="task_queue_low",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/low.pdf"],
            priority=200,
            status="pending",
        )
        self.store.create_task(
            task_id="task_queue_high",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/high.pdf"],
            priority=20,
            status="pending",
        )

        self.service._schedule_folder_import_task(task_id="task_queue_low", deps=self.deps, ctx=self.ctx)
        self.service._schedule_folder_import_task(task_id="task_queue_high", deps=self.deps, ctx=self.ctx)
        await asyncio.sleep(0.05)

        low_payload = await self.service.get_folder_import_task("task_queue_low", deps=self.deps, ctx=self.ctx)
        high_payload = await self.service.get_folder_import_task("task_queue_high", deps=self.deps, ctx=self.ctx)

        self.assertEqual(high_payload["task_priority"], 20)
        self.assertEqual(low_payload["task_priority"], 200)
        self.assertEqual(high_payload["queue_position"], 1)
        self.assertEqual(low_payload["queue_position"], 2)

    async def test_task_payload_contains_user_quota_block_reason(self):
        nas_browser_module._MAX_CONCURRENT_IMPORTS = 5
        nas_browser_module._MAX_CONCURRENT_IMPORTS_PER_USER = 1
        nas_browser_module._MAX_CONCURRENT_NAS_IMPORTS = 5

        self.store.create_task(
            task_id="task_quota_user_1",
            folder_path="folder",
            kb_ref="kb",
            created_by_user_id="u1",
            total_files=1,
            pending_files=["folder/a.pdf"],
            priority=10,
            status="pending",
        )

        nas_browser_module._RUNNING_TASKS.add("running_u1")
        nas_browser_module._RUNNING_TASK_META["running_u1"] = {"owner_user_id": "u1", "task_kind": "nas_import"}
        nas_browser_module._QUEUED_TASK_IDS.add("task_quota_user_1")
        heapq.heappush(
            nas_browser_module._QUEUED_TASK_HEAP,
            (10, 1, "task_quota_user_1", self.deps, self.ctx, "u1"),
        )

        payload = await self.service.get_folder_import_task("task_quota_user_1", deps=self.deps, ctx=self.ctx)

        self.assertEqual(payload["queue_position"], 1)
        self.assertEqual(payload["quota_blocked_reason"], "user_limit")
        self.assertEqual(payload["quota"]["per_user_limit"], 1)

    async def test_recover_startup_tasks_requeues_running_task(self):
        self.store.create_task(
            task_id="task_recover_1",
            folder_path="folder",
            kb_ref="kb",
            created_by_user_id="u1",
            total_files=2,
            processed_files=1,
            pending_files=["folder/b.pdf"],
            status="running",
        )
        scheduled: list[str] = []
        self.service._schedule_folder_import_task = lambda **kwargs: scheduled.append(kwargs["task_id"])  # type: ignore[method-assign]

        summary = await self.service.recover_startup_tasks(deps=self.deps)
        refreshed = self.store.get_task("task_recover_1")

        self.assertEqual(summary["requeued"], 1)
        self.assertIn("task_recover_1", scheduled)
        self.assertEqual(refreshed.status, "pending")

    async def test_recover_startup_tasks_converts_canceling_to_canceled(self):
        self.store.create_task(
            task_id="task_recover_cancel",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            status="canceling",
            cancel_requested_at_ms=123,
        )

        summary = await self.service.recover_startup_tasks(deps=self.deps)
        refreshed = self.store.get_task("task_recover_cancel")

        self.assertEqual(summary["canceled"], 1)
        self.assertEqual(refreshed.status, "canceled")

    async def test_start_folder_import_task_rejects_when_cross_kind_quota_exceeded(self):
        self.service._collect_folder_files_sync = (  # type: ignore[method-assign]
            lambda _relative_path, _deps: ([{"name": "a.pdf", "path": "folder/a.pdf"}], [])
        )
        self.deps.data_security_store = SimpleNamespace(
            list_jobs=lambda limit=2000: [SimpleNamespace(status="running")]
        )
        actor_ctx = SimpleNamespace(
            deps=self.deps,
            payload=SimpleNamespace(sub="u_nas_1"),
            user=SimpleNamespace(),
            snapshot=SimpleNamespace(is_admin=True),
        )

        with patch.object(nas_browser_module.settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 1), patch.object(
            nas_browser_module.settings, "TASK_USER_CONCURRENCY_LIMIT", 10
        ), patch.object(nas_browser_module.settings, "TASK_NAS_CONCURRENCY_LIMIT", 10):
            with self.assertRaises(RuntimeError) as ctx:
                await self.service.start_folder_import_task(
                    relative_path="folder",
                    kb_ref="kb",
                    deps=self.deps,
                    ctx=actor_ctx,
                    priority=100,
                )

        self.assertIn("task_quota_exceeded:global", str(ctx.exception))
        self.assertEqual(len(self.store.list_tasks(limit=10)), 0)


if __name__ == "__main__":
    unittest.main()
