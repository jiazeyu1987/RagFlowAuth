import unittest

from authx import TokenPayload
from fastapi import FastAPI
from fastapi import Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.chat.router import router as chat_router


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
    def __init__(self, *, chats_result=True):
        self._chats_result = chats_result

    def list_chats(self, *args, **kwargs):
        return self._chats_result  # regression: some RAGFlow deployments return invalid `data` payloads

    def list_agents(self, *args, **kwargs):
        return False


class _FakeDeps:
    def __init__(self, *, chats_result=True):
        self.user_store = _FakeUserStore()
        self.permission_group_store = _FakePermissionGroupStore()
        self.ragflow_chat_service = _FakeRagflowChatService(chats_result=chats_result)


class TestMyChatsEndpoint(unittest.TestCase):
    def _make_client(self, *, chats_result=True) -> TestClient:
        app = FastAPI()
        app.state.deps = _FakeDeps(chats_result=chats_result)
        app.include_router(chat_router, prefix="/api")

        def _override_get_current_payload(request: Request) -> TokenPayload:  # noqa: ARG001
            return TokenPayload(sub="u1")

        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_my_chats_handles_non_list_responses(self):
        with self._make_client(chats_result=True) as client:
            resp = client.get("/api/chats/my")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"chats": [], "count": 0})

    def test_my_chats_drops_non_dict_items(self):
        chats = [True, {"id": "c1", "name": "n1"}, 1, {"id": "c2", "name": "n2"}]
        with self._make_client(chats_result=chats) as client:
            resp = client.get("/api/chats/my")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"chats": [{"id": "c1", "name": "n1"}, {"id": "c2", "name": "n2"}], "count": 2})
