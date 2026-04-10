import unittest
from types import SimpleNamespace

from backend.app.core.permission_resolver import ResourceScope, resolve_permissions


class _PermissionGroupStore:
    def __init__(self, groups):
        self._groups = groups

    def get_group(self, group_id):
        return self._groups.get(group_id)


class _RagflowService:
    def get_dataset_index(self):
        return {"by_id": {}, "by_name": {}}


class _UserToolPermissionStore:
    def __init__(self, tool_ids_by_user: dict[str, list[str]]):
        self._tool_ids_by_user = tool_ids_by_user

    def list_tool_ids(self, user_id: str):
        return list(self._tool_ids_by_user.get(str(user_id), []))


class TestPermissionResolverToolsScopeUnit(unittest.TestCase):
    def test_tools_scope_is_none_when_user_has_no_tool_grants(self):
        deps = SimpleNamespace(
            permission_group_store=_PermissionGroupStore(
                {
                    1: {
                        "can_view_tools": True,
                        "accessible_tools": ["paper_download", "nmpa"],
                    }
                }
            ),
            ragflow_service=_RagflowService(),
            knowledge_directory_manager=None,
            user_tool_permission_store=_UserToolPermissionStore({"u-1": []}),
        )
        user = SimpleNamespace(user_id="u-1", role="viewer", group_ids=[1])
        snapshot = resolve_permissions(deps, user)
        self.assertEqual(snapshot.tool_scope, ResourceScope.NONE)
        self.assertFalse(snapshot.can_view_tools)
        self.assertEqual(snapshot.permissions_dict()["accessible_tools"], [])

    def test_tools_scope_set_when_user_has_tool_grants(self):
        deps = SimpleNamespace(
            permission_group_store=_PermissionGroupStore(
                {
                    1: {
                        "can_view_tools": True,
                        "accessible_tools": ["package_drawing"],
                    }
                }
            ),
            ragflow_service=_RagflowService(),
            knowledge_directory_manager=None,
            user_tool_permission_store=_UserToolPermissionStore({"u-2": ["paper_download", "nmpa"]}),
        )
        user = SimpleNamespace(user_id="u-2", role="viewer", group_ids=[1])
        snapshot = resolve_permissions(deps, user)
        self.assertEqual(snapshot.tool_scope, ResourceScope.SET)
        self.assertEqual(snapshot.permissions_dict()["accessible_tools"], ["nmpa", "paper_download"])

    def test_tools_scope_prefers_user_embedded_tool_ids_over_store(self):
        deps = SimpleNamespace(
            permission_group_store=_PermissionGroupStore(
                {
                    1: {
                        "can_view_tools": True,
                        "accessible_tools": ["paper_download", "nmpa"],
                    }
                }
            ),
            ragflow_service=_RagflowService(),
            knowledge_directory_manager=None,
            user_tool_permission_store=_UserToolPermissionStore({"u-3": []}),
        )
        user = SimpleNamespace(
            user_id="u-3",
            role="viewer",
            group_ids=[1],
            tool_ids=["paper_download", "nmpa"],
        )

        snapshot = resolve_permissions(deps, user)

        self.assertEqual(snapshot.tool_scope, ResourceScope.SET)
        self.assertEqual(snapshot.permissions_dict()["accessible_tools"], ["nmpa", "paper_download"])


if __name__ == "__main__":
    unittest.main()
