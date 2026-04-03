import os
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.review.routes.approve import _approve_document_impl
from backend.app.modules.review.routes.reject import _reject_document_impl
from backend.database.schema.ensure import ensure_schema
from backend.models.document import DocumentReviewRequest
from backend.services.approval import ApprovalWorkflowService, ApprovalWorkflowStore
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.training_compliance import TrainingComplianceService
from backend.services.users import hash_password
from backend.tests._training_test_utils import qualify_user_for_action
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


SIGN_PASSWORD = "SignPass123"


class _Doc:
    def __init__(
        self,
        *,
        doc_id: str,
        filename: str,
        file_path: str,
        status: str,
        kb_id: str,
        kb_dataset_id: str | None = None,
        kb_name: str | None = None,
    ):
        now_ms = int(time.time() * 1000)
        self.doc_id = doc_id
        self.filename = filename
        self.file_size = 1
        self.mime_type = "text/plain"
        self.uploaded_by = "uploader-1"
        self.status = status
        self.uploaded_at_ms = now_ms
        self.reviewed_by = None
        self.reviewed_at_ms = None
        self.review_notes = None
        self.ragflow_doc_id = None
        self.kb_id = kb_id
        self.kb_dataset_id = kb_dataset_id
        self.kb_name = kb_name
        self.file_path = file_path


class _KbStore:
    def __init__(self, docs: dict[str, _Doc], db_path: str):
        self._docs = docs
        self.db_path = db_path

    def get_document(self, doc_id: str):
        return self._docs.get(str(doc_id))

    def update_document_status(
        self,
        *,
        doc_id: str,
        status: str,
        reviewed_by: str | None,
        review_notes: str | None,
        ragflow_doc_id: str | None = None,
    ):
        doc = self._docs[str(doc_id)]
        doc.status = status
        doc.reviewed_by = reviewed_by
        doc.review_notes = review_notes
        doc.reviewed_at_ms = int(time.time() * 1000)
        if ragflow_doc_id is not None:
            doc.ragflow_doc_id = ragflow_doc_id
        return doc


class _RagflowService:
    def upload_document_blob(self, **kwargs):  # noqa: ARG002
        return "rag-doc-1"

    def parse_document(self, **kwargs):  # noqa: ARG002
        return True


class _OrgCompany:
    name = "Acme"


class _OrgDepartment:
    name = "R&D"


class _OrgStore:
    def get_company(self, company_id):  # noqa: ARG002
        return _OrgCompany()

    def get_department(self, department_id):  # noqa: ARG002
        return _OrgDepartment()


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


def _issue_review_request(
    signature_service: ElectronicSignatureService,
    user,
    *,
    meaning: str,
    reason: str,
    review_notes: str | None = None,
) -> DocumentReviewRequest:
    challenge = signature_service.issue_challenge(user=user, password=SIGN_PASSWORD)
    return DocumentReviewRequest(
        sign_token=challenge["sign_token"],
        signature_meaning=meaning,
        signature_reason=reason,
        review_notes=review_notes,
    )


class TestReviewAuditIntegration(unittest.TestCase):
    def test_approve_and_reject_emit_audit_events(self):
        td = make_temp_dir(prefix="ragflowauth_review_audit")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            audit_store = AuditLogStore(db_path=db_path)
            audit_mgr = AuditLogManager(store=audit_store)
            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))

            file_path = Path(td) / "doc-a.txt"
            file_path.write_text("ok", encoding="utf-8")
            doc_a = _Doc(
                doc_id="doc-a",
                filename="doc-a.txt",
                file_path=str(file_path),
                status="pending",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
            )
            doc_b = _Doc(
                doc_id="doc-b",
                filename="doc-b.txt",
                file_path=str(file_path),
                status="pending",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
            )
            kb_store = _KbStore({"doc-a": doc_a, "doc-b": doc_b}, db_path=db_path)
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
                org_directory_store=_OrgStore(),
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

            step_approved = _approve_document_impl(
                "doc-a",
                ctx,
                request=_Request("rid-approve"),
                review_data=_issue_review_request(
                    signature_service,
                    user,
                    meaning="Approve step",
                    reason="Approve workflow step 1",
                    review_notes="approve notes",
                ),
            )
            self.assertEqual(step_approved.status, "pending")
            self.assertEqual(step_approved.approval_status, "in_progress")
            self.assertEqual(step_approved.current_step_no, 2)
            self.assertIsNotNone(step_approved.signature_id)
            self.assertTrue(signature_service.verify_signature(signature_id=step_approved.signature_id))
            total_step, rows_step = audit_store.list_events(action="document_approve_step", request_id="rid-approve")
            self.assertEqual(total_step, 1)
            self.assertIsNotNone(rows_step[0].signature_id)
            self.assertEqual(rows_step[0].signature_id, step_approved.signature_id)
            self.assertIn('"current_step_no":1', rows_step[0].before_json or "")
            self.assertIn('"current_step_no":2', rows_step[0].after_json or "")

            approved = _approve_document_impl(
                "doc-a",
                ctx,
                request=_Request("rid-approve-final"),
                review_data=_issue_review_request(
                    signature_service,
                    user,
                    meaning="Approve final",
                    reason="Approve final document",
                    review_notes="approve notes final",
                ),
            )
            self.assertEqual(approved.status, "approved")
            self.assertEqual(approved.approval_status, "approved")
            self.assertIsNotNone(approved.signature_id)
            self.assertTrue(signature_service.verify_signature(signature_id=approved.signature_id))
            total_a, rows_a = audit_store.list_events(action="document_approve", request_id="rid-approve-final")
            self.assertEqual(total_a, 1)
            self.assertEqual(rows_a[0].resource_type, "knowledge_document")
            self.assertEqual(rows_a[0].resource_id, "doc-a")
            self.assertEqual(rows_a[0].reason, "Approve final document")
            self.assertEqual(rows_a[0].signature_id, approved.signature_id)
            self.assertIn('"status":"pending"', rows_a[0].before_json or "")
            self.assertIn('"status":"approved"', rows_a[0].after_json or "")

            rejected = _reject_document_impl(
                "doc-b",
                ctx,
                request=_Request("rid-reject"),
                review_data=_issue_review_request(
                    signature_service,
                    user,
                    meaning="Reject document",
                    reason="Reject pending document",
                    review_notes="reject notes",
                ),
            )
            self.assertEqual(rejected.status, "rejected")
            self.assertIsNotNone(rejected.signature_id)
            self.assertTrue(signature_service.verify_signature(signature_id=rejected.signature_id))
            total_r, rows_r = audit_store.list_events(action="document_reject", request_id="rid-reject")
            self.assertEqual(total_r, 1)
            self.assertEqual(rows_r[0].resource_type, "knowledge_document")
            self.assertEqual(rows_r[0].resource_id, "doc-b")
            self.assertEqual(rows_r[0].reason, "Reject pending document")
            self.assertEqual(rows_r[0].signature_id, rejected.signature_id)
            self.assertIn('"status":"pending"', rows_r[0].before_json or "")
            self.assertIn('"status":"rejected"', rows_r[0].after_json or "")
        finally:
            cleanup_dir(td)
