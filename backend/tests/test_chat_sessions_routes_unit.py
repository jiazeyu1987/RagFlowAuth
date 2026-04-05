import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.chat.router import router as chat_router


class _FakeUser:
    def __init__(self, *, role: str = "admin", group_id=None, user_id: str = "u1"):
        self.role = role
        self.group_id = group_id
        self.user_id = user_id


class _FakeUserStore:
    def get_by_user_id(self, user_id: str):
        return _FakeUser(role="admin", group_id=None)


class _FakePermissionGroupStore:
    def get_group(self, group_id: int):
        return None


class _FakeRagflowChatService:
    def __init__(self, *, sessions_result):
        self._sessions_result = sessions_result

    def list_sessions(self, *args, **kwargs):
        return self._sessions_result


class _FakeChatSessionStore:
    def __init__(self, *, sessions_result):
        self._sessions_result = sessions_result

    def get_user_sessions(self, chat_id: str, user_id: str):
        return self._sessions_result


class _FakeDeps:
    def __init__(self, *, ragflow_sessions, local_sessions):
        self.user_store = _FakeUserStore()
        self.permission_group_store = _FakePermissionGroupStore()
        self.ragflow_chat_service = _FakeRagflowChatService(sessions_result=ragflow_sessions)
        self.chat_session_store = _FakeChatSessionStore(sessions_result=local_sessions)


class TestChatSessionsEndpoint(unittest.TestCase):
    def _make_client(self, *, ragflow_sessions, local_sessions) -> TestClient:
        app = FastAPI()
        app.state.deps = _FakeDeps(ragflow_sessions=ragflow_sessions, local_sessions=local_sessions)
        app.include_router(chat_router, prefix="/api")

        def _override_get_current_payload(request: Request) -> TokenPayload:  # noqa: ARG001
            return TokenPayload(sub="u1")

        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_list_sessions_keeps_local_name_for_upstream_session(self):
        ragflow_sessions = [{"id": "s-upstream", "name": "Ragflow Name", "messages": [{"role": "assistant", "content": "hello"}]}]
        local_sessions = [{"id": "s-upstream", "name": "Local Name", "messages": []}]

        with self._make_client(ragflow_sessions=ragflow_sessions, local_sessions=local_sessions) as client:
            resp = client.get("/api/chats/chat-1/sessions")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "sessions": [{"id": "s-upstream", "name": "Local Name", "messages": [{"role": "assistant", "content": "hello"}]}],
                "count": 1,
            },
        )

    def test_list_sessions_includes_local_only_session(self):
        ragflow_sessions = [{"id": "s-existing", "name": "Existing", "messages": []}]
        local_sessions = [
            {"id": "s-local", "chat_id": "chat-1", "user_id": "u1", "name": "Pending Session", "create_time": 200, "messages": []},
            {"id": "s-existing", "chat_id": "chat-1", "user_id": "u1", "name": "Existing Local", "create_time": 100, "messages": []},
        ]

        with self._make_client(ragflow_sessions=ragflow_sessions, local_sessions=local_sessions) as client:
            resp = client.get("/api/chats/chat-1/sessions")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "sessions": [
                    {
                        "id": "s-local",
                        "chat_id": "chat-1",
                        "user_id": "u1",
                        "name": "Pending Session",
                        "create_time": 200,
                        "messages": [],
                    },
                    {"id": "s-existing", "name": "Existing Local", "messages": []},
                ],
                "count": 2,
            },
        )
