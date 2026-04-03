import unittest
from types import SimpleNamespace

from backend.models.user import UserCreate, UserUpdate
from backend.services.users.manager import UserManagementError, UserManagementManager


def _make_user(
    user_id: str,
    *,
    username: str,
    company_id: int = 1,
    department_id: int = 10,
    status: str = "active",
    manager_user_id: str | None = None,
):
    return SimpleNamespace(
        user_id=user_id,
        username=username,
        full_name=username.title(),
        email=f"{username}@example.com",
        manager_user_id=manager_user_id,
        role="viewer",
        group_id=1,
        group_ids=[1],
        company_id=company_id,
        department_id=department_id,
        status=status,
        can_change_password=True,
        disable_login_enabled=False,
        disable_login_until_ms=None,
        max_login_sessions=3,
        idle_timeout_minutes=120,
        created_at_ms=1,
        last_login_at_ms=None,
        managed_kb_root_node_id=None,
    )


class _FakePort:
    def __init__(self):
        self.users = {
            "mgr-1": _make_user("mgr-1", username="manager_one"),
            "mgr-2": _make_user("mgr-2", username="manager_two", company_id=2),
            "mgr-inactive": _make_user("mgr-inactive", username="manager_inactive", status="inactive"),
            "user-1": _make_user("user-1", username="user_one"),
        }
        self.create_calls: list[dict] = []
        self.update_calls: list[dict] = []

    def list_users(self, **_kwargs):
        return [self.users["user-1"]]

    def get_user(self, user_id: str):
        return self.users.get(str(user_id))

    def create_user(self, **kwargs):
        self.create_calls.append(dict(kwargs))
        user = _make_user(
            "created-1",
            username=str(kwargs["username"]),
            company_id=int(kwargs["company_id"]) if kwargs.get("company_id") is not None else 1,
            department_id=int(kwargs["department_id"]) if kwargs.get("department_id") is not None else 10,
            manager_user_id=kwargs.get("manager_user_id"),
        )
        user.full_name = kwargs.get("full_name")
        user.email = kwargs.get("email")
        self.users[user.user_id] = user
        return user

    def update_user(self, **kwargs):
        self.update_calls.append(dict(kwargs))
        user = self.users.get(str(kwargs["user_id"]))
        if not user:
            return None
        if "manager_user_id" in kwargs:
            value = kwargs.get("manager_user_id")
            user.manager_user_id = str(value).strip() or None if value is not None else user.manager_user_id
        if kwargs.get("company_id") is not None:
            user.company_id = int(kwargs["company_id"])
        return user

    def delete_user(self, _user_id: str) -> bool:
        return False

    def update_password(self, _user_id: str, _new_password: str) -> None:
        return None

    def set_user_permission_groups(self, user_id: str, group_ids: list[int]) -> None:
        user = self.users[str(user_id)]
        user.group_ids = list(group_ids)
        user.group_id = group_ids[0] if group_ids else None

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

    def get_company(self, company_id: int):
        return SimpleNamespace(name=f"Company-{company_id}") if company_id in {1, 2} else None

    def get_department(self, department_id: int):
        if department_id == 10:
            return SimpleNamespace(name="Department-10", path_name="Company-1 / Department-10", company_id=1)
        if department_id == 20:
            return SimpleNamespace(name="Department-20", path_name="Company-2 / Department-20", company_id=2)
        return None

    def get_login_session_summary(self, _user_id: str, _idle_timeout_minutes: int | None):
        return {"active_session_count": 0, "active_session_last_activity_at_ms": None}

    def get_login_session_summaries(self, _idle_timeout_by_user: dict[str, int | None]):
        return {"user-1": {"active_session_count": 0, "active_session_last_activity_at_ms": None}}


class UserManagementManagerManagerUserTests(unittest.TestCase):
    def setUp(self):
        self.port = _FakePort()
        self.manager = UserManagementManager(self.port)

    def test_create_user_accepts_valid_manager_user(self):
        response = self.manager.create_user(
            user_data=UserCreate(
                username="new_user",
                password="Pass1234",
                full_name="New User",
                email="new_user@example.com",
                company_id=1,
                department_id=10,
                manager_user_id="mgr-1",
                group_ids=[1],
            ),
            created_by="admin-1",
        )

        self.assertEqual("mgr-1", self.port.create_calls[0]["manager_user_id"])
        self.assertEqual("mgr-1", response.manager_user_id)
        self.assertEqual("manager_one", response.manager_username)

    def test_create_user_rejects_missing_or_inactive_or_cross_company_manager(self):
        cases = [
            ("manager_user_not_found", "missing-user"),
            ("manager_user_inactive", "mgr-inactive"),
            ("manager_user_company_mismatch", "mgr-2"),
        ]

        for expected_code, manager_user_id in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(UserManagementError) as ctx:
                    self.manager.create_user(
                        user_data=UserCreate(
                            username=f"user_{expected_code}",
                            password="Pass1234",
                            company_id=1,
                            department_id=10,
                            manager_user_id=manager_user_id,
                            group_ids=[1],
                        ),
                        created_by="admin-1",
                    )
                self.assertEqual(expected_code, ctx.exception.code)

    def test_update_user_rejects_self_reference_manager(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.update_user(
                user_id="user-1",
                user_data=UserUpdate(manager_user_id="user-1"),
            )
        self.assertEqual("manager_user_self_reference_not_allowed", ctx.exception.code)

    def test_create_user_rejects_department_from_other_company(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="cross_company_user",
                    password="Pass1234",
                    company_id=1,
                    department_id=20,
                    group_ids=[1],
                ),
                created_by="admin-1",
            )
        self.assertEqual("department_company_mismatch", ctx.exception.code)

    def test_get_user_and_list_users_include_manager_fields(self):
        self.port.users["user-1"].manager_user_id = "mgr-1"

        detail = self.manager.get_user("user-1")
        listing = self.manager.list_users(
            q=None,
            role=None,
            group_id=None,
            company_id=None,
            department_id=None,
            status=None,
            created_from_ms=None,
            created_to_ms=None,
            limit=20,
        )

        self.assertEqual("mgr-1", detail.manager_user_id)
        self.assertEqual("manager_one", detail.manager_username)
        self.assertEqual("mgr-1", listing[0].manager_user_id)
        self.assertEqual("manager_one", listing[0].manager_username)


if __name__ == "__main__":
    unittest.main()
