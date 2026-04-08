import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.modules.auth.router import router as auth_router
from backend.app.core import auth as auth_module


class _FakeUser:
    def __init__(self):
        self.user_id = "u_admin"
        self.username = "admin"
        self.email = "admin@example.com"
        self.role = "admin"
        self.status = "active"
        self.group_id = None
        self.group_ids = []


class _FakeUserStore:
    def get_by_user_id(self, user_id: str):
        return _FakeUser()


class _FakeRagflowService:
    def list_datasets(self):
        return [{"name": "kb_b"}, {"name": "kb_a"}, {"name": ""}, {}]

    def list_all_kb_names(self):
        return ["kb_a", "kb_b"]

    def list_all_datasets(self):
        return [{"id": "id_a", "name": "kb_a"}, {"id": "id_b", "name": "kb_b"}]


class _FakeRagflowChatService:
    def list_chats(self, *args, **kwargs):  # noqa: ARG002
        return [{"id": "c1"}, {"id": "c2"}]

    def list_agents(self, *args, **kwargs):  # noqa: ARG002
        return [{"id": "a1"}]

    def list_all_chat_ids(self, *args, **kwargs):  # noqa: ARG002
        return ["agent_a1", "chat_c1", "chat_c2"]


class _FakePermissionGroupStore:
    def get_group(self, group_id: int):
        return None


class _FakeDeps:
    def __init__(self):
        self.user_store = _FakeUserStore()
        self.ragflow_service = _FakeRagflowService()
        self.ragflow_chat_service = _FakeRagflowChatService()
        self.permission_group_store = _FakePermissionGroupStore()


class TestAuthMeAdmin(unittest.TestCase):
    def test_admin_gets_permission_admin_scope_without_file_ops(self):
        app = FastAPI()
        app.state.deps = _FakeDeps()
        app.include_router(auth_router, prefix="/api/auth")

        def _override_get_current_payload(request: Request) -> TokenPayload:  # noqa: ARG001
            return TokenPayload(sub="u_admin")

        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        with TestClient(app) as client:
            resp = client.get("/api/auth/me")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["role"], "admin")
        self.assertEqual(
            body["permissions"],
            {
                "can_upload": True,
                "can_review": True,
                "can_download": True,
                "can_copy": True,
                "can_delete": True,
                "can_manage_kb_directory": True,
                "can_view_kb_config": True,
                "can_view_tools": True,
                "accessible_tools": [],
            },
        )
        self.assertEqual(body["accessible_kbs"], ["kb_a", "kb_b"])
        self.assertEqual(body["accessible_kb_ids"], ["id_a", "id_b"])
        self.assertEqual(body["accessible_chats"], ["agent_a1", "chat_c1", "chat_c2"])
        self.assertEqual(body["capabilities"]["users"]["manage"], {"scope": "all", "targets": []})
        self.assertEqual(body["capabilities"]["tools"]["view"], {"scope": "all", "targets": []})
        self.assertEqual(body["capabilities"]["kb_documents"]["view"], {"scope": "all", "targets": []})
