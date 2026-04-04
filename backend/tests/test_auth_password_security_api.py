import hashlib
import os
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.modules.auth.router import router as auth_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.services.notification import NotificationService, NotificationStore
from backend.services.users import UserStore, is_legacy_password_hash, verify_password
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _NoopAdapter:
    def send(self, **kwargs):  # noqa: ARG002
        return None


class _Deps:
    def __init__(self, db_path: str, user_store):
        self.user_store = user_store
        self.auth_session_store = None
        self.auth_session_manager = None
        self.audit_log_store = AuditLogStore(db_path=db_path)
        self.notification_service = NotificationService(
            store=NotificationStore(db_path=db_path),
            email_adapter=_NoopAdapter(),
            dingtalk_adapter=_NoopAdapter(),
            retry_interval_seconds=1,
        )
        self.notification_manager = self.notification_service


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
            app.state.deps = _Deps(db_path, user_store)
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
            user_store.create_user(username="admin1", password="AdminPass123", role="admin", email="admin1@example.com")
            user_store.create_user(username="subadmin1", password="AdminPass456", role="sub_admin", email="subadmin1@example.com")

            app = FastAPI()
            app.state.deps = _Deps(db_path, user_store)
            app.state.deps.notification_service.upsert_channel(
                channel_id="inapp-main",
                channel_type="in_app",
                name="In App",
                enabled=True,
                config={},
            )
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

            jobs = app.state.deps.notification_service.list_jobs(limit=10)
            self.assertEqual(len(jobs), 2)
            self.assertTrue(all(job["status"] == "sent" for job in jobs))
            recipients = {job["recipient_username"] for job in jobs}
            self.assertEqual(recipients, {"admin1", "subadmin1"})
            self.assertTrue(all(job["event_type"] == "credential_lockout" for job in jobs))

            total, events = app.state.deps.audit_log_store.list_events(action="credential_lockout")
            self.assertEqual(total, 1)
            self.assertEqual(events[0].resource_id, user_store.get_by_username("bob").user_id)
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
