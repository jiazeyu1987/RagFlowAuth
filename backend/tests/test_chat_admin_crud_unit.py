import unittest

from authx import TokenPayload
from fastapi import FastAPI
from fastapi import Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.chat.router import router as chat_router


class _FakeUser:
    def __init__(self, *, role: str = "admin", group_id=None, user_id: str = "u1"):
        self.user_id = user_id
        self.role = role
        self.group_id = group_id


class _FakeUserStore:
    def __init__(self, *, role: str):
        self._role = role

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return _FakeUser(role=self._role, group_id=None, user_id=user_id)


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

    def get_chat(self, chat_id):
        return {"id": chat_id, "name": f"chat-{chat_id}"}

    def delete_chat(self, chat_id):
        self.deleted.append(chat_id)
        return True


class _FakeChatManagementError(Exception):
    def __init__(self, code: str, *, status_code: int = 403):
        super().__init__(code)
        self.status_code = status_code


class _FakeChatManagementManager:
    def __init__(self, *, manageable_chat_ids=None):
        self.manageable_chat_ids = set(manageable_chat_ids or {"c1"})
        self.validated_payloads = []
        self.recorded = []
        self.cleaned = []
        self.asserted_chat_ids = []

    def validate_chat_payload(self, *, user, payload):  # noqa: ARG002
        self.validated_payloads.append(dict(payload or {}))
        dataset_ids = payload.get("dataset_ids") if isinstance(payload, dict) else None
        if dataset_ids == ["ds_out"]:
            raise _FakeChatManagementError("dataset_out_of_management_scope", status_code=403)

    def assert_chat_manageable(self, *, user, chat_id):  # noqa: ARG002
        self.asserted_chat_ids.append(chat_id)
        if chat_id not in self.manageable_chat_ids:
            raise _FakeChatManagementError("chat_out_of_management_scope", status_code=403)
        return chat_id

    def record_created_chat(self, *, user, chat):
        self.recorded.append((user.user_id, chat.get("id")))

    def cleanup_deleted_chat(self, chat_id):
        self.cleaned.append(chat_id)

    def list_auto_granted_chat_refs(self, user):  # noqa: ARG002
        return frozenset()


class _FakeDeps:
    def __init__(self, *, role: str):
        self.user_store = _FakeUserStore(role=role)
        self.permission_group_store = _FakePermissionGroupStore()
        self.ragflow_chat_service = _FakeRagflowChatService()
        self.chat_management_manager = _FakeChatManagementManager()


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
            self.assertEqual(r3.json(), {"result": {"message": "chat_deleted"}})
            self.assertEqual(deps.ragflow_chat_service.deleted, ["c1"])

    def test_get_chat_returns_named_chat_envelope(self):
        client, _deps = self._make_client(role="admin")
        with client:
            resp = client.get("/api/chats/c1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"chat": {"id": "c1", "name": "chat-c1"}})

    def test_chat_list_fails_fast_on_invalid_service_payload(self):
        client, deps = self._make_client(role="admin")
        deps.ragflow_chat_service.list_chats = lambda *args, **kwargs: ["bad"]  # noqa: ARG005
        with client:
            resp = client.get("/api/chats")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "chat_list_invalid_payload")

    def test_get_chat_fails_fast_on_invalid_service_payload(self):
        client, deps = self._make_client(role="admin")
        deps.ragflow_chat_service.get_chat = lambda chat_id: "bad-payload"  # noqa: ARG005
        with client:
            resp = client.get("/api/chats/c1")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "chat_invalid_payload")

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

    def test_sub_admin_can_create_update_delete_owned_chat(self):
        client, deps = self._make_client(role="sub_admin")
        with client:
            r1 = client.post("/api/chats", json={"name": "n1", "dataset_ids": ["ds_1"]})
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r1.json()["chat"]["id"], "c1")
            self.assertEqual(deps.chat_management_manager.recorded, [("u1", "c1")])
            self.assertEqual(deps.chat_management_manager.validated_payloads[0]["dataset_ids"], ["ds_1"])

            r2 = client.put("/api/chats/c1", json={"name": "n2"})
            self.assertEqual(r2.status_code, 200)
            self.assertEqual(r2.json()["chat"]["id"], "c1")
            self.assertIn("c1", deps.chat_management_manager.asserted_chat_ids)

            r3 = client.delete("/api/chats/c1")
            self.assertEqual(r3.status_code, 200)
            self.assertEqual(r3.json(), {"result": {"message": "chat_deleted"}})
            self.assertEqual(deps.chat_management_manager.cleaned, ["c1"])

    def test_sub_admin_cannot_create_chat_with_out_of_scope_dataset(self):
        client, _deps = self._make_client(role="sub_admin")
        with client:
            resp = client.post("/api/chats", json={"name": "n1", "dataset_ids": ["ds_out"]})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "dataset_out_of_management_scope")

    def test_sub_admin_cannot_update_unowned_chat(self):
        client, deps = self._make_client(role="sub_admin")
        deps.chat_management_manager.manageable_chat_ids = {"owned-chat"}
        with client:
            resp = client.put("/api/chats/c1", json={"name": "n2"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "chat_out_of_management_scope")
