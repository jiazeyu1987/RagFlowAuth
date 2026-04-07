import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.admin_notifications.router import router as admin_notifications_router
from backend.database.schema.ensure import ensure_schema
from backend.services.notification import NotificationService, NotificationStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self, role: str):
        self.user_id = "u1"
        self.username = "admin1"
        self.full_name = "Admin User"
        self.email = "admin1@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.company_id = 1
        self.department_id = 1


class _UserStore:
    def __init__(self, user: _User):
        self._user = user
        self.assignments: dict[str, str | None] = {}

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user

    def list_users(self, status: str | None = None, limit: int = 100):  # noqa: ARG002
        if status and status != self._user.status:
            return []
        return [self._user]

    def sync_employee_user_ids(self, assignments: dict[str, str | None]) -> None:
        self.assignments.update(assignments or {})
        if self._user.user_id in self.assignments:
            self._user.employee_user_id = self.assignments[self._user.user_id]


class _NoopAdapter:
    def validate_channel(self, **kwargs):  # noqa: ARG002
        return "access-token"

    def send(self, **kwargs):  # noqa: ARG002
        return None


class _Deps:
    def __init__(self, db_path: str):
        self.user_store = _UserStore(_User(role="admin"))
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.org_directory_store = SimpleNamespace(
            get_company=lambda *_args, **_kwargs: None,
            get_department=lambda *_args, **_kwargs: None,
            list_employees=lambda: [],
        )
        self.org_structure_manager = self.org_directory_store
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.notification_manager = NotificationService(
            store=NotificationStore(db_path=db_path),
            email_adapter=_NoopAdapter(),
            dingtalk_adapter=_NoopAdapter(),
            retry_interval_seconds=1,
        )
        self.notification_service = self.notification_manager


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestAdminNotificationsApiUnit(unittest.TestCase):
    def test_channel_crud_retry_and_resend_job(self):
        td = make_temp_dir(prefix="ragflowauth_notification_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            deps = _Deps(db_path=db_path)
            app.state.deps = deps
            app.include_router(admin_notifications_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                put_resp = client.put(
                    "/api/admin/notifications/channels/email-main",
                    json={
                        "channel_type": "email",
                        "name": "Main Email",
                        "enabled": True,
                        "config": {"to_emails": ["qa@example.com"]},
                    },
                )
                self.assertEqual(put_resp.status_code, 200, put_resp.text)
                self.assertEqual(put_resp.json()["channel"].get("channel_id"), "email-main")

                list_channels_resp = client.get("/api/admin/notifications/channels")
                self.assertEqual(list_channels_resp.status_code, 200, list_channels_resp.text)
                self.assertEqual(list_channels_resp.json().get("count"), 1)

                list_rules_resp = client.get("/api/admin/notifications/rules")
                self.assertEqual(list_rules_resp.status_code, 200, list_rules_resp.text)
                self.assertGreaterEqual(int(list_rules_resp.json().get("count") or 0), 1)

                update_rules_resp = client.put(
                    "/api/admin/notifications/rules",
                    json={
                        "items": [
                            {
                                "event_type": "review_todo_approval",
                                "enabled_channel_types": ["email"],
                            }
                        ]
                    },
                )
                self.assertEqual(update_rules_resp.status_code, 200, update_rules_resp.text)

                dispatch_empty_resp = client.post("/api/admin/notifications/dispatch?limit=10")
                self.assertEqual(dispatch_empty_resp.status_code, 200, dispatch_empty_resp.text)
                self.assertEqual(dispatch_empty_resp.json()["dispatch"], {"total": 0, "items": []})

                jobs = deps.notification_manager.notify_event(
                    event_type="review_todo_approval",
                    payload={"doc_id": "doc-1", "filename": "spec.txt"},
                    recipients=[
                        {
                            "user_id": "u1",
                            "username": "admin1",
                            "email": "admin1@example.com",
                        }
                    ],
                    dedupe_key="review_todo_approval:doc-1:step-1",
                    channel_types=["email"],
                )
                job_id = int(jobs[0]["job_id"])

                list_jobs_resp = client.get("/api/admin/notifications/jobs?limit=10")
                self.assertEqual(list_jobs_resp.status_code, 200, list_jobs_resp.text)
                self.assertGreaterEqual(int(list_jobs_resp.json().get("count") or 0), 1)
                self.assertEqual(list_jobs_resp.json()["items"][0]["channel_type"], "email")

                filtered_jobs_resp = client.get(
                    "/api/admin/notifications/jobs?limit=10&event_type=review_todo_approval&channel_type=email&status=queued"
                )
                self.assertEqual(filtered_jobs_resp.status_code, 200, filtered_jobs_resp.text)
                self.assertEqual(int(filtered_jobs_resp.json().get("count") or 0), 1)

                retry_resp = client.post(f"/api/admin/notifications/jobs/{job_id}/retry")
                self.assertEqual(retry_resp.status_code, 200, retry_resp.text)
                self.assertEqual(retry_resp.json()["job"].get("status"), "sent")

                resend_resp = client.post(f"/api/admin/notifications/jobs/{job_id}/resend")
                self.assertEqual(resend_resp.status_code, 200, resend_resp.text)
                self.assertEqual(resend_resp.json()["job"].get("status"), "sent")
                self.assertEqual(resend_resp.json()["job"].get("source_job_id"), job_id)

                logs_resp = client.get(f"/api/admin/notifications/jobs/{job_id}/logs?limit=10")
                self.assertEqual(logs_resp.status_code, 200, logs_resp.text)
                self.assertGreaterEqual(int(logs_resp.json().get("count") or 0), 1)
        finally:
            cleanup_dir(td)

    def test_rebuild_dingtalk_recipient_map_endpoint(self):
        td = make_temp_dir(prefix="ragflowauth_notification_api_recipient_map")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            deps = _Deps(db_path=db_path)
            deps.notification_manager.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "real-key",
                    "app_secret": "real-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {"legacy": "legacy-user"},
                },
            )
            deps.org_structure_manager = SimpleNamespace(
                get_company=lambda *_args, **_kwargs: None,
                get_department=lambda *_args, **_kwargs: None,
                list_employees=lambda: [
                    SimpleNamespace(
                        employee_user_id="ding-u1",
                        name="Admin User",
                        company_id=1,
                        department_id=1,
                    )
                ],
            )
            app.state.deps = deps
            app.include_router(admin_notifications_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.post(
                    "/api/admin/notifications/channels/ding-main/recipient-map/rebuild-from-org",
                    json={},
                )
                self.assertEqual(resp.status_code, 200, resp.text)
                self.assertEqual(
                    resp.json(),
                    {
                        "channel_id": "ding-main",
                        "org_user_count": 1,
                        "directory_entry_count": 1,
                        "alias_entry_count": 0,
                        "invalid_org_user_count": 0,
                        "invalid_org_users": [],
                    },
                )
        finally:
            cleanup_dir(td)
