import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.modules.users import management_access


class UsersManagementAccessUnitTest(unittest.TestCase):
    def test_assert_manageable_target_user_skips_lookup_for_admin(self):
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=True))
        user_store = object()

        with patch.object(management_access, "get_manageable_target_user") as get_manageable_target_user:
            management_access.assert_manageable_target_user(ctx, user_store, "u-1")

        get_manageable_target_user.assert_not_called()

    def test_assert_manageable_target_user_delegates_for_sub_admin(self):
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=False))
        user_store = object()

        with patch.object(management_access, "get_manageable_target_user") as get_manageable_target_user:
            management_access.assert_manageable_target_user(ctx, user_store, "u-2")

        get_manageable_target_user.assert_called_once_with(
            ctx,
            user_store,
            "u-2",
            detail=management_access.MANAGEABLE_USER_DETAIL,
        )


if __name__ == "__main__":
    unittest.main()
