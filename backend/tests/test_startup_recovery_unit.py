import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import backend.app.modules.data_security.runner as backup_runner
from backend.database.schema.ensure import ensure_schema
from backend.services.data_security_store import DataSecurityStore
from backend.services.paper_download.manager import PaperDownloadManager
from backend.services.paper_download.store import PaperDownloadStore
from backend.services.patent_download.manager import PatentDownloadManager
from backend.services.patent_download.store import PatentDownloadStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestStartupRecoveryUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_startup_recovery")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def _deps(self):
        return SimpleNamespace(
            paper_download_store=PaperDownloadStore(db_path=self.db_path),
            patent_download_store=PatentDownloadStore(db_path=self.db_path),
        )

    def test_download_session_recovery_converges_running_and_stopping(self):
        deps = self._deps()
        paper_store = deps.paper_download_store
        patent_store = deps.patent_download_store

        paper_store.create_session(
            session_id="paper_running_1",
            created_by="u1",
            keyword_text="alpha",
            keywords=["alpha"],
            use_and=True,
            sources={"arxiv": {"enabled": True, "limit": 3}},
            status="running",
        )
        paper_store.create_session(
            session_id="paper_stopping_1",
            created_by="u1",
            keyword_text="beta",
            keywords=["beta"],
            use_and=False,
            sources={"arxiv": {"enabled": True, "limit": 3}},
            status="stopping",
        )
        patent_store.create_session(
            session_id="patent_pending_1",
            created_by="u2",
            keyword_text="gamma",
            keywords=["gamma"],
            use_and=True,
            sources={"uspto": {"enabled": True, "limit": 3}},
            status="pending",
        )

        paper_summary = PaperDownloadManager(deps).recover_startup_sessions(limit=100)
        patent_summary = PatentDownloadManager(deps).recover_startup_sessions(limit=100)

        self.assertEqual(paper_summary["scanned"], 2)
        self.assertEqual(paper_summary["failed"], 1)
        self.assertEqual(paper_summary["stopped"], 1)
        self.assertEqual(patent_summary["scanned"], 1)
        self.assertEqual(patent_summary["failed"], 1)
        self.assertEqual(patent_summary["stopped"], 0)

        self.assertEqual(paper_store.get_session("paper_running_1").status, "failed")
        self.assertEqual(paper_store.get_session("paper_stopping_1").status, "stopped")
        self.assertEqual(patent_store.get_session("patent_pending_1").status, "failed")

    def test_backup_recovery_converges_canceling_job(self):
        store = DataSecurityStore(db_path=self.db_path)
        job = store.create_job_v2(kind="incremental", status="canceling", message="canceling")

        with patch.object(
            backup_runner,
            "DataSecurityStore",
            side_effect=lambda: DataSecurityStore(db_path=self.db_path),
        ):
            summary = backup_runner.recover_startup_jobs(limit=10)

        self.assertEqual(summary["scanned"], 1)
        self.assertEqual(summary["canceled"], 1)
        self.assertEqual(summary["resumed"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(store.get_job(job.id).status, "canceled")

    def test_backup_recovery_resumes_one_active_job_and_fails_duplicate(self):
        store = DataSecurityStore(db_path=self.db_path)
        older = store.create_job_v2(kind="incremental", status="queued", message="older")
        newer = store.create_job_v2(kind="full", status="running", message="newer")

        with patch.object(
            backup_runner,
            "DataSecurityStore",
            side_effect=lambda: DataSecurityStore(db_path=self.db_path),
        ), patch.object(backup_runner, "start_job_if_idle", return_value=newer.id) as start_mock:
            summary = backup_runner.recover_startup_jobs(limit=10)

        self.assertEqual(summary["scanned"], 2)
        self.assertEqual(summary["resumed"], 1)
        self.assertEqual(summary["canceled"], 0)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(start_mock.call_count, 1)
        self.assertEqual(store.get_job(older.id).status, "failed")
        self.assertEqual(store.get_job(newer.id).status, "running")


if __name__ == "__main__":
    unittest.main()
