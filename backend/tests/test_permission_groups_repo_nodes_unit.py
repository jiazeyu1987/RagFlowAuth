import unittest

from backend.app.modules.permission_groups.repo import PermissionGroupsRepo


class _KnowledgeDirectoryStore:
    def list_nodes(self):
        return [
            {"node_id": "n-1", "name": "A"},
            {"node_id": "n-2", "name": "B"},
        ]


class _Deps:
    def __init__(self):
        self.knowledge_directory_store = _KnowledgeDirectoryStore()


class TestPermissionGroupsRepoNodesUnit(unittest.TestCase):
    def test_normalize_accessible_kb_nodes_filters_unknown_ids(self):
        repo = PermissionGroupsRepo(_Deps())
        out = repo._normalize_accessible_kb_nodes(["n-1", " n-2 ", "n-x", "", None])
        self.assertEqual(out, ["n-1", "n-2"])


if __name__ == "__main__":
    unittest.main()
