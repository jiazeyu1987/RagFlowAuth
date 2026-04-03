import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.review.routes.approve import _approve_document_impl
from backend.app.modules.review.routes.reject import _reject_document_impl
from backend.database.schema.ensure import ensure_schema
from backend.models.document import DocumentReviewRequest
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
    def upload_document_blob(self, **kwargs):  # noqa: ARG002
        return "rag-doc-1"

    def parse_document(self, **kwargs):  # noqa: ARG002
        return True


class _Request:
    def __init__(self, request_id: str):
        self.state = SimpleNamespace(request_id=request_id)
        self.client = SimpleNamespace(host="127.0.0.1")


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


def _reviewer(user_id: str):
    return SimpleNamespace(
        user_id=user_id,
        username=user_id,
        company_id=1,
        department_id=10,
        password_hash=hash_password(SIGN_PASSWORD),
        status="active",
        role="reviewer",
        group_ids=[],
    )


def _review_request(signature_service: ElectronicSignatureService, user, *, reason: str):
    challenge = signature_service.issue_challenge(user=user, password=SIGN_PASSWORD)
    return DocumentReviewRequest(
        sign_token=challenge["sign_token"],
        signature_meaning="Document review",
        signature_reason=reason,
        review_notes=reason,
    )


class TestReviewAssignmentIntegrationUnit(unittest.TestCase):
    def test_non_current_actor_is_rejected_without_side_effects(self):
        td = make_temp_dir(prefix="ragflowauth_review_assignment")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            kb_store = KbStore(db_path=db_path)
            audit_mgr = AuditLogManager(store=AuditLogStore(db_path=db_path))
            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            workflow_service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            workflow_service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A Workflow",
                steps=[
                    {"step_no": 1, "step_name": "Step 1", "approver_user_id": "reviewer-a"},
                    {"step_no": 2, "step_name": "Step 2", "approver_user_id": "reviewer-b"},
                ],
            )
            qualify_user_for_action(db_path, user_id="reviewer-a", action_code="document_review")
            qualify_user_for_action(db_path, user_id="reviewer-b", action_code="document_review")

            file_path = Path(td) / "doc-a.txt"
            file_path.write_text("doc-a", encoding="utf-8")
            doc = kb_store.create_document(
                filename="doc-a.txt",
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )

            wrong_user = _reviewer("reviewer-b")
            wrong_ctx = SimpleNamespace(
                deps=SimpleNamespace(
                    kb_store=kb_store,
                    ragflow_service=_RagflowService(),
                    audit_log_manager=audit_mgr,
                    approval_workflow_service=workflow_service,
                    electronic_signature_service=signature_service,
                    training_compliance_service=TrainingComplianceService(db_path=db_path),
                ),
                payload=SimpleNamespace(sub="reviewer-b"),
                user=wrong_user,
                snapshot=_snapshot("kb-a"),
            )

            with self.assertRaises(HTTPException) as exc:
                _approve_document_impl(
                    doc.doc_id,
                    wrong_ctx,
                    request=_Request("rid-wrong-approve"),
                    review_data=_review_request(signature_service, wrong_user, reason="wrong reviewer approve"),
                )
            self.assertEqual(exc.exception.status_code, 403)
            self.assertEqual(kb_store.get_document(doc.doc_id).status, "pending")
            self.assertEqual(
                signature_service.list_by_record(record_type="knowledge_document_review", record_id=doc.doc_id),
                [],
            )

            with self.assertRaises(HTTPException) as exc_reject:
                _reject_document_impl(
                    doc.doc_id,
                    wrong_ctx,
                    request=_Request("rid-wrong-reject"),
                    review_data=_review_request(signature_service, wrong_user, reason="wrong reviewer reject"),
                )
            self.assertEqual(exc_reject.exception.status_code, 403)
            self.assertEqual(kb_store.get_document(doc.doc_id).status, "pending")
            self.assertEqual(
                signature_service.list_by_record(record_type="knowledge_document_review", record_id=doc.doc_id),
                [],
            )
        finally:
            cleanup_dir(td)

    def test_disabled_assigned_reviewer_cannot_sign_current_step(self):
        td = make_temp_dir(prefix="ragflowauth_review_assignment_disabled")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            kb_store = KbStore(db_path=db_path)
            audit_mgr = AuditLogManager(store=AuditLogStore(db_path=db_path))
            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            workflow_service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            workflow_service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A Workflow",
                steps=[{"step_no": 1, "step_name": "Step 1", "approver_user_id": "reviewer-a"}, {"step_no": 2, "step_name": "Step 2", "approver_user_id": "reviewer-b"}],
            )
            qualify_user_for_action(db_path, user_id="reviewer-a", action_code="document_review")

            file_path = Path(td) / "doc-disabled.txt"
            file_path.write_text("doc-disabled", encoding="utf-8")
            doc = kb_store.create_document(
                filename="doc-disabled.txt",
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )

            disabled_user = _reviewer("reviewer-a")
            disabled_user.disable_login_enabled = True
            disabled_user.disable_login_until_ms = 4_102_444_800_000
            self.assertFalse(workflow_service.can_user_review_current_step(doc=doc, user=disabled_user))

            with self.assertRaises(Exception) as sign_ctx:
                _review_request(signature_service, disabled_user, reason="disabled reviewer")
            self.assertEqual(getattr(sign_ctx.exception, "code", None), "signature_user_disabled")
            self.assertEqual(signature_service.list_by_record(record_type="knowledge_document_review", record_id=doc.doc_id), [])
        finally:
            cleanup_dir(td)

    def test_step_one_and_step_two_are_owned_by_different_reviewers(self):
        td = make_temp_dir(prefix="ragflowauth_review_assignment_serial")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            kb_store = KbStore(db_path=db_path)
            audit_mgr = AuditLogManager(store=AuditLogStore(db_path=db_path))
            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            workflow_service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            workflow_service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A Workflow",
                steps=[
                    {"step_no": 1, "step_name": "Step 1", "approver_user_id": "reviewer-a"},
                    {"step_no": 2, "step_name": "Step 2", "approver_user_id": "reviewer-b"},
                ],
            )
            qualify_user_for_action(db_path, user_id="reviewer-a", action_code="document_review")
            qualify_user_for_action(db_path, user_id="reviewer-b", action_code="document_review")

            file_path = Path(td) / "doc-a.txt"
            file_path.write_text("doc-a", encoding="utf-8")
            doc = kb_store.create_document(
                filename="doc-a.txt",
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )

            reviewer_a = _reviewer("reviewer-a")
            reviewer_b = _reviewer("reviewer-b")
            base_deps = SimpleNamespace(
                kb_store=kb_store,
                ragflow_service=_RagflowService(),
                audit_log_manager=audit_mgr,
                approval_workflow_service=workflow_service,
                electronic_signature_service=signature_service,
                training_compliance_service=TrainingComplianceService(db_path=db_path),
            )
            ctx_a = SimpleNamespace(
                deps=base_deps,
                payload=SimpleNamespace(sub="reviewer-a"),
                user=reviewer_a,
                snapshot=_snapshot("kb-a"),
            )
            ctx_b = SimpleNamespace(
                deps=base_deps,
                payload=SimpleNamespace(sub="reviewer-b"),
                user=reviewer_b,
                snapshot=_snapshot("kb-a"),
            )

            step_one = _approve_document_impl(
                doc.doc_id,
                ctx_a,
                request=_Request("rid-step-1"),
                review_data=_review_request(signature_service, reviewer_a, reason="step 1"),
            )
            self.assertEqual(step_one.status, "pending")
            self.assertEqual(step_one.current_step_no, 2)

            with self.assertRaises(HTTPException) as exc:
                _approve_document_impl(
                    doc.doc_id,
                    ctx_a,
                    request=_Request("rid-step-2-fail"),
                    review_data=_review_request(signature_service, reviewer_a, reason="step 2 wrong actor"),
                )
            self.assertEqual(exc.exception.status_code, 403)

            final_step = _approve_document_impl(
                doc.doc_id,
                ctx_b,
                request=_Request("rid-step-2"),
                review_data=_review_request(signature_service, reviewer_b, reason="step 2"),
            )
            self.assertEqual(final_step.status, "approved")
            self.assertEqual(final_step.approval_status, "approved")
        finally:
            cleanup_dir(td)
