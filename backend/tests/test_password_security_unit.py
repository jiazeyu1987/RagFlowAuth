import hashlib
import os
import unittest
from types import SimpleNamespace

from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.services.electronic_signature import ElectronicSignatureError, ElectronicSignatureService, ElectronicSignatureStore
from backend.services.notification import NotificationService, NotificationStore
from backend.services.users import UserStore, hash_password, is_legacy_password_hash, verify_password
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


SIGN_PASSWORD = "SignPass123"


class _NoopAdapter:
    def send(self, **kwargs):  # noqa: ARG002
        return None


class TestPasswordSecurityUnit(unittest.TestCase):
    def test_verify_password_supports_pbkdf2_and_legacy_sha256(self):
        strong_hash = hash_password(SIGN_PASSWORD)
        ok, needs_rehash = verify_password(SIGN_PASSWORD, strong_hash)
        self.assertTrue(ok)
        self.assertFalse(needs_rehash)

        legacy_hash = hashlib.sha256(SIGN_PASSWORD.encode("utf-8")).hexdigest()
        ok, needs_rehash = verify_password(SIGN_PASSWORD, legacy_hash)
        self.assertTrue(ok)
        self.assertTrue(needs_rehash)
        self.assertTrue(is_legacy_password_hash(legacy_hash))

    def test_password_history_and_credential_lockout_are_persisted(self):
        td = make_temp_dir(prefix="ragflowauth_password_security_store")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = UserStore(db_path=db_path)
            user = store.create_user(username="alice", password="OldPass123", role="viewer")

            store.update_password(user.user_id, "NewPass456")
            self.assertTrue(store.password_matches_recent_history(user.user_id, "OldPass123", limit=5))
            self.assertTrue(store.password_matches_recent_history(user.user_id, "NewPass456", limit=5))
            self.assertFalse(store.password_matches_recent_history(user.user_id, "AnotherPass789", limit=5))

            locked_until = None
            newly_locked = False
            for _ in range(5):
                locked_until, newly_locked = store.record_credential_failure(user.user_id, now_ms=1_000)
            self.assertEqual(locked_until, 1_000 + 15 * 60 * 1000)
            self.assertTrue(newly_locked)

            locked_user = store.get_by_user_id(user.user_id)
            self.assertIsNotNone(locked_user)
            self.assertGreater(int(getattr(locked_user, "credential_locked_until_ms") or 0), 1_000)

            store.clear_credential_failures(user.user_id)
            unlocked_user = store.get_by_user_id(user.user_id)
            self.assertEqual(int(getattr(unlocked_user, "credential_fail_count") or 0), 0)
            self.assertIsNone(getattr(unlocked_user, "credential_locked_until_ms"))
        finally:
            cleanup_dir(td)

    def test_signature_challenge_upgrades_legacy_hash_and_locks_after_failures(self):
        td = make_temp_dir(prefix="ragflowauth_password_security_signature")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            user_store = UserStore(db_path=db_path)
            user = user_store.create_user(username="bob", password=SIGN_PASSWORD, role="reviewer")
            user_store.create_user(username="admin1", password="AdminPass123", role="admin", email="admin1@example.com")
            notification_service = NotificationService(
                store=NotificationStore(db_path=db_path),
                email_adapter=_NoopAdapter(),
                dingtalk_adapter=_NoopAdapter(),
                retry_interval_seconds=1,
            )
            notification_service.upsert_channel(
                channel_id="inapp-main",
                channel_type="in_app",
                name="In App",
                enabled=True,
                config={},
            )
            deps = SimpleNamespace(
                user_store=user_store,
                notification_service=notification_service,
                audit_log_store=AuditLogStore(db_path=db_path),
            )

            legacy_hash = hashlib.sha256(SIGN_PASSWORD.encode("utf-8")).hexdigest()
            with user_store._get_connection() as conn:  # noqa: SLF001
                conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (legacy_hash, user.user_id))
                conn.commit()

            user = user_store.get_by_user_id(user.user_id)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            challenge = service.issue_challenge(user=user, password=SIGN_PASSWORD, user_store=user_store, deps=deps)
            self.assertIn("sign_token", challenge)

            upgraded_user = user_store.get_by_user_id(user.user_id)
            self.assertFalse(is_legacy_password_hash(upgraded_user.password_hash))
            self.assertTrue(verify_password(SIGN_PASSWORD, upgraded_user.password_hash)[0])

            last_error = None
            for _ in range(5):
                try:
                    service.issue_challenge(user=upgraded_user, password="WrongPass123", user_store=user_store, deps=deps)
                except ElectronicSignatureError as exc:  # noqa: PERF203
                    last_error = exc
            self.assertIsNotNone(last_error)
            self.assertEqual(last_error.code, "signature_credentials_locked")

            jobs = notification_service.list_jobs(limit=10)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["status"], "sent")
            self.assertEqual(jobs[0]["event_type"], "credential_lockout")
            self.assertEqual(jobs[0]["recipient_username"], "admin1")

            total, events = deps.audit_log_store.list_events(action="credential_lockout", source="electronic_signature")
            self.assertEqual(total, 1)
            self.assertEqual(events[0].reason, "signature_password_invalid")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
