import unittest
from types import SimpleNamespace

from backend.app.modules.users.repo import UsersRepo


class _AuthSessionStore:
    def __init__(self, revoked_ids):
        self.revoked_ids = list(revoked_ids)
        self.calls = []

    def enforce_user_session_limit(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.revoked_ids)


class _AuditStore:
    def __init__(self):
        self.events = []

    def log_event(self, **kwargs):
        self.events.append(kwargs)


class _UserStore:
    def __init__(self):
        self.user = SimpleNamespace(
            user_id="u1",
            username="alice",
            company_id=None,
            department_id=None,
        )

    def get_by_user_id(self, user_id: str):
        if user_id == "u1":
            return self.user
        return None


class _OrgDirectoryStore:
    def get_company(self, _company_id: int):
        return None

    def get_department(self, _department_id: int):
        return None


class TestUsersRepoUnit(unittest.TestCase):
    def test_enforce_login_session_limit_logs_audit_when_revoked(self):
        deps = SimpleNamespace(
            auth_session_store=_AuthSessionStore(["sid_a", "sid_b"]),
            audit_log_store=_AuditStore(),
            user_store=_UserStore(),
            org_directory_store=_OrgDirectoryStore(),
        )
        repo = UsersRepo(deps)

        revoked = repo.enforce_login_session_limit("u1", 1)

        self.assertEqual(revoked, ["sid_a", "sid_b"])
        self.assertEqual(len(deps.auth_session_store.calls), 1)
        self.assertEqual(len(deps.audit_log_store.events), 1)
        event = deps.audit_log_store.events[0]
        self.assertEqual(event.get("action"), "auth_session_kick")
        self.assertEqual(event.get("actor"), "u1")
        self.assertEqual(event.get("source"), "auth")
        self.assertEqual(event.get("meta", {}).get("reason"), "policy_limit_updated")
        self.assertEqual(event.get("meta", {}).get("kicked_count"), 2)

    def test_enforce_login_session_limit_no_audit_when_nothing_revoked(self):
        deps = SimpleNamespace(
            auth_session_store=_AuthSessionStore([]),
            audit_log_store=_AuditStore(),
            user_store=_UserStore(),
            org_directory_store=_OrgDirectoryStore(),
        )
        repo = UsersRepo(deps)

        revoked = repo.enforce_login_session_limit("u1", 3)

        self.assertEqual(revoked, [])
        self.assertEqual(len(deps.audit_log_store.events), 0)


if __name__ == "__main__":
    unittest.main()
