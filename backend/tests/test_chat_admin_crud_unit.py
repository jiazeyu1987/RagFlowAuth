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
    def __init__(self, *, role: str):
        self._role = role

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return _FakeUser(role=self._role, group_id=None)


class _FakePermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _FakeRagflowChatService:
    def __init__(self):
        self.created = []
        self.updated = []
        self.deleted = []

    def list_chats(self, *args, **kwargs):  # noqa: ARG002
        return []

    def create_chat(self, payload):
        self.created.append(payload)
        return {"id": "c1", **payload}

    def update_chat(self, chat_id, payload):
        self.updated.append((chat_id, payload))
        return {"id": chat_id, **payload}

    def delete_chat(self, chat_id):
        self.deleted.append(chat_id)
        return True


class _FakeDeps:
    def __init__(self, *, role: str):
        self.user_store = _FakeUserStore(role=role)
        self.permission_group_store = _FakePermissionGroupStore()
        self.ragflow_chat_service = _FakeRagflowChatService()


class TestChatAdminCrudUnit(unittest.TestCase):
    def _make_client(self, *, role: str) -> tuple[TestClient, _FakeDeps]:
        app = FastAPI()
        deps = _FakeDeps(role=role)
        app.state.deps = deps
        app.include_router(chat_router, prefix="/api")

        def _override_get_current_payload(request: Request) -> TokenPayload:  # noqa: ARG001
            return TokenPayload(sub="u1")

        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app), deps

    def test_admin_can_create_update_delete_chat(self):
        client, deps = self._make_client(role="admin")
        with client:
            r1 = client.post("/api/chats", json={"name": "n1", "foo": "bar", "id": "x"})
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r1.json()["chat"]["id"], "c1")
            self.assertEqual(deps.ragflow_chat_service.created[0].get("id"), None)

            r2 = client.put("/api/chats/c1", json={"name": "n2", "id": "x"})
            self.assertEqual(r2.status_code, 200)
            self.assertEqual(r2.json()["chat"]["id"], "c1")
            self.assertEqual(deps.ragflow_chat_service.updated[0][0], "c1")
            self.assertEqual(deps.ragflow_chat_service.updated[0][1].get("id"), None)

            r3 = client.delete("/api/chats/c1")
            self.assertEqual(r3.status_code, 200)
            self.assertEqual(r3.json(), {"ok": True})
            self.assertEqual(deps.ragflow_chat_service.deleted, ["c1"])

    def test_non_admin_forbidden(self):
        client, _deps = self._make_client(role="user")
        with client:
            r1 = client.post("/api/chats", json={"name": "n1"})
            self.assertEqual(r1.status_code, 403)
            self.assertEqual(r1.json()["detail"], "admin_required")

            r2 = client.put("/api/chats/c1", json={"name": "n2"})
            self.assertEqual(r2.status_code, 403)
            self.assertEqual(r2.json()["detail"], "admin_required")

            r3 = client.delete("/api/chats/c1")
            self.assertEqual(r3.status_code, 403)
            self.assertEqual(r3.json()["detail"], "admin_required")

