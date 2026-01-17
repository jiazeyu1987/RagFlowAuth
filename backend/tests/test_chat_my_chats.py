import unittest

from authx import TokenPayload
from fastapi import FastAPI
from fastapi import Request
from fastapi.testclient import TestClient

from app.core import auth as auth_module
from app.modules.chat.router import router as chat_router


class _FakeUser:
    def __init__(self, *, role: str = "admin", group_id=None):
        self.role = role
        self.group_id = group_id


class _FakeUserStore:
    def get_by_user_id(self, user_id: str):
        return _FakeUser(role="admin", group_id=None)


class _FakePermissionGroupStore:
    def get_group(self, group_id: int):
        return None


class _FakeRagflowChatService:
    def list_chats(self, *args, **kwargs):
        return True  # regression: some RAGFlow deployments return booleans in `data`

    def list_agents(self, *args, **kwargs):
        return False


class _FakeDeps:
    def __init__(self):
        self.user_store = _FakeUserStore()
        self.permission_group_store = _FakePermissionGroupStore()
        self.ragflow_chat_service = _FakeRagflowChatService()


class TestMyChatsEndpoint(unittest.TestCase):
    def test_my_chats_handles_non_list_responses(self):
        app = FastAPI()
        app.state.deps = _FakeDeps()
        app.include_router(chat_router, prefix="/api")

        def _override_get_current_payload(request: Request) -> TokenPayload:  # noqa: ARG001
            return TokenPayload(sub="u1")

        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        with TestClient(app) as client:
            resp = client.get("/api/chats/my")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"chats": [], "count": 0})
