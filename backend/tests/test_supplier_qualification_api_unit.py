import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.supplier_qualification.router import router as supplier_qualification_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.supplier_qualification import SupplierQualificationService
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def __init__(self, users: dict[str, SimpleNamespace]):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)


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
        self.supplier_qualification_service = SupplierQualificationService(db_path=db_path)


def _make_user(*, user_id: str, role: str) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        status="active",
        group_id=None,
        group_ids=[],
        company_id=1,
        department_id=1,
    )


class TestSupplierQualificationApiUnit(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(supplier_qualification_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_non_admin_cannot_upsert_component(self):
        td = make_temp_dir(prefix="ragflowauth_supplier_qualification_forbidden")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "reviewer-1": _make_user(user_id="reviewer-1", role="reviewer"),
            }
            app = self._build_app(current_user_id="reviewer-1", deps=_Deps(db_path=db_path, users=users))

            with TestClient(app) as client:
                response = client.post(
                    "/api/supplier-qualifications/components",
                    json={
                        "component_code": "ragflow",
                        "component_name": "RAGFlow",
                        "supplier_name": "RAGFlow",
                        "component_category": "vendor_service",
                        "deployment_scope": "shared_service",
                        "current_version": "1.0.0",
                        "approved_version": "1.0.0",
                        "supplier_approval_status": "approved",
                        "intended_use_summary": "用于知识检索和问答服务。",
                        "qualification_summary": "供应商在受监管行业有成熟部署记录。",
                        "supplier_audit_summary": "已评审供应商开发与支持能力。",
                        "known_issue_review": "已核对当前版本已知缺陷并确认可接受。",
                        "migration_plan_summary": "新版本发布后先评审再迁移。",
                    },
                )
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["detail"], "admin_required")
        finally:
            cleanup_dir(td)

    def test_version_change_marks_component_for_requalification(self):
        td = make_temp_dir(prefix="ragflowauth_supplier_qualification_version")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="admin-1", deps=deps)

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/supplier-qualifications/components",
                    json={
                        "component_code": "ragflow",
                        "component_name": "RAGFlow",
                        "supplier_name": "RAGFlow",
                        "component_category": "vendor_service",
                        "deployment_scope": "shared_service",
                        "current_version": "1.0.0",
                        "approved_version": "1.0.0",
                        "supplier_approval_status": "approved",
                        "intended_use_summary": "用于知识检索和问答服务。",
                        "qualification_summary": "供应商在受监管行业有成熟部署记录。",
                        "supplier_audit_summary": "已评审供应商开发与支持能力。",
                        "known_issue_review": "已核对当前版本已知缺陷并确认可接受。",
                        "migration_plan_summary": "新版本发布后先评审再迁移。",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                self.assertEqual(create_resp.json()["qualification_status"], "approved")

                version_resp = client.post(
                    "/api/supplier-qualifications/components/ragflow/version-change",
                    json={
                        "new_version": "1.1.0",
                        "change_summary": "供应商发布新版本，需要重新评审已知缺陷与回归范围。",
                    },
                )
                self.assertEqual(version_resp.status_code, 200, version_resp.text)
                data = version_resp.json()
                self.assertEqual(data["current_version"], "1.1.0")
                self.assertEqual(data["approved_version"], "1.0.0")
                self.assertEqual(data["qualification_status"], "requalification_required")
                self.assertIn("重新评审", data["revalidation_trigger"])
        finally:
            cleanup_dir(td)

    def test_tenant_database_environment_record_requires_company_id(self):
        td = make_temp_dir(prefix="ragflowauth_supplier_qualification_tenant")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "qa-1": _make_user(user_id="qa-1", role="reviewer"),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="admin-1", deps=deps)

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/supplier-qualifications/components",
                    json={
                        "component_code": "tenant-auth-db",
                        "component_name": "Tenant Auth DB",
                        "supplier_name": "SQLite",
                        "component_category": "database",
                        "deployment_scope": "tenant_database",
                        "current_version": "3.45.0",
                        "approved_version": "3.45.0",
                        "supplier_approval_status": "approved",
                        "intended_use_summary": "承载租户鉴权和审计数据。",
                        "qualification_summary": "数据库版本已纳入批准范围。",
                        "supplier_audit_summary": "内部批准使用该数据库版本。",
                        "known_issue_review": "已检查版本已知缺陷，无阻断项。",
                        "migration_plan_summary": "版本升级时重新执行租户库确认。",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)

                env_resp = client.post(
                    "/api/supplier-qualifications/environment-records",
                    json={
                        "component_code": "tenant-auth-db",
                        "environment_name": "prod-tenant-auth-db",
                        "release_version": "2.0.0",
                        "protocol_ref": "IQ-OQ-PQ-TENANT-001",
                        "iq_status": "passed",
                        "oq_status": "passed",
                        "pq_status": "passed",
                        "qualification_summary": "已完成安装、运行和性能鉴定。",
                        "executed_by_user_id": "qa-1",
                    },
                )
                self.assertEqual(env_resp.status_code, 400, env_resp.text)
                self.assertEqual(env_resp.json()["detail"], "tenant_company_id_required")
        finally:
            cleanup_dir(td)

    def test_happy_path_records_environment_qualification_and_audit(self):
        td = make_temp_dir(prefix="ragflowauth_supplier_qualification_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "qa-1": _make_user(user_id="qa-1", role="reviewer"),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="admin-1", deps=deps)

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/supplier-qualifications/components",
                    json={
                        "component_code": "onlyoffice",
                        "component_name": "ONLYOFFICE",
                        "supplier_name": "Ascensio",
                        "component_category": "off_the_shelf_software",
                        "deployment_scope": "server",
                        "current_version": "8.0.1",
                        "approved_version": "8.0.1",
                        "supplier_approval_status": "approved",
                        "intended_use_summary": "用于 Office 文档受控预览。",
                        "qualification_summary": "供应商产品符合当前预期用途。",
                        "supplier_audit_summary": "已评审供应商提供的确认资料和支持计划。",
                        "known_issue_review": "已审查已知缺陷清单并确认无阻断项。",
                        "migration_plan_summary": "升级前复核供应商测试套件和兼容性。",
                        "review_due_date": "2026-10-03",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)

                env_resp = client.post(
                    "/api/supplier-qualifications/environment-records",
                    json={
                        "component_code": "onlyoffice",
                        "environment_name": "prod-onlyoffice-node-1",
                        "company_id": None,
                        "release_version": "2.0.0",
                        "protocol_ref": "IQ-OQ-PQ-OO-001",
                        "iq_status": "passed",
                        "oq_status": "passed",
                        "pq_status": "passed",
                        "qualification_summary": "供应商测试套件和补充场景均通过。",
                        "deviation_summary": "",
                        "executed_by_user_id": "qa-1",
                    },
                )
                self.assertEqual(env_resp.status_code, 200, env_resp.text)
                data = env_resp.json()
                self.assertEqual(data["qualification_status"], "approved")
                self.assertEqual(data["executed_by_user_id"], "qa-1")
                self.assertEqual(data["approved_by_user_id"], "admin-1")

                list_resp = client.get("/api/supplier-qualifications/environment-records?component_code=onlyoffice")
                self.assertEqual(list_resp.status_code, 200, list_resp.text)
                self.assertEqual(list_resp.json()["count"], 1)

            total, rows = deps.audit_log_store.list_events(limit=20)
            self.assertGreaterEqual(total, 2)
            actions = [row.action for row in rows]
            self.assertIn("supplier_component_upsert", actions)
            self.assertIn("environment_qualification_record", actions)
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
