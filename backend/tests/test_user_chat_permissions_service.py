import unittest

from backend.app.core.permission_resolver import ResourceScope, resolve_permissions


class _User:
    def __init__(self, *, role: str = "viewer", group_id=None, group_ids=None, user_id: str = "u1"):
        self.user_id = user_id
        self.role = role
        self.group_id = group_id
        self.group_ids = group_ids or []
        self.username = "u1"


class _PermissionGroupStore:
    def __init__(self, groups: dict[int, dict]):
        self._groups = groups

    def get_group(self, group_id: int):
        return self._groups.get(group_id)


class _UserChatPermissionStore:
    def __init__(self, grants: list[str]):
        self._grants = grants

    def get_user_chats(self, user_id: str):  # noqa: ARG002
        return list(self._grants)


class _UserKbPermissionStore:
    def get_user_kbs(self, user_id: str):  # noqa: ARG002
        return []


class _Deps:
    def __init__(self, *, groups: dict[int, dict], user_chat_grants: list[str]):
        self.permission_group_store = _PermissionGroupStore(groups)
        self.user_kb_permission_store = _UserKbPermissionStore()
        self.user_chat_permission_store = _UserChatPermissionStore(user_chat_grants)


class TestUserChatPermissionsResolver(unittest.TestCase):
    def test_non_admin_no_group_returns_empty(self):
        deps = _Deps(groups={}, user_chat_grants=[])
        snapshot = resolve_permissions(deps, _User(role="viewer", group_id=None, group_ids=[]))
        self.assertEqual(snapshot.chat_scope, ResourceScope.NONE)
        self.assertEqual(sorted(snapshot.chat_ids), [])

    def test_non_admin_empty_accessible_chats_means_none(self):
        deps = _Deps(groups={1: {"accessible_chats": []}}, user_chat_grants=[])
        snapshot = resolve_permissions(deps, _User(role="viewer", group_id=1))
        self.assertEqual(snapshot.chat_scope, ResourceScope.NONE)
        self.assertEqual(sorted(snapshot.chat_ids), [])

    def test_non_admin_unions_accessible_chats_across_groups_and_grants(self):
        deps = _Deps(
            groups={
                1: {"accessible_chats": ["chat_c1"]},
                2: {"accessible_chats": ["agent_a1", "chat_c1"]},
            },
            user_chat_grants=["chat_c2"],
        )
        snapshot = resolve_permissions(deps, _User(role="viewer", group_ids=[1, 2]))
        self.assertEqual(sorted(snapshot.chat_ids), ["agent_a1", "chat_c1"])

    def test_admin_gets_all_scope(self):
        deps = _Deps(groups={}, user_chat_grants=[])
        snapshot = resolve_permissions(deps, _User(role="admin"))
        self.assertEqual(snapshot.chat_scope, ResourceScope.ALL)
