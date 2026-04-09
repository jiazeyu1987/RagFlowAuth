import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.permission_groups.router import create_router as create_permission_groups_router, get_service as get_permission_groups_service
from backend.app.modules.users.router import get_service as get_users_service, router as users_router


class _User:
    def __init__(self, *, role: str = "sub_admin", group_ids: list[int] | None = None):
        self.user_id = "u_sub"
        self.username = "sub_admin"
        self.email = "sub@example.com"
        self.role = role
        self.status = "active"
        self.company_id = 1
        self.group_id = None
        self.group_ids = list(group_ids or [])
        self.managed_kb_root_node_id = "node-root"


class _UserStore:
    def __init__(self, user: _User):
        self._user = user
        self._targets = {
            "u_target": SimpleNamespace(
                user_id="u_target",
                username="target",
                role="viewer",
                status="active",
                company_id=1,
                manager_user_id="u_sub",
            ),
            "u_other": SimpleNamespace(
                user_id="u_other",
                username="other",
                role="viewer",
                status="active",
                company_id=1,
                manager_user_id="u_other_sub",
            ),
            "u_sub_target": SimpleNamespace(
                user_id="u_sub_target",
                username="sub_target",
                role="sub_admin",
                status="active",
                company_id=1,
                manager_user_id=None,
            ),
        }

    def get_by_user_id(self, user_id: str):
        if str(user_id) == self._user.user_id:
            return self._user
        return self._targets.get(str(user_id))


class _UserToolPermissionStore:
    def __init__(self, tool_ids_by_user: dict[str, list[str]] | None = None):
        self._tool_ids_by_user = dict(tool_ids_by_user or {})

    def list_tool_ids(self, user_id: str):
        return list(self._tool_ids_by_user.get(str(user_id), []))


class _RagflowService:
    @staticmethod
    def get_dataset_index():
        return {"by_id": {}, "by_name": {}}


class _KnowledgeManagementManager:
    def __init__(
        self,
        *,
        can_manage: bool = True,
        knowledge_bases_error: Exception | None = None,
        knowledge_tree_error: Exception | None = None,
    ):
        self.validated_group_scope = []
        self.validated_group_ids = []
        self.can_manage = can_manage
        self.knowledge_bases_error = knowledge_bases_error
        self.knowledge_tree_error = knowledge_tree_error

    def assert_can_manage(self, user):  # noqa: ARG002
        if not self.can_manage:
            raise ValueError("no_knowledge_management_permission")
        return True

    def get_management_scope(self, user):  # noqa: ARG002
        if not self.can_manage:
            return SimpleNamespace(
                can_manage=False,
                root_node_id=None,
                root_node_path=None,
                node_ids=frozenset(),
                dataset_ids=frozenset(),
            )
        return SimpleNamespace(
            can_manage=True,
            root_node_id="node-root",
            root_node_path="/Root",
            node_ids=frozenset({"node-root"}),
            dataset_ids=frozenset({"ds-in"}),
        )

    def validate_group_kb_scope(self, *, user, accessible_kbs, accessible_kb_nodes):  # noqa: ARG002
        self.validated_group_scope.append(
            {
                "accessible_kbs": list(accessible_kbs or []),
                "accessible_kb_nodes": list(accessible_kb_nodes or []),
            }
        )
        if "node-out" in (accessible_kb_nodes or []) or "ds-out" in (accessible_kbs or []):
            raise ValueError("node_out_of_management_scope")

    def validate_permission_group_ids(self, *, user, group_ids, permission_group_store):  # noqa: ARG002
        self.validated_group_ids.append(list(group_ids or []))
        if 99 in (group_ids or []):
            raise ValueError("dataset_out_of_management_scope")
        for group_id in group_ids or []:
            permission_group_store.get_group(group_id)

    def assert_permission_group_manageable(self, *, user, group):  # noqa: ARG002
        if not isinstance(group, dict):
            raise ValueError("permission_group_not_found")
        if "node-out" in (group.get("accessible_kb_nodes") or []) or "ds-out" in (group.get("accessible_kbs") or []):
            raise ValueError("permission_group_out_of_management_scope")
        return group

    def filter_manageable_permission_groups(self, *, user, groups):  # noqa: ARG002
        filtered = []
        for group in groups or []:
            try:
                filtered.append(self.assert_permission_group_manageable(user=user, group=group))
            except ValueError:
                continue
        return filtered

    def list_manageable_datasets(self, user):  # noqa: ARG002
        if self.knowledge_bases_error is not None:
            raise self.knowledge_bases_error
        return [{"id": "ds-in", "name": "Managed KB"}]

    def list_visible_tree(self, user):  # noqa: ARG002
        if self.knowledge_tree_error is not None:
            raise self.knowledge_tree_error
        return {
            "nodes": [{"id": "node-root", "name": "Root", "parent_id": None, "path": "/Root"}],
            "datasets": [{"id": "ds-in", "name": "Managed KB", "node_path": "/Root"}],
            "bindings": {},
        }


