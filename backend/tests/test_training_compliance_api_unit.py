import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.data_security import router as data_security_router
from backend.app.modules.review.routes.approve import _approve_document_impl
from backend.app.modules.training_compliance.router import router as training_router
from backend.database.schema.ensure import ensure_schema
from backend.models.document import DocumentReviewRequest
from backend.services.approval import ApprovalWorkflowService, ApprovalWorkflowStore
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.data_security.store import DataSecurityStore
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.kb import KbStore
from backend.services.training_compliance import TrainingComplianceService
from backend.services.users import hash_password
from backend.tests._training_test_utils import qualify_user_for_action
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


SIGN_PASSWORD = "SignPass123"


class _UserStore:
    def __init__(self, users: dict[str, SimpleNamespace]):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)


class _OrgStore:
    def get_company(self, company_id):  # noqa: ARG002
        return SimpleNamespace(name="Acme")

    def get_department(self, department_id):  # noqa: ARG002
        return SimpleNamespace(name="QA")


class _Deps:
    def __init__(self, *, db_path: str, users: dict[str, SimpleNamespace]):
        audit_store = AuditLogStore(db_path=db_path)
        self.user_store = _UserStore(users)
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.audit_log_store = audit_store
        self.audit_log_manager = AuditLogManager(store=audit_store)
        self.training_compliance_service = TrainingComplianceService(db_path=db_path)
        self.data_security_store = DataSecurityStore(db_path=db_path)
        self.org_directory_store = _OrgStore()


class _Request:
    def __init__(self, request_id: str):
        self.state = SimpleNamespace(request_id=request_id)
        self.client = SimpleNamespace(host="127.0.0.1")


class _RagflowService:
    def upload_document_blob(self, **kwargs):  # noqa: ARG002
        return "rag-doc-1"

    def parse_document(self, **kwargs):  # noqa: ARG002
        return True


def _make_user(*, user_id: str, role: str, company_id: int = 1, department_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        status="active",
        group_id=None,
        group_ids=[],
        company_id=company_id,
        department_id=department_id,
        password_hash=hash_password(SIGN_PASSWORD),
    )


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


def _issue_review_request(signature_service: ElectronicSignatureService, user, *, reason: str) -> DocumentReviewRequest:
    challenge = signature_service.issue_challenge(user=user, password=SIGN_PASSWORD)
    return DocumentReviewRequest(
        sign_token=challenge["sign_token"],
        signature_meaning="Document review",
        signature_reason=reason,
        review_notes=reason,
    )


