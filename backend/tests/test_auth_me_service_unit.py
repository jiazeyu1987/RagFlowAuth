import unittest
from types import SimpleNamespace

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.core.tool_catalog import ASSIGNABLE_TOOL_IDS
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


class _BrokenManagementManager:
    def get_management_scope(self, user):  # noqa: ARG002
        raise RuntimeError("management_scope_failed")


class TestAuthMeServiceUnit(unittest.TestCase):
    def test_permissions_dict_returns_assignable_tools_for_all_scope(self):
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=False,
            can_copy=False,
            can_delete=False,
            can_manage_kb_directory=False,
            can_view_kb_config=False,
            can_view_tools=True,
            kb_scope=ResourceScope.NONE,
            kb_names=frozenset(),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
            tool_scope=ResourceScope.ALL,
            tool_ids=frozenset(),
        )

        self.assertEqual(
            snapshot.permissions_dict()["accessible_tools"],
            list(ASSIGNABLE_TOOL_IDS),
        )

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
            can_copy=True,
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
            can_manage_users=True,
        )

        payload = build_auth_me_payload(deps=deps, user=user, snapshot=snapshot)
        self.assertEqual(payload["accessible_kb_ids"], ["id-a", "id-b"])
        self.assertEqual(payload["accessible_kbs"], ["kb-a", "kb-b"])
        self.assertEqual(payload["accessible_chats"], ["agent-a1", "chat-c1"])
        self.assertEqual(payload["permission_groups"], [{"group_id": 1, "group_name": "g1"}])
        self.assertEqual(payload["permissions"]["accessible_tools"], list(ASSIGNABLE_TOOL_IDS))
        self.assertEqual(payload["capabilities"]["users"]["manage"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["kb_documents"]["view"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["tools"]["view"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["quality_system"]["view"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["quality_system"]["manage"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["document_control"]["create"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["complaints"]["view"], {"scope": "all", "targets": []})

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
            can_copy=False,
            can_delete=False,
            can_manage_kb_directory=False,
            can_view_kb_config=False,
            can_view_tools=True,
            kb_scope=ResourceScope.SET,
            kb_names=frozenset({"kb-k1"}),
            chat_scope=ResourceScope.SET,
            chat_ids=frozenset({"chat-c2"}),
            tool_scope=ResourceScope.SET,
            tool_ids=frozenset({"nmpa"}),
        )

        payload = build_auth_me_payload(deps=deps, user=user, snapshot=snapshot)
        self.assertEqual(payload["accessible_kb_ids"], ["id-k1"])
        self.assertEqual(payload["accessible_kbs"], ["kb-k1"])
        self.assertEqual(payload["accessible_chats"], ["chat-c2"])
        self.assertEqual(payload["permission_groups"], [])
        self.assertEqual(payload["permissions"]["accessible_tools"], ["nmpa"])
        self.assertEqual(payload["capabilities"]["kb_documents"]["view"], {"scope": "set", "targets": ["id-k1"]})
        self.assertEqual(payload["capabilities"]["ragflow_documents"]["preview"], {"scope": "set", "targets": ["id-k1"]})
        self.assertEqual(payload["capabilities"]["tools"]["view"], {"scope": "set", "targets": ["nmpa"]})
        self.assertEqual(payload["capabilities"]["quality_system"]["view"], {"scope": "none", "targets": []})
        self.assertEqual(payload["capabilities"]["quality_system"]["manage"], {"scope": "none", "targets": []})
        self.assertEqual(payload["capabilities"]["audit_events"]["view"], {"scope": "none", "targets": []})
        self.assertEqual(payload["capabilities"]["complaints"]["view"], {"scope": "none", "targets": []})
        self.assertEqual(payload["capabilities"]["training_ack"]["acknowledge"], {"scope": "all", "targets": []})

    def test_build_payload_sub_admin_gets_quality_capabilities_without_quality_system_manage(self):
        deps = SimpleNamespace(
            ragflow_service=_RagflowService(),
            ragflow_chat_service=_RagflowChatService(),
            permission_group_store=_PermissionGroupStore(),
        )
        user = SimpleNamespace(
            user_id="u-sub",
            username="quality-sub",
            email="quality-sub@example.com",
            role="sub_admin",
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
            can_copy=False,
            can_delete=False,
            can_manage_kb_directory=False,
            can_view_kb_config=False,
            can_view_tools=False,
            kb_scope=ResourceScope.NONE,
            kb_names=frozenset(),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
            tool_scope=ResourceScope.NONE,
            tool_ids=frozenset(),
            can_manage_users=True,
        )

        payload = build_auth_me_payload(deps=deps, user=user, snapshot=snapshot)
        self.assertEqual(payload["capabilities"]["quality_system"]["view"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["quality_system"]["manage"], {"scope": "none", "targets": []})
        self.assertEqual(payload["capabilities"]["document_control"]["create"], {"scope": "all", "targets": []})
        self.assertEqual(payload["capabilities"]["change_control"]["create"], {"scope": "all", "targets": []})

    def test_build_payload_does_not_silence_management_scope_failures(self):
        deps = SimpleNamespace(
            ragflow_service=_RagflowService(),
            ragflow_chat_service=_RagflowChatService(),
            permission_group_store=_PermissionGroupStore(),
            knowledge_management_manager=_BrokenManagementManager(),
        )
        user = SimpleNamespace(
            user_id="u3",
            username="charlie",
            email="charlie@example.com",
            role="sub_admin",
            status="active",
            group_id=None,
            group_ids=[],
            managed_kb_root_node_id="root-1",
        )
        snapshot = PermissionSnapshot(
            is_admin=False,
            can_upload=False,
            can_review=False,
            can_download=False,
            can_copy=False,
            can_delete=False,
            can_manage_kb_directory=False,
            can_view_kb_config=False,
            can_view_tools=False,
            kb_scope=ResourceScope.NONE,
            kb_names=frozenset(),
            chat_scope=ResourceScope.NONE,
            chat_ids=frozenset(),
            tool_scope=ResourceScope.NONE,
            tool_ids=frozenset(),
        )

        with self.assertRaisesRegex(RuntimeError, "management_scope_failed"):
            build_auth_me_payload(deps=deps, user=user, snapshot=snapshot)


if __name__ == "__main__":
    unittest.main()
