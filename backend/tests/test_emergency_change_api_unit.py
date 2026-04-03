import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.emergency_changes.router import router as emergency_changes_router
from backend.database.schema.ensure import ensure_schema
from backend.services.emergency_change import EmergencyChangeService
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def __init__(self, users: dict[str, SimpleNamespace]):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)


class _Deps:
    def __init__(self, *, db_path: str, users: dict[str, SimpleNamespace]):
        self.user_store = _UserStore(users)
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.emergency_change_service = EmergencyChangeService(db_path=db_path)


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


class TestEmergencyChangeApiUnit(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(emergency_changes_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_non_admin_cannot_create_emergency_change(self):
        td = make_temp_dir(prefix="ragflowauth_emergency_change_forbidden")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "reviewer-1": _make_user(user_id="reviewer-1", role="reviewer"),
                "authorizer-1": _make_user(user_id="authorizer-1", role="reviewer"),
                "qa-1": _make_user(user_id="qa-1", role="reviewer"),
            }
            app = self._build_app(current_user_id="reviewer-1", deps=_Deps(db_path=db_path, users=users))

            with TestClient(app) as client:
                response = client.post(
                    "/api/emergency-changes",
                    json={
                        "title": "Patch urgent auth bug",
                        "summary": "Need emergency fix",
                        "authorizer_user_id": "authorizer-1",
                        "reviewer_user_id": "qa-1",
                        "authorization_basis": "生产缺陷阻断业务",
                        "risk_assessment": "误授权风险高",
                        "risk_control": "发布前双人复核",
                        "rollback_plan": "回滚上一发布版本",
                        "training_notification_plan": "完成后通知值班与QA",
                    },
                )
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["detail"], "admin_required")
        finally:
            cleanup_dir(td)

    def test_wrong_authorizer_cannot_authorize_and_deploy_requires_authorization(self):
        td = make_temp_dir(prefix="ragflowauth_emergency_change_authz")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "authorizer-1": _make_user(user_id="authorizer-1", role="reviewer"),
                "reviewer-1": _make_user(user_id="reviewer-1", role="reviewer"),
                "reviewer-2": _make_user(user_id="reviewer-2", role="reviewer"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_resp = client.post(
                    "/api/emergency-changes",
                    json={
                        "title": "Patch urgent auth bug",
                        "summary": "Need emergency fix",
                        "authorizer_user_id": "authorizer-1",
                        "reviewer_user_id": "reviewer-1",
                        "authorization_basis": "生产缺陷阻断业务",
                        "risk_assessment": "误授权风险高",
                        "risk_control": "发布前双人复核",
                        "rollback_plan": "回滚上一发布版本",
                        "training_notification_plan": "完成后通知值班与QA",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                change_id = create_resp.json()["change_id"]

                deploy_resp = client.post(
                    f"/api/emergency-changes/{change_id}/deploy",
                    json={"deployment_summary": "直接上线修复"},
                )
                self.assertEqual(deploy_resp.status_code, 409, deploy_resp.text)
                self.assertEqual(
                    deploy_resp.json()["detail"],
                    "emergency_change_must_be_authorized_before_deploy",
                )

            wrong_authorizer_app = self._build_app(current_user_id="reviewer-2", deps=deps)
            with TestClient(wrong_authorizer_app) as client:
                auth_resp = client.post(
                    f"/api/emergency-changes/{change_id}/authorize",
                    json={"authorization_notes": "I should not approve this"},
                )
                self.assertEqual(auth_resp.status_code, 403, auth_resp.text)
                self.assertEqual(auth_resp.json()["detail"], "emergency_change_authorizer_required")
        finally:
            cleanup_dir(td)

    def test_close_requires_post_review_fields(self):
        td = make_temp_dir(prefix="ragflowauth_emergency_change_close")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "authorizer-1": _make_user(user_id="authorizer-1", role="reviewer"),
                "reviewer-1": _make_user(user_id="reviewer-1", role="reviewer"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_resp = client.post(
                    "/api/emergency-changes",
                    json={
                        "title": "Patch urgent auth bug",
                        "summary": "Need emergency fix",
                        "authorizer_user_id": "authorizer-1",
                        "reviewer_user_id": "reviewer-1",
                        "authorization_basis": "生产缺陷阻断业务",
                        "risk_assessment": "误授权风险高",
                        "risk_control": "发布前双人复核",
                        "rollback_plan": "回滚上一发布版本",
                        "training_notification_plan": "完成后通知值班与QA",
                    },
                )
                change_id = create_resp.json()["change_id"]

            authorizer_app = self._build_app(current_user_id="authorizer-1", deps=deps)
            with TestClient(authorizer_app) as client:
                auth_resp = client.post(
                    f"/api/emergency-changes/{change_id}/authorize",
                    json={"authorization_notes": "允许执行紧急修复"},
                )
                self.assertEqual(auth_resp.status_code, 200, auth_resp.text)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                deploy_resp = client.post(
                    f"/api/emergency-changes/{change_id}/deploy",
                    json={"deployment_summary": "22:30 热修复上线"},
                )
                self.assertEqual(deploy_resp.status_code, 200, deploy_resp.text)

            reviewer_app = self._build_app(current_user_id="reviewer-1", deps=deps)
            with TestClient(reviewer_app) as client:
                close_resp = client.post(
                    f"/api/emergency-changes/{change_id}/close",
                    json={
                        "impact_assessment_summary": "影响已受控",
                        "post_review_summary": "",
                        "capa_actions": "补回归测试",
                        "verification_summary": "生产冒烟正常",
                    },
                )
                self.assertEqual(close_resp.status_code, 400, close_resp.text)
                self.assertEqual(close_resp.json()["detail"], "post_review_summary_required")
        finally:
            cleanup_dir(td)

    def test_happy_path_create_authorize_deploy_close(self):
        td = make_temp_dir(prefix="ragflowauth_emergency_change_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "authorizer-1": _make_user(user_id="authorizer-1", role="reviewer"),
                "reviewer-1": _make_user(user_id="reviewer-1", role="reviewer"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_resp = client.post(
                    "/api/emergency-changes",
                    json={
                        "title": "Patch urgent auth bug",
                        "summary": "Need emergency fix",
                        "authorizer_user_id": "authorizer-1",
                        "reviewer_user_id": "reviewer-1",
                        "authorization_basis": "生产缺陷阻断业务",
                        "risk_assessment": "误授权风险高",
                        "risk_control": "发布前双人复核",
                        "rollback_plan": "回滚上一发布版本",
                        "training_notification_plan": "完成后通知值班与QA",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                change_id = create_resp.json()["change_id"]
                self.assertEqual(create_resp.json()["status"], "requested")

            authorizer_app = self._build_app(current_user_id="authorizer-1", deps=deps)
            with TestClient(authorizer_app) as client:
                auth_resp = client.post(
                    f"/api/emergency-changes/{change_id}/authorize",
                    json={"authorization_notes": "允许运维窗口内执行"},
                )
                self.assertEqual(auth_resp.status_code, 200, auth_resp.text)
                self.assertEqual(auth_resp.json()["status"], "authorized")
                self.assertEqual(auth_resp.json()["authorized_by_user_id"], "authorizer-1")

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                deploy_resp = client.post(
                    f"/api/emergency-changes/{change_id}/deploy",
                    json={"deployment_summary": "22:30 热修复上线"},
                )
                self.assertEqual(deploy_resp.status_code, 200, deploy_resp.text)
                self.assertEqual(deploy_resp.json()["status"], "deployed")

            reviewer_app = self._build_app(current_user_id="reviewer-1", deps=deps)
            with TestClient(reviewer_app) as client:
                close_resp = client.post(
                    f"/api/emergency-changes/{change_id}/close",
                    json={
                        "impact_assessment_summary": "未发现新增偏差",
                        "post_review_summary": "完成根因复盘并补齐正式评审",
                        "capa_actions": "增加回归测试并更新作业指导",
                        "verification_summary": "生产与回滚验证均通过",
                    },
                )
                self.assertEqual(close_resp.status_code, 200, close_resp.text)
                data = close_resp.json()
                self.assertEqual(data["status"], "closed")
                self.assertEqual(data["closed_by_user_id"], "reviewer-1")
                self.assertEqual(
                    [item["action"] for item in data["actions"]],
                    ["requested", "authorized", "deployed", "closed"],
                )
        finally:
            cleanup_dir(td)