class TestTrainingComplianceApiUnit(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps, include_restore_router: bool = False):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(training_router, prefix="/api")
        if include_restore_router:
            app.include_router(data_security_router.router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_non_admin_cannot_create_training_requirement(self):
        td = make_temp_dir(prefix="ragflowauth_training_requirement_forbidden")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {"reviewer-1": _make_user(user_id="reviewer-1", role="reviewer")}
            app = self._build_app(current_user_id="reviewer-1", deps=_Deps(db_path=db_path, users=users))

            with TestClient(app) as client:
                response = client.post(
                    "/api/training-compliance/requirements",
                    json={
                        "requirement_code": "TR-100",
                        "requirement_name": "额外培训",
                        "role_code": "reviewer",
                        "controlled_action": "document_review",
                        "curriculum_version": "2026.05",
                        "training_material_ref": "doc/compliance/training_matrix.md#tr-100",
                        "effectiveness_required": True,
                        "recertification_interval_days": 180,
                        "active": True,
                    },
                )
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["detail"], "admin_required")
        finally:
            cleanup_dir(td)

    def test_admin_api_creates_record_certification_and_status_endpoint_allows_action(self):
        td = make_temp_dir(prefix="ragflowauth_training_status_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "reviewer-1": _make_user(user_id="reviewer-1", role="reviewer", department_id=2),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="admin-1", deps=deps)

            with TestClient(app) as client:
                record_resp = client.post(
                    "/api/training-compliance/records",
                    json={
                        "requirement_code": "TR-001",
                        "user_id": "reviewer-1",
                        "curriculum_version": "2026.04",
                        "trainer_user_id": "admin-1",
                        "training_outcome": "passed",
                        "effectiveness_status": "effective",
                        "effectiveness_score": 98,
                        "effectiveness_summary": "审批操作演练通过",
                        "training_notes": "已完成文件审批与签名培训",
                        "completed_at_ms": 1_770_000_000_000,
                        "effectiveness_reviewed_by_user_id": "admin-1",
                        "effectiveness_reviewed_at_ms": 1_770_000_000_000,
                    },
                )
                self.assertEqual(record_resp.status_code, 200, record_resp.text)
                self.assertEqual(record_resp.json()["effectiveness_status"], "effective")

                cert_resp = client.post(
                    "/api/training-compliance/certifications",
                    json={
                        "requirement_code": "TR-001",
                        "user_id": "reviewer-1",
                        "granted_by_user_id": "admin-1",
                        "certification_status": "active",
                        "granted_at_ms": 1_770_000_000_000,
                        "valid_until_ms": 1_900_000_000_000,
                        "certification_notes": "审批员上岗认证",
                    },
                )
                self.assertEqual(cert_resp.status_code, 200, cert_resp.text)
                self.assertEqual(cert_resp.json()["certification_status"], "active")

                status_resp = client.get("/api/training-compliance/actions/document_review/users/reviewer-1")
                self.assertEqual(status_resp.status_code, 200, status_resp.text)
                status_data = status_resp.json()
                self.assertTrue(status_data["allowed"])
                self.assertEqual(status_data["requirements"][0]["failure_code"], None)
        finally:
            cleanup_dir(td)

    def test_curriculum_version_change_blocks_review_until_retrained(self):
        td = make_temp_dir(prefix="ragflowauth_training_requalification")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            qualify_user_for_action(db_path, user_id="reviewer-1", action_code="document_review")

            kb_store = KbStore(db_path=db_path)
            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
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

            file_path = Path(td) / "doc.txt"
            file_path.write_text("doc", encoding="utf-8")
            doc = kb_store.create_document(
                filename="doc.txt",
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )

            reviewer = _make_user(user_id="reviewer-1", role="reviewer", department_id=2)
            deps = SimpleNamespace(
                kb_store=kb_store,
                ragflow_service=_RagflowService(),
                audit_log_manager=AuditLogManager(store=AuditLogStore(db_path=db_path)),
                approval_workflow_service=workflow_service,
                electronic_signature_service=signature_service,
                training_compliance_service=TrainingComplianceService(db_path=db_path),
            )
            ctx = SimpleNamespace(
                deps=deps,
                payload=SimpleNamespace(sub="reviewer-1"),
                user=reviewer,
                snapshot=_snapshot("kb-a"),
            )

            service = TrainingComplianceService(db_path=db_path)
            requirement = service.get_requirement("TR-001")
            service.upsert_requirement(
                requirement_code="TR-001",
                requirement_name=requirement["requirement_name"],
                role_code=requirement["role_code"],
                controlled_action=requirement["controlled_action"],
                curriculum_version="2026.05",
                training_material_ref=requirement["training_material_ref"],
                effectiveness_required=requirement["effectiveness_required"],
                recertification_interval_days=requirement["recertification_interval_days"],
                review_due_date=requirement["review_due_date"],
                active=requirement["active"],
            )

            with self.assertRaises(HTTPException) as exc:
                _approve_document_impl(
                    doc.doc_id,
                    ctx,
                    request=_Request("rid-outdated"),
                    review_data=_issue_review_request(signature_service, reviewer, reason="outdated training"),
                )
            self.assertEqual(exc.exception.status_code, 403)
            self.assertEqual(exc.exception.detail, "training_curriculum_outdated")

            qualify_user_for_action(
                db_path,
                user_id="reviewer-1",
                action_code="document_review",
                completed_at_ms=1_900_000_000_000,
                valid_until_ms=2_000_000_000_000,
            )
            first_step = _approve_document_impl(
                doc.doc_id,
                ctx,
                request=_Request("rid-retrained"),
                review_data=_issue_review_request(signature_service, reviewer, reason="retrained"),
            )
            self.assertEqual(first_step.status, "pending")
            self.assertEqual(first_step.approval_status, "in_progress")

            approved = _approve_document_impl(
                doc.doc_id,
                ctx,
                request=_Request("rid-retrained-final"),
                review_data=_issue_review_request(signature_service, reviewer, reason="retrained final"),
            )
            self.assertEqual(approved.status, "approved")
            self.assertEqual(approved.approval_status, "approved")
        finally:
            cleanup_dir(td)

    def test_expired_restore_drill_certification_is_blocked(self):
        td = make_temp_dir(prefix="ragflowauth_restore_training_block")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            qualify_user_for_action(
                db_path,
                user_id="admin-1",
                action_code="restore_drill_execute",
                completed_at_ms=1_700_000_000_000,
                valid_until_ms=1_700_000_001_000,
            )
            users = {"admin-1": _make_user(user_id="admin-1", role="admin")}
            deps = _Deps(db_path=db_path, users=users)
            base_job = deps.data_security_store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_restore"
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "auth.db").write_text("sqlite-data", encoding="utf-8")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            from backend.services.data_security.backup_service import _compute_backup_package_hash

            pack_hash = _compute_backup_package_hash(pack_dir)
            deps.data_security_store.update_job(base_job.id, output_dir=str(pack_dir), package_hash=pack_hash)

            app = self._build_app(current_user_id="admin-1", deps=deps, include_restore_router=True)
            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/admin/data-security/restore-drills",
                    json={
                        "job_id": base_job.id,
                        "backup_path": str(pack_dir),
                        "backup_hash": pack_hash,
                        "restore_target": "qa-staging",
                    },
                )
                self.assertEqual(create_resp.status_code, 403, create_resp.text)
                self.assertEqual(create_resp.json()["detail"], "operator_certification_expired")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
