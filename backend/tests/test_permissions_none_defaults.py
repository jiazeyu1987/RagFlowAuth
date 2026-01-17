import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core import auth as auth_module
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router


class _User:
    def __init__(self, *, role: str = "viewer", group_id=None, group_ids=None):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = role
        self.status = "active"
        self.group_id = group_id
        self.group_ids = group_ids or []


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _RagflowService:
    def list_datasets(self):
        return [{"name": "kb_a"}, {"name": "kb_b"}]


class _RagflowChatService:
    def list_chats(self, *args, **kwargs):  # noqa: ARG002
        return [{"id": "c1", "name": "Chat1"}]

    def list_agents(self, *args, **kwargs):  # noqa: ARG002
        return [{"id": "a1", "name": "Agent1"}]


class _Deps:
    def __init__(self, user: _User):
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore()
        self.ragflow_service = _RagflowService()
        self.ragflow_chat_service = _RagflowChatService()


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestNoneDefaults(unittest.TestCase):
    def test_auth_me_non_admin_no_group_returns_none_access(self):
        app = FastAPI()
        app.state.deps = _Deps(_User(role="viewer", group_id=None, group_ids=[]))
        app.include_router(auth_router, prefix="/api/auth")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        with TestClient(app) as client:
            resp = client.get("/api/auth/me")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["permissions"], {"can_upload": False, "can_review": False, "can_download": False, "can_delete": False})
        self.assertEqual(body["accessible_kbs"], [])
        self.assertEqual(body["accessible_chats"], [])

    def test_chat_list_non_admin_no_group_returns_empty(self):
        app = FastAPI()
        app.state.deps = _Deps(_User(role="viewer", group_id=None, group_ids=[]))
        app.include_router(chat_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        with TestClient(app) as client:
            resp = client.get("/api/chats")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"chats": [], "count": 0})

