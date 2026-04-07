import unittest

from backend.app.modules.users.list_params import build_list_users_kwargs


class UsersListParamsUnitTest(unittest.TestCase):
    def test_build_list_users_kwargs_returns_expected_payload_shape(self):
        self.assertEqual(
            build_list_users_kwargs(
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
            ),
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


if __name__ == "__main__":
    unittest.main()
