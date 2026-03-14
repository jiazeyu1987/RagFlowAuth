import unittest

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.services.permission_decision_service import PermissionDecisionError, PermissionDecisionService


class _User:
    def __init__(self, *, role: str = "viewer", group_ids=None):
        self.role = role
        self.group_ids = list(group_ids or [])


class _PermissionGroupStore:
    def __init__(self, groups: dict[int, dict]):
        self._groups = groups

    def get_group(self, group_id: int):
        return self._groups.get(group_id)


class _KnowledgeDirectoryManager:
    def resolve_dataset_ids_from_nodes(self, node_ids):
        result = []
        if "root" in set(node_ids or []):
            result.extend(["ds_1", "ds_2"])
        return result


class _RagflowService:
    def get_dataset_index(self):
        return {
            "by_id": {"ds_1": "KB-1", "ds_2": "KB-2"},
            "by_name": {"KB-1": "ds_1", "KB-2": "ds_2"},
        }


class _Deps:
    def __init__(self):
        self.permission_group_store = _PermissionGroupStore(
            {
                1: {
                    "can_upload": False,
                    "can_review": True,
                    "can_download": True,
                    "can_delete": False,
                    "accessible_kbs": [],
                    "accessible_kb_nodes": ["root"],
                    "accessible_chats": ["chat_1", "agent_2"],
                }
            }
        )
        self.knowledge_directory_manager = _KnowledgeDirectoryManager()
        self.ragflow_service = _RagflowService()


class TestPermissionDecisionServiceUnit(unittest.TestCase):
    def setUp(self):
        self.svc = PermissionDecisionService()

    def test_resolve_snapshot_includes_kbs_from_inherited_nodes(self):
        snapshot = self.svc.resolve_snapshot(_Deps(), _User(role="viewer", group_ids=[1]))
        self.assertEqual(snapshot.kb_scope, ResourceScope.SET)
        self.assertIn("ds_1", snapshot.kb_names)
        self.assertIn("ds_2", snapshot.kb_names)
        self.assertIn("KB-1", snapshot.kb_names)
        self.assertIn("KB-2", snapshot.kb_names)

    def test_ensure_admin_rejects_non_admin_with_stable_reason(self):
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=False,
            can_delete=False,
            kb_scope=ResourceScope.NONE,
            kb_names=frozenset(),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
        )
        with self.assertRaises(PermissionDecisionError) as ctx:
            self.svc.ensure_admin(snapshot)
        self.assertEqual(ctx.exception.code, "permission_denied")
        self.assertEqual(ctx.exception.reason, "admin_required")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_ensure_chat_access_supports_chat_and_agent_prefix(self):
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=False,
            can_delete=False,
            kb_scope=ResourceScope.NONE,
            kb_names=frozenset(),
            chat_scope=ResourceScope.SET,
            chat_ids=frozenset({"chat_1", "agent_2"}),
        )
        self.svc.ensure_chat_access(snapshot, "1")
        self.svc.ensure_chat_access(snapshot, "2")
        with self.assertRaises(PermissionDecisionError) as ctx:
            self.svc.ensure_chat_access(snapshot, "3")
        self.assertEqual(ctx.exception.reason, "no_chat_permission")

    def test_ensure_kb_access_accepts_variant_iterable(self):
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=True,
            can_delete=False,
            kb_scope=ResourceScope.SET,
            kb_names=frozenset({"ds_1"}),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
        )
        self.svc.ensure_kb_access(snapshot, ("KB-1", "ds_1"))
        with self.assertRaises(PermissionDecisionError) as ctx:
            self.svc.ensure_kb_access(snapshot, ("KB-2", "ds_2"))
        self.assertEqual(ctx.exception.reason, "kb_not_allowed")


if __name__ == "__main__":
    unittest.main()
