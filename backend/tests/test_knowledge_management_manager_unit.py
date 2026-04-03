import os
import tempfile
import unittest
from types import SimpleNamespace

from backend.database.schema.ensure import ensure_schema
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_management import KnowledgeManagementError, KnowledgeManagementManager
from backend.services.knowledge_tree import KnowledgeTreeManager


class _RagflowService:
    def __init__(self):
        self.datasets = [
            {"id": "ds_root", "name": "Root KB"},
            {"id": "ds_child", "name": "Child KB"},
            {"id": "ds_other", "name": "Other KB"},
        ]

    def list_all_datasets(self):
        return list(self.datasets)

    def list_datasets(self):
        return list(self.datasets)

    def normalize_dataset_id(self, dataset_ref: str):
        for dataset in self.datasets:
            if dataset_ref in {dataset["id"], dataset["name"]}:
                return dataset["id"]
        return None

    def resolve_dataset_name(self, dataset_ref: str):
        for dataset in self.datasets:
            if dataset_ref in {dataset["id"], dataset["name"]}:
                return dataset["name"]
        return None

    def create_dataset(self, payload):
        created = {"id": "created_ds", **payload}
        self.datasets.append(created)
        return created

    def update_dataset(self, dataset_ref: str, updates):
        dataset_id = self.normalize_dataset_id(dataset_ref)
        for dataset in self.datasets:
            if dataset["id"] == dataset_id:
                dataset.update(updates)
                return dict(dataset)
        return None

    def delete_dataset_if_empty(self, dataset_ref: str):
        dataset_id = self.normalize_dataset_id(dataset_ref)
        self.datasets = [dataset for dataset in self.datasets if dataset["id"] != dataset_id]


class TestKnowledgeManagementManagerUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = KnowledgeDirectoryStore(self.db_path)
        self.tree_manager = KnowledgeTreeManager(self.store)
        self.ragflow = _RagflowService()
        self.manager = KnowledgeManagementManager(
            tree_manager=self.tree_manager,
            directory_store=self.store,
            ragflow_service=self.ragflow,
        )

        self.root = self.tree_manager.create_node(name="Root", parent_id=None, created_by="admin")
        self.child = self.tree_manager.create_node(name="Child", parent_id=self.root["id"], created_by="admin")
        self.other = self.tree_manager.create_node(name="Other", parent_id=None, created_by="admin")
        self.tree_manager.assign_dataset(dataset_id="ds_root", node_id=self.root["id"])
        self.tree_manager.assign_dataset(dataset_id="ds_child", node_id=self.child["id"])
        self.tree_manager.assign_dataset(dataset_id="ds_other", node_id=self.other["id"])

    def tearDown(self):
        self._tmp.cleanup()

    def test_admin_scope_returns_full_tree(self):
        user = SimpleNamespace(role="admin", managed_kb_root_node_id=None)
        scope = self.manager.get_management_scope(user)
        self.assertEqual(scope.mode, "all")
        self.assertEqual(scope.dataset_ids, frozenset({"ds_root", "ds_child", "ds_other"}))

    def test_sub_admin_scope_returns_bound_subtree(self):
        user = SimpleNamespace(role="sub_admin", managed_kb_root_node_id=self.root["id"])
        scope = self.manager.get_management_scope(user)
        self.assertEqual(scope.mode, "subtree")
        self.assertEqual(scope.node_ids, frozenset({self.root["id"], self.child["id"]}))
        self.assertEqual(scope.dataset_ids, frozenset({"ds_root", "ds_child"}))

    def test_sub_admin_without_root_has_no_management_scope(self):
        user = SimpleNamespace(role="sub_admin", managed_kb_root_node_id=None)
        scope = self.manager.get_management_scope(user)
        self.assertEqual(scope.mode, "none")
        self.assertFalse(scope.can_manage)

    def test_sub_admin_with_missing_root_reports_precise_error(self):
        user = SimpleNamespace(role="sub_admin", managed_kb_root_node_id="missing-node")
        with self.assertRaises(KnowledgeManagementError) as cm:
            self.manager.assert_can_manage(user)
        self.assertEqual(cm.exception.code, "managed_kb_root_node_not_found")

    def test_assert_node_manageable_rejects_out_of_scope_node(self):
        user = SimpleNamespace(role="sub_admin", managed_kb_root_node_id=self.root["id"])
        with self.assertRaises(KnowledgeManagementError) as cm:
            self.manager.assert_node_manageable(user, self.other["id"])
        self.assertEqual(cm.exception.code, "node_out_of_management_scope")

    def test_assert_dataset_manageable_rejects_out_of_scope_dataset(self):
        user = SimpleNamespace(role="sub_admin", managed_kb_root_node_id=self.root["id"])
        with self.assertRaises(KnowledgeManagementError) as cm:
            self.manager.assert_dataset_manageable(user, "ds_other")
        self.assertEqual(cm.exception.code, "dataset_out_of_management_scope")


if __name__ == "__main__":
    unittest.main()
