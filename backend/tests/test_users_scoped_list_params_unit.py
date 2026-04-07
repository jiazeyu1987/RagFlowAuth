import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.modules.users.scoped_list_params import (
    build_ctx_scoped_list_users_kwargs,
    build_scoped_list_users_kwargs,
)


class UsersScopedListParamsUnitTest(unittest.TestCase):
    def test_build_scoped_list_users_kwargs_uses_scoped_company_and_manager(self):
        self.assertEqual(
            build_scoped_list_users_kwargs(
                q="alice",
                role="viewer",
                group_id=7,
                scoped_company_id=1,
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

    def test_build_ctx_scoped_list_users_kwargs_resolves_scope_before_building_kwargs(self):
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=False))

        with patch(
            "backend.app.modules.users.scoped_list_params.resolve_user_list_scope",
            return_value=(1, "u-sub"),
        ) as resolver:
            self.assertEqual(
                build_ctx_scoped_list_users_kwargs(
                    ctx,
                    q="alice",
                    role="viewer",
                    group_id=7,
                    company_id=2,
                    department_id=11,
                    status="active",
                    created_from_ms=1000,
                    created_to_ms=2000,
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

        resolver.assert_called_once_with(ctx, 2)


if __name__ == "__main__":
    unittest.main()
