import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Response

from backend.models.auth import LoginRequest
from backend.services import auth_flow_service
from backend.services.user_store import hash_password


class _UserStore:
    def __init__(self, user):
        self._user = user
        self.last_login_user_id = None

    def get_by_username(self, username: str):
        if username == self._user.username:
            return self._user
        return None

    def get_by_user_id(self, user_id: str):
        if user_id == self._user.user_id:
            return self._user
        return None

    def update_last_login(self, user_id: str):
        self.last_login_user_id = user_id


class _OrgDirectoryStore:
    def get_company(self, _company_id: int):
        return None

    def get_department(self, _department_id: int):
        return None


class _AuditStore:
    def __init__(self):
        self.events = []

    def log_event(self, **kwargs):
        self.events.append(kwargs)


class _SessionManager:
    def __init__(self):
        self.issue_calls = []
        self.bind_calls = []

    def issue_session_for_login(self, **kwargs):
        self.issue_calls.append(kwargs)
        return "sid_new", ["sid_old_1", "sid_old_2"]

    def bind_refresh_session(self, **kwargs):
        self.bind_calls.append(kwargs)


class TestAuthFlowServiceUnit(unittest.TestCase):
    def test_login_logs_session_kick_audit_when_limit_exceeded(self):
        user = SimpleNamespace(
            user_id="u1",
            username="alice",
            password_hash=hash_password("Pass1234"),
            status="active",
            max_login_sessions=1,
            company_id=None,
            department_id=None,
        )
        deps = SimpleNamespace(
            user_store=_UserStore(user),
            auth_session_store=None,
            auth_session_manager=_SessionManager(),
            audit_log_store=_AuditStore(),
            org_directory_store=_OrgDirectoryStore(),
        )
        credentials = LoginRequest(username="alice", password="Pass1234")
        response = Response()

        with (
            patch("backend.services.auth_flow_service.auth.create_refresh_token", return_value="refresh_token"),
            patch("backend.services.auth_flow_service.auth.create_access_token", return_value="access_token"),
            patch(
                "backend.services.auth_flow_service.auth.verify_token",
                return_value=SimpleNamespace(jti="rj1", exp=9_999_999_999),
            ),
            patch("backend.services.auth_flow_service.auth.set_access_cookies"),
            patch("backend.services.auth_flow_service.auth.set_refresh_cookies"),
        ):
            token = auth_flow_service.login(
                credentials=credentials,
                response=response,
                deps=deps,
            )

        self.assertEqual(token.access_token, "access_token")
        self.assertEqual(token.refresh_token, "refresh_token")
        self.assertEqual(deps.user_store.last_login_user_id, "u1")
        self.assertEqual(len(deps.auth_session_manager.issue_calls), 1)
        self.assertEqual(len(deps.auth_session_manager.bind_calls), 1)

        actions = [e.get("action") for e in deps.audit_log_store.events]
        self.assertEqual(actions, ["auth_session_kick", "auth_login"])
        kick_event = deps.audit_log_store.events[0]
        self.assertEqual(kick_event.get("actor"), "u1")
        self.assertEqual(kick_event.get("source"), "auth")
        self.assertEqual(kick_event.get("meta", {}).get("reason"), "session_limit_exceeded")
        self.assertEqual(kick_event.get("meta", {}).get("kicked_count"), 2)


if __name__ == "__main__":
    unittest.main()
