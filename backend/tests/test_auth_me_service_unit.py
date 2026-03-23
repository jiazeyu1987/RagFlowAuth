import unittest
from types import SimpleNamespace

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.services.auth_me_service import build_auth_me_payload


class _RagflowService:
    def list_all_datasets(self):
        return [{"id": "id-a", "name": "kb-a"}, {"id": "id-b", "name": "kb-b"}]

    def normalize_dataset_ids(self, refs):  # noqa: ARG002
        return ["id-k1"]

    def resolve_dataset_names(self, refs):  # noqa: ARG002
        return ["kb-k1"]


class _RagflowChatService:
    def list_all_chat_ids(self):
        return ["chat-c1", "agent-a1"]


class _PermissionGroupStore:
    def get_group(self, group_id):
        if group_id == 1:
            return {"group_name": "g1", "accessible_kbs": ["kb-a"]}
        return None


class TestAuthMeServiceUnit(unittest.TestCase):
    def test_build_payload_all_scope(self):
        deps = SimpleNamespace(
            ragflow_service=_RagflowService(),
            ragflow_chat_service=_RagflowChatService(),
            permission_group_store=_PermissionGroupStore(),
        )
        user = SimpleNamespace(
            user_id="u1",
            username="alice",
            email="alice@example.com",
            role="admin",
            status="active",
            group_id=None,
            group_ids=[1],
            max_login_sessions=5,
            idle_timeout_minutes=60,
        )
        snapshot = PermissionSnapshot(
            is_admin=True,
            can_upload=True,
            can_review=True,
            can_download=True,
            can_delete=True,
            can_manage_kb_directory=True,
            can_view_kb_config=True,
            can_view_tools=True,
            kb_scope=ResourceScope.ALL,
            kb_names=frozenset(),
            chat_scope=ResourceScope.ALL,
            chat_ids=frozenset(),
            tool_scope=ResourceScope.ALL,
            tool_ids=frozenset(),
        )

        payload = build_auth_me_payload(deps=deps, user=user, snapshot=snapshot)
        self.assertEqual(payload["accessible_kb_ids"], ["id-a", "id-b"])
        self.assertEqual(payload["accessible_kbs"], ["kb-a", "kb-b"])
        self.assertEqual(payload["accessible_chats"], ["agent-a1", "chat-c1"])
        self.assertEqual(payload["permission_groups"], [{"group_id": 1, "group_name": "g1"}])

    def test_build_payload_set_scope(self):
        deps = SimpleNamespace(
            ragflow_service=_RagflowService(),
            ragflow_chat_service=_RagflowChatService(),
            permission_group_store=_PermissionGroupStore(),
        )
        user = SimpleNamespace(
            user_id="u2",
            username="bob",
            email="bob@example.com",
            role="viewer",
            status="active",
            group_id=None,
            group_ids=[],
            max_login_sessions=3,
            idle_timeout_minutes=120,
        )
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=False,
            can_delete=False,
            can_manage_kb_directory=False,
            can_view_kb_config=False,
            can_view_tools=False,
            kb_scope=ResourceScope.SET,
            kb_names=frozenset({"kb-k1"}),
            chat_scope=ResourceScope.SET,
            chat_ids=frozenset({"chat-c2"}),
            tool_scope=ResourceScope.NONE,
            tool_ids=frozenset(),
        )

        payload = build_auth_me_payload(deps=deps, user=user, snapshot=snapshot)
        self.assertEqual(payload["accessible_kb_ids"], ["id-k1"])
        self.assertEqual(payload["accessible_kbs"], ["kb-k1"])
        self.assertEqual(payload["accessible_chats"], ["chat-c2"])
        self.assertEqual(payload["permission_groups"], [])


if __name__ == "__main__":
    unittest.main()
