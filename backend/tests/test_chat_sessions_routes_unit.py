import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.chat.router import router as chat_router
from backend.services.chat_message_sources_store import content_hash_hex


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
    def __init__(self, *, sessions_result, create_session_result=None):
        self._sessions_result = sessions_result
        self._create_session_result = create_session_result
        self.create_session_calls = []

    def list_sessions(self, *args, **kwargs):
        return self._sessions_result

    def create_session(self, **kwargs):
        self.create_session_calls.append(kwargs)
        if callable(self._create_session_result):
            return self._create_session_result(**kwargs)
        if self._create_session_result is not None:
            return self._create_session_result
        return {
            "id": "session-created",
            "name": kwargs["name"],
            "messages": [],
        }


class _FakeChatSessionStore:
    def __init__(self, *, sessions_result):
        self._sessions_result = sessions_result

    def get_user_sessions(self, chat_id: str, user_id: str):
        return self._sessions_result


class _FakeChatMessageSourcesStore:
    def __init__(self, *, sources_map=None):
        self._sources_map = dict(sources_map or {})
        self.calls = []

    def get_sources_map(self, *, chat_id: str, session_id: str, content_hashes: list[str]):
        self.calls.append(
            {
                "chat_id": chat_id,
                "session_id": session_id,
                "content_hashes": list(content_hashes),
            }
        )
        return {content_hash: self._sources_map[content_hash] for content_hash in content_hashes if content_hash in self._sources_map}


class _FakeDeps:
    def __init__(self, *, ragflow_sessions, local_sessions, create_session_result=None, sources_map=None):
        self.user_store = _FakeUserStore()
        self.permission_group_store = _FakePermissionGroupStore()
        self.ragflow_chat_service = _FakeRagflowChatService(
            sessions_result=ragflow_sessions,
            create_session_result=create_session_result,
        )
        self.chat_session_store = _FakeChatSessionStore(sessions_result=local_sessions)
        self.chat_message_sources_store = _FakeChatMessageSourcesStore(sources_map=sources_map)


class TestChatSessionsEndpoint(unittest.TestCase):
    def _make_client(
        self,
        *,
        ragflow_sessions,
        local_sessions,
        create_session_result=None,
        sources_map=None,
    ) -> TestClient:
        app = FastAPI()
        app.state.deps = _FakeDeps(
            ragflow_sessions=ragflow_sessions,
            local_sessions=local_sessions,
            create_session_result=create_session_result,
            sources_map=sources_map,
        )
        app.include_router(chat_router, prefix="/api")

        def _override_get_current_payload(request: Request) -> TokenPayload:  # noqa: ARG001
            return TokenPayload(sub="u1")

        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_create_session_reads_name_from_json_body(self):
        with self._make_client(ragflow_sessions=[], local_sessions=[]) as client:
            resp = client.post("/api/chats/chat-1/sessions", json={"name": "Created From Body"})

            self.assertEqual(
                client.app.state.deps.ragflow_chat_service.create_session_calls,
                [{"chat_id": "chat-1", "name": "Created From Body", "user_id": "u1"}],
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "id": "session-created",
                "name": "Created From Body",
                "messages": [],
            },
        )

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

    def test_list_sessions_normalizes_legacy_assistant_answer_and_restores_sources(self):
        legacy_answer = "legacy assistant answer"
        sources = [{"doc_id": "doc-1", "dataset": "kb-1", "filename": "Spec.pdf"}]
        ragflow_sessions = [{"id": "s-upstream", "name": "Legacy", "messages": [{"role": "assistant", "answer": legacy_answer}]}]

        with self._make_client(
            ragflow_sessions=ragflow_sessions,
            local_sessions=[],
            sources_map={content_hash_hex(legacy_answer): sources},
        ) as client:
            resp = client.get("/api/chats/chat-1/sessions")

            self.assertEqual(
                client.app.state.deps.chat_message_sources_store.calls,
                [
                    {
                        "chat_id": "chat-1",
                        "session_id": "s-upstream",
                        "content_hashes": [content_hash_hex(legacy_answer)],
                    }
                ],
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "sessions": [
                    {
                        "id": "s-upstream",
                        "name": "Legacy",
                        "messages": [{"role": "assistant", "content": legacy_answer, "sources": sources}],
                    }
                ],
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
