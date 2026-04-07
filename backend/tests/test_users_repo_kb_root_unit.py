import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.modules.users.repo import UsersRepo


def _build_repo():
    deps = SimpleNamespace(
        user_store=SimpleNamespace(db_path="D:\\tenant\\auth.db"),
        org_structure_manager=SimpleNamespace(),
    )
    return UsersRepo(deps)


class _KnowledgeStore:
    def __init__(self, node=None):
        self.node = node

    def get_node(self, node_id):
        if self.node is None:
            return None
        return {**self.node, "id": node_id}


class _KnowledgeTreeManager:
    def __init__(self, tree):
        self.tree = tree

    def snapshot(self, *_args, **_kwargs):
        return self.tree


class UsersRepoKbRootUnitTest(unittest.TestCase):
    def test_get_managed_kb_root_path_returns_none_for_missing_company_or_node(self):
        repo = _build_repo()

        self.assertIsNone(repo.get_managed_kb_root_path(company_id=None, node_id="node-1"))
        self.assertIsNone(repo.get_managed_kb_root_path(company_id=1, node_id=""))

    def test_get_managed_kb_root_path_returns_none_when_node_is_missing(self):
        repo = _build_repo()

        with patch("backend.app.modules.users.repo.resolve_tenant_auth_db_path", return_value="D:\\tenant\\tenant.db"), patch(
            "backend.app.modules.users.repo.ensure_schema"
        ) as ensure_schema, patch(
            "backend.app.modules.users.repo.KnowledgeDirectoryStore",
            return_value=_KnowledgeStore(node=None),
        ) as store_cls, patch("backend.app.modules.users.repo.KnowledgeTreeManager") as tree_manager_cls:
            result = repo.get_managed_kb_root_path(company_id=1, node_id="node-1")

        self.assertIsNone(result)
        ensure_schema.assert_called_once_with("D:\\tenant\\tenant.db")
        store_cls.assert_called_once_with(db_path="D:\\tenant\\tenant.db")
        tree_manager_cls.assert_not_called()

    def test_get_managed_kb_root_path_returns_trimmed_tree_path_for_matching_node(self):
        repo = _build_repo()
        store = _KnowledgeStore(node={"name": "Root"})
        tree_manager = _KnowledgeTreeManager(
            {
                "nodes": [
                    {"id": "other", "path": "/Other"},
                    {"id": "node-1", "path": " /Root/Node 1 "},
                ]
            }
        )

        with patch("backend.app.modules.users.repo.resolve_tenant_auth_db_path", return_value="D:\\tenant\\tenant.db"), patch(
            "backend.app.modules.users.repo.ensure_schema"
        ), patch(
            "backend.app.modules.users.repo.KnowledgeDirectoryStore",
            return_value=store,
        ), patch(
            "backend.app.modules.users.repo.KnowledgeTreeManager",
            return_value=tree_manager,
        ):
            result = repo.get_managed_kb_root_path(company_id=1, node_id=" node-1 ")

        self.assertEqual(result, "/Root/Node 1")

    def test_get_managed_kb_root_path_returns_none_when_tree_has_no_matching_path(self):
        repo = _build_repo()
        store = _KnowledgeStore(node={"name": "Root"})
        tree_manager = _KnowledgeTreeManager(
            {
                "nodes": [
                    {"id": "node-1", "path": " "},
                    {"id": "node-2", "path": "/Root/Other"},
                    "bad-node",
                ]
            }
        )

        with patch("backend.app.modules.users.repo.resolve_tenant_auth_db_path", return_value="D:\\tenant\\tenant.db"), patch(
            "backend.app.modules.users.repo.ensure_schema"
        ), patch(
            "backend.app.modules.users.repo.KnowledgeDirectoryStore",
            return_value=store,
        ), patch(
            "backend.app.modules.users.repo.KnowledgeTreeManager",
            return_value=tree_manager,
        ):
            result = repo.get_managed_kb_root_path(company_id=1, node_id="node-1")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
