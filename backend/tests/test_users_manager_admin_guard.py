import unittest
from types import SimpleNamespace

from backend.models.user import UserUpdate
from backend.services.users.manager import UserManagementError, UserManagementManager


class _FakePort:
    def __init__(self):
        now_ms = 1760000000000
        self.users = {
            'u_admin': SimpleNamespace(
                user_id='u_admin',
                username='admin',
                email='admin@example.com',
                company_id=None,
                department_id=None,
                group_id=None,
                group_ids=[],
                role='admin',
            status='active',
            can_change_password=True,
            disable_login_enabled=False,
            disable_login_until_ms=None,
            max_login_sessions=3,
            idle_timeout_minutes=120,
            created_at_ms=now_ms,
            last_login_at_ms=None,
            ),
            'u_viewer': SimpleNamespace(
                user_id='u_viewer',
                username='alice',
                email='alice@example.com',
                company_id=None,
                department_id=None,
                group_id=None,
                group_ids=[],
                role='viewer',
            status='active',
            can_change_password=True,
            disable_login_enabled=False,
            disable_login_until_ms=None,
            max_login_sessions=3,
            idle_timeout_minutes=120,
            created_at_ms=now_ms,
            last_login_at_ms=None,
            ),
        }

    def list_users(self, **_kwargs):
        return list(self.users.values())

    def get_user(self, user_id: str):
        return self.users.get(user_id)

    def create_user(self, **_kwargs):
        raise NotImplementedError

    def update_user(
        self,
        *,
        user_id: str,
        full_name=None,
        email=None,
        company_id=None,
        department_id=None,
        role=None,
        group_id=None,
        status=None,
        can_change_password=None,
        disable_login_enabled=None,
        disable_login_until_ms=None,
        max_login_sessions=None,
        idle_timeout_minutes=None,
    ):
        user = self.users.get(user_id)
        if not user:
            return None
        if full_name is not None:
            user.full_name = full_name
        if email is not None:
            user.email = email
        if company_id is not None:
            user.company_id = company_id
        if department_id is not None:
            user.department_id = department_id
        if role is not None:
            user.role = role
        if group_id is not None:
            user.group_id = group_id
        if status is not None:
            user.status = status
        if can_change_password is not None:
            user.can_change_password = bool(can_change_password)
        if disable_login_enabled is not None:
            user.disable_login_enabled = bool(disable_login_enabled)
        if disable_login_until_ms is not None:
            user.disable_login_until_ms = int(disable_login_until_ms)
        elif disable_login_enabled is not None and not disable_login_enabled:
            user.disable_login_until_ms = None
        if max_login_sessions is not None:
            user.max_login_sessions = max_login_sessions
        if idle_timeout_minutes is not None:
            user.idle_timeout_minutes = idle_timeout_minutes
        return user

    def delete_user(self, _user_id: str) -> bool:
        raise NotImplementedError

    def update_password(self, _user_id: str, _new_password: str) -> None:
        raise NotImplementedError

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
        return {'active_session_count': 0, 'active_session_last_activity_at_ms': None}

    def get_login_session_summaries(self, _idle_timeout_by_user: dict[str, int | None]):
        return {}


class UserManagementManagerAdminGuardTests(unittest.TestCase):
    def setUp(self):
        self.port = _FakePort()
        self.manager = UserManagementManager(self.port)

    def test_builtin_admin_cannot_be_disabled(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.update_user(user_id='u_admin', user_data=UserUpdate(status='inactive'))
        self.assertEqual('admin_user_cannot_be_disabled', ctx.exception.code)

    def test_non_admin_can_be_disabled(self):
        result = self.manager.update_user(user_id='u_viewer', user_data=UserUpdate(status='inactive'))
        self.assertEqual('inactive', result.status)


if __name__ == '__main__':
    unittest.main()
