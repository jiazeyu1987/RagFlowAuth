import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.me.router import router as me_router
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
    def __init__(self, db_path: str, *, datasets: list[dict] | None = None):
        all_datasets = list(datasets or [])
        self.user_store = _UserStore(_User())
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.ragflow_service = SimpleNamespace(
            list_datasets=lambda: list(all_datasets),
            list_all_datasets=lambda: list(all_datasets),
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


class TestMeMessagesApiUnit(unittest.TestCase):
    def test_kbs_list_returns_wrapped_payload(self):
        td = make_temp_dir(prefix="ragflowauth_me_kbs_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            deps = _Deps(
                db_path=db_path,
                datasets=[
                    {"id": "kb-2", "name": "KB B"},
                    {"id": "kb-1", "name": "KB A"},
                    {"id": "kb-1", "name": "KB A"},
                    {"id": "", "name": ""},
                ],
            )
            app.state.deps = deps
            app.include_router(me_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/me/kbs")

            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(
                resp.json(),
                {
                    "kbs": {
                        "kb_ids": ["kb-1", "kb-2"],
                        "kb_names": ["KB A", "KB B"],
                    }
                },
            )
        finally:
            cleanup_dir(td)

    def test_messages_list_read_state_and_mark_all(self):
        td = make_temp_dir(prefix="ragflowauth_me_messages_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            deps = _Deps(db_path=db_path)
            app.state.deps = deps
            app.include_router(me_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            deps.notification_manager.upsert_channel(
                channel_id="inapp-main",
                channel_type="in_app",
                name="In App",
                enabled=True,
                config={},
            )
            jobs = deps.notification_manager.notify_event(
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1", "filename": "a.txt"},
                recipients=[{"user_id": "u1", "username": "admin1", "email": "admin1@example.com"}],
                dedupe_key="doc-1:step-1",
            )
            self.assertEqual(len(jobs), 1)
            job_id = int(jobs[0]["job_id"])
            deps.notification_manager.dispatch_pending(limit=10)

            with TestClient(app) as client:
                list_resp = client.get("/api/me/messages")
                self.assertEqual(list_resp.status_code, 200, list_resp.text)
                self.assertEqual(int(list_resp.json().get("total") or 0), 1)
                self.assertEqual(int(list_resp.json().get("unread_count") or 0), 1)

                read_resp = client.patch(
                    f"/api/me/messages/{job_id}/read-state",
                    json={"read": True},
                )
                self.assertEqual(read_resp.status_code, 200, read_resp.text)
                self.assertIsNotNone(read_resp.json()["message"].get("read_at_ms"))

                unread_resp = client.get("/api/me/messages?unread_only=true")
                self.assertEqual(unread_resp.status_code, 200, unread_resp.text)
                self.assertEqual(int(unread_resp.json().get("total") or 0), 1)
                self.assertEqual(int(unread_resp.json().get("count") or 0), 0)
                self.assertEqual(int(unread_resp.json().get("unread_count") or 0), 0)

                unread_again_resp = client.patch(
                    f"/api/me/messages/{job_id}/read-state",
                    json={"read": False},
                )
                self.assertEqual(unread_again_resp.status_code, 200, unread_again_resp.text)
                self.assertIsNone(unread_again_resp.json()["message"].get("read_at_ms"))

                mark_all_resp = client.post("/api/me/messages/mark-all-read", json={})
                self.assertEqual(mark_all_resp.status_code, 200, mark_all_resp.text)
                self.assertEqual(int(mark_all_resp.json()["result"].get("updated_count") or 0), 1)

                final_resp = client.get("/api/me/messages?unread_only=true")
                self.assertEqual(final_resp.status_code, 200, final_resp.text)
                self.assertEqual(int(final_resp.json().get("unread_count") or 0), 0)
        finally:
            cleanup_dir(td)
