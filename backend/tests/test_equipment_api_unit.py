import os
import unittest
from datetime import date, timedelta
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.equipment.router import router as equipment_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.equipment import EquipmentService
from backend.services.notification import NotificationManager, NotificationStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def __init__(self, users):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)


class _Deps:
    def __init__(self, *, db_path: str, users):
        audit_store = AuditLogStore(db_path=db_path)
        self.user_store = _UserStore(users)
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_tool_permission_store = SimpleNamespace(list_tool_ids=lambda *_args, **_kwargs: [])
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.audit_log_store = audit_store
        self.audit_log_manager = AuditLogManager(store=audit_store)
        self.notification_manager = NotificationManager(
            store=NotificationStore(db_path=db_path),
            audit_log_manager=self.audit_log_manager,
        )
        self.notification_manager.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="站内信",
            enabled=True,
            config={},
        )
        self.equipment_service = EquipmentService(
            db_path=db_path,
            notification_manager=self.notification_manager,
        )


def _make_user(*, user_id: str, role: str):
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


class EquipmentApiUnitTests(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(equipment_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_non_admin_cannot_create_equipment_asset(self):
        td = make_temp_dir(prefix="ragflowauth_equipment_forbidden")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "viewer-1": _make_user(user_id="viewer-1", role="viewer"),
                "owner-1": _make_user(user_id="owner-1", role="viewer"),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="viewer-1", deps=deps)

            with TestClient(app) as client:
                response = client.post(
                    "/api/equipment/assets",
                    json={
                        "asset_code": "EQ-001",
                        "equipment_name": "压差测试仪",
                        "owner_user_id": "owner-1",
                    },
                )
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["detail"], "equipment_lifecycle_forbidden")
        finally:
            cleanup_dir(td)

    def test_admin_can_create_transition_export_and_dispatch_reminder(self):
        td = make_temp_dir(prefix="ragflowauth_equipment_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "owner-1": _make_user(user_id="owner-1", role="viewer"),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="admin-1", deps=deps)
            due_date = (date.today() + timedelta(days=3)).isoformat()

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/equipment/assets",
                    json={
                        "asset_code": "EQ-001",
                        "equipment_name": "压差测试仪",
                        "owner_user_id": "owner-1",
                        "location": "一号实验室",
                        "retirement_due_date": due_date,
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                equipment = create_resp.json()
                self.assertEqual(equipment["status"], "purchased")
                self.assertEqual(len(equipment["status_history"]), 1)

                reminder_resp = client.post("/api/equipment/reminders/dispatch?window_days=7")
                self.assertEqual(reminder_resp.status_code, 200, reminder_resp.text)
                self.assertEqual(reminder_resp.json()["count"], 1)
                jobs = deps.notification_manager.list_jobs(event_type="equipment_due_soon", limit=10)
                self.assertEqual(len(jobs), 1)

                accept_resp = client.post(
                    f"/api/equipment/assets/{equipment['equipment_id']}/accept",
                    json={"status_date": date.today().isoformat(), "notes": "完成入厂验收"},
                )
                self.assertEqual(accept_resp.status_code, 200, accept_resp.text)
                self.assertEqual(accept_resp.json()["status"], "accepted")

                commission_resp = client.post(
                    f"/api/equipment/assets/{equipment['equipment_id']}/commission",
                    json={"status_date": date.today().isoformat()},
                )
                self.assertEqual(commission_resp.status_code, 200, commission_resp.text)
                self.assertEqual(commission_resp.json()["status"], "in_service")

                retire_resp = client.post(
                    f"/api/equipment/assets/{equipment['equipment_id']}/retire",
                    json={"status_date": date.today().isoformat(), "notes": "设备报废"},
                )
                self.assertEqual(retire_resp.status_code, 200, retire_resp.text)
                retired = retire_resp.json()
                self.assertEqual(retired["status"], "retired")
                self.assertEqual(len(retired["status_history"]), 4)

                export_resp = client.get("/api/equipment/assets/export")
                self.assertEqual(export_resp.status_code, 200, export_resp.text)
                self.assertIn("text/csv", export_resp.headers["content-type"])
                self.assertIn("equipment-assets.csv", export_resp.headers["content-disposition"])
                self.assertIn("EQ-001", export_resp.text)

            events = deps.audit_log_manager.list_events(source="equipment_lifecycle", limit=20)["items"]
            actions = {item["action"] for item in events}
            self.assertIn("equipment_asset_create", actions)
            self.assertIn("equipment_due_dispatch", actions)
            self.assertIn("equipment_asset_accept", actions)
            self.assertIn("equipment_asset_commission", actions)
            self.assertIn("equipment_asset_retire", actions)
            self.assertIn("equipment_asset_export", actions)
        finally:
            cleanup_dir(td)

    def test_sub_admin_can_create_transition_export_and_dispatch_reminder(self):
        td = make_temp_dir(prefix="ragflowauth_equipment_sub_admin_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "sub-admin-1": _make_user(user_id="sub-admin-1", role="sub_admin"),
                "owner-1": _make_user(user_id="owner-1", role="viewer"),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="sub-admin-1", deps=deps)
            due_date = (date.today() + timedelta(days=3)).isoformat()

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/equipment/assets",
                    json={
                        "asset_code": "EQ-002",
                        "equipment_name": "温湿度计",
                        "owner_user_id": "owner-1",
                        "location": "二号实验室",
                        "retirement_due_date": due_date,
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                equipment = create_resp.json()

                reminder_resp = client.post("/api/equipment/reminders/dispatch?window_days=7")
                self.assertEqual(reminder_resp.status_code, 200, reminder_resp.text)

                accept_resp = client.post(
                    f"/api/equipment/assets/{equipment['equipment_id']}/accept",
                    json={"status_date": date.today().isoformat(), "notes": "完成入厂验收"},
                )
                self.assertEqual(accept_resp.status_code, 200, accept_resp.text)

                export_resp = client.get("/api/equipment/assets/export")
                self.assertEqual(export_resp.status_code, 200, export_resp.text)
                self.assertIn("EQ-002", export_resp.text)
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
