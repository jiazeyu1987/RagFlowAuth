import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.modules.users import writes as user_writes


class _Service:
    def __init__(self):
        self.calls = []

    def create_user(self, *, user_data, created_by):
        self.calls.append(("create_user", {"user_data": user_data, "created_by": created_by}))
        return {"user_id": "u-created"}

    def update_user(self, *, user_id, user_data):
        self.calls.append(("update_user", {"user_id": user_id, "user_data": user_data}))
        return {"user_id": user_id}

    def delete_user(self, user_id):
        self.calls.append(("delete_user", user_id))
        return True


class UsersWritesUnitTest(unittest.TestCase):
    def test_create_user_result_wraps_service_response(self):
        service = _Service()
        user_data = object()

        result = user_writes.create_user_result(
            service=service,
            user_data=user_data,
            created_by="u-admin",
        )

        self.assertEqual(result, {"user": {"user_id": "u-created"}})
        self.assertEqual(
            service.calls,
            [("create_user", {"user_data": user_data, "created_by": "u-admin"})],
        )

    def test_update_user_result_skips_sub_admin_guards_for_admin(self):
        service = _Service()
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=True))
        user_data = SimpleNamespace(group_ids=[7], group_id=None, model_fields_set={"group_ids"})

        with patch.object(user_writes, "assert_sub_admin_group_assignment_only") as assert_only, patch.object(
            user_writes, "assert_manageable_target_user"
        ) as assert_target, patch.object(user_writes, "validate_sub_admin_assignable_group_ids") as validate_groups:
            result = user_writes.update_user_result(
                ctx=ctx,
                user_store=object(),
                service=service,
                user_id="u-1",
                user_data=user_data,
            )

        assert_only.assert_not_called()
        assert_target.assert_not_called()
        validate_groups.assert_not_called()
        self.assertEqual(result, {"user": {"user_id": "u-1"}})
        self.assertEqual(
            service.calls,
            [("update_user", {"user_id": "u-1", "user_data": user_data})],
        )

    def test_update_user_result_validates_manageable_group_assignment_for_sub_admin(self):
        service = _Service()
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=False))
        user_store = object()
        user_data = SimpleNamespace(group_ids=None, group_id=7, model_fields_set={"group_id"})

        with patch.object(user_writes, "assert_sub_admin_group_assignment_only") as assert_only, patch.object(
            user_writes, "assert_manageable_target_user"
        ) as assert_target, patch.object(user_writes, "validate_sub_admin_assignable_group_ids") as validate_groups:
            result = user_writes.update_user_result(
                ctx=ctx,
                user_store=user_store,
                service=service,
                user_id="u-2",
                user_data=user_data,
            )

        assert_only.assert_called_once_with(ctx, user_data)
        assert_target.assert_called_once_with(
            ctx,
            user_store,
            "u-2",
        )
        validate_groups.assert_called_once_with(ctx, group_ids=[7])
        self.assertEqual(result, {"user": {"user_id": "u-2"}})

    def test_update_user_result_allows_empty_group_patch_without_group_validation(self):
        service = _Service()
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=False))
        user_store = object()
        user_data = SimpleNamespace(group_ids=None, group_id=None, model_fields_set=set())

        with patch.object(user_writes, "assert_sub_admin_group_assignment_only") as assert_only, patch.object(
            user_writes, "assert_manageable_target_user"
        ) as assert_target, patch.object(user_writes, "validate_sub_admin_assignable_group_ids") as validate_groups:
            user_writes.update_user_result(
                ctx=ctx,
                user_store=user_store,
                service=service,
                user_id="u-3",
                user_data=user_data,
            )

        assert_only.assert_called_once_with(ctx, user_data)
        assert_target.assert_called_once_with(
            ctx,
            user_store,
            "u-3",
        )
        validate_groups.assert_not_called()

    def test_delete_user_result_returns_result_envelope(self):
        service = _Service()

        result = user_writes.delete_user_result(service=service, user_id="u-9")

        self.assertEqual(result, {"result": {"message": "user_deleted"}})
        self.assertEqual(service.calls, [("delete_user", "u-9")])


if __name__ == "__main__":
    unittest.main()
