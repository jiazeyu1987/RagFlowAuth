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
from backend.services.notification import NotificationService, NotificationStore
from backend.services.training_compliance import TrainingComplianceService
from backend.services.user_store import UserStore
from backend.services.users import hash_password
from backend.tests._training_test_utils import qualify_user_for_action
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


SIGN_PASSWORD = "SignPass123"


class _Doc:
    def __init__(self, *, doc_id: str, filename: str, file_path: str, status: str, kb_id: str):
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
        self.kb_dataset_id = kb_id
        self.kb_name = kb_id
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


class _FailingNotificationService:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def notify_event(self, *, event_type: str, payload: dict, recipients: list[dict], dedupe_key: str):  # noqa: ARG002
        self.calls.append(("notify", event_type))
        raise RuntimeError("notification_service_down")

    def dispatch_pending(self, *, limit: int = 20):  # noqa: ARG002
        self.calls.append(("dispatch", str(limit)))
        return {"total": 0, "items": []}


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


class _CaptureEmailAdapter:
    def __init__(self):
        self.calls: list[dict] = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return None


class TestReviewNotificationIntegrationUnit(unittest.TestCase):
    def test_current_step_notification_targets_only_assigned_user(self):
        td = make_temp_dir(prefix="ragflowauth_review_notification_targeting")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            user_store = UserStore(db_path=db_path)
            uploader = user_store.create_user(
                username="uploader",
                password="UploaderPass123",
                email="uploader@example.com",
                role="operator",
                company_id=1,
                department_id=1,
            )
            reviewer_a = user_store.create_user(
                username="reviewer_a",
                password="ReviewerPass123",
                email="reviewer.a@example.com",
                role="reviewer",
                company_id=1,
                department_id=2,
            )
            reviewer_b = user_store.create_user(
                username="reviewer_b",
                password="ReviewerPass123",
                email="reviewer.b@example.com",
                role="reviewer",
                company_id=1,
                department_id=3,
            )
            reviewer_c = user_store.create_user(
                username="reviewer_c",
                password="ReviewerPass123",
                email="reviewer.c@example.com",
                role="reviewer",
                company_id=2,
                department_id=3,
            )

            capture_email = _CaptureEmailAdapter()
            notification_service = NotificationService(
                store=NotificationStore(db_path=db_path),
                email_adapter=capture_email,
                dingtalk_adapter=_RagflowService(),
                retry_interval_seconds=1,
            )
            notification_service.upsert_channel(
                channel_id="email-main",
                channel_type="email",
                name="Main Email",
                enabled=True,
                config={"host": "smtp.example.com", "from_email": "noreply@example.com"},
            )

            workflow_service = ApprovalWorkflowService(
                store=ApprovalWorkflowStore(db_path=db_path),
                notification_service=notification_service,
                user_store=user_store,
            )
            workflow_service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A Workflow",
                steps=[
                    {"step_no": 1, "step_name": "Author Review", "approver_user_id": reviewer_a.user_id},
                    {"step_no": 2, "step_name": "QA Review", "approver_user_id": reviewer_b.user_id},
                ],
            )

            file_path = Path(td) / "doc-r5.txt"
            file_path.write_text("ok", encoding="utf-8")
            doc = _Doc(doc_id="doc-r5", filename="doc-r5.txt", file_path=str(file_path), status="pending", kb_id="kb-a")
            doc.uploaded_by = uploader.user_id

            workflow_service.notify_current_step(doc=doc, actor=uploader.user_id, notes="initial submit")

            self.assertEqual(len(capture_email.calls), 1)
            first_call = capture_email.calls[0]
            self.assertEqual(first_call["event_type"], "review_todo_approval")
            self.assertEqual(first_call["recipient"]["address"], "reviewer.a@example.com")
            self.assertEqual(first_call["payload"]["current_step_name"], "Author Review")
            self.assertEqual(first_call["payload"]["filename"], "doc-r5.txt")
            self.assertEqual(first_call["payload"]["approval_target"]["doc_id"], "doc-r5")
            self.assertEqual(
                first_call["payload"]["approval_target"]["route_path"],
                "/documents?tab=approve&doc_id=doc-r5",
            )

            recipients_after_first = {call["recipient"]["address"] for call in capture_email.calls}
            self.assertNotIn("reviewer.b@example.com", recipients_after_first)
            self.assertNotIn("reviewer.c@example.com", recipients_after_first)

            step_two = workflow_service.approve_step(
                doc=doc,
                actor=reviewer_a.user_id,
                actor_user=user_store.get_by_user_id(reviewer_a.user_id),
                notes="step one approved",
                final=False,
            )
            self.assertEqual(step_two["current_step_no"], 2)
            self.assertEqual(step_two["current_step_name"], "QA Review")

            self.assertEqual(len(capture_email.calls), 2)
            second_call = capture_email.calls[1]
            self.assertEqual(second_call["recipient"]["address"], "reviewer.b@example.com")
            self.assertEqual(second_call["payload"]["current_step_name"], "QA Review")
            recipients_after_second = {call["recipient"]["address"] for call in capture_email.calls}
            self.assertNotIn("reviewer.c@example.com", recipients_after_second)

            jobs = notification_service.list_jobs(limit=10)
            pending_jobs = [job for job in jobs if job["event_type"] == "review_todo_approval"]
            self.assertEqual(len(pending_jobs), 2)
            self.assertEqual(
                {job["recipient_user_id"] for job in pending_jobs},
                {reviewer_a.user_id, reviewer_b.user_id},
            )
        finally:
            cleanup_dir(td)

    def test_notification_failure_does_not_block_approve_or_reject(self):
        td = make_temp_dir(prefix="ragflowauth_review_notification")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            audit_store = AuditLogStore(db_path=db_path)
            audit_mgr = AuditLogManager(store=audit_store)
            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user_store = UserStore(db_path=db_path)
            uploader = user_store.create_user(
                username="uploader",
                password="UploaderPass123",
                email="uploader@example.com",
                role="operator",
                company_id=1,
                department_id=1,
            )
            reviewer = user_store.create_user(
                username="reviewer-1",
                password="ReviewerPass123",
                email="reviewer@example.com",
                role="reviewer",
                company_id=1,
                department_id=2,
            )

            file_path = Path(td) / "doc-a.txt"
            file_path.write_text("ok", encoding="utf-8")

            doc_a = _Doc(doc_id="doc-a", filename="doc-a.txt", file_path=str(file_path), status="pending", kb_id="kb-a")
            doc_b = _Doc(doc_id="doc-b", filename="doc-b.txt", file_path=str(file_path), status="pending", kb_id="kb-a")
            doc_a.uploaded_by = uploader.user_id
            doc_b.uploaded_by = uploader.user_id
            kb_store = _KbStore({"doc-a": doc_a, "doc-b": doc_b}, db_path=db_path)

            failing_notification = _FailingNotificationService()
            workflow_service = ApprovalWorkflowService(
                store=ApprovalWorkflowStore(db_path=db_path),
                notification_service=failing_notification,
                user_store=user_store,
            )
            workflow_service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A Workflow",
                steps=[
                    {"step_no": 1, "step_name": "Step 1", "approver_user_id": reviewer.user_id},
                    {"step_no": 2, "step_name": "Step 2", "approver_user_id": reviewer.user_id},
                ],
            )
            qualify_user_for_action(db_path, user_id=reviewer.user_id, action_code="document_review")

            user = SimpleNamespace(
                user_id=reviewer.user_id,
                username=reviewer.username,
                email=reviewer.email,
                role=reviewer.role,
                status="active",
                company_id=1,
                department_id=2,
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
                payload=SimpleNamespace(sub=reviewer.user_id),
                user=user,
                snapshot=_snapshot("kb-a"),
            )

            stepped = _approve_document_impl(
                "doc-a",
                ctx,
                request=_Request("rid-step"),
                review_data=_issue_review_request(
                    signature_service,
                    user,
                    meaning="Approve step",
                    reason="Approve workflow step",
                    review_notes="step-approve",
                ),
            )
            self.assertEqual(stepped.status, "pending")
            self.assertEqual(stepped.approval_status, "in_progress")
            self.assertEqual(stepped.current_step_no, 2)
            self.assertIsNotNone(stepped.signature_id)

            approved = _approve_document_impl(
                "doc-a",
                ctx,
                request=_Request("rid-final"),
                review_data=_issue_review_request(
                    signature_service,
                    user,
                    meaning="Approve final",
                    reason="Approve final workflow step",
                    review_notes="final-approve",
                ),
            )
            self.assertEqual(approved.status, "approved")
            self.assertEqual(approved.approval_status, "approved")
            self.assertIsNotNone(approved.signature_id)

            rejected = _reject_document_impl(
                "doc-b",
                ctx,
                request=_Request("rid-reject"),
                review_data=_issue_review_request(
                    signature_service,
                    user,
                    meaning="Reject document",
                    reason="Reject workflow item",
                    review_notes="reject",
                ),
            )
            self.assertEqual(rejected.status, "rejected")
            self.assertEqual(rejected.approval_status, "rejected")
            self.assertIsNotNone(rejected.signature_id)

            notify_calls = [x for x in failing_notification.calls if x[0] == "notify"]
            self.assertGreaterEqual(len(notify_calls), 3)
        finally:
            cleanup_dir(td)
