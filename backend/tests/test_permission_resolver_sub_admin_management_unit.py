import os
import unittest
from types import SimpleNamespace

from backend.app.core.permission_resolver import ResourceScope, resolve_permissions
from backend.database.schema.ensure import ensure_schema
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir
from backend.services.chat_management import ChatManagementManager, ChatOwnershipStore
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_management import KnowledgeManagementManager
from backend.services.knowledge_tree import KnowledgeTreeManager


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _RagflowService:
    def list_datasets(self):
        return [{"id": "ds_1", "name": "KB 1"}]

    def get_dataset_index(self):
        return {
            "by_id": {"ds_1": "KB 1"},
            "by_name": {"KB 1": "ds_1"},
        }


class _RagflowChatService:
    def list_chats(self, *args, **kwargs):  # noqa: ARG002
        return [{"id": "c1", "name": "Chat 1"}]


class TestPermissionResolverSubAdminManagementUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_chat_management")
        self.db_path = os.path.join(self._tmp, "auth.db")
        ensure_schema(self.db_path)
        self.store = KnowledgeDirectoryStore(self.db_path)
        self.tree_manager = KnowledgeTreeManager(store=self.store)
        self.ragflow_service = _RagflowService()
        self.chat_store = ChatOwnershipStore(self.db_path)
        self.ragflow_chat_service = _RagflowChatService()
        self.management_manager = KnowledgeManagementManager(
            tree_manager=self.tree_manager,
            directory_store=self.store,
            ragflow_service=self.ragflow_service,
        )
        self.chat_management_manager = ChatManagementManager(
            store=self.chat_store,
            ragflow_chat_service=self.ragflow_chat_service,
            knowledge_management_manager=self.management_manager,
        )

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_valid_sub_admin_gets_manage_upload_delete_and_subtree_kb_scope(self):
        root = self.store.create_node("Root", None, created_by="admin")
        child = self.store.create_node("Child", root["node_id"], created_by="admin")
        self.store.assign_dataset("ds_1", child["node_id"])
        self.chat_store.save_chat_owner(chat_id="c1", created_by="u_sub")

        deps = SimpleNamespace(
            permission_group_store=_PermissionGroupStore(),
            ragflow_service=self.ragflow_service,
            knowledge_directory_manager=self.tree_manager,
            knowledge_management_manager=self.management_manager,
            chat_management_manager=self.chat_management_manager,
        )
        user = SimpleNamespace(
            role="sub_admin",
            group_ids=[],
            user_id="u_sub",
            managed_kb_root_node_id=root["node_id"],
        )

        snapshot = resolve_permissions(deps, user)

        self.assertTrue(snapshot.can_upload)
        self.assertTrue(snapshot.can_delete)
        self.assertTrue(snapshot.can_manage_kb_directory)
        self.assertTrue(snapshot.can_view_kb_config)
        self.assertEqual(ResourceScope.SET, snapshot.kb_scope)
        self.assertIn("ds_1", snapshot.kb_names)
        self.assertIn("KB 1", snapshot.kb_names)
        self.assertEqual(ResourceScope.SET, snapshot.chat_scope)
        self.assertIn("chat_c1", snapshot.chat_ids)

    def test_invalid_sub_admin_root_keeps_management_permissions_disabled(self):
        deps = SimpleNamespace(
            permission_group_store=_PermissionGroupStore(),
            ragflow_service=self.ragflow_service,
            knowledge_directory_manager=self.tree_manager,
            knowledge_management_manager=self.management_manager,
            chat_management_manager=self.chat_management_manager,
        )
        user = SimpleNamespace(
            role="sub_admin",
            group_ids=[],
            user_id="u_sub",
            managed_kb_root_node_id="missing-root",
        )

        snapshot = resolve_permissions(deps, user)

        self.assertFalse(snapshot.can_upload)
        self.assertFalse(snapshot.can_delete)
        self.assertFalse(snapshot.can_manage_kb_directory)
        self.assertFalse(snapshot.can_view_kb_config)
        self.assertEqual(ResourceScope.NONE, snapshot.kb_scope)
        self.assertEqual(ResourceScope.NONE, snapshot.chat_scope)


if __name__ == "__main__":
    unittest.main()
