import os
import sqlite3
import time
import unittest
from types import SimpleNamespace

from backend.app.core.config import settings
from backend.database.schema.ensure import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.audit_log_store import AuditLogStore
from backend.services.document_control import DocumentControlService
from backend.services.document_control_scheduler import DocumentControlScheduler
from backend.services.notification import NotificationManager, NotificationStore
from backend.services.training_compliance import TrainingComplianceService
from backend.tests.test_document_control_service_unit import _KbStore, _RagflowService, _UploadFile, _UserStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestDocumentControlSchedulerUnit(unittest.TestCase):
    def setUp(self):
        self._temp_dir = make_temp_dir(prefix="ragflowauth_doc_control_scheduler")
        self._db_path = os.path.join(str(self._temp_dir), "auth.db")
        self._old_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = str(self._temp_dir / "uploads")
        ensure_schema(self._db_path)
        self.notification_manager = NotificationManager(store=NotificationStore(db_path=self._db_path))
        self.notification_manager.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="站内信",
            enabled=True,
            config={},
        )
        self.training_service = TrainingComplianceService(db_path=self._db_path)
        self.user_store = _UserStore(
            {
                "reviewer-1": SimpleNamespace(user_id="reviewer-1", username="reviewer", status="active"),
                "cosigner-1": SimpleNamespace(user_id="cosigner-1", username="cosigner1", status="active"),
                "cosigner-2": SimpleNamespace(user_id="cosigner-2", username="cosigner2", status="active"),
                "approver-1": SimpleNamespace(user_id="approver-1", username="approver", status="active"),
                "standardizer-1": SimpleNamespace(user_id="standardizer-1", username="standardizer", status="active"),
            }
        )
        self.deps = SimpleNamespace(
            kb_store=_KbStore(self._db_path),
            ragflow_service=_RagflowService(),
            audit_log_store=AuditLogStore(db_path=self._db_path),
            training_compliance_service=self.training_service,
            notification_manager=self.notification_manager,
            org_structure_manager=None,
            user_store=self.user_store,
        )
        self.service = DocumentControlService.from_deps(self.deps)
        for document_type in ("urs", "sop"):
            self.service.upsert_document_type_workflow(
                document_type=document_type,
                name=f"{document_type} workflow",
                steps=[
                    {
                        "step_type": "cosign",
                        "approval_rule": "all",
                        "member_source": "fixed",
                        "timeout_reminder_minutes": 60,
                        "approver_user_ids": ["cosigner-1", "cosigner-2"],
                    },
                    {
                        "step_type": "approve",
                        "approval_rule": "all",
                        "member_source": "fixed",
                        "timeout_reminder_minutes": 60,
                        "approver_user_ids": ["approver-1"],
                    },
                    {
                        "step_type": "standardize_review",
                        "approval_rule": "all",
                        "member_source": "fixed",
                        "timeout_reminder_minutes": 60,
                        "approver_user_ids": ["standardizer-1"],
                    },
                ],
            )

    def tearDown(self):
        settings.UPLOAD_DIR = self._old_upload_dir
        cleanup_dir(self._temp_dir)

    def test_run_once_sends_overdue_approval_reminder(self):
        ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="reviewer-1"),
            user=SimpleNamespace(user_id="reviewer-1", username="reviewer", company_id=None, department_id=None),
        )
        created = self.service.create_document(
            doc_code="DOC-SCHED-001",
            title="Scheduler",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("scheduler.pdf", b"%PDF-1.4 scheduler\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        self.service.submit_revision_for_approval(
            controlled_revision_id=revision_id,
            ctx=ctx,
            note="submit",
        )

        conn = connect_sqlite(self._db_path)
        try:
            past_ms = int(time.time() * 1000) - 61 * 60 * 1000
            conn.execute(
                """
                UPDATE operation_approval_request_steps
                SET activated_at_ms = ?
                WHERE request_id = (
                    SELECT approval_request_id FROM controlled_revisions WHERE controlled_revision_id = ?
                )
                  AND step_no = 1
                """,
                (past_ms, revision_id),
            )
            conn.commit()
        finally:
            conn.close()

        scheduler = DocumentControlScheduler(deps=self.deps, interval_seconds=60)
        result = scheduler.run_once()
        self.assertEqual(result["reminded"], 2)
        refreshed = self.service.get_document(controlled_document_id=created.controlled_document_id).current_revision
        self.assertIsNotNone(refreshed.current_approval_step_last_reminded_at_ms)

    def test_approval_revision_ids_skips_db_without_controlled_revisions_table(self):
        missing_db_path = os.path.join(str(self._temp_dir), "missing.db")
        sqlite3.connect(missing_db_path).close()
        deps = SimpleNamespace(kb_store=SimpleNamespace(db_path=missing_db_path))
        scheduler = DocumentControlScheduler(deps=self.deps, interval_seconds=60)

        revision_ids = scheduler._approval_revision_ids(deps)

        self.assertEqual(revision_ids, [])


if __name__ == "__main__":
    unittest.main()
