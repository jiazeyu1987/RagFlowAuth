import os
import tempfile
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.auth_session import AuthSessionError, AuthSessionManager
from backend.services.auth_session_store import AuthSessionStore
from backend.services.users.store import UserStore


class TestAuthSessionManagerUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.user_store = UserStore(self.db_path)
        self.session_store = AuthSessionStore(self.db_path)
        self.manager = AuthSessionManager(port=self.session_store)
        self.user = self.user_store.create_user(username="u1", password="Pass1234")

    def tearDown(self):
        self._tmp.cleanup()

    def test_issue_and_bind_and_validate_refresh_session(self):
        sid = self.manager.issue_session_id_for_login(
            user_id=self.user.user_id,
            max_sessions=3,
            reserve_slots=1,
        )
        self.assertTrue(isinstance(sid, str) and sid)

        self.manager.bind_refresh_session(
            session_id=sid,
            user_id=self.user.user_id,
            refresh_jti="r1",
            expires_at=9_999_999_999,
        )

        self.manager.validate_refresh_session(
            session_id=sid,
            user_id=self.user.user_id,
            idle_timeout_minutes=60,
            refresh_jti="r1",
        )

    def test_validate_access_session_raises_on_idle_timeout(self):
        sid = self.manager.issue_session_id_for_login(
            user_id=self.user.user_id,
            max_sessions=1,
        )
        self.manager.bind_refresh_session(
            session_id=sid,
            user_id=self.user.user_id,
            refresh_jti="r1",
            expires_at=9_999_999_999,
        )

        # Force stale activity directly in store, then validate through manager.
        with self.session_store._conn() as conn:  # noqa: SLF001
            conn.execute(
                "UPDATE auth_login_sessions SET last_activity_at_ms = ? WHERE session_id = ?",
                (0, sid),
            )
            conn.commit()

        with self.assertRaises(AuthSessionError) as cm:
            self.manager.validate_session(
                session_id=sid,
                user_id=self.user.user_id,
                idle_timeout_minutes=1,
                mark_refresh=False,
                touch=False,
            )
        self.assertEqual(cm.exception.code, "idle_timeout")


if __name__ == "__main__":
    unittest.main()
