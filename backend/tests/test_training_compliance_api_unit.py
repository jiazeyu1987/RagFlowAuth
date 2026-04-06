import os
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.data_security import router as data_security_router
from backend.app.modules.operation_approvals.router import router as operation_approval_router
from backend.app.modules.training_compliance.router import router as training_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.data_security.store import DataSecurityStore
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.training_compliance import TrainingComplianceService
from backend.services.users.store import UserStore
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
    def __init__(
        self,
        *,
        db_path: str,
        users: dict[str, SimpleNamespace],
        training_db_path: str | None = None,
    ):
        audit_store = AuditLogStore(db_path=db_path)
        training_db_path = training_db_path or db_path
        self._seed_users(db_path=training_db_path, users=users)
        self.user_store = _UserStore(users)
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.audit_log_store = audit_store
        self.audit_log_manager = AuditLogManager(store=audit_store)
        self.training_compliance_service = TrainingComplianceService(db_path=training_db_path)
        self.data_security_store = DataSecurityStore(db_path=db_path)
        self.org_directory_store = _OrgStore()
        self.org_structure_manager = self.org_directory_store

    @staticmethod
    def _seed_users(*, db_path: str, users: dict[str, SimpleNamespace]) -> None:
        conn = sqlite3.connect(db_path)
        try:
            for item in users.values():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users (
                        user_id,
                        username,
                        password_hash,
                        email,
                        role,
                        group_id,
                        company_id,
                        department_id,
                        status,
                        created_at_ms,
                        full_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(getattr(item, "user_id", "") or ""),
                        str(getattr(item, "username", "") or getattr(item, "user_id", "") or ""),
                        str(getattr(item, "password_hash", "") or ""),
                        str(getattr(item, "email", "") or ""),
                        str(getattr(item, "role", "") or "viewer"),
                        getattr(item, "group_id", None),
                        getattr(item, "company_id", None),
                        getattr(item, "department_id", None),
                        str(getattr(item, "status", "") or "active"),
                        1,
                        str(getattr(item, "full_name", "") or getattr(item, "username", "") or ""),
                    ),
                )
            conn.commit()
        finally:
            conn.close()


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


def _issue_review_request(signature_service: ElectronicSignatureService, user, *, reason: str) -> dict:
    challenge = signature_service.issue_challenge(user=user, password=SIGN_PASSWORD)
    return {
        "sign_token": challenge["sign_token"],
        "signature_meaning": "Document review",
        "signature_reason": reason,
        "notes": reason,
    }


class _FakeOperationApprovalService:
    def __init__(self):
        self.calls: list[dict] = []

    def approve_request(self, **kwargs):
        self.calls.append(dict(kwargs))
        return {"request_id": kwargs.get("request_id"), "status": "approved"}


