import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.auth.router import router as auth_router
from backend.services.users import hash_password


class _FakeUser:
    def __init__(self):
        self.user_id = "builtin_super_admin"
        self.username = "SuperAdmin"
        self.email = "superadmin@local"
        self.role = "admin"
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.password_hash = hash_password("SuperAdmin")


class _FakeUserStore:
    def __init__(self):
        self.user = _FakeUser()
        self.update_called = False

    def get_by_user_id(self, _user_id: str):
        return self.user

    def update_password(self, _user_id: str, _new_password: str) -> None:
        self.update_called = True


class _FakeDeps:
    def __init__(self):
        self.user_store = _FakeUserStore()


class TestPasswordChangeSuperAdminAPI(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.deps = _FakeDeps()
        self.app.state.deps = self.deps
        self.app.include_router(auth_router, prefix="/api/auth")

        def _override_get_current_payload(request: Request) -> MagicMock:  # noqa: ARG001
            payload = MagicMock()
            payload.sub = "builtin_super_admin"
            return payload

        self.app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

    def test_super_admin_password_is_fixed(self):
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={"old_password": "SuperAdmin", "new_password": "AnyNew123"},
            )
        self.assertEqual(resp.status_code, 403)
        body = resp.json()
        self.assertEqual("super_admin_password_fixed", body.get("detail"))
        self.assertFalse(self.deps.user_store.update_called)


if __name__ == "__main__":
    unittest.main()
