import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.modules.auth.router import router as auth_router
from app.core import auth as auth_module


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


class _FakePermissionGroupStore:
    def get_group(self, group_id: int):
        return None


class _FakeDeps:
    def __init__(self):
        self.user_store = _FakeUserStore()
        self.ragflow_service = _FakeRagflowService()
        self.permission_group_store = _FakePermissionGroupStore()


class TestAuthMeAdmin(unittest.TestCase):
    def test_admin_gets_all_permissions_and_kbs(self):
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
            {"can_upload": True, "can_review": True, "can_download": True, "can_delete": True},
        )
        self.assertEqual(body["accessible_kbs"], ["kb_a", "kb_b"])

