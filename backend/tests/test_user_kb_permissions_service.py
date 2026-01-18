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


class _UserKbPermissionStore:
    def __init__(self, grants: list[str]):
        self._grants = grants

    def get_user_kbs(self, user_id: str):  # noqa: ARG002
        return list(self._grants)


class _UserChatPermissionStore:
    def get_user_chats(self, user_id: str):  # noqa: ARG002
        return []


class _Deps:
    def __init__(self, *, groups: dict[int, dict], user_kb_grants: list[str]):
        self.permission_group_store = _PermissionGroupStore(groups)
        self.user_kb_permission_store = _UserKbPermissionStore(user_kb_grants)
        self.user_chat_permission_store = _UserChatPermissionStore()


class TestUserKbPermissionsResolver(unittest.TestCase):
    def test_non_admin_no_group_means_none(self):
        deps = _Deps(groups={}, user_kb_grants=["kb_x"])
        snapshot = resolve_permissions(deps, _User(role="viewer", group_id=None, group_ids=[]))
        self.assertEqual(snapshot.kb_scope, ResourceScope.NONE)
        self.assertEqual(sorted(snapshot.kb_names), [])

    def test_non_admin_empty_accessible_kbs_means_none(self):
        deps = _Deps(groups={1: {"accessible_kbs": []}}, user_kb_grants=[])
        snapshot = resolve_permissions(deps, _User(role="viewer", group_id=1))
        self.assertEqual(snapshot.kb_scope, ResourceScope.NONE)
        self.assertEqual(sorted(snapshot.kb_names), [])

    def test_non_admin_unions_accessible_kbs_across_groups_and_grants(self):
        deps = _Deps(
            groups={
                1: {"accessible_kbs": ["kb_a"]},
                2: {"accessible_kbs": ["kb_b", "kb_a"]},
            },
            user_kb_grants=["kb_x"],
        )
        snapshot = resolve_permissions(deps, _User(role="viewer", group_ids=[1, 2]))
        self.assertEqual(sorted(snapshot.kb_names), ["kb_a", "kb_b"])

    def test_admin_gets_all_scope(self):
        deps = _Deps(groups={}, user_kb_grants=[])
        snapshot = resolve_permissions(deps, _User(role="admin"))
        self.assertEqual(snapshot.kb_scope, ResourceScope.ALL)
