import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.core.config import settings
from backend.database.schema.ensure import ensure_schema
from backend.services.data_security_store import DataSecurityStore
from backend.services.kb_store import KbStore
from backend.services.nas_task_store import NasTaskStore
from backend.services.paper_download.store import PaperDownloadStore
from backend.services.paper_plag_store import PaperPlagStore
from backend.services.patent_download.store import PatentDownloadStore
from backend.services.unified_task_quota_service import UnifiedTaskQuotaService
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestUnifiedTaskQuotaServiceUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_task_quota")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.deps = SimpleNamespace(
            nas_task_store=NasTaskStore(db_path=self.db_path),
            data_security_store=DataSecurityStore(db_path=self.db_path),
            paper_download_store=PaperDownloadStore(db_path=self.db_path),
            patent_download_store=PatentDownloadStore(db_path=self.db_path),
            kb_store=KbStore(db_path=self.db_path),
            paper_plag_store=PaperPlagStore(db_path=self.db_path),
        )
        self.service = UnifiedTaskQuotaService()

    def tearDown(self):
        cleanup_dir(self._tmp)

    @staticmethod
    def _seed_download_session(*, store, session_id: str, created_by: str, status: str) -> None:
        store.create_session(
            session_id=session_id,
            created_by=created_by,
            keyword_text="alpha",
            keywords=["alpha"],
            use_and=True,
            sources={"s1": {"enabled": True, "limit": 5}},
            status=status,
            source_errors={},
            source_stats={"s1": {"enabled": True, "limit": 5}},
        )

    def _seed_upload_doc(self, *, status: str, uploaded_by: str = "u1") -> None:
        self.deps.kb_store.create_document(
            filename="a.pdf",
            file_path="data/uploads/unit/a.pdf",
            file_size=16,
            mime_type="application/pdf",
            uploaded_by=uploaded_by,
            kb_id="kb1",
            status=status,
        )

    def _seed_paper_plag_report(self, *, report_id: str, status: str, created_by: str = "u1") -> None:
        self.deps.paper_plag_store.create_report(
            report_id=report_id,
            paper_id="paper_1",
            version_id=None,
            task_id=report_id,
            status=status,
            created_by_user_id=created_by,
        )

    def test_global_quota_exceeded(self):
        self._seed_download_session(
            store=self.deps.paper_download_store,
            session_id="paper_active_1",
            created_by="u1",
            status="running",
        )

        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 1), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 10
        ), patch.object(settings, "TASK_PATENT_DOWNLOAD_CONCURRENCY_LIMIT", 10):
            with self.assertRaises(RuntimeError):
                self.service.assert_can_start(
                    deps=self.deps,
                    actor_user_id="u2",
                    task_kind=UnifiedTaskQuotaService.PATENT_KIND,
                )

    def test_task_kind_quota_exceeded(self):
        self._seed_download_session(
            store=self.deps.paper_download_store,
            session_id="paper_active_2",
            created_by="u1",
            status="running",
        )

        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 10), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 10
        ), patch.object(settings, "TASK_PAPER_DOWNLOAD_CONCURRENCY_LIMIT", 1):
            with self.assertRaises(RuntimeError):
                self.service.assert_can_start(
                    deps=self.deps,
                    actor_user_id="u2",
                    task_kind=UnifiedTaskQuotaService.PAPER_KIND,
                )

    def test_user_quota_exceeded(self):
        self._seed_download_session(
            store=self.deps.paper_download_store,
            session_id="paper_active_3",
            created_by="u1",
            status="running",
        )

        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 10), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 1
        ), patch.object(settings, "TASK_PATENT_DOWNLOAD_CONCURRENCY_LIMIT", 10):
            with self.assertRaises(RuntimeError):
                self.service.assert_can_start(
                    deps=self.deps,
                    actor_user_id="u1",
                    task_kind=UnifiedTaskQuotaService.PATENT_KIND,
                )

    def test_backup_task_kind_quota_exceeded(self):
        self.deps.data_security_store.create_job_v2(kind="incremental", status="queued", message="queued")

        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 10), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 10
        ), patch.object(settings, "TASK_BACKUP_CONCURRENCY_LIMIT", 1):
            with self.assertRaises(RuntimeError):
                self.service.assert_can_start(
                    deps=self.deps,
                    actor_user_id="admin_u1",
                    task_kind=UnifiedTaskQuotaService.BACKUP_KIND,
                )

    def test_quota_allows_when_under_limits(self):
        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 5), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 5
        ), patch.object(settings, "TASK_PAPER_DOWNLOAD_CONCURRENCY_LIMIT", 2):
            snapshot = self.service.assert_can_start(
                deps=self.deps,
                actor_user_id="u1",
                task_kind=UnifiedTaskQuotaService.PAPER_KIND,
            )

        self.assertEqual(snapshot.global_active, 0)
        self.assertEqual(snapshot.user_active, 0)

    def test_upload_task_kind_quota_exceeded(self):
        self._seed_upload_doc(status="pending", uploaded_by="u1")

        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 10), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 10
        ), patch.object(settings, "TASK_UPLOAD_CONCURRENCY_LIMIT", 1):
            with self.assertRaises(RuntimeError):
                self.service.assert_can_start(
                    deps=self.deps,
                    actor_user_id="u2",
                    task_kind=UnifiedTaskQuotaService.UPLOAD_KIND,
                )

    def test_paper_plag_task_kind_quota_exceeded(self):
        self._seed_paper_plag_report(report_id="plag_q_1", status="running", created_by="u1")

        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 10), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 10
        ), patch.object(settings, "TASK_PAPER_PLAG_CONCURRENCY_LIMIT", 1):
            with self.assertRaises(RuntimeError):
                self.service.assert_can_start(
                    deps=self.deps,
                    actor_user_id="u2",
                    task_kind=UnifiedTaskQuotaService.PAPER_PLAG_KIND,
                )

    def test_collection_task_kind_quota_exceeded_across_paper_and_patent(self):
        self._seed_download_session(
            store=self.deps.paper_download_store,
            session_id="paper_active_collection_1",
            created_by="u1",
            status="running",
        )

        with patch.object(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 10), patch.object(
            settings, "TASK_USER_CONCURRENCY_LIMIT", 10
        ), patch.object(settings, "TASK_COLLECTION_CONCURRENCY_LIMIT", 1), patch.object(
            settings, "TASK_PATENT_DOWNLOAD_CONCURRENCY_LIMIT", 10
        ):
            with self.assertRaises(RuntimeError):
                self.service.assert_can_start(
                    deps=self.deps,
                    actor_user_id="u2",
                    task_kind=UnifiedTaskQuotaService.PATENT_KIND,
                )


if __name__ == "__main__":
    unittest.main()
