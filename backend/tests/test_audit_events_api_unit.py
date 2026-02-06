import os
import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.audit.router import router as audit_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self, role: str):
        self.user_id = "u1"
        self.username = "alice"
        self.email = "alice@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.company_id = 1
        self.department_id = 2


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _UserKbPermissionStore:
    def get_user_kbs(self, user_id: str):  # noqa: ARG002
        return []


class _UserChatPermissionStore:
    def get_user_chats(self, user_id: str):  # noqa: ARG002
        return []


class _Deps:
    def __init__(self, user: _User, audit_log_store: AuditLogStore):
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore()
        self.user_kb_permission_store = _UserKbPermissionStore()
        self.user_chat_permission_store = _UserChatPermissionStore()
        self.audit_log_store = audit_log_store


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestAuditEventsApiUnit(unittest.TestCase):
    def test_list_returns_total_and_items(self):
        td = make_temp_dir(prefix="ragflowauth_audit_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = AuditLogStore(db_path=db_path)
            store.log_event(action="auth_login", actor="u1", actor_username="alice", source="auth")
            store.log_event(
                action="document_preview",
                actor="u1",
                actor_username="alice",
                company_id=1,
                department_id=2,
                source="knowledge",
                doc_id="d1",
                filename="a.md",
                kb_id="展厅",
            )

            app = FastAPI()
            app.state.deps = _Deps(_User(role="admin"), store)
            app.include_router(audit_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/audit/events?limit=50&action=document_preview&username=alice&company_id=1")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIsInstance(data.get("total"), int)
            self.assertIsInstance(data.get("items"), list)
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["action"], "document_preview")
            self.assertEqual(data["items"][0]["filename"], "a.md")
        finally:
            cleanup_dir(td)

