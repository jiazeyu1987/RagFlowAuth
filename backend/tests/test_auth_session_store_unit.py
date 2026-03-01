import os
import tempfile
import unittest
import uuid

from backend.database.schema.ensure import ensure_schema
from backend.services.auth_session_store import AuthSessionStore
from backend.services.users.store import UserStore


class TestAuthSessionStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.user_store = UserStore(self.db_path)
        self.session_store = AuthSessionStore(self.db_path)
        self.user = self.user_store.create_user(username="u1", password="Pass1234")

    def tearDown(self):
        self._tmp.cleanup()

    def test_enforce_limit_keeps_newest_sessions(self):
        s1 = str(uuid.uuid4())
        s2 = str(uuid.uuid4())
        self.session_store.create_session(
            session_id=s1,
            user_id=self.user.user_id,
            refresh_jti="r1",
            expires_at=9_999_999_999,
            now_ms=1000,
        )
        self.session_store.create_session(
            session_id=s2,
            user_id=self.user.user_id,
            refresh_jti="r2",
            expires_at=9_999_999_999,
            now_ms=2000,
        )

        revoked = self.session_store.enforce_user_session_limit(
            user_id=self.user.user_id,
            max_sessions=1,
            reserve_slots=0,
            now_ms=3000,
        )

        self.assertIn(s1, revoked)
        self.assertNotIn(s2, revoked)
        active = self.session_store.list_active_sessions(user_id=self.user.user_id, now_ms=3000)
        self.assertEqual([s.session_id for s in active], [s2])

    def test_validate_session_idle_timeout(self):
        sid = str(uuid.uuid4())
        self.session_store.create_session(
            session_id=sid,
            user_id=self.user.user_id,
            refresh_jti="r1",
            expires_at=9_999_999_999,
            now_ms=0,
        )

        ok, reason = self.session_store.validate_session(
            session_id=sid,
            user_id=self.user.user_id,
            idle_timeout_minutes=5,
            now_ms=5 * 60 * 1000 + 1,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "idle_timeout")

    def test_validate_session_refresh_jti_mismatch(self):
        sid = str(uuid.uuid4())
        self.session_store.create_session(
            session_id=sid,
            user_id=self.user.user_id,
            refresh_jti="r1",
            expires_at=9_999_999_999,
            now_ms=1000,
        )

        ok, reason = self.session_store.validate_session(
            session_id=sid,
            user_id=self.user.user_id,
            idle_timeout_minutes=60,
            refresh_jti="r2",
            mark_refresh=True,
            now_ms=2000,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "refresh_jti_mismatch")

    def test_active_session_summaries_respect_idle_timeout(self):
        user2 = self.user_store.create_user(username="u2", password="Pass1234")
        s1 = str(uuid.uuid4())
        s2 = str(uuid.uuid4())
        s3 = str(uuid.uuid4())
        self.session_store.create_session(
            session_id=s1,
            user_id=self.user.user_id,
            refresh_jti="r1",
            expires_at=9_999_999_999,
            now_ms=0,
        )
        self.session_store.create_session(
            session_id=s2,
            user_id=self.user.user_id,
            refresh_jti="r2",
            expires_at=9_999_999_999,
            now_ms=9 * 60 * 1000,
        )
        self.session_store.create_session(
            session_id=s3,
            user_id=user2.user_id,
            refresh_jti="r3",
            expires_at=9_999_999_999,
            now_ms=0,
        )

        summaries = self.session_store.get_active_session_summaries(
            idle_timeout_by_user={
                self.user.user_id: 5,
                user2.user_id: 5,
            },
            now_ms=10 * 60 * 1000,
        )

        user1_summary = summaries.get(self.user.user_id) or {}
        user2_summary = summaries.get(user2.user_id) or {}
        self.assertEqual(user1_summary.get("active_session_count"), 1)
        self.assertEqual(user1_summary.get("active_session_last_activity_at_ms"), 9 * 60 * 1000)
        self.assertEqual(user2_summary.get("active_session_count"), 0)
        self.assertIsNone(user2_summary.get("active_session_last_activity_at_ms"))


if __name__ == "__main__":
    unittest.main()