class TestTrainingComplianceApiUnit(unittest.TestCase):
    def _build_app(
        self,
        *,
        current_user_id: str,
        deps,
        include_restore_router: bool = False,
        include_operation_approval_router: bool = False,
    ):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(training_router, prefix="/api")
        if include_restore_router:
            app.include_router(data_security_router.router, prefix="/api")
        if include_operation_approval_router:
            app.include_router(operation_approval_router, prefix="/api")
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
                requirement_resp = client.post(
                    "/api/training-compliance/requirements",
                    json={
                        "requirement_code": "TR-001",
                        "requirement_name": "文件审批培训",
                        "role_code": "reviewer",
                        "controlled_action": "document_review",
                        "curriculum_version": "2026.04",
                        "training_material_ref": "doc/compliance/training_matrix.md#tr-001",
                        "effectiveness_required": True,
                        "recertification_interval_days": 365,
                        "active": True,
                    },
                )
                self.assertEqual(requirement_resp.status_code, 200, requirement_resp.text)
                self.assertEqual(requirement_resp.json()["requirement"]["requirement_code"], "TR-001")

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
                self.assertEqual(record_resp.json()["record"]["effectiveness_status"], "effective")

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
                self.assertEqual(cert_resp.json()["certification"]["certification_status"], "active")

                status_resp = client.get("/api/training-compliance/actions/document_review/users/reviewer-1")
                self.assertEqual(status_resp.status_code, 200, status_resp.text)
                status_data = status_resp.json()["status"]
                self.assertTrue(status_data["allowed"])
                self.assertEqual(status_data["requirements"][0]["failure_code"], None)
        finally:
            cleanup_dir(td)

    def test_curriculum_version_change_blocks_operation_approval_until_retrained(self):
        td = make_temp_dir(prefix="ragflowauth_training_requalification")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            qualify_user_for_action(db_path, user_id="reviewer-1", action_code="document_review")

            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            fake_operation_approval_service = _FakeOperationApprovalService()

            reviewer = _make_user(user_id="reviewer-1", role="reviewer", department_id=2)
            users = {"reviewer-1": reviewer}
            deps = _Deps(db_path=db_path, users=users)
            deps.operation_approval_service = fake_operation_approval_service
            deps.electronic_signature_service = signature_service

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

            app = self._build_app(
                current_user_id="reviewer-1",
                deps=deps,
                include_operation_approval_router=True,
            )
            with TestClient(app) as client:
                blocked_resp = client.post(
                    "/api/operation-approvals/requests/req-1/approve",
                    json=_issue_review_request(signature_service, reviewer, reason="outdated training"),
                )
            self.assertEqual(blocked_resp.status_code, 403, blocked_resp.text)
            self.assertEqual(blocked_resp.json()["detail"], "training_curriculum_outdated")
            self.assertEqual(fake_operation_approval_service.calls, [])

            qualify_user_for_action(
                db_path,
                user_id="reviewer-1",
                action_code="document_review",
                completed_at_ms=1_900_000_000_000,
                valid_until_ms=2_000_000_000_000,
            )
            with TestClient(app) as client:
                approved_resp = client.post(
                    "/api/operation-approvals/requests/req-1/approve",
                    json=_issue_review_request(signature_service, reviewer, reason="retrained"),
                )
            self.assertEqual(approved_resp.status_code, 200, approved_resp.text)
            self.assertEqual(approved_resp.json()["status"], "approved")
            self.assertEqual(len(fake_operation_approval_service.calls), 1)
        finally:
            cleanup_dir(td)

    def test_training_status_endpoint_uses_training_service_db_for_user_lookup(self):
        td = make_temp_dir(prefix="ragflowauth_training_status_cross_db")
        try:
            tenant_db_path = os.path.join(str(td), "tenant.db")
            global_db_path = os.path.join(str(td), "global.db")
            ensure_schema(tenant_db_path)
            ensure_schema(global_db_path)

            global_user_store = UserStore(db_path=global_db_path)
            stored_admin = global_user_store.create_user(
                username="admin_status",
                password="Pass1234",
                role="admin",
                company_id=2,
            )
            stored_reviewer = global_user_store.create_user(
                username="reviewer_status",
                password="Pass1234",
                role="reviewer",
                company_id=2,
            )
            qualify_user_for_action(global_db_path, user_id=stored_reviewer.user_id, action_code="document_review")

            deps = _Deps(
                db_path=tenant_db_path,
                training_db_path=global_db_path,
                users={
                    stored_admin.user_id: _make_user(
                        user_id=stored_admin.user_id,
                        role="admin",
                        company_id=2,
                    )
                },
            )
            app = self._build_app(current_user_id=stored_admin.user_id, deps=deps)

            with TestClient(app) as client:
                status_resp = client.get(
                    f"/api/training-compliance/actions/document_review/users/{stored_reviewer.user_id}"
                )
                self.assertEqual(status_resp.status_code, 200, status_resp.text)
                self.assertTrue(status_resp.json()["status"]["allowed"])
        finally:
            cleanup_dir(td)

    def test_operation_approval_requirement_seed_migrates_legacy_reviewer_binding_to_wildcard(self):
        td = make_temp_dir(prefix="ragflowauth_training_requirement_migration")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    UPDATE training_requirements
                    SET role_code = ?, updated_at_ms = ?
                    WHERE requirement_code = ?
                    """,
                    ("reviewer", 1, "TR-001"),
                )
                conn.commit()
            finally:
                conn.close()

            ensure_schema(db_path)

            signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            fake_operation_approval_service = _FakeOperationApprovalService()
            admin = _make_user(user_id="admin-1", role="admin", department_id=2)
            users = {"admin-1": admin}
            deps = _Deps(db_path=db_path, users=users)
            deps.operation_approval_service = fake_operation_approval_service
            deps.electronic_signature_service = signature_service

            service = TrainingComplianceService(db_path=db_path)
            requirement = service.get_requirement("TR-001")
            self.assertEqual(requirement["role_code"], "*")

            app = self._build_app(
                current_user_id="admin-1",
                deps=deps,
                include_operation_approval_router=True,
            )
            with TestClient(app) as client:
                blocked_resp = client.post(
                    "/api/operation-approvals/requests/req-1/approve",
                    json=_issue_review_request(signature_service, admin, reason="admin approval without qualification"),
                )
            self.assertEqual(blocked_resp.status_code, 403, blocked_resp.text)
            self.assertEqual(blocked_resp.json()["detail"], "training_record_missing")
            self.assertEqual(fake_operation_approval_service.calls, [])

            qualify_user_for_action(db_path, user_id="admin-1", action_code="document_review")

            with TestClient(app) as client:
                approved_resp = client.post(
                    "/api/operation-approvals/requests/req-1/approve",
                    json=_issue_review_request(signature_service, admin, reason="admin approval after qualification"),
                )
            self.assertEqual(approved_resp.status_code, 200, approved_resp.text)
            self.assertEqual(approved_resp.json()["status"], "approved")
            self.assertEqual(len(fake_operation_approval_service.calls), 1)
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