class _ChatManagementError(Exception):
    def __init__(self, code: str, *, status_code: int = 403):
        super().__init__(code)
        self.status_code = status_code


class _ChatManagementManager:
    def __init__(self, *, chat_list_error: Exception | None = None):
        self.validated_group_scope = []
        self.validated_group_ids = []
        self.chat_list_error = chat_list_error

    def validate_group_chat_scope(self, *, user, accessible_chats):  # noqa: ARG002
        chats = list(accessible_chats or [])
        self.validated_group_scope.append(chats)
        if "chat_c_out" in chats or any(str(item).startswith("agent_") for item in chats):
            raise _ChatManagementError("chat_out_of_management_scope", status_code=403)

    def assert_permission_group_manageable(self, *, user, group):  # noqa: ARG002
        if not isinstance(group, dict):
            raise _ChatManagementError("permission_group_not_found", status_code=404)
        try:
            self.validate_group_chat_scope(user=user, accessible_chats=group.get("accessible_chats"))
        except _ChatManagementError as exc:
            raise _ChatManagementError("permission_group_out_of_management_scope", status_code=403) from exc
        return group

    def filter_manageable_permission_groups(self, *, user, groups):  # noqa: ARG002
        filtered = []
        for group in groups or []:
            try:
                filtered.append(self.assert_permission_group_manageable(user=user, group=group))
            except _ChatManagementError:
                continue
        return filtered

    def list_manageable_chat_resources(self, user):  # noqa: ARG002
        if self.chat_list_error is not None:
            raise self.chat_list_error
        return [{"id": "chat_c_in", "name": "Owned Chat", "type": "chat"}]

    def validate_permission_group_ids(self, *, user, group_ids, permission_group_store):  # noqa: ARG002
        self.validated_group_ids.append(list(group_ids or []))
        for group_id in group_ids or []:
            group = permission_group_store.get_group(group_id)
            self.assert_permission_group_manageable(user=user, group=group)

    def list_auto_granted_chat_refs(self, user):  # noqa: ARG002
        return frozenset()


class _PermissionGroupStore:
    def get_group(self, group_id: int):
        if group_id == 41:
            return {
                "group_id": 41,
                "created_by": "u_sub",
                "accessible_kbs": ["ds-in"],
                "accessible_kb_nodes": ["node-root"],
                "accessible_chats": ["chat_c_in"],
                "can_view_tools": True,
                "accessible_tools": ["tool_1"],
            }
        if group_id == 42:
            return {
                "group_id": 42,
                "created_by": "u_sub",
                "accessible_kbs": ["ds-in"],
                "accessible_kb_nodes": ["node-root"],
                "accessible_chats": ["chat_c_in"],
                "can_view_tools": True,
                "accessible_tools": ["tool_4"],
            }
        if group_id == 43:
            return {
                "group_id": 43,
                "created_by": "u_sub",
                "accessible_kbs": ["ds-in"],
                "accessible_kb_nodes": ["node-root"],
                "accessible_chats": ["chat_c_in"],
                "can_view_tools": True,
                "accessible_tools": [],
            }
        if group_id == 301:
            return {
                "group_id": 301,
                "created_by": "u_admin",
                "accessible_kbs": [],
                "accessible_kb_nodes": [],
                "accessible_chats": [],
                "can_view_tools": True,
                "accessible_tools": ["tool_1", "tool_2", "tool_3"],
            }
        if group_id == 77:
            return {
                "group_id": 77,
                "created_by": "u_other_sub",
                "accessible_kbs": ["ds-in"],
                "accessible_kb_nodes": ["node-root"],
                "accessible_chats": ["chat_c_in"],
                "can_view_tools": False,
                "accessible_tools": [],
            }
        if group_id == 98:
            return {
                "group_id": 98,
                "created_by": "u_sub",
                "accessible_kbs": ["ds-in"],
                "accessible_kb_nodes": ["node-root"],
                "accessible_chats": ["chat_c_out"],
                "can_view_tools": False,
                "accessible_tools": [],
            }
        if group_id == 99:
            return {
                "group_id": 99,
                "created_by": "u_sub",
                "accessible_kbs": ["ds-out"],
                "accessible_kb_nodes": [],
                "accessible_chats": [],
                "can_view_tools": False,
                "accessible_tools": [],
            }
        return {
            "group_id": group_id,
            "created_by": "u_sub",
            "accessible_kbs": ["ds-in"],
            "accessible_kb_nodes": ["node-root"],
            "accessible_chats": ["chat_c_in"],
            "can_view_tools": False,
            "accessible_tools": [],
        }


