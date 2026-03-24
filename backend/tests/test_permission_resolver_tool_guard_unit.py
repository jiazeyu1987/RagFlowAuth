import unittest

from fastapi import HTTPException

from backend.app.core.permission_resolver import (
    PermissionSnapshot,
    ResourceScope,
    assert_tool_allowed,
)


class TestPermissionResolverToolGuardUnit(unittest.TestCase):
    def _snapshot(self, *, can_view_tools: bool, tool_scope: ResourceScope, tool_ids: set[str] | None = None):
        return PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=False,
            can_delete=False,
            can_manage_kb_directory=False,
            can_view_kb_config=False,
            can_view_tools=can_view_tools,
            kb_scope=ResourceScope.NONE,
            kb_names=frozenset(),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
            tool_scope=tool_scope,
            tool_ids=frozenset(tool_ids or set()),
        )

    def test_set_scope_allows_only_selected_tool(self):
        snapshot = self._snapshot(can_view_tools=True, tool_scope=ResourceScope.SET, tool_ids={"package_drawing"})
        assert_tool_allowed(snapshot, "package_drawing")
        with self.assertRaises(HTTPException) as cm:
            assert_tool_allowed(snapshot, "paper_download")
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "tool_not_allowed")

    def test_no_tools_permission_rejected(self):
        snapshot = self._snapshot(can_view_tools=False, tool_scope=ResourceScope.NONE)
        with self.assertRaises(HTTPException) as cm:
            assert_tool_allowed(snapshot, "package_drawing")
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "no_tools_view_permission")

    def test_all_scope_allows_any_tool(self):
        snapshot = self._snapshot(can_view_tools=True, tool_scope=ResourceScope.ALL)
        assert_tool_allowed(snapshot, "package_drawing")
        assert_tool_allowed(snapshot, "paper_download")


if __name__ == "__main__":
    unittest.main()
