import os
import tempfile
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_tree import KnowledgeTreeError, KnowledgeTreeManager


class TestKnowledgeTreeManagerUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = KnowledgeDirectoryStore(self.db_path)
        self.manager = KnowledgeTreeManager(self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def test_create_update_assign_snapshot(self):
        root = self.manager.create_node(name="Root", parent_id=None, created_by="u1")
        child = self.manager.create_node(name="Child", parent_id=root["id"], created_by="u1")
        moved = self.manager.update_node(node_id=child["id"], payload={"parent_id": None})
        self.assertIsNone(moved["parent_id"])

        self.manager.assign_dataset(dataset_id="ds_1", node_id=root["id"])
        tree = self.manager.snapshot([{"id": "ds_1", "name": "KB-1"}], prune_unknown=True)
        self.assertEqual(len(tree["nodes"]), 2)
        self.assertEqual(tree["bindings"].get("ds_1"), root["id"])

    def test_delete_node_not_found_maps_404(self):
        with self.assertRaises(KnowledgeTreeError) as cm:
            self.manager.delete_node("missing-id")
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.code, "node_not_found")


if __name__ == "__main__":
    unittest.main()
