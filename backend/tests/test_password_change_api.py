"""
Integration tests for password change API endpoint.

Tests the /api/auth/password endpoint which allows authenticated users
to change their own password (not admin reset).
"""
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core.authz import AuthContext, get_auth_context
from backend.app.modules.auth.router import router as auth_router
from backend.app.core import auth as auth_module
from backend.services.users import User, hash_password, verify_password


class _FakeUser:
    def __init__(self, user_id="u_test", username="testuser", password_hash=None):
        self.user_id = user_id
        self.username = username
        self.email = "test@example.com"
        self.role = "user"
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.password_hash = password_hash or hash_password("OldPass123")


class _FakeUserStore:
    def __init__(self):
        self.user = _FakeUser()
        self.update_called = False
        self.update_password_hash = None
        self.password_reused = False

    def get_by_user_id(self, user_id: str):
        return self.user

    def update_password(self, user_id: str, new_password: str) -> None:
        self.update_called = True
        self.update_password_hash = hash_password(new_password)

    def password_matches_recent_history(self, user_id: str, password: str, *, limit: int = 5) -> bool:  # noqa: ARG002
        return self.password_reused


class _FakeDeps:
    def __init__(self):
        self.user_store = _FakeUserStore()


class _TenantOnlyDeps:
    def __init__(self):
        self.user_store = _FakeUserStore()


class TestPasswordChangeAPI(unittest.TestCase):
    """Test password change API endpoint"""

    def setUp(self):
        """Set up test app and client"""
        self.app = FastAPI()
        self.deps = _FakeDeps()
        self.app.state.deps = self.deps
        self.app.include_router(auth_router, prefix="/api/auth")

        # Mock authentication to return test user
        def _override_get_current_payload(request: Request) -> MagicMock:  # noqa: ARG001
            payload = MagicMock()
            payload.sub = "u_test"
            return payload

        self.app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

    def test_change_password_success(self):
        """Successful password change with valid data"""
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "NewPass456"
                }
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["message"], "密码修改成功")

        # Verify password was updated in store
        self.assertTrue(self.deps.user_store.update_called)
        self.assertTrue(verify_password("NewPass456", self.deps.user_store.update_password_hash)[0])

    def test_change_password_wrong_old_password(self):
        """Reject password change when old password is incorrect"""
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "WrongPass123",
                    "new_password": "NewPass456"
                }
            )

        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("旧密码错误", body["detail"])

        # Verify password was NOT updated
        self.assertFalse(self.deps.user_store.update_called)

    def test_change_password_invalid_new_password_too_short(self):
        """Reject password change when new password is too short"""
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "Abc12"
                }
            )

        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("密码不符合要求", body["detail"])

    def test_change_password_invalid_new_password_no_numbers(self):
        """Reject password change when new password has no numbers"""
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "nopassword"
                }
            )

        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("密码不符合要求", body["detail"])

    def test_change_password_invalid_new_password_common(self):
        """Reject password change when new password is too common"""
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "password"
                }
            )

        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("密码不符合要求", body["detail"])

    def test_change_password_same_as_old(self):
        """Reject password change when new password matches old password"""
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "OldPass123"
                }
            )

        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("新密码不能与旧密码相同", body["detail"])

    def test_change_password_missing_fields(self):
        """Reject password change when required fields are missing"""
        with TestClient(self.app) as client:
            # Missing old_password
            resp = client.put(
                "/api/auth/password",
                json={"new_password": "NewPass456"}
            )
            self.assertEqual(resp.status_code, 422)  # Validation error

            # Missing new_password
            resp = client.put(
                "/api/auth/password",
                json={"old_password": "OldPass123"}
            )
            self.assertEqual(resp.status_code, 422)  # Validation error

    def test_change_password_rejects_recent_password_reuse(self):
        self.deps.user_store.password_reused = True

        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "NewPass456"
                }
            )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "new_password_reused_from_recent_history")
        self.assertFalse(self.deps.user_store.update_called)

    def test_change_password_unauthenticated(self):
        """Reject password change when user is not authenticated"""
        # Remove auth override
        self.app.dependency_overrides = {}

        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "NewPass456"
                }
            )

        self.assertEqual(resp.status_code, 401)

    def test_change_password_user_not_found(self):
        """Handle case where user is not found in store"""
        # Make get_by_user_id return None
        self.deps.user_store.get_by_user_id = lambda user_id: None

        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "NewPass456"
                }
            )

        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertIn("detail", body)

    def test_change_password_updates_global_user_store_even_if_auth_context_is_tenant_scoped(self):
        tenant_deps = _TenantOnlyDeps()

        def _override_auth_context(request: Request) -> AuthContext:  # noqa: ARG001
            return AuthContext(
                deps=tenant_deps,
                payload=MagicMock(sub="u_test"),
                user=self.deps.user_store.user,
                snapshot=MagicMock(),
            )

        self.app.dependency_overrides[get_auth_context] = _override_auth_context

        with TestClient(self.app) as client:
            resp = client.put(
                "/api/auth/password",
                json={
                    "old_password": "OldPass123",
                    "new_password": "NewPass456",
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(self.deps.user_store.update_called)
        self.assertFalse(tenant_deps.user_store.update_called)
        self.assertTrue(verify_password("NewPass456", self.deps.user_store.update_password_hash)[0])


if __name__ == "__main__":
    unittest.main()
