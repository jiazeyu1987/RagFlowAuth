import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.inbox.router import router as inbox_router
from backend.database.schema.ensure import ensure_schema
from backend.services.notification import NotificationService, NotificationStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self):
        self.user_id = "u1"
        self.username = "admin1"
        self.email = "admin1@example.com"
        self.role = "admin"
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.company_id = 1
        self.department_id = 1


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _NoopAdapter:
    def send(self, **kwargs):  # noqa: ARG002
        return None


class _Deps:
    def __init__(self, db_path: str):
        self.user_store = _UserStore(_User())
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.ragflow_service = SimpleNamespace(
            list_datasets=lambda: [],
            list_all_datasets=lambda: [],
            normalize_dataset_ids=lambda refs: list(refs),
            resolve_dataset_names=lambda refs: list(refs),
            get_dataset_index=lambda: {"by_id": {}, "by_name": {}},
        )
        self.knowledge_directory_manager = SimpleNamespace(resolve_dataset_ids_from_nodes=lambda *_args, **_kwargs: [])
        self.org_directory_store = SimpleNamespace(
            get_company=lambda *_args, **_kwargs: None,
            get_department=lambda *_args, **_kwargs: None,
        )
        self.org_structure_manager = self.org_directory_store
        self.notification_manager = NotificationService(
            store=NotificationStore(db_path=db_path),
            email_adapter=_NoopAdapter(),
            dingtalk_adapter=_NoopAdapter(),
            retry_interval_seconds=1,
        )
        self.notification_service = self.notification_manager


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestInboxApiUnit(unittest.TestCase):
    def test_inbox_routes_keep_message_center_contract(self):
        td = make_temp_dir(prefix="ragflowauth_inbox_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            deps = _Deps(db_path=db_path)
            app.state.deps = deps
            app.include_router(inbox_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            deps.notification_manager.upsert_channel(
                channel_id="inapp-main",
                channel_type="in_app",
                name="In App",
                enabled=True,
                config={},
            )
            items = deps.notification_manager.notify_event(
                event_type="operation_approval_todo",
                payload={
                    "title": "Approval Pending",
                    "body": "Please process approval req-1",
                    "link_path": "/approvals?request_id=req-1",
                    "request_id": "req-1",
                },
                recipients=[{"user_id": "u1", "username": "admin1", "email": "admin1@example.com"}],
                dedupe_key="operation_approval_todo:req-1",
                channel_types=["in_app"],
            )
            self.assertEqual(len(items), 1)
            deps.notification_manager.dispatch_pending(limit=10)
            inbox_id = str(items[0]["job_id"])

            with TestClient(app) as client:
                list_resp = client.get("/api/inbox")
                self.assertEqual(list_resp.status_code, 200, list_resp.text)
                self.assertEqual(int(list_resp.json().get("count") or 0), 1)
                self.assertEqual(int(list_resp.json().get("unread_count") or 0), 1)
                self.assertEqual(list_resp.json()["items"][0]["inbox_id"], inbox_id)
                self.assertEqual(list_resp.json()["items"][0]["title"], "Approval Pending")
                self.assertEqual(list_resp.json()["items"][0]["status"], "unread")

                read_resp = client.post(f"/api/inbox/{inbox_id}/read", json={})
                self.assertEqual(read_resp.status_code, 200, read_resp.text)
                self.assertEqual(
                    read_resp.json(),
                    {
                        "result": {
                            "message": "inbox_notification_marked_read",
                            "inbox_id": inbox_id,
                            "status": "read",
                        }
                    },
                )

                after_read_resp = client.get("/api/inbox?unread_only=true")
                self.assertEqual(after_read_resp.status_code, 200, after_read_resp.text)
                self.assertEqual(int(after_read_resp.json().get("count") or 0), 0)
                self.assertEqual(int(after_read_resp.json().get("unread_count") or 0), 0)

                second_items = deps.notification_manager.notify_event(
                    event_type="operation_approval_submitted",
                    payload={
                        "title": "Request Submitted",
                        "body": "req-2",
                        "link_path": "/approvals?request_id=req-2",
                        "request_id": "req-2",
                    },
                    recipients=[{"user_id": "u1", "username": "admin1", "email": "admin1@example.com"}],
                    dedupe_key="operation_approval_submitted:req-2",
                    channel_types=["in_app"],
                )
                self.assertEqual(len(second_items), 1)
                deps.notification_manager.dispatch_pending(limit=10)

                hidden_resp = client.get("/api/inbox?unread_only=true")
                self.assertEqual(hidden_resp.status_code, 200, hidden_resp.text)
                self.assertEqual(int(hidden_resp.json().get("count") or 0), 0)
                self.assertEqual(int(hidden_resp.json().get("unread_count") or 0), 0)

                mark_all_resp = client.post("/api/inbox/read-all", json={})
                self.assertEqual(mark_all_resp.status_code, 200, mark_all_resp.text)
                self.assertEqual(int(mark_all_resp.json()["result"].get("updated") or 0), 1)
                self.assertEqual(int(mark_all_resp.json()["result"].get("unread_count") or 0), 0)
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
