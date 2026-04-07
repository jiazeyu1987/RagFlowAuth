import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.modules.users import reads as user_reads


class _Service:
    def __init__(self):
        self.calls = []

    def list_users(self, **kwargs):
        self.calls.append(("list_users", kwargs))
        return ["user-a"]

    def get_user(self, user_id):
        self.calls.append(("get_user", user_id))
        return {"user_id": user_id}


class UsersReadsUnitTest(unittest.TestCase):
    def test_list_users_result_uses_scoped_kwargs(self):
        service = _Service()
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=False))

        with patch.object(
            user_reads,
            "build_ctx_scoped_list_users_kwargs",
            return_value={
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
        ) as builder:
            result = user_reads.list_users_result(
                ctx=ctx,
                service=service,
                q="alice",
                role="viewer",
                group_id=7,
                company_id=2,
                department_id=11,
                status="active",
                created_from_ms=1000,
                created_to_ms=2000,
                limit=50,
            )

        self.assertEqual(result, ["user-a"])
        builder.assert_called_once_with(
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
        )
        self.assertEqual(
            service.calls,
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

    def test_get_user_result_checks_visibility_for_sub_admin(self):
        service = _Service()
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=False))
        user_store = object()

        with patch.object(user_reads, "assert_manageable_target_user") as assert_manageable_target_user:
            result = user_reads.get_user_result(
                ctx=ctx,
                user_store=user_store,
                service=service,
                user_id="u-1",
            )

        assert_manageable_target_user.assert_called_once_with(
            ctx,
            user_store,
            "u-1",
        )
        self.assertEqual(result, {"user_id": "u-1"})
        self.assertEqual(service.calls, [("get_user", "u-1")])

    def test_get_user_result_skips_visibility_check_for_admin(self):
        service = _Service()
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=True))
        user_store = object()

        with patch.object(user_reads, "assert_manageable_target_user") as assert_manageable_target_user:
            result = user_reads.get_user_result(
                ctx=ctx,
                user_store=user_store,
                service=service,
                user_id="u-2",
            )

        assert_manageable_target_user.assert_called_once_with(
            ctx,
            user_store,
            "u-2",
        )
        self.assertEqual(result, {"user_id": "u-2"})
        self.assertEqual(service.calls, [("get_user", "u-2")])


if __name__ == "__main__":
    unittest.main()
