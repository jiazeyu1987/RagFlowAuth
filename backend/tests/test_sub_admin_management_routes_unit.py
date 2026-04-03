import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.permission_groups.router import create_router as create_permission_groups_router, get_service as get_permission_groups_service
from backend.app.modules.users.router import get_service as get_users_service, router as users_router


class _User:
    def __init__(self, *, role: str = "sub_admin"):
        self.user_id = "u_sub"
        self.username = "sub_admin"
        self.email = "sub@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.managed_kb_root_node_id = "node-root"


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _KnowledgeManagementManager:
    def __init__(self):
        self.validated_group_scope = []
        self.validated_group_ids = []

    def assert_can_manage(self, user):  # noqa: ARG002
        return True

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


class _PermissionGroupStore:
    def get_group(self, group_id: int):
        if group_id == 99:
            return {"group_id": 99, "accessible_kbs": ["ds-out"], "accessible_kb_nodes": []}
        return {"group_id": group_id, "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"]}


class _PermissionGroupsService:
    def __init__(self):
        self.created_payloads = []

    def list_groups(self):
        return []

    def get_group(self, group_id: int):
        return {"group_id": group_id, "accessible_kbs": ["ds-in"], "accessible_kb_nodes": ["node-root"]}

    def create_group(self, payload):
        self.created_payloads.append(dict(payload))
        return 1

    def update_group(self, group_id, payload):  # noqa: ARG002
        return True

    def delete_group(self, group_id):  # noqa: ARG002
        return True

    def list_knowledge_bases(self):
        return []

    def list_knowledge_tree(self):
        return {"nodes": [], "datasets": [], "bindings": {}}

    def list_chat_agents(self):
        return []

    def list_group_folders(self):
        return {"folders": [], "group_bindings": {}, "root_group_count": 0}

    def create_group_folder(self, name, parent_id, *, created_by):  # noqa: ARG002
        return {"id": "folder-1", "name": name, "parent_id": parent_id}

    def update_group_folder(self, folder_id, payload):  # noqa: ARG002
        return {"id": folder_id, **payload}

    def delete_group_folder(self, folder_id):  # noqa: ARG002
        return True


class _UsersService:
    def __init__(self):
        self.updated = []

    def list_users(self, **kwargs):  # noqa: ARG002
        return []

    def get_user(self, user_id: str):
        return {
            "user_id": user_id,
            "username": "target",
            "role": "viewer",
            "status": "active",
            "group_id": None,
            "group_ids": [],
            "permission_groups": [],
            "max_login_sessions": 3,
            "idle_timeout_minutes": 120,
            "created_at_ms": 1,
        }

    def update_user(self, *, user_id, user_data):
        self.updated.append((user_id, user_data))
        return {
            "user_id": user_id,
            "username": "target",
            "role": "viewer",
            "status": "active",
            "group_id": None,
            "group_ids": list(user_data.group_ids or []),
            "permission_groups": [],
            "max_login_sessions": 3,
            "idle_timeout_minutes": 120,
            "created_at_ms": 1,
        }


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u_sub")


def _make_permission_group_client():
    user = _User(role="sub_admin")
    km = _KnowledgeManagementManager()
    service = _PermissionGroupsService()
    app = FastAPI()
    app.state.deps = SimpleNamespace(
        user_store=_UserStore(user),
        permission_group_store=_PermissionGroupStore(),
        knowledge_management_manager=km,
    )
    router = create_permission_groups_router()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
    app.dependency_overrides[get_permission_groups_service] = lambda: service
    return TestClient(app), km, service


def _make_users_client():
    user = _User(role="sub_admin")
    km = _KnowledgeManagementManager()
    service = _UsersService()
    app = FastAPI()
    app.state.deps = SimpleNamespace(
        user_store=_UserStore(user),
        permission_group_store=_PermissionGroupStore(),
        knowledge_management_manager=km,
    )
    app.include_router(users_router, prefix="/api/users")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
    app.dependency_overrides[get_users_service] = lambda: service
    return TestClient(app), km, service


class TestSubAdminPermissionGroupRoutesUnit(unittest.TestCase):
    def test_sub_admin_can_create_group_with_in_scope_kb_resources(self):
        client, km, service = _make_permission_group_client()
        with client:
            resp = client.post(
                "/api/permission-groups",
                json={
                    "group_name": "kb-subtree",
                    "accessible_kbs": ["ds-in"],
                    "accessible_kb_nodes": ["node-root"],
                },
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["group_id"], 1)
        self.assertEqual(service.created_payloads[0]["accessible_kbs"], ["ds-in"])
        self.assertEqual(km.validated_group_scope[0]["accessible_kb_nodes"], ["node-root"])

    def test_sub_admin_cannot_create_group_with_out_of_scope_kb_resources(self):
        client, _, _ = _make_permission_group_client()
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


class TestSubAdminUserGroupAssignmentRoutesUnit(unittest.TestCase):
    def test_sub_admin_can_assign_in_scope_permission_groups(self):
        client, km, service = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [1, 2]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(km.validated_group_ids[0], [1, 2])
        self.assertEqual(service.updated[0][0], "u_target")

    def test_sub_admin_cannot_assign_out_of_scope_permission_groups(self):
        client, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"group_ids": [99]})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "dataset_out_of_management_scope")

    def test_sub_admin_cannot_modify_non_group_fields(self):
        client, _, _ = _make_users_client()
        with client:
            resp = client.put("/api/users/u_target", json={"role": "admin"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "sub_admin_group_assignment_only")


if __name__ == "__main__":
    unittest.main()
