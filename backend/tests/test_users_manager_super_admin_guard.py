import unittest
from types import SimpleNamespace

from backend.models.user import UserUpdate
from backend.services.super_admin import SUPER_ADMIN_USER_ID, SUPER_ADMIN_USERNAME
from backend.services.users.manager import UserManagementError, UserManagementManager


class _FakePort:
    def __init__(self):
        now_ms = 1760000000000
        self.users = {
            SUPER_ADMIN_USER_ID: SimpleNamespace(
                user_id=SUPER_ADMIN_USER_ID,
                username=SUPER_ADMIN_USERNAME,
                email="superadmin@local",
                company_id=None,
                department_id=None,
                group_id=None,
                group_ids=[],
                role="admin",
                status="active",
                max_login_sessions=10,
                idle_timeout_minutes=240,
                created_at_ms=now_ms,
                last_login_at_ms=None,
            ),
            "u_viewer": SimpleNamespace(
                user_id="u_viewer",
                username="alice",
                email="alice@example.com",
                company_id=None,
                department_id=None,
                group_id=None,
                group_ids=[],
                role="viewer",
                status="active",
                max_login_sessions=3,
                idle_timeout_minutes=120,
                created_at_ms=now_ms,
                last_login_at_ms=None,
            ),
        }
        self.deleted_ids: list[str] = []
        self.updated_password_ids: list[str] = []

    def list_users(self, **_kwargs):
        return list(self.users.values())

    def get_user(self, user_id: str):
        return self.users.get(user_id)

    def create_user(self, **_kwargs):
        raise NotImplementedError

    def update_user(self, *, user_id: str, **_kwargs):
        return self.users.get(user_id)

    def delete_user(self, user_id: str) -> bool:
        self.deleted_ids.append(user_id)
        return bool(self.users.pop(user_id, None))

    def update_password(self, user_id: str, _new_password: str) -> None:
        self.updated_password_ids.append(user_id)

    def set_user_permission_groups(self, user_id: str, group_ids: list[int]) -> None:
        user = self.users.get(user_id)
        if user:
            user.group_ids = list(group_ids)

    def enforce_login_session_limit(self, _user_id: str, _max_sessions: int) -> list[str]:
        return []

    def get_permission_group(self, _group_id: int):
        return None

    def get_group_by_name(self, _name: str):
        return None

    def get_company(self, _company_id: int):
        return None

    def get_department(self, _department_id: int):
        return None

    def get_login_session_summary(self, _user_id: str, _idle_timeout_minutes: int | None):
        return {"active_session_count": 0, "active_session_last_activity_at_ms": None}

    def get_login_session_summaries(self, _idle_timeout_by_user: dict[str, int | None]):
        return {}


class UserManagementManagerSuperAdminGuardTests(unittest.TestCase):
    def setUp(self):
        self.port = _FakePort()
        self.manager = UserManagementManager(self.port)

    def test_list_users_hides_super_admin(self):
        users = self.manager.list_users(
            q=None,
            role=None,
            group_id=None,
            company_id=None,
            department_id=None,
            status=None,
            created_from_ms=None,
            created_to_ms=None,
            limit=100,
        )
        usernames = [item.username for item in users]
        self.assertNotIn(SUPER_ADMIN_USERNAME, usernames)
        self.assertIn("alice", usernames)

    def test_get_super_admin_returns_not_found(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.get_user(SUPER_ADMIN_USER_ID)
        self.assertEqual("user_not_found", ctx.exception.code)

    def test_update_super_admin_returns_not_found(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.update_user(user_id=SUPER_ADMIN_USER_ID, user_data=UserUpdate(status="inactive"))
        self.assertEqual("user_not_found", ctx.exception.code)

    def test_delete_super_admin_returns_not_found(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.delete_user(SUPER_ADMIN_USER_ID)
        self.assertEqual("user_not_found", ctx.exception.code)
        self.assertEqual([], self.port.deleted_ids)

    def test_reset_super_admin_password_returns_not_found(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.reset_password(SUPER_ADMIN_USER_ID, "NewPass123")
        self.assertEqual("user_not_found", ctx.exception.code)
        self.assertEqual([], self.port.updated_password_ids)


if __name__ == "__main__":
    unittest.main()
