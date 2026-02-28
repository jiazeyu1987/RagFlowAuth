import os
import tempfile
import unittest

from backend.app.core.permission_resolver import ResourceScope, resolve_permissions
from backend.database.schema.ensure import ensure_schema
from backend.services.knowledge_directory.manager import KnowledgeDirectoryManager
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore


class _User:
    def __init__(self):
        self.role = "viewer"
        self.group_ids = [1]


class _PermissionGroupStore:
    def __init__(self, node_id: str):
        self._node_id = node_id

    def get_group(self, group_id: int):  # noqa: ARG002
        return {
            "can_upload": False,
            "can_review": False,
            "can_download": True,
            "can_delete": False,
            "accessible_kbs": [],
            "accessible_kb_nodes": [self._node_id],
            "accessible_chats": [],
        }


class _RagflowService:
    def get_dataset_index(self):
        return {
            "by_id": {"ds_1": "KB-1", "ds_2": "KB-2"},
            "by_name": {"KB-1": "ds_1", "KB-2": "ds_2"},
        }


class _Deps:
    def __init__(self, manager: KnowledgeDirectoryManager, node_id: str):
        self.permission_group_store = _PermissionGroupStore(node_id=node_id)
        self.knowledge_directory_manager = manager
        self.ragflow_service = _RagflowService()


class TestKnowledgeDirectoryAndResolverUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = KnowledgeDirectoryStore(self.db_path)
        self.manager = KnowledgeDirectoryManager(self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def test_resolve_dataset_ids_from_parent_node_includes_descendants(self):
        parent = self.store.create_node("Parent", None, created_by="u1")
        child = self.store.create_node("Child", parent["node_id"], created_by="u1")
        self.store.assign_dataset("ds_1", parent["node_id"])
        self.store.assign_dataset("ds_2", child["node_id"])

        dataset_ids = self.manager.resolve_dataset_ids_from_nodes([parent["node_id"]])
        self.assertEqual(sorted(dataset_ids), ["ds_1", "ds_2"])

    def test_update_node_explicit_parent_none_moves_to_root(self):
        parent = self.store.create_node("Parent", None, created_by="u1")
        child = self.store.create_node("Child", parent["node_id"], created_by="u1")

        updated = self.store.update_node(child["node_id"], parent_id=None)
        self.assertIsNone(updated["parent_id"])

    def test_permission_resolver_includes_kbs_from_selected_nodes(self):
        parent = self.store.create_node("Parent", None, created_by="u1")
        child = self.store.create_node("Child", parent["node_id"], created_by="u1")
        self.store.assign_dataset("ds_1", parent["node_id"])
        self.store.assign_dataset("ds_2", child["node_id"])

        deps = _Deps(manager=self.manager, node_id=parent["node_id"])
        snapshot = resolve_permissions(deps, _User())

        self.assertEqual(snapshot.kb_scope, ResourceScope.SET)
        self.assertIn("ds_1", snapshot.kb_names)
        self.assertIn("ds_2", snapshot.kb_names)
        self.assertIn("KB-1", snapshot.kb_names)
        self.assertIn("KB-2", snapshot.kb_names)


if __name__ == "__main__":
    unittest.main()
