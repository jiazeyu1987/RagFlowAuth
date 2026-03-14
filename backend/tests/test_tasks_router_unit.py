import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.services.download_execution.manager as download_exec_module
import backend.services.nas_browser_service as nas_browser_module
import backend.services.task_control_service as task_control_module
from backend.app.core.authz import AuthContext, get_auth_context
from backend.app.modules.tasks.router import router as tasks_router
from backend.database.schema.ensure import ensure_schema
from backend.services.kb_store import KbStore
from backend.services.data_security_store import DataSecurityStore
from backend.services.nas_task_store import NasTaskStore
from backend.services.paper_plag_store import PaperPlagStore
from backend.services.paper_download.store import PaperDownloadStore
from backend.services.patent_download.store import PatentDownloadStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestTasksRouterUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_tasks_router")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = NasTaskStore(db_path=self.db_path)
        self.backup_store = DataSecurityStore(db_path=self.db_path)
        self.paper_store = PaperDownloadStore(db_path=self.db_path)
        self.patent_store = PatentDownloadStore(db_path=self.db_path)
        self.kb_store = KbStore(db_path=self.db_path)
        self.paper_plag_store = PaperPlagStore(db_path=self.db_path)
        self.deps = SimpleNamespace(
            nas_task_store=self.store,
            data_security_store=self.backup_store,
            paper_download_store=self.paper_store,
            patent_download_store=self.patent_store,
            kb_store=self.kb_store,
            paper_plag_store=self.paper_plag_store,
        )
        self.app = FastAPI()
        self.app.include_router(tasks_router, prefix="/api")

        self._orig_schedule = nas_browser_module.NasBrowserService._schedule_folder_import_task
        nas_browser_module.NasBrowserService._schedule_folder_import_task = lambda *_args, **_kwargs: None
        nas_browser_module._ACTIVE_TASKS.clear()
        nas_browser_module._RUNNING_TASK_META.clear()
        nas_browser_module._QUEUED_TASK_IDS.clear()
        nas_browser_module._QUEUED_TASK_HEAP.clear()
        task_control_module._METRIC_ALERT_CACHE.clear()
        task_control_module._METRIC_SNAPSHOT_CACHE.clear()
        task_control_module._TASK_KIND_CACHE.clear()
        task_control_module._TASK_PAYLOAD_CACHE.clear()
        self._clear_download_execution_registry()

    def tearDown(self):
        nas_browser_module.NasBrowserService._schedule_folder_import_task = self._orig_schedule
        nas_browser_module._ACTIVE_TASKS.clear()
        nas_browser_module._RUNNING_TASK_META.clear()
        nas_browser_module._QUEUED_TASK_IDS.clear()
        nas_browser_module._QUEUED_TASK_HEAP.clear()
        task_control_module._METRIC_ALERT_CACHE.clear()
        task_control_module._METRIC_SNAPSHOT_CACHE.clear()
        task_control_module._TASK_KIND_CACHE.clear()
        task_control_module._TASK_PAYLOAD_CACHE.clear()
        self._clear_download_execution_registry()
        cleanup_dir(self._tmp)

    @staticmethod
    def _clear_download_execution_registry() -> None:
        download_exec_module.DownloadExecutionManager._jobs.clear()
        download_exec_module.DownloadExecutionManager._cancelled_sessions.clear()
        download_exec_module.DownloadExecutionManager._stop_requested_sessions.clear()

    def _client(self, *, is_admin: bool = True) -> TestClient:
        ctx = AuthContext(
            deps=self.deps,
            payload=TokenPayload(sub="u1"),
            user=SimpleNamespace(user_id="u1"),
            snapshot=SimpleNamespace(is_admin=is_admin),
        )
        self.app.dependency_overrides[get_auth_context] = lambda: ctx
        return TestClient(self.app)

    @staticmethod
    def _create_download_session(*, store, session_id: str, status: str, created_by: str = "u1") -> None:
        store.create_session(
            session_id=session_id,
            created_by=created_by,
            keyword_text="alpha,beta",
            keywords=["alpha", "beta"],
            use_and=True,
            sources={"s1": {"enabled": True, "limit": 5}},
            status=status,
            source_errors={},
            source_stats={"s1": {"enabled": True, "limit": 5}},
        )

    def _create_upload_doc(self, *, doc_status: str = "pending", uploaded_by: str = "u1") -> str:
        doc = self.kb_store.create_document(
            filename="paper-a.pdf",
            file_path="data/uploads/unit/paper-a.pdf",
            file_size=128,
            mime_type="application/pdf",
            uploaded_by=uploaded_by,
            kb_id="kb1",
            status=doc_status,
        )
        return str(doc.doc_id)

    def _create_paper_plag_report(
        self,
        *,
        report_id: str,
        status: str = "pending",
        paper_id: str = "paper_1",
        created_by: str = "u1",
    ) -> str:
        report = self.paper_plag_store.create_report(
            report_id=report_id,
            paper_id=paper_id,
            version_id=None,
            task_id=report_id,
            status=status,
            created_by_user_id=created_by,
        )
        return str(report.report_id)

    def test_get_task_status_auto_detects_nas_task(self):
        self.store.create_task(
            task_id="task_auto_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            status="pending",
        )

        with self._client() as client:
            resp = client.get("/api/tasks/task_auto_1")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], "task_auto_1")
        self.assertEqual(payload["task_kind"], "nas_import")

    def test_get_task_status_auto_detects_backup_job(self):
        job = self.backup_store.create_job_v2(kind="incremental", status="queued", message="queued")

        with self._client() as client:
            resp = client.get(f"/api/tasks/{job.id}?kind=auto")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], str(job.id))
        self.assertEqual(payload["task_kind"], "backup_job")
        self.assertEqual(payload["status"], "pending")

    def test_get_task_status_auto_detects_paper_download_session(self):
        self._create_download_session(store=self.paper_store, session_id="paper_session_auto_1", status="running")

        with self._client() as client:
            resp = client.get("/api/tasks/paper_session_auto_1?kind=auto")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], "paper_session_auto_1")
        self.assertEqual(payload["task_kind"], "paper_download")
        self.assertEqual(payload["status"], "running")

    def test_get_task_status_auto_detects_patent_download_session(self):
        self._create_download_session(store=self.patent_store, session_id="patent_session_auto_1", status="completed")

        with self._client() as client:
            resp = client.get("/api/tasks/patent_session_auto_1?kind=auto")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], "patent_session_auto_1")
        self.assertEqual(payload["task_kind"], "patent_download")
        self.assertEqual(payload["status"], "completed")

    def test_get_task_status_with_collection_kind_detects_paper_download(self):
        self._create_download_session(store=self.paper_store, session_id="paper_session_collection_1", status="running")

        with self._client() as client:
            resp = client.get("/api/tasks/paper_session_collection_1?kind=collection")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], "paper_session_collection_1")
        self.assertEqual(payload["task_kind"], "paper_download")
        self.assertEqual(payload["status"], "running")

    def test_get_task_status_auto_detects_knowledge_upload(self):
        doc_id = self._create_upload_doc(doc_status="pending")

        with self._client() as client:
            resp = client.get(f"/api/tasks/{doc_id}?kind=auto")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], doc_id)
        self.assertEqual(payload["task_kind"], "knowledge_upload")
        self.assertEqual(payload["status"], "pending")

    def test_get_task_status_with_explicit_knowledge_upload_kind(self):
        doc_id = self._create_upload_doc(doc_status="approved")

        with self._client() as client:
            resp = client.get(f"/api/tasks/{doc_id}?kind=knowledge_upload")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], doc_id)
        self.assertEqual(payload["task_kind"], "knowledge_upload")
        self.assertEqual(payload["status"], "completed")

    def test_get_task_status_auto_detects_paper_plagiarism(self):
        report_id = self._create_paper_plag_report(report_id="plag_auto_1", status="running")

        with self._client() as client:
            resp = client.get(f"/api/tasks/{report_id}?kind=auto")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], report_id)
        self.assertEqual(payload["task_kind"], "paper_plagiarism")
        self.assertEqual(payload["status"], "running")

    def test_get_task_status_with_explicit_paper_plagiarism_kind(self):
        report_id = self._create_paper_plag_report(report_id="plag_explicit_1", status="completed")

        with self._client() as client:
            resp = client.get(f"/api/tasks/{report_id}?kind=paper_plagiarism")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], report_id)
        self.assertEqual(payload["task_kind"], "paper_plagiarism")
        self.assertEqual(payload["status"], "completed")

    def test_get_task_status_auto_backup_avoids_redundant_nas_probe(self):
        job = self.backup_store.create_job_v2(kind="incremental", status="queued", message="queued")

        with patch.object(task_control_module.settings, "TASK_STATUS_CACHE_TTL_MS", 3000), patch.object(
            self.store, "get_task", wraps=self.store.get_task
        ) as nas_get_task_mock, patch.object(self.backup_store, "get_job", wraps=self.backup_store.get_job) as backup_get_job_mock:
            with self._client() as client:
                self.assertEqual(client.get(f"/api/tasks/{job.id}?kind=auto").status_code, 200)
                self.assertEqual(client.get(f"/api/tasks/{job.id}?kind=auto").status_code, 200)

        self.assertEqual(nas_get_task_mock.call_count, 0)
        self.assertEqual(backup_get_job_mock.call_count, 1)

    def test_pause_and_resume_with_unified_routes(self):
        self.store.create_task(
            task_id="task_ctrl_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=2,
            pending_files=["folder/a.pdf", "folder/b.pdf"],
            status="pending",
        )

        with self._client() as client:
            pause_resp = client.post("/api/tasks/task_ctrl_1/pause")
            resume_resp = client.post("/api/tasks/task_ctrl_1/resume?kind=nas_import")

        self.assertEqual(pause_resp.status_code, 200)
        self.assertEqual(pause_resp.json()["status"], "paused")
        self.assertEqual(resume_resp.status_code, 200)
        self.assertEqual(resume_resp.json()["status"], "pending")

    def test_retry_with_unified_route(self):
        self.store.create_task(
            task_id="task_retry_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            processed_files=1,
            failed_count=1,
            status="failed",
            failed=[{"path": "folder/a.pdf", "reason": "ingestion_failed", "detail": "boom"}],
        )

        with self._client() as client:
            resp = client.post("/api/tasks/task_retry_1/retry")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["retry_count"], 1)
        self.assertEqual(payload["task_kind"], "nas_import")

    def test_retry_with_unified_route_for_knowledge_upload(self):
        doc_id = self._create_upload_doc(doc_status="rejected")

        with self._client() as client:
            resp = client.post(f"/api/tasks/{doc_id}/retry?kind=knowledge_upload")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_id"], doc_id)
        self.assertEqual(payload["task_kind"], "knowledge_upload")
        self.assertEqual(payload["status"], "pending")
        self.assertFalse(bool(payload.get("can_retry")))

    def test_retry_knowledge_upload_pending_returns_409(self):
        doc_id = self._create_upload_doc(doc_status="pending")

        with self._client() as client:
            resp = client.post(f"/api/tasks/{doc_id}/retry?kind=knowledge_upload")

        self.assertEqual(resp.status_code, 409)

    def test_cancel_with_unified_route_for_backup_job(self):
        job = self.backup_store.create_job_v2(kind="full", status="running", message="running")

        with self._client() as client:
            resp = client.post(f"/api/tasks/{job.id}/cancel?kind=backup_job")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "backup_job")
        self.assertIn(payload["status"], ("canceling", "canceled"))

    def test_cancel_with_unified_route_for_paper_download(self):
        self._create_download_session(store=self.paper_store, session_id="paper_cancel_1", status="running")

        with self._client() as client:
            resp = client.post("/api/tasks/paper_cancel_1/cancel?kind=paper_download")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "paper_download")
        self.assertIn(payload["status"], ("canceling", "canceled"))

    def test_cancel_with_unified_route_for_patent_download(self):
        self._create_download_session(store=self.patent_store, session_id="patent_cancel_1", status="running")

        with self._client() as client:
            resp = client.post("/api/tasks/patent_cancel_1/cancel?kind=patent_download")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "patent_download")
        self.assertIn(payload["status"], ("canceling", "canceled"))

    def test_cancel_with_unified_route_for_collection_kind(self):
        self._create_download_session(store=self.paper_store, session_id="paper_cancel_collection_1", status="running")

        with self._client() as client:
            resp = client.post("/api/tasks/paper_cancel_collection_1/cancel?kind=collection")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "paper_download")
        self.assertIn(payload["status"], ("canceling", "canceled"))

    def test_cancel_with_unified_route_for_paper_plagiarism(self):
        report_id = self._create_paper_plag_report(report_id="plag_cancel_1", status="running")

        with self._client() as client:
            resp = client.post(f"/api/tasks/{report_id}/cancel?kind=paper_plagiarism")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "paper_plagiarism")
        self.assertIn(payload["status"], ("canceling", "canceled"))

    def test_pause_backup_job_returns_409(self):
        job = self.backup_store.create_job_v2(kind="incremental", status="queued", message="queued")

        with self._client() as client:
            resp = client.post(f"/api/tasks/{job.id}/pause?kind=backup_job")

        self.assertEqual(resp.status_code, 409)

    def test_unsupported_kind_returns_400(self):
        self.store.create_task(
            task_id="task_kind_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            status="pending",
        )

        with self._client() as client:
            resp = client.get("/api/tasks/task_kind_1?kind=paper")

        self.assertEqual(resp.status_code, 400)

    def test_get_metrics_returns_failure_rate_and_backlog(self):
        self.store.create_task(
            task_id="metric_task_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            status="pending",
        )
        self.store.create_task(
            task_id="metric_task_2",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            processed_files=1,
            failed_count=1,
            status="failed",
            pending_files=[],
        )

        with self._client() as client:
            resp = client.get("/api/tasks/metrics?kind=nas_import")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "nas_import")
        self.assertEqual(payload["total_tasks"], 2)
        self.assertEqual(payload["failed_tasks"], 1)
        self.assertEqual(payload["backlog_tasks"], 1)
        self.assertAlmostEqual(float(payload["failure_rate"]), 0.5, places=4)
        self.assertTrue(payload["has_alert"])
        self.assertTrue(any(item.get("metric") == "failure_rate" for item in payload.get("alerts") or []))

    def test_get_metrics_all_contains_backup_nas_paper_patent(self):
        self.store.create_task(
            task_id="metric_mix_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="pending",
            pending_files=["folder/a.pdf"],
        )
        self.backup_store.create_job_v2(kind="full", status="failed", message="failed")
        self._create_download_session(store=self.paper_store, session_id="metric_paper_1", status="failed")
        self._create_download_session(store=self.patent_store, session_id="metric_patent_1", status="running")
        self._create_paper_plag_report(report_id="metric_plag_1", status="running")
        self._create_upload_doc(doc_status="pending")

        with self._client() as client:
            resp = client.get("/api/tasks/metrics?kind=all")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "all")
        self.assertEqual(payload["total_tasks"], 6)
        metrics_by_kind = payload.get("metrics_by_kind") or {}
        self.assertIn("nas_import", metrics_by_kind)
        self.assertIn("backup_job", metrics_by_kind)
        self.assertIn("paper_download", metrics_by_kind)
        self.assertIn("patent_download", metrics_by_kind)
        self.assertIn("paper_plagiarism", metrics_by_kind)
        self.assertIn("knowledge_upload", metrics_by_kind)

    def test_get_metrics_for_knowledge_upload_kind(self):
        self._create_upload_doc(doc_status="pending")
        self._create_upload_doc(doc_status="rejected")

        with self._client() as client:
            resp = client.get("/api/tasks/metrics?kind=knowledge_upload")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "knowledge_upload")
        self.assertEqual(payload["total_tasks"], 2)
        self.assertEqual(payload["backlog_tasks"], 1)
        self.assertEqual(payload["failed_tasks"], 1)

    def test_get_metrics_for_paper_plagiarism_kind(self):
        self._create_paper_plag_report(report_id="plag_metric_1", status="running")
        self._create_paper_plag_report(report_id="plag_metric_2", status="failed")

        with self._client() as client:
            resp = client.get("/api/tasks/metrics?kind=paper_plagiarism")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "paper_plagiarism")
        self.assertEqual(payload["total_tasks"], 2)
        self.assertEqual(payload["backlog_tasks"], 1)
        self.assertEqual(payload["failed_tasks"], 1)

    def test_get_metrics_for_collection_kind(self):
        self._create_download_session(store=self.paper_store, session_id="paper_metric_collection_1", status="running")
        self._create_download_session(store=self.patent_store, session_id="patent_metric_collection_1", status="failed")

        with self._client() as client:
            resp = client.get("/api/tasks/metrics?kind=collection")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "collection")
        self.assertEqual(payload["total_tasks"], 2)
        self.assertEqual(payload["backlog_tasks"], 1)
        self.assertEqual(payload["failed_tasks"], 1)
        metrics_by_kind = payload.get("metrics_by_kind") or {}
        self.assertIn("paper_download", metrics_by_kind)
        self.assertIn("patent_download", metrics_by_kind)

    def test_list_tasks_all_contains_backup_nas_paper_patent(self):
        self.store.create_task(
            task_id="list_mix_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="pending",
            pending_files=["folder/a.pdf"],
        )
        self.backup_store.create_job_v2(kind="full", status="failed", message="failed")
        self._create_download_session(store=self.paper_store, session_id="list_paper_1", status="failed")
        self._create_download_session(store=self.patent_store, session_id="list_patent_1", status="running")
        self._create_paper_plag_report(report_id="list_plag_1", status="running")
        self._create_upload_doc(doc_status="pending")

        with self._client() as client:
            resp = client.get("/api/tasks?kind=all&limit=20")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "all")
        self.assertEqual(payload["limit"], 20)
        self.assertEqual(payload["status_filter"], [])
        self.assertEqual(payload["total_tasks"], 6)
        kinds = {str(item.get("task_kind") or "") for item in (payload.get("tasks") or [])}
        self.assertIn("nas_import", kinds)
        self.assertIn("backup_job", kinds)
        self.assertIn("paper_download", kinds)
        self.assertIn("patent_download", kinds)
        self.assertIn("paper_plagiarism", kinds)
        self.assertIn("knowledge_upload", kinds)

    def test_list_tasks_for_knowledge_upload_kind(self):
        pending_id = self._create_upload_doc(doc_status="pending")
        approved_id = self._create_upload_doc(doc_status="approved")

        with self._client() as client:
            resp = client.get("/api/tasks?kind=knowledge_upload&limit=20")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "knowledge_upload")
        tasks = payload.get("tasks") or []
        self.assertGreaterEqual(len(tasks), 2)
        task_ids = {str(item.get("task_id") or "") for item in tasks}
        self.assertIn(pending_id, task_ids)
        self.assertIn(approved_id, task_ids)
        self.assertTrue(all(str(item.get("task_kind") or "") == "knowledge_upload" for item in tasks))

    def test_list_tasks_for_paper_plagiarism_kind(self):
        first_id = self._create_paper_plag_report(report_id="list_plag_kind_1", status="running")
        second_id = self._create_paper_plag_report(report_id="list_plag_kind_2", status="completed")

        with self._client() as client:
            resp = client.get("/api/tasks?kind=paper_plagiarism&limit=20")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "paper_plagiarism")
        tasks = payload.get("tasks") or []
        self.assertGreaterEqual(len(tasks), 2)
        task_ids = {str(item.get("task_id") or "") for item in tasks}
        self.assertIn(first_id, task_ids)
        self.assertIn(second_id, task_ids)
        self.assertTrue(all(str(item.get("task_kind") or "") == "paper_plagiarism" for item in tasks))

    def test_list_tasks_for_collection_kind(self):
        first_id = "paper_list_collection_1"
        second_id = "patent_list_collection_1"
        self._create_download_session(store=self.paper_store, session_id=first_id, status="running")
        self._create_download_session(store=self.patent_store, session_id=second_id, status="completed")

        with self._client() as client:
            resp = client.get("/api/tasks?kind=collection&limit=20")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "collection")
        tasks = payload.get("tasks") or []
        self.assertGreaterEqual(len(tasks), 2)
        task_ids = {str(item.get("task_id") or "") for item in tasks}
        self.assertIn(first_id, task_ids)
        self.assertIn(second_id, task_ids)
        task_kinds = {str(item.get("task_kind") or "") for item in tasks}
        self.assertEqual(task_kinds, {"paper_download", "patent_download"})

    def test_list_tasks_status_filter_failed(self):
        self.store.create_task(
            task_id="list_status_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="pending",
            pending_files=["folder/a.pdf"],
        )
        self.backup_store.create_job_v2(kind="incremental", status="failed", message="failed")

        with self._client() as client:
            resp = client.get("/api/tasks?kind=all&status=failed")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["task_kind"], "all")
        self.assertEqual(payload["status_filter"], ["failed"])
        tasks = payload.get("tasks") or []
        self.assertEqual(payload["total_tasks"], len(tasks))
        self.assertGreaterEqual(len(tasks), 1)
        self.assertTrue(all(str(item.get("status") or "") == "failed" for item in tasks))

    def test_list_tasks_invalid_status_filter_returns_400(self):
        with self._client() as client:
            resp = client.get("/api/tasks?status=unknown")

        self.assertEqual(resp.status_code, 400)

    def test_metric_alert_logs_are_deduplicated_across_kinds(self):
        self.store.create_task(
            task_id="metric_alert_nas",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            status="pending",
            pending_files=["folder/a.pdf"],
        )
        self.backup_store.create_job_v2(kind="incremental", status="running", message="running")

        with patch.object(task_control_module.settings, "TASK_ALERT_BACKLOG_THRESHOLD", 1), patch.object(
            task_control_module.settings, "TASK_ALERT_LOG_COOLDOWN_SECONDS", 300
        ), patch.object(task_control_module.logger, "warning") as warning_mock:
            with self._client() as client:
                self.assertEqual(client.get("/api/tasks/metrics?kind=nas_import").status_code, 200)
                self.assertEqual(client.get("/api/tasks/metrics?kind=all").status_code, 200)
                self.assertEqual(client.get("/api/tasks/metrics?kind=nas_import").status_code, 200)
                self.assertEqual(client.get("/api/tasks/metrics?kind=all").status_code, 200)

        self.assertEqual(warning_mock.call_count, 2)

    def test_metrics_endpoint_uses_cache_within_ttl(self):
        self.backup_store.create_job_v2(kind="incremental", status="running", message="running")

        with patch.object(task_control_module.settings, "TASK_METRICS_CACHE_TTL_MS", 3000), patch.object(
            self.backup_store, "list_jobs", wraps=self.backup_store.list_jobs
        ) as list_jobs_mock:
            with self._client() as client:
                self.assertEqual(client.get("/api/tasks/metrics?kind=backup_job").status_code, 200)
                self.assertEqual(client.get("/api/tasks/metrics?kind=backup_job").status_code, 200)

        self.assertEqual(list_jobs_mock.call_count, 1)

    def test_non_admin_is_forbidden(self):
        self.store.create_task(
            task_id="task_auth_1",
            folder_path="folder",
            kb_ref="kb",
            total_files=1,
            pending_files=["folder/a.pdf"],
            status="pending",
        )

        with self._client(is_admin=False) as client:
            resp = client.get("/api/tasks/task_auth_1")
            list_resp = client.get("/api/tasks")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(list_resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
