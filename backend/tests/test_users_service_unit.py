import unittest

from fastapi import HTTPException

from backend.app.modules.users.service import UsersService
from backend.services.users.manager import UserManagementError


class _FakeManager:
    def __init__(self):
        self.calls = []

    def create_user(self, **kwargs):
        self.calls.append(("create_user", kwargs))
        return {"user_id": "u-created"}

    def get_user(self, user_id):
        self.calls.append(("get_user", {"user_id": user_id}))
        return {"user_id": user_id}

    def update_user(self, **kwargs):
        self.calls.append(("update_user", kwargs))
        return {"user_id": kwargs["user_id"]}

    def delete_user(self, user_id):
        self.calls.append(("delete_user", {"user_id": user_id}))
        return None

    def list_users(self, **kwargs):
        self.calls.append(("list_users", kwargs))
        return ["user-a"]

    def reset_password(self, user_id, new_password):
        self.calls.append(("reset_password", {"user_id": user_id, "new_password": new_password}))
        return None


class _ErrorManager:
    def create_user(self, **kwargs):
        raise UserManagementError("user_already_exists", status_code=409)


class UsersServiceUnitTest(unittest.TestCase):
    def test_list_users_delegates_to_manager(self):
        service = UsersService(object())
        fake_manager = _FakeManager()
        service._manager = fake_manager

        result = service.list_users(
            q="alice",
            role="viewer",
            group_id=7,
            company_id=1,
            department_id=11,
            status="active",
            created_from_ms=1000,
            created_to_ms=2000,
            manager_user_id="u-sub",
            limit=50,
        )

        self.assertEqual(result, ["user-a"])
        self.assertEqual(
            fake_manager.calls,
            [
                (
                    "list_users",
                    {
                        "q": "alice",
                        "role": "viewer",
                        "group_id": 7,
                        "company_id": 1,
                        "department_id": 11,
                        "status": "active",
                        "created_from_ms": 1000,
                        "created_to_ms": 2000,
                        "manager_user_id": "u-sub",
                        "limit": 50,
                    },
                )
            ],
        )

    def test_reset_password_delegates_to_manager(self):
        service = UsersService(object())
        fake_manager = _FakeManager()
        service._manager = fake_manager

        service.reset_password(user_id="u-1", new_password="Password123")

        self.assertEqual(
            fake_manager.calls,
            [("reset_password", {"user_id": "u-1", "new_password": "Password123"})],
        )

    def test_create_get_update_and_delete_delegate_through_common_helpers(self):
        service = UsersService(object())
        fake_manager = _FakeManager()
        service._manager = fake_manager

        self.assertEqual(
            service.create_user(user_data="payload", created_by="u-admin"),
            {"user_id": "u-created"},
        )
        self.assertEqual(service.get_user(user_id="u-2"), {"user_id": "u-2"})
        self.assertEqual(
            service.update_user(user_id="u-3", user_data="patch"),
            {"user_id": "u-3"},
        )
        service.delete_user(user_id="u-4")

        self.assertEqual(
            fake_manager.calls,
            [
                ("create_user", {"user_data": "payload", "created_by": "u-admin"}),
                ("get_user", {"user_id": "u-2"}),
                ("update_user", {"user_id": "u-3", "user_data": "patch"}),
                ("delete_user", {"user_id": "u-4"}),
            ],
        )

    def test_create_user_translates_domain_errors_to_http_exception(self):
        service = UsersService(object())
        service._manager = _ErrorManager()

        with self.assertRaises(HTTPException) as ctx:
            service.create_user(user_data=object(), created_by="u-admin")

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "user_already_exists")


if __name__ == "__main__":
    unittest.main()
