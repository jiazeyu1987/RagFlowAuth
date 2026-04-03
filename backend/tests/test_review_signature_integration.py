import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.review.routes.approve import approve_documents_batch
from backend.app.modules.review.routes.overwrite import approve_document_overwrite
from backend.database.schema.ensure import ensure_schema
from backend.models.document import BatchDocumentReviewRequest, DocumentOverwriteReviewRequest
from backend.services.approval import ApprovalWorkflowService, ApprovalWorkflowStore
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.kb import KbStore
from backend.services.training_compliance import TrainingComplianceService
from backend.services.users import hash_password
from backend.tests._training_test_utils import qualify_user_for_action
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


SIGN_PASSWORD = "SignPass123"


class _RagflowService:
    def __init__(self):
        self.deleted = []
        self.uploaded = []

    def delete_document(self, ragflow_doc_id, dataset_name=None):
        self.deleted.append((ragflow_doc_id, dataset_name))
        return True

    def upload_document_blob(self, **kwargs):
        self.uploaded.append(kwargs)
        return "rag-new-1"

    def parse_document(self, **kwargs):  # noqa: ARG002
        return True


class _DeletionLogStore:
    def __init__(self):
        self.calls = []

    def log_deletion(self, **kwargs):
        self.calls.append(kwargs)


class _Request:
    def __init__(self, request_id: str, client_ip: str = "127.0.0.1"):
        self.state = SimpleNamespace(request_id=request_id)
        self.client = SimpleNamespace(host=client_ip)


def _snapshot(kb_id: str) -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=False,
        can_upload=False,
        can_review=True,
        can_download=False,
        can_copy=False,
        can_delete=False,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
        kb_scope=ResourceScope.SET,
        kb_names=frozenset({kb_id}),
        chat_scope=ResourceScope.NONE,
        chat_ids=frozenset(),
        tool_scope=ResourceScope.NONE,
        tool_ids=frozenset(),
    )


def _issue_sign_token(signature_service: ElectronicSignatureService, user) -> str:
    challenge = signature_service.issue_challenge(user=user, password=SIGN_PASSWORD)
    return str(challenge["sign_token"])


