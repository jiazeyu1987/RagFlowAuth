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


class TestPermissionResolverToolsScopeUnit(unittest.TestCase):
    def test_tools_default_to_all_when_group_has_no_tool_list(self):
        deps = SimpleNamespace(
            permission_group_store=_PermissionGroupStore(
                {
                    1: {
                        "can_view_tools": True,
                        "accessible_tools": [],
                    }
                }
            ),
            ragflow_service=_RagflowService(),
            knowledge_directory_manager=None,
        )
        user = SimpleNamespace(role="viewer", group_ids=[1])
        snapshot = resolve_permissions(deps, user)
        self.assertEqual(snapshot.tool_scope, ResourceScope.ALL)
        self.assertEqual(snapshot.permissions_dict()["accessible_tools"], [])

    def test_tools_scope_set_when_group_specifies_tool_list(self):
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
        )
        user = SimpleNamespace(role="viewer", group_ids=[1])
        snapshot = resolve_permissions(deps, user)
        self.assertEqual(snapshot.tool_scope, ResourceScope.SET)
        self.assertEqual(snapshot.permissions_dict()["accessible_tools"], ["nmpa", "paper_download"])


if __name__ == "__main__":
    unittest.main()

