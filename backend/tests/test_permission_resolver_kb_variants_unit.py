import unittest

from fastapi import HTTPException

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope, assert_kb_allowed


class TestPermissionResolverKbVariantsUnit(unittest.TestCase):
    def test_assert_kb_allowed_accepts_variant_list(self):
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=True,
            can_delete=False,
            kb_scope=ResourceScope.SET,
            kb_names=frozenset({"c1521554db2d11f0ab20d6899ff928cb"}),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
        )

        assert_kb_allowed(snapshot, ("展厅", "c1521554db2d11f0ab20d6899ff928cb"))

    def test_assert_kb_allowed_rejects_when_no_variant_matches(self):
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=True,
            can_delete=False,
            kb_scope=ResourceScope.SET,
            kb_names=frozenset({"other-id"}),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
        )

        with self.assertRaises(HTTPException) as ctx:
            assert_kb_allowed(snapshot, ("展厅", "c1521554db2d11f0ab20d6899ff928cb"))
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "kb_not_allowed")


if __name__ == "__main__":
    unittest.main()
