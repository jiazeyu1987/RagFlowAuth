import os
import unittest
from datetime import date, timedelta
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.maintenance.router import router as maintenance_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.equipment import EquipmentService
from backend.services.maintenance import MaintenanceService
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
        self.equipment_service = EquipmentService(db_path=db_path, notification_manager=self.notification_manager)
        self.maintenance_service = MaintenanceService(db_path=db_path, notification_manager=self.notification_manager)


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


class MaintenanceApiUnitTests(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(maintenance_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_maintenance_workflow_dispatches_reminders_and_updates_equipment(self):
        td = make_temp_dir(prefix="ragflowauth_maintenance_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "owner-1": _make_user(user_id="owner-1", role="viewer"),
            }
            deps = _Deps(db_path=db_path, users=users)
            equipment = deps.equipment_service.create_asset(
                asset_code="EQ-MN-001",
                equipment_name="恒温箱",
                owner_user_id="owner-1",
                actor_user_id="admin-1",
            )
            deps.equipment_service.transition_status(
                equipment_id=equipment["equipment_id"],
                action="accept",
                actor_user_id="admin-1",
                status_date=date.today().isoformat(),
            )
            deps.equipment_service.transition_status(
                equipment_id=equipment["equipment_id"],
                action="commission",
                actor_user_id="admin-1",
                status_date=date.today().isoformat(),
            )
            app = self._build_app(current_user_id="admin-1", deps=deps)
            planned_due = (date.today() + timedelta(days=1)).isoformat()
            next_due = (date.today() + timedelta(days=60)).isoformat()

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/maintenance/records",
                    json={
                        "equipment_id": equipment["equipment_id"],
                        "responsible_user_id": "owner-1",
                        "maintenance_type": "preventive",
                        "planned_due_date": planned_due,
                        "summary": "安排季度保养。",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                record = create_resp.json()
                self.assertEqual(record["status"], "planned")

                reminder_resp = client.post("/api/maintenance/reminders/dispatch?window_days=7")
                self.assertEqual(reminder_resp.status_code, 200, reminder_resp.text)
                self.assertEqual(reminder_resp.json()["count"], 1)
                self.assertEqual(len(deps.notification_manager.list_jobs(event_type="maintenance_due_soon", limit=10)), 1)

                execution_resp = client.post(
                    f"/api/maintenance/records/{record['record_id']}/record",
                    json={
                        "performed_at_ms": 1712193600000,
                        "summary": "完成预防性维护。",
                        "outcome_summary": "设备运行正常。",
                        "next_due_date": next_due,
                        "attachments": [
                            {
                                "attachment_id": "att-m-1",
                                "filename": "maintenance.pdf",
                                "mime_type": "application/pdf",
                                "storage_ref": "s3://evidence/maintenance.pdf",
                                "evidence_role": "maintenance_report",
                            }
                        ],
                    },
                )
                self.assertEqual(execution_resp.status_code, 200, execution_resp.text)
                self.assertEqual(execution_resp.json()["status"], "recorded")

                approve_resp = client.post(
                    f"/api/maintenance/records/{record['record_id']}/approve",
                    json={"notes": "批准归档。"},
                )
                self.assertEqual(approve_resp.status_code, 200, approve_resp.text)
                approved = approve_resp.json()
                self.assertEqual(approved["status"], "approved")
                self.assertEqual(approved["approved_by_user_id"], "admin-1")

                export_resp = client.get("/api/maintenance/records/export")
                self.assertEqual(export_resp.status_code, 200, export_resp.text)
                self.assertIn("text/csv", export_resp.headers["content-type"])
                self.assertIn(record["record_id"], export_resp.text)

            asset = deps.equipment_service.get_asset(equipment["equipment_id"])
            self.assertEqual(asset["status"], "in_service")
            self.assertEqual(asset["next_maintenance_due_date"], next_due)

            events = deps.audit_log_manager.list_events(source="maintenance", limit=20)["items"]
            actions = {item["action"] for item in events}
            self.assertIn("maintenance_record_create", actions)
            self.assertIn("maintenance_due_dispatch", actions)
            self.assertIn("maintenance_record_record", actions)
            self.assertIn("maintenance_record_approve", actions)
            self.assertIn("maintenance_record_export", actions)
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
