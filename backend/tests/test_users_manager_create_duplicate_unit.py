import unittest

from backend.models.user import UserCreate
from backend.services.users.manager import UserManagementError, UserManagementManager


class _FakePort:
    def list_users(self, **_kwargs):
        return []

    def get_user(self, _user_id: str):
        return None

    def create_user(self, **_kwargs):
        raise ValueError("Username 'admin' already exists")

    def update_user(self, **_kwargs):
        return None

    def delete_user(self, _user_id: str) -> bool:
        return False

    def update_password(self, _user_id: str, _new_password: str) -> None:
        return None

    def set_user_permission_groups(self, _user_id: str, _group_ids: list[int]) -> None:
        return None

    def enforce_login_session_limit(self, _user_id: str, _max_sessions: int) -> list[str]:
        return []

    def get_permission_group(self, group_id: int):
        if group_id == 1:
            return {"group_id": 1, "group_name": "viewer"}
        return None

    def get_group_by_name(self, name: str):
        if name == "viewer":
            return {"group_id": 1, "group_name": "viewer"}
        return None

    def get_company(self, _company_id: int):
        return None

    def get_department(self, _department_id: int):
        return None

    def get_login_session_summary(self, _user_id: str, _idle_timeout_minutes: int | None):
        return {"active_session_count": 0, "active_session_last_activity_at_ms": None}

    def get_login_session_summaries(self, _idle_timeout_by_user: dict[str, int | None]):
        return {}


class UserManagementManagerCreateDuplicateTests(unittest.TestCase):
    def test_create_user_duplicate_username_maps_to_business_error(self):
        manager = UserManagementManager(_FakePort())
        with self.assertRaises(UserManagementError) as ctx:
            manager.create_user(
                user_data=UserCreate(
                    username="admin",
                    password="Pass1234",
                    group_ids=[1],
                ),
                created_by="u_admin",
            )
        self.assertEqual("username_already_exists", ctx.exception.code)
        self.assertEqual(409, ctx.exception.status_code)


if __name__ == "__main__":
    unittest.main()