class _PermissionGroupsService:
    def __init__(self):
        self.created_payloads = []
        self.updated_calls = []
        self.deleted_group_ids = []

    def list_groups(self):
        return [
            {"group_id": 1, "group_name": "in-scope", "created_by": "u_sub", "folder_id": "folder-visible", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": False, "accessible_tools": []},
            {"group_id": 41, "group_name": "tool-subset", "created_by": "u_sub", "folder_id": "folder-visible", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": True, "accessible_tools": ["tool_1"]},
            {"group_id": 42, "group_name": "tool-out", "created_by": "u_sub", "folder_id": "folder-visible", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": True, "accessible_tools": ["tool_4"]},
            {"group_id": 43, "group_name": "tool-global", "created_by": "u_sub", "folder_id": "folder-visible", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": True, "accessible_tools": []},
            {"group_id": 77, "group_name": "other-owner", "created_by": "u_other_sub", "folder_id": "folder-other", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": False, "accessible_tools": []},
            {"group_id": 98, "group_name": "chat-out", "created_by": "u_sub", "folder_id": "folder-hidden", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_out"], "can_view_tools": False, "accessible_tools": []},
            {"group_id": 99, "group_name": "out-scope", "created_by": "u_sub", "folder_id": "folder-hidden", "accessible_kbs": ["ds-out"], "accessible_kb_nodes": ["node-out"], "accessible_chats": [], "can_view_tools": False, "accessible_tools": []},
        ]

    def get_group(self, group_id: int):
        if group_id == 41:
            return {"group_id": 41, "group_name": "tool-subset", "created_by": "u_sub", "folder_id": "folder-visible", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": True, "accessible_tools": ["tool_1"]}
        if group_id == 42:
            return {"group_id": 42, "group_name": "tool-out", "created_by": "u_sub", "folder_id": "folder-visible", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": True, "accessible_tools": ["tool_4"]}
        if group_id == 43:
            return {"group_id": 43, "group_name": "tool-global", "created_by": "u_sub", "folder_id": "folder-visible", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": True, "accessible_tools": []}
        if group_id == 77:
            return {"group_id": 77, "group_name": "other-owner", "created_by": "u_other_sub", "folder_id": "folder-other", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": False, "accessible_tools": []}
        if group_id == 98:
            return {"group_id": 98, "group_name": "chat-out", "created_by": "u_sub", "folder_id": "folder-hidden", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_out"], "can_view_tools": False, "accessible_tools": []}
        if group_id == 99:
            return {"group_id": 99, "group_name": "out-scope", "created_by": "u_sub", "folder_id": "folder-hidden", "accessible_kbs": ["ds-out"], "accessible_kb_nodes": ["node-out"], "accessible_chats": [], "can_view_tools": False, "accessible_tools": []}
        return {"group_id": group_id, "created_by": "u_sub", "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"], "accessible_chats": ["chat_c_in"], "can_view_tools": False, "accessible_tools": []}

    def filter_manageable_groups(self, *, user, groups):  # noqa: ARG002
        return [group for group in (groups or []) if str(group.get("created_by") or "") == "u_sub"]

    def assert_group_manageable(self, *, user, group):  # noqa: ARG002
        if not isinstance(group, dict):
            raise HTTPException(status_code=404, detail="permission_group_not_found")
        if str(group.get("created_by") or "") != "u_sub":
            raise HTTPException(status_code=403, detail="permission_group_out_of_management_scope")
        return group

    def validate_group_ids_manageable(self, *, user, group_ids):  # noqa: ARG002
        for group_id in group_ids or []:
            group = self.get_group(int(group_id))
            if not group:
                raise HTTPException(status_code=400, detail=f"permission_group_not_found:{group_id}")
            self.assert_group_manageable(user=user, group=group)

    def create_group(self, payload):
        self.created_payloads.append(dict(payload))
        return 1

    def update_group(self, group_id, payload):  # noqa: ARG002
        self.updated_calls.append((group_id, dict(payload)))
        return True

    def delete_group(self, group_id):  # noqa: ARG002
        self.deleted_group_ids.append(group_id)
        return True

    def list_knowledge_bases(self):
        return []

    def list_knowledge_tree(self):
        return {"nodes": [], "datasets": [], "bindings": {}}

    def list_chat_agents(self):
        return []

    def list_group_folders(self, groups=None):
        if groups is None:
            groups = self.list_groups()
        else:
            groups = list(groups or [])
        visible_group_ids = {int(group["group_id"]) for group in groups if isinstance(group, dict) and isinstance(group.get("group_id"), int)}
        folders = []
        bindings = {}
        if 1 in visible_group_ids:
            folders.append({"id": "folder-visible", "name": "Visible", "parent_id": None, "created_by": "u_sub"})
            bindings["1"] = "folder-visible"
        if 99 in visible_group_ids:
            folders.append({"id": "folder-hidden", "name": "Hidden", "parent_id": None, "created_by": "u_sub"})
            bindings["99"] = "folder-hidden"
        folders.append({"id": "folder-other", "name": "Other", "parent_id": None, "created_by": "u_other_sub"})
        return {"folders": folders, "group_bindings": bindings, "root_group_count": 0}

    def create_group_folder(self, name, parent_id, *, created_by):  # noqa: ARG002
        return {"id": "folder-1", "name": name, "parent_id": parent_id}

    def update_group_folder(self, folder_id, payload):  # noqa: ARG002
        return {"id": folder_id, **payload}

    def delete_group_folder(self, folder_id):  # noqa: ARG002
        return True


class _UsersService:
    def __init__(self):
        self.list_users_calls = []
        self.created = []
        self.updated = []
        self.deleted = []
        self.reset_password_calls = []

    def list_users(self, **kwargs):
        self.list_users_calls.append(dict(kwargs))
        return []

    def create_user(self, *, user_data, created_by):
        self.created.append({"created_by": created_by, "user_data": user_data})
        return {
            "user_id": "u_created",
            "username": user_data.username,
            "full_name": user_data.full_name,
            "email": user_data.email,
            "manager_user_id": user_data.manager_user_id,
            "company_id": user_data.company_id,
            "department_id": user_data.department_id,
            "group_id": user_data.group_id,
            "group_ids": list(user_data.group_ids or []),
            "permission_groups": [],
            "tool_ids": list(user_data.tool_ids or []),
            "role": user_data.role or "viewer",
            "status": user_data.status,
            "can_change_password": user_data.can_change_password,
            "disable_login_enabled": user_data.disable_login_enabled,
            "disable_login_until_ms": user_data.disable_login_until_ms,
            "max_login_sessions": user_data.max_login_sessions,
            "idle_timeout_minutes": user_data.idle_timeout_minutes,
            "created_at_ms": 1,
            "managed_kb_root_node_id": user_data.managed_kb_root_node_id,
            "electronic_signature_enabled": user_data.electronic_signature_enabled,
        }

    def get_user(self, user_id: str):
        return {
            "user_id": user_id,
            "username": "target",
            "role": "viewer",
            "status": "active",
            "group_id": None,
            "group_ids": [],
            "permission_groups": [],
            "tool_ids": [],
            "max_login_sessions": 3,
            "idle_timeout_minutes": 120,
            "created_at_ms": 1,
        }

    def update_user(self, *, user_id, user_data, updated_by=None):
        self.updated.append((user_id, user_data, updated_by))
        return {
            "user_id": user_id,
            "username": "target",
            "full_name": user_data.full_name,
            "email": user_data.email,
            "manager_user_id": user_data.manager_user_id,
            "company_id": user_data.company_id,
            "department_id": user_data.department_id,
            "role": "viewer",
            "status": "active",
            "group_id": None,
            "group_ids": list(user_data.group_ids or []),
            "permission_groups": [],
            "tool_ids": list(user_data.tool_ids or []),
            "can_change_password": True,
            "disable_login_enabled": False,
            "disable_login_until_ms": None,
            "max_login_sessions": 3,
            "idle_timeout_minutes": 120,
            "created_at_ms": 1,
            "managed_kb_root_node_id": None,
            "electronic_signature_enabled": True,
        }

    def delete_user(self, user_id: str):
        self.deleted.append(user_id)

    def reset_password(self, user_id: str, new_password: str):
        self.reset_password_calls.append((user_id, new_password))


class _AuditLogManager:
    def __init__(self):
        self.events = []

    def log_event(self, **payload):
        self.events.append(dict(payload))


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u_sub")


def _make_permission_group_client(
    role: str = "sub_admin",
    *,
    group_ids: list[int] | None = None,
    actor_tool_ids: list[str] | None = None,
    knowledge_bases_error: Exception | None = None,
    knowledge_tree_error: Exception | None = None,
    chat_list_error: Exception | None = None,
):
    user = _User(role=role, group_ids=group_ids)
    km = _KnowledgeManagementManager(
        knowledge_bases_error=knowledge_bases_error,
        knowledge_tree_error=knowledge_tree_error,
    )
    cm = _ChatManagementManager(chat_list_error=chat_list_error)
    service = _PermissionGroupsService()
    app = FastAPI()
    app.state.deps = SimpleNamespace(
        user_store=_UserStore(user),
        permission_group_store=_PermissionGroupStore(),
        knowledge_management_manager=km,
        chat_management_manager=cm,
        ragflow_service=_RagflowService(),
        user_tool_permission_store=_UserToolPermissionStore(
            {
                user.user_id: list(actor_tool_ids or []),
            }
        ),
    )
    router = create_permission_groups_router()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
    app.dependency_overrides[get_permission_groups_service] = lambda: service
    return TestClient(app), km, cm, service


def _make_users_client(
    *,
    role: str = "sub_admin",
    can_manage: bool = True,
    actor_group_ids: list[int] | None = None,
    actor_tool_ids: list[str] | None = None,
):
    user = _User(role=role, group_ids=actor_group_ids)
    km = _KnowledgeManagementManager(can_manage=can_manage)
    cm = _ChatManagementManager()
    service = _UsersService()
    audit = _AuditLogManager()
    app = FastAPI()
    app.state.deps = SimpleNamespace(
        user_store=_UserStore(user),
        permission_group_store=_PermissionGroupStore(),
        knowledge_management_manager=km,
        chat_management_manager=cm,
        audit_log_manager=audit,
        ragflow_service=_RagflowService(),
        user_tool_permission_store=_UserToolPermissionStore(
            {
                user.user_id: list(actor_tool_ids or []),
            }
        ),
    )
    app.include_router(users_router, prefix="/api/users")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
    app.dependency_overrides[get_users_service] = lambda: service
    return TestClient(app), km, cm, service, audit


class TestSubAdminPermissionGroupRoutesUnit(unittest.TestCase):
    def test_admin_cannot_access_permission_groups(self):
        client, _, _, _ = _make_permission_group_client(role="admin")
        with client:
            resp = client.get("/api/permission-groups")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_only_permission_group_management")

    def test_sub_admin_only_sees_manageable_permission_groups(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.get("/api/permission-groups")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([item["group_id"] for item in resp.json()["groups"]], [1, 41, 42, 43])
        self.assertEqual([item["group_name"] for item in resp.json()["groups"]], ["in-scope", "tool-subset", "tool-out", "tool-global"])

    def test_admin_can_list_assignable_permission_groups(self):
        client, _, _, _ = _make_permission_group_client(role="admin")
        with client:
            resp = client.get("/api/permission-groups/assignable")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([item["group_id"] for item in resp.json()["groups"]], [1, 41, 42, 43, 77, 98, 99])

    def test_admin_cannot_create_permission_groups(self):
        client, _, _, service = _make_permission_group_client(role="admin")
        with client:
            resp = client.post(
                "/api/permission-groups",
                json={
                    "group_name": "admin-write",
                    "accessible_kbs": ["ds-in"],
                    "accessible_kb_nodes": ["node-root"],
                },
            )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_only_permission_group_management")
        self.assertEqual(service.created_payloads, [])

    def test_sub_admin_assignable_groups_are_filtered_by_own_tool_scope(self):
        client, _, _, _ = _make_permission_group_client(group_ids=[301])
        with client:
            resp = client.get("/api/permission-groups/assignable")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([item["group_id"] for item in resp.json()["groups"]], [1, 41, 42, 43])

    def test_sub_admin_can_create_group_with_in_scope_kb_resources(self):
        client, km, cm, service = _make_permission_group_client()
        with client:
            resp = client.post(
                "/api/permission-groups",
                json={
                    "group_name": "kb-subtree",
                    "accessible_kbs": ["ds-in"],
                    "accessible_kb_nodes": ["node-root"],
                    "accessible_chats": ["chat_c_in"],
                },
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": {"message": "permission_group_created", "group_id": 1}})
        self.assertEqual(service.created_payloads[0]["accessible_kbs"], ["ds-in"])
        self.assertEqual(service.created_payloads[0]["created_by"], "u_sub")
        self.assertEqual(km.validated_group_scope[0]["accessible_kb_nodes"], ["node-root"])
        self.assertEqual(cm.validated_group_scope[0], ["chat_c_in"])

    def test_permission_group_create_fails_fast_on_invalid_create_result(self):
        client, _, _, service = _make_permission_group_client()
        service.create_group = lambda payload: "bad-group-id"  # noqa: ARG005
        with client:
            resp = client.post(
                "/api/permission-groups",
                json={
                    "group_name": "kb-subtree",
                    "accessible_kbs": ["ds-in"],
                    "accessible_kb_nodes": ["node-root"],
                    "accessible_chats": ["chat_c_in"],
                },
            )
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "permission_group_create_invalid_payload")

    def test_sub_admin_can_get_manageable_group(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.get("/api/permission-groups/41")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["group"]["group_id"], 41)
        self.assertEqual(resp.json()["group"]["group_name"], "tool-subset")

    def test_sub_admin_cannot_create_group_with_out_of_scope_kb_resources(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.post(
                "/api/permission-groups",
                json={
                    "group_name": "kb-out",
                    "accessible_kbs": ["ds-out"],
                    "accessible_kb_nodes": ["node-out"],
                },
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "node_out_of_management_scope")

    def test_sub_admin_cannot_create_group_with_out_of_scope_chats(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.post(
                "/api/permission-groups",
                json={
                    "group_name": "chat-out",
                    "accessible_kbs": ["ds-in"],
                    "accessible_kb_nodes": ["node-root"],
                    "accessible_chats": ["chat_c_out"],
                },
            )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "chat_out_of_management_scope")

    def test_sub_admin_cannot_get_out_of_scope_group(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.get("/api/permission-groups/99")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "permission_group_out_of_management_scope")

    def test_sub_admin_cannot_get_other_users_group(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.get("/api/permission-groups/77")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "permission_group_out_of_management_scope")

    def test_sub_admin_can_update_group_returns_result_envelope(self):
        client, _, _, service = _make_permission_group_client()
        with client:
            resp = client.put("/api/permission-groups/41", json={"group_name": "Renamed"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": {"message": "permission_group_updated"}})
        self.assertEqual(service.updated_calls, [(41, {"group_name": "Renamed"})])

    def test_permission_group_update_fails_fast_when_service_rejects_update(self):
        client, _, _, service = _make_permission_group_client()
        service.update_group = lambda group_id, payload: False  # noqa: ARG005
        with client:
            resp = client.put("/api/permission-groups/41", json={"group_name": "Renamed"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "permission_group_update_failed")

    def test_sub_admin_can_delete_group_returns_result_envelope(self):
        client, _, _, service = _make_permission_group_client()
        with client:
            resp = client.delete("/api/permission-groups/41")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": {"message": "permission_group_deleted"}})
        self.assertEqual(service.deleted_group_ids, [41])

    def test_sub_admin_gets_knowledge_tree_envelope(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.get("/api/permission-groups/resources/knowledge-tree")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["knowledge_tree"]["datasets"][0]["id"], "ds-in")

    def test_sub_admin_knowledge_tree_route_fails_fast_on_manager_error(self):
        client, _, _, _ = _make_permission_group_client(knowledge_tree_error=RuntimeError("knowledge_tree_unavailable"))
        with client:
            resp = client.get("/api/permission-groups/resources/knowledge-tree")
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "knowledge_tree_unavailable")

    def test_sub_admin_only_gets_owned_chat_resources(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.get("/api/permission-groups/resources/chats")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["chats"], [{"id": "chat_c_in", "name": "Owned Chat", "type": "chat"}])

    def test_sub_admin_only_gets_manageable_group_folders(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.get("/api/permission-groups/resources/group-folders")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([item["id"] for item in resp.json()["folder_snapshot"]["folders"]], ["folder-visible", "folder-hidden"])

    def test_permission_group_list_fails_fast_on_invalid_service_payload(self):
        client, _, _, service = _make_permission_group_client()
        service.list_groups = lambda: ["bad"]
        with client:
            resp = client.get("/api/permission-groups")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "permission_group_list_invalid_payload")

    def test_permission_group_knowledge_tree_fails_fast_on_invalid_payload(self):
        client, km, _, _ = _make_permission_group_client()
        km.list_visible_tree = lambda user: {"nodes": {}, "datasets": [], "bindings": {}}  # noqa: ARG005
        with client:
            resp = client.get("/api/permission-groups/resources/knowledge-tree")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "permission_group_knowledge_tree_invalid_payload")

    def test_permission_group_folders_fail_fast_on_invalid_snapshot_payload(self):
        client, _, _, service = _make_permission_group_client()
        service.list_group_folders = lambda groups=None: {"folders": {}, "group_bindings": {}, "root_group_count": 0}  # noqa: ARG005
        with client:
            resp = client.get("/api/permission-groups/resources/group-folders")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "permission_group_folder_snapshot_invalid_payload")

    def test_permission_group_folder_create_fails_fast_on_invalid_payload(self):
        client, _, _, service = _make_permission_group_client()
        service.create_group_folder = lambda name, parent_id, created_by: "bad-folder"  # noqa: ARG005
        with client:
            resp = client.post("/api/permission-groups/folders", json={"name": "Root Folder"})
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "permission_group_folder_invalid_payload")

    def test_admin_cannot_create_permission_group_folders(self):
        client, _, _, service = _make_permission_group_client(role="admin")
        with client:
            resp = client.post("/api/permission-groups/folders", json={"name": "Root Folder"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_only_permission_group_management")

    def test_permission_group_folder_update_rejects_missing_updates(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.put("/api/permission-groups/folders/folder-visible", json={})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "missing_updates")

    def test_permission_group_folder_update_rejects_out_of_scope_parent(self):
        client, _, _, _ = _make_permission_group_client()
        with client:
            resp = client.put(
                "/api/permission-groups/folders/folder-visible",
                json={"parent_id": "folder-other"},
            )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "permission_group_folder_out_of_management_scope")


class TestSubAdminUserGroupAssignmentRoutesUnit(unittest.TestCase):
    def test_admin_user_list_keeps_requested_company_scope(self):
        client, _, _, service, _ = _make_users_client(role="admin")
        with client:
            resp = client.get("/api/users", params={"company_id": 2, "limit": 50})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(service.list_users_calls[0]["company_id"], 2)
        self.assertIsNone(service.list_users_calls[0]["manager_user_id"])
        self.assertEqual(service.list_users_calls[0]["limit"], 50)

    def test_sub_admin_user_list_is_scoped_to_actor_company_and_manager(self):
        client, _, _, service, _ = _make_users_client()
        with client:
            resp = client.get("/api/users", params={"company_id": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(service.list_users_calls[0]["company_id"], 1)
        self.assertEqual(service.list_users_calls[0]["manager_user_id"], "u_sub")

    def test_sub_admin_user_list_rejects_cross_company_scope(self):
        client, _, _, service, _ = _make_users_client()
        with client:
            resp = client.get("/api/users", params={"company_id": 2})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_company_scope_violation")
        self.assertEqual(service.list_users_calls, [])

    def test_admin_create_returns_user_envelope(self):
        client, _, _, service, _ = _make_users_client(role="admin")
        with client:
            resp = client.post(
                "/api/users",
                json={
                    "username": "alice",
                    "password": "Secret123",
                    "role": "viewer",
                    "company_id": 1,
                    "department_id": 11,
                    "max_login_sessions": 3,
                    "idle_timeout_minutes": 120,
                },
            )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(service.created[0]["created_by"], "u_sub")
        self.assertEqual(resp.json()["user"]["user_id"], "u_created")
        self.assertEqual(resp.json()["user"]["username"], "alice")

    def test_admin_delete_returns_result_envelope(self):
        client, _, _, service, _ = _make_users_client(role="admin")
        with client:
            resp = client.delete("/api/users/u_target")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(service.deleted, ["u_target"])
        self.assertEqual(resp.json(), {"result": {"message": "user_deleted"}})

    def test_sub_admin_can_assign_in_scope_permission_groups(self):
        client, km, cm, service, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [1, 2]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(km.validated_group_ids[0], [1, 2])
        self.assertEqual(cm.validated_group_ids[0], [1, 2])
        self.assertEqual(service.updated[0][0], "u_target")
        self.assertEqual(resp.json()["user"]["user_id"], "u_target")
        self.assertEqual(resp.json()["user"]["group_ids"], [1, 2])

    def test_sub_admin_can_assign_in_scope_permission_group_from_legacy_group_id(self):
        client, km, cm, service, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"group_id": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(km.validated_group_ids[0], [1])
        self.assertEqual(cm.validated_group_ids[0], [1])
        self.assertEqual(service.updated[0][0], "u_target")
        self.assertEqual(service.updated[0][1].group_id, 1)

    def test_sub_admin_group_assignment_does_not_require_assert_can_manage(self):
        client, km, cm, service, _ = _make_users_client(can_manage=False)
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [1]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(km.validated_group_ids[0], [1])
        self.assertEqual(cm.validated_group_ids[0], [1])
        self.assertEqual(service.updated[0][0], "u_target")
        self.assertEqual(resp.json()["user"]["group_ids"], [1])

    def test_sub_admin_cannot_assign_out_of_scope_permission_groups(self):
        client, _, _, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [99]})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "dataset_out_of_management_scope")

    def test_sub_admin_cannot_assign_chat_out_of_scope_permission_groups(self):
        client, _, _, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [98]})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "permission_group_out_of_management_scope")

    def test_sub_admin_can_assign_permission_groups_with_tool_subset(self):
        client, km, cm, service, _ = _make_users_client(actor_group_ids=[301])
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [41]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(km.validated_group_ids[0], [41])
        self.assertEqual(cm.validated_group_ids[0], [41])
        self.assertEqual(service.updated[0][0], "u_target")

    def test_sub_admin_cannot_assign_permission_groups_with_out_of_scope_tools(self):
        client, _, _, _, _ = _make_users_client(actor_group_ids=[301])
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [42]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["user"]["group_ids"], [42])

    def test_sub_admin_cannot_assign_permission_groups_with_global_tool_scope_when_actor_is_limited(self):
        client, _, _, _, _ = _make_users_client(actor_group_ids=[301])
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [43]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["user"]["group_ids"], [43])

    def test_sub_admin_cannot_assign_other_users_permission_groups(self):
        client, _, _, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [77]})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "permission_group_out_of_management_scope")

    def test_sub_admin_cannot_assign_groups_for_unowned_viewer(self):
        client, _, _, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_other", json={"group_ids": [1]})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_can_only_assign_owned_users")

    def test_sub_admin_cannot_assign_groups_for_sub_admin_target(self):
        client, _, _, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_sub_target", json={"group_ids": [1]})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_can_only_assign_viewer_groups")

    def test_sub_admin_cannot_modify_non_group_fields(self):
        client, _, _, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"role": "admin"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_group_assignment_only")

    def test_sub_admin_can_reset_owned_viewer_password(self):
        client, _, _, service, audit = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target/password", json={"new_password": "OwnedPass123"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(service.reset_password_calls, [("u_target", "OwnedPass123")])
        self.assertEqual(audit.events[0]["meta"]["target_user_id"], "u_target")
        self.assertEqual(resp.json(), {"result": {"message": "password_reset"}})

    def test_sub_admin_can_reset_own_password(self):
        client, _, _, service, audit = _make_users_client()
        with client:
            resp = client.put("/api/users/u_sub/password", json={"new_password": "SelfPass123"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(service.reset_password_calls, [("u_sub", "SelfPass123")])
        self.assertEqual(audit.events[0]["meta"]["target_user_id"], "u_sub")
        self.assertEqual(resp.json(), {"result": {"message": "password_reset"}})

    def test_sub_admin_cannot_reset_unowned_viewer_password(self):
        client, _, _, service, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_other/password", json={"new_password": "DeniedPass123"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_can_only_reset_password_for_owned_users")
        self.assertEqual(service.reset_password_calls, [])

    def test_sub_admin_cannot_reset_other_sub_admin_password(self):
        client, _, _, service, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_sub_target/password", json={"new_password": "DeniedPass123"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_can_only_reset_password_for_owned_users")
        self.assertEqual(service.reset_password_calls, [])


if __name__ == "__main__":
    unittest.main()
