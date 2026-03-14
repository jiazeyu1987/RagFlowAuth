import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.authz import AuthContext, get_auth_context
from backend.app.modules.paper_plag.router import router as paper_plag_router
from backend.database.schema.ensure import ensure_schema
from backend.services.kb_store import KbStore
from backend.services.paper_plag_store import PaperPlagStore
from backend.services.system_feature_flag_store import FLAG_PAPER_PLAG_ENABLED, SystemFeatureFlagStore
import backend.services.paper_plagiarism_service as paper_plag_service_module
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestPaperPlagRouterUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_paper_plag_router")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = PaperPlagStore(db_path=self.db_path)
        self.feature_flag_store = SystemFeatureFlagStore(db_path=self.db_path)
        self.kb_store = KbStore(db_path=self.db_path)
        self.deps = SimpleNamespace(
            paper_plag_store=self.store,
            feature_flag_store=self.feature_flag_store,
            kb_store=self.kb_store,
        )

        self.app = FastAPI()
        self.app.include_router(paper_plag_router, prefix="/api")
        paper_plag_service_module._PLAG_QUEUE.clear()
        paper_plag_service_module._PLAG_RUNNING_REPORTS.clear()

    def tearDown(self):
        paper_plag_service_module._PLAG_QUEUE.clear()
        paper_plag_service_module._PLAG_RUNNING_REPORTS.clear()
        cleanup_dir(self._tmp)

    def _client(self) -> TestClient:
        ctx = AuthContext(
            deps=self.deps,
            payload=TokenPayload(sub="u1"),
            user=SimpleNamespace(user_id="u1"),
            snapshot=SimpleNamespace(is_admin=True),
        )
        self.app.dependency_overrides[get_auth_context] = lambda: ctx
        return TestClient(self.app)

    def _create_report(self, *, report_id: str, status: str = "pending", user_id: str = "u1") -> str:
        report = self.store.create_report(
            report_id=report_id,
            paper_id="paper_1",
            version_id=None,
            task_id=report_id,
            status=status,
            created_by_user_id=user_id,
        )
        return str(report.report_id)

    def test_start_report_returns_report_payload(self):
        with self._client() as client:
            resp = client.post(
                "/api/paper-plag/reports/start",
                json={
                    "paper_id": "paper_101",
                    "title": "paper title",
                    "content_text": "alpha beta gamma",
                    "sources": [{"source_doc_id": "s1", "content_text": "alpha gamma"}],
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        report = payload.get("report") or {}
        self.assertTrue(str(report.get("report_id") or "").strip())
        self.assertEqual(report.get("paper_id"), "paper_101")
        self.assertEqual(report.get("created_by_user_id"), "u1")
        self.assertIn(str(report.get("status") or ""), {"pending", "running", "completed"})

        persisted = self.store.get_report(str(report.get("report_id") or ""))
        self.assertIsNotNone(persisted)

    def test_get_report_not_found_returns_404(self):
        with self._client() as client:
            resp = client.get("/api/paper-plag/reports/not-exist")

        self.assertEqual(resp.status_code, 404)

    def test_list_reports_filters_status(self):
        self._create_report(report_id="plag_list_pending", status="pending")
        self._create_report(report_id="plag_list_failed", status="failed")

        with self._client() as client:
            resp = client.get("/api/paper-plag/reports?status=failed")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        items = payload.get("items") or []
        self.assertEqual(int(payload.get("total") or 0), 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get("report_id"), "plag_list_failed")

    def test_cancel_report_pending_to_canceled(self):
        report_id = self._create_report(report_id="plag_cancel_1", status="pending")

        with self._client() as client:
            resp = client.post(f"/api/paper-plag/reports/{report_id}/cancel")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        report = payload.get("report") or {}
        self.assertEqual(report.get("report_id"), report_id)
        self.assertEqual(report.get("status"), "canceled")

    def test_start_report_quota_exceeded_returns_409(self):
        with patch(
            "backend.app.modules.paper_plag.router.UnifiedTaskQuotaService.assert_can_start",
            side_effect=RuntimeError("task_quota_exceeded:task_kind:paper_plagiarism"),
        ):
            with self._client() as client:
                resp = client.post(
                    "/api/paper-plag/reports/start",
                    json={
                        "paper_id": "paper_102",
                        "title": "paper title",
                        "content_text": "alpha beta gamma",
                        "sources": [],
                    },
                )

        self.assertEqual(resp.status_code, 409)
        self.assertIn("task_quota_exceeded", str(resp.json().get("detail") or ""))

    def test_paper_plag_feature_disabled_returns_503(self):
        self.feature_flag_store.update_flags({FLAG_PAPER_PLAG_ENABLED: False}, actor_user_id="admin_u1")
        with self._client() as client:
            resp = client.post(
                "/api/paper-plag/reports/start",
                json={
                    "paper_id": "paper_102",
                    "title": "paper title",
                    "content_text": "alpha beta gamma",
                    "sources": [],
                },
            )
        self.assertEqual(resp.status_code, 503)
        self.assertIn("feature_disabled:paper_plag", str(resp.json().get("detail") or ""))

    def test_save_list_get_versions(self):
        with self._client() as client:
            save_first = client.post(
                "/api/paper-plag/papers/paper_v1/versions/save",
                json={"title": "v1", "content_text": "alpha beta", "note": "first"},
            )
            save_second = client.post(
                "/api/paper-plag/papers/paper_v1/versions/save",
                json={"title": "v2", "content_text": "alpha beta gamma", "note": "second"},
            )
            list_resp = client.get("/api/paper-plag/papers/paper_v1/versions?limit=10")

        self.assertEqual(save_first.status_code, 200)
        self.assertEqual(save_second.status_code, 200)
        self.assertEqual(list_resp.status_code, 200)
        listed = list_resp.json()
        self.assertEqual(listed.get("paper_id"), "paper_v1")
        self.assertGreaterEqual(int(listed.get("total") or 0), 2)
        items = listed.get("items") or []
        self.assertGreaterEqual(len(items), 2)
        latest_id = int(items[0].get("id") or 0)
        self.assertGreater(latest_id, 0)

        with self._client() as client:
            get_resp = client.get(f"/api/paper-plag/papers/paper_v1/versions/{latest_id}")
        self.assertEqual(get_resp.status_code, 200)
        version = (get_resp.json() or {}).get("version") or {}
        self.assertEqual(int(version.get("id") or 0), latest_id)

    def test_diff_and_rollback_versions(self):
        v1 = self.store.create_version(
            paper_id="paper_diff_1",
            title="v1",
            content_text="line-1\nline-2\nline-3",
            content_hash="h1",
            author_user_id="u1",
            note="v1",
        )
        v2 = self.store.create_version(
            paper_id="paper_diff_1",
            title="v2",
            content_text="line-1\nline-2-modified\nline-3\nline-4",
            content_hash="h2",
            author_user_id="u1",
            note="v2",
        )
        with self._client() as client:
            diff_resp = client.post(
                "/api/paper-plag/papers/paper_diff_1/versions/diff",
                json={"from_version_id": int(v1.id), "to_version_id": int(v2.id)},
            )
            rollback_resp = client.post(
                f"/api/paper-plag/papers/paper_diff_1/versions/{int(v1.id)}/rollback",
                json={"note": "manual rollback"},
            )

        self.assertEqual(diff_resp.status_code, 200)
        diff_payload = diff_resp.json()
        self.assertEqual(diff_payload.get("paper_id"), "paper_diff_1")
        self.assertGreaterEqual(int(diff_payload.get("added_lines") or 0), 1)
        self.assertGreaterEqual(int(diff_payload.get("removed_lines") or 0), 1)
        self.assertIsInstance(diff_payload.get("diff_preview"), list)

        self.assertEqual(rollback_resp.status_code, 200)
        rollback_payload = rollback_resp.json()
        self.assertEqual(rollback_payload.get("paper_id"), "paper_diff_1")
        restored_version = rollback_payload.get("version") or {}
        self.assertTrue(str(restored_version.get("note") or "").startswith("rollback_from_version="))

    def test_export_report_returns_attachment_and_persists_file_path(self):
        report_id = self._create_report(report_id="plag_export_1", status="completed")
        self.store.update_report(
            report_id,
            duplicate_rate=0.25,
            score=75.0,
            summary="max_similarity=25.0%",
            source_count=1,
        )
        self.store.replace_hits(
            report_id=report_id,
            hits=[
                {
                    "source_doc_id": "src-1",
                    "source_title": "source title",
                    "source_uri": "https://example.com/source-1",
                    "similarity_score": 0.25,
                    "start_offset": 0,
                    "end_offset": 10,
                    "snippet_text": "alpha beta",
                }
            ],
        )

        with self._client() as client:
            resp = client.get(f"/api/paper-plag/reports/{report_id}/export")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", str(resp.headers.get("content-disposition") or ""))
        self.assertIn(report_id, resp.text)
        self.assertIn("Paper Plagiarism Report", resp.text)

        persisted = self.store.get_report(report_id)
        self.assertIsNotNone(persisted)
        self.assertTrue(str(getattr(persisted, "report_file_path", "") or "").strip())
        self.assertTrue(os.path.exists(str(getattr(persisted, "report_file_path", "") or "")))


if __name__ == "__main__":
    unittest.main()
