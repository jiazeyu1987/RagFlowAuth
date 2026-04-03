import hashlib
import os
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.modules.auth.router import router as auth_router
from backend.database.schema.ensure import ensure_schema
from backend.services.users import UserStore, is_legacy_password_hash, verify_password
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _Deps:
    def __init__(self, user_store):
        self.user_store = user_store
        self.auth_session_store = None
        self.auth_session_manager = None
        self.audit_log_store = None


class TestAuthPasswordSecurityApi(unittest.TestCase):
    def test_login_upgrades_legacy_hash(self):
        td = make_temp_dir(prefix="ragflowauth_auth_password_upgrade")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            user_store = UserStore(db_path=db_path)
            user = user_store.create_user(username="alice", password="OldPass123", role="viewer")
            legacy_hash = hashlib.sha256("OldPass123".encode("utf-8")).hexdigest()
            with user_store._get_connection() as conn:  # noqa: SLF001
                conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (legacy_hash, user.user_id))
                conn.commit()

            app = FastAPI()
            app.state.deps = _Deps(user_store)
            app.include_router(auth_router, prefix="/api/auth")

            with TestClient(app) as client:
                response = client.post("/api/auth/login", json={"username": "alice", "password": "OldPass123"})

            self.assertEqual(response.status_code, 200)
            upgraded_user = user_store.get_by_user_id(user.user_id)
            self.assertFalse(is_legacy_password_hash(upgraded_user.password_hash))
            self.assertTrue(verify_password("OldPass123", upgraded_user.password_hash)[0])
        finally:
            cleanup_dir(td)

    def test_login_locks_after_repeated_failures(self):
        td = make_temp_dir(prefix="ragflowauth_auth_password_lock")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            user_store = UserStore(db_path=db_path)
            user_store.create_user(username="bob", password="GoodPass123", role="viewer")

            app = FastAPI()
            app.state.deps = _Deps(user_store)
            app.include_router(auth_router, prefix="/api/auth")

            with TestClient(app) as client:
                last_response = None
                for _ in range(5):
                    last_response = client.post("/api/auth/login", json={"username": "bob", "password": "WrongPass123"})
                self.assertIsNotNone(last_response)
                self.assertEqual(last_response.status_code, 423)
                self.assertEqual(last_response.json()["detail"], "credentials_locked")

                locked_response = client.post("/api/auth/login", json={"username": "bob", "password": "GoodPass123"})
                self.assertEqual(locked_response.status_code, 423)
                self.assertEqual(locked_response.json()["detail"], "credentials_locked")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