class TestReviewSignatureIntegration(unittest.TestCase):
    def test_batch_approve_reuses_single_signature_challenge(self):
        td = make_temp_dir(prefix="ragflowauth_review_signature_batch")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            kb_store = KbStore(db_path=db_path)
            audit_store = AuditLogStore(db_path=db_path)
            audit_mgr = AuditLogManager(store=audit_store)
            signature_store = ElectronicSignatureStore(db_path=db_path)
            signature_service = ElectronicSignatureService(store=signature_store)
            workflow_service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            workflow_service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A Workflow",
                steps=[
                    {"step_no": 1, "step_name": "Step 1", "approver_user_id": "reviewer-1"},
                    {"step_no": 2, "step_name": "Step 2", "approver_user_id": "reviewer-1"},
                ],
            )
            qualify_user_for_action(db_path, user_id="reviewer-1", action_code="document_review")

            file_a = Path(td) / "doc-a.txt"
            file_b = Path(td) / "doc-b.txt"
            file_a.write_text("doc-a", encoding="utf-8")
            file_b.write_text("doc-b", encoding="utf-8")
            doc_a = kb_store.create_document(
                filename="doc-a.txt",
                file_path=str(file_a),
                file_size=file_a.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )
            doc_b = kb_store.create_document(
                filename="doc-b.txt",
                file_path=str(file_b),
                file_size=file_b.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )

            user = SimpleNamespace(
                user_id="reviewer-1",
                username="bob",
                company_id=1,
                department_id=2,
                role="reviewer",
                status="active",
                password_hash=hash_password(SIGN_PASSWORD),
            )
            deps = SimpleNamespace(
                kb_store=kb_store,
                ragflow_service=_RagflowService(),
                audit_log_manager=audit_mgr,
                approval_workflow_service=workflow_service,
                electronic_signature_service=signature_service,
                training_compliance_service=TrainingComplianceService(db_path=db_path),
            )
            ctx = SimpleNamespace(
                deps=deps,
                payload=SimpleNamespace(sub="reviewer-1"),
                user=user,
                snapshot=_snapshot("kb-a"),
            )

            body = BatchDocumentReviewRequest(
                doc_ids=[doc_a.doc_id, doc_b.doc_id],
                sign_token=_issue_sign_token(signature_service, user),
                signature_meaning="Batch document approval",
                signature_reason="Approve both documents in one batch",
            )

            result = approve_documents_batch(body, _Request("rid-batch"), ctx)

            self.assertEqual(result.success_count, 2)
            sig_a = signature_service.latest_by_record(record_type="knowledge_document_review", record_id=doc_a.doc_id)
            sig_b = signature_service.latest_by_record(record_type="knowledge_document_review", record_id=doc_b.doc_id)
            self.assertIsNotNone(sig_a)
            self.assertIsNotNone(sig_b)
            self.assertEqual(sig_a.sign_token_id, sig_b.sign_token_id)
            self.assertEqual(sig_a.signed_by, "reviewer-1")
            self.assertEqual(sig_a.signed_by_username, "bob")
            self.assertEqual(sig_a.meaning, "Batch document approval")
            self.assertEqual(sig_a.reason, "Approve both documents in one batch")
            self.assertEqual(sig_a.action, "document_approve_step")
            self.assertGreater(sig_a.signed_at_ms, 0)
            self.assertTrue(signature_service.verify_signature(signature_id=sig_a.signature_id))
            self.assertTrue(signature_service.verify_signature(signature_id=sig_b.signature_id))
            total, rows = audit_store.list_events(action="document_approve_step", request_id="rid-batch")
            self.assertEqual(total, 2)
            self.assertTrue(all(row.signature_id for row in rows))
        finally:
            cleanup_dir(td)

    def test_overwrite_approval_writes_signature_record(self):
        td = make_temp_dir(prefix="ragflowauth_review_signature_overwrite")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            kb_store = KbStore(db_path=db_path)
            audit_store = AuditLogStore(db_path=db_path)
            audit_mgr = AuditLogManager(store=audit_store)
            signature_store = ElectronicSignatureStore(db_path=db_path)
            signature_service = ElectronicSignatureService(store=signature_store)
            workflow_service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            workflow_service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A Workflow",
                steps=[
                    {"step_no": 1, "step_name": "Step 1", "approver_user_id": "seed-reviewer"},
                    {"step_no": 2, "step_name": "Step 2", "approver_user_id": "reviewer-1"},
                ],
            )
            qualify_user_for_action(db_path, user_id="reviewer-1", action_code="document_review")

            old_path = Path(td) / "old.txt"
            new_path = Path(td) / "new.txt"
            old_path.write_text("old version", encoding="utf-8")
            new_path.write_text("new version", encoding="utf-8")

            old_doc = kb_store.create_document(
                filename="same.txt",
                file_path=str(old_path),
                file_size=old_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="approved",
            )
            kb_store.update_document_status(
                doc_id=old_doc.doc_id,
                status="approved",
                reviewed_by="seed-user",
                review_notes="seed approved",
                ragflow_doc_id="rag-old-1",
            )

            new_doc = kb_store.create_document(
                filename="same.txt",
                file_path=str(new_path),
                file_size=new_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )
            workflow_service.approval_progress(doc=new_doc)
            workflow_service.approve_step(
                doc=new_doc,
                actor="seed-reviewer",
                actor_user=SimpleNamespace(
                    user_id="seed-reviewer",
                    username="seed",
                    company_id=1,
                    department_id=2,
                    status="active",
                    role="reviewer",
                    group_ids=[],
                ),
                notes="advance to final step",
                final=False,
            )

            ragflow_service = _RagflowService()
            deletion_log_store = _DeletionLogStore()
            user = SimpleNamespace(
                user_id="reviewer-1",
                username="bob",
                company_id=1,
                department_id=2,
                role="reviewer",
                status="active",
                password_hash=hash_password(SIGN_PASSWORD),
            )
            deps = SimpleNamespace(
                kb_store=kb_store,
                ragflow_service=ragflow_service,
                deletion_log_store=deletion_log_store,
                audit_log_manager=audit_mgr,
                approval_workflow_service=workflow_service,
                electronic_signature_service=signature_service,
                training_compliance_service=TrainingComplianceService(db_path=db_path),
            )
            ctx = SimpleNamespace(
                deps=deps,
                payload=SimpleNamespace(sub="reviewer-1"),
                user=user,
                snapshot=_snapshot("kb-a"),
            )

            response = approve_document_overwrite(
                new_doc.doc_id,
                _Request("rid-overwrite"),
                ctx,
                DocumentOverwriteReviewRequest(
                    replace_doc_id=old_doc.doc_id,
                    sign_token=_issue_sign_token(signature_service, user),
                    signature_meaning="Document supersede approval",
                    signature_reason="Replace approved document with revised version",
                ),
            )

            self.assertEqual(response.status, "approved")
            self.assertIsNotNone(response.signature_id)
            self.assertEqual(len(ragflow_service.deleted), 1)
            self.assertEqual(len(ragflow_service.uploaded), 1)
            self.assertEqual(len(deletion_log_store.calls), 1)
            old_after = kb_store.get_document(old_doc.doc_id)
            new_after = kb_store.get_document(new_doc.doc_id)
            self.assertIsNotNone(old_after)
            self.assertIsNotNone(new_after)
            self.assertFalse(old_after.is_current)
            self.assertEqual(old_after.effective_status, "superseded")
            self.assertEqual(old_after.superseded_by_doc_id, new_after.doc_id)
            self.assertTrue(Path(old_after.file_path).exists())
            self.assertEqual(new_after.version_no, 2)
            self.assertEqual(new_after.previous_doc_id, old_after.doc_id)
            self.assertEqual(kb_store.get_current_document(old_doc.doc_id).doc_id, new_after.doc_id)
            self.assertEqual([item.doc_id for item in kb_store.list_versions(new_after.doc_id)], [new_after.doc_id, old_after.doc_id])

            signature = signature_service.get_signature(response.signature_id)
            self.assertEqual(signature.action, "document_supersede")
            self.assertTrue(signature_service.verify_signature(signature_id=signature.signature_id))
            total, rows = audit_store.list_events(action="document_supersede", request_id="rid-overwrite")
            self.assertEqual(total, 1)
            self.assertEqual(rows[0].signature_id, response.signature_id)
        finally:
            cleanup_dir(td)
