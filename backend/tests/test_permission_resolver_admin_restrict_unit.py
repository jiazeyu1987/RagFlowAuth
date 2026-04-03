import unittest

from fastapi import HTTPException

from backend.app.core.permission_resolver import (
    PermissionSnapshot,
    ResourceScope,
    assert_can_delete,
    assert_can_download,
    assert_can_manage_kb_directory,
    assert_can_review,
    assert_can_upload,
    assert_can_view_kb_config,
    assert_can_view_tools,
)


def _admin_snapshot() -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=True,
        can_upload=False,
        can_review=False,
        can_download=False,
        can_copy=False,
        can_delete=False,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
        kb_scope=ResourceScope.NONE,
        kb_names=frozenset(),
        chat_scope=ResourceScope.NONE,
        chat_ids=frozenset(),
        tool_scope=ResourceScope.NONE,
        tool_ids=frozenset(),
    )


class TestPermissionResolverAdminRestrictUnit(unittest.TestCase):
    def test_admin_without_flags_cannot_upload(self):
        with self.assertRaises(HTTPException) as cm:
            assert_can_upload(_admin_snapshot())
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_upload_permission")

    def test_admin_without_flags_cannot_review(self):
        with self.assertRaises(HTTPException) as cm:
            assert_can_review(_admin_snapshot())
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_review_permission")

    def test_admin_without_flags_cannot_download(self):
        with self.assertRaises(HTTPException) as cm:
            assert_can_download(_admin_snapshot())
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_download_permission")

    def test_admin_without_flags_cannot_delete(self):
        with self.assertRaises(HTTPException) as cm:
            assert_can_delete(_admin_snapshot())
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_delete_permission")

    def test_admin_without_flags_cannot_manage_kb_directory(self):
        with self.assertRaises(HTTPException) as cm:
            assert_can_manage_kb_directory(_admin_snapshot())
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_kb_directory_manage_permission")

    def test_admin_without_flags_cannot_view_kb_config(self):
        with self.assertRaises(HTTPException) as cm:
            assert_can_view_kb_config(_admin_snapshot())
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_kb_config_view_permission")

    def test_admin_without_flags_cannot_view_tools(self):
        with self.assertRaises(HTTPException) as cm:
            assert_can_view_tools(_admin_snapshot())
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_tools_view_permission")


if __name__ == "__main__":
    unittest.main()
