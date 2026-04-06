import unittest
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.knowledge.routes.directory import router as directory_router


class _User:
    def __init__(self, *, role: str = "viewer", group_ids=None):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = list(group_ids or [])


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    def __init__(self, *, can_manage_kb_directory: bool, accessible_kbs=None, can_view_kb_config: bool = False):
        self._can_manage_kb_directory = bool(can_manage_kb_directory)
        self._accessible_kbs = list(accessible_kbs or [])
        self._can_view_kb_config = bool(can_view_kb_config)

    def get_group(self, group_id: int):  # noqa: ARG002
        return {
            "can_upload": False,
            "can_review": False,
            "can_download": False,
            "can_delete": False,
            "can_manage_kb_directory": self._can_manage_kb_directory,
            "can_view_kb_config": self._can_view_kb_config,
            "accessible_kbs": list(self._accessible_kbs),
            "accessible_chats": [],
        }


class _RagflowService:
    def get_dataset_index(self):
        return {
            "by_id": {"ds_1": "KB-1"},
            "by_name": {"KB-1": "ds_1"},
        }

    def normalize_dataset_id(self, dataset_ref: str):
        index = self.get_dataset_index()
        if dataset_ref in index["by_id"]:
            return dataset_ref
        return index["by_name"].get(dataset_ref)

    def list_datasets(self):
        return [{"id": "ds_1", "name": "KB-1"}]


class _DirectoryManager:
    def __init__(self):
        self.create_calls = []
        self.assign_calls = []
        self.delete_calls = []
        self.nodes = []

    def create_node(self, *, name: str, parent_id: str | None, created_by: str):
        self.create_calls.append({"name": name, "parent_id": parent_id, "created_by": created_by})
        node = {"id": f"node_{len(self.create_calls)}", "name": name, "parent_id": parent_id}
        self.nodes.append(node)
        return node

    def snapshot(self, datasets, *, prune_unknown: bool):  # noqa: ARG002
        normalized = []
        bindings = {}
        for dataset in datasets or []:
            dataset_id = dataset.get("id")
            if not dataset_id:
                continue
            normalized.append(
                {
                    "id": dataset_id,
                    "name": dataset.get("name"),
                    "node_id": None,
                    "node_path": "/",
                }
            )
            bindings[str(dataset_id)] = None
        return {"nodes": list(self.nodes), "datasets": normalized, "bindings": bindings}

    def assign_dataset(self, *, dataset_id: str, node_id: str | None):
        self.assign_calls.append({"dataset_id": dataset_id, "node_id": node_id})
        return True

    def delete_node(self, node_id: str):
        self.delete_calls.append(node_id)
        return True


class _Deps:
    def __init__(self, *, user: _User, can_manage_kb_directory: bool, accessible_kbs=None, can_view_kb_config: bool = False):
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore(
            can_manage_kb_directory=can_manage_kb_directory,
            accessible_kbs=accessible_kbs,
            can_view_kb_config=can_view_kb_config,
        )
        self.ragflow_service = _RagflowService()
        self.knowledge_tree_manager = _DirectoryManager()
        self.knowledge_directory_manager = self.knowledge_tree_manager


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


def _make_client(
    *,
    role: str,
    can_manage_kb_directory: bool,
    accessible_kbs=None,
    can_view_kb_config: bool = False,
) -> tuple[TestClient, _Deps]:
    user = _User(role=role, group_ids=[1] if role != "admin" else [])
    deps = _Deps(
        user=user,
        can_manage_kb_directory=can_manage_kb_directory,
        accessible_kbs=accessible_kbs,
        can_view_kb_config=can_view_kb_config,
    )

    app = FastAPI()
    app.state.deps = deps
    app.include_router(directory_router, prefix="/api/knowledge")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

    return TestClient(app), deps


class TestKnowledgeDirectoryRoutePermissionsUnit(unittest.TestCase):
    def test_list_directories_allows_user_with_kb_scope_without_kb_config_permission(self):
        client, _ = _make_client(
            role="viewer",
            can_manage_kb_directory=False,
            accessible_kbs=["ds_1"],
            can_view_kb_config=False,
        )
        with client:
            resp = client.get("/api/knowledge/directories")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual([item.get("id") for item in body.get("datasets", [])], ["ds_1"])

    def test_create_directory_rejects_user_without_manage_permission(self):
        client, _ = _make_client(role="viewer", can_manage_kb_directory=False)
        with client:
            resp = client.post("/api/knowledge/directories", json={"name": "Folder A"})

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("detail"), "no_kb_directory_manage_permission")

    def test_create_directory_allows_user_with_manage_permission(self):
        client, deps = _make_client(role="viewer", can_manage_kb_directory=True)
        with client:
            resp = client.post(
                "/api/knowledge/directories",
                json={"name": "Folder A", "parent_id": None},
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("node", {}).get("id"), "node_1")
        self.assertEqual(len(deps.knowledge_directory_manager.create_calls), 1)
        self.assertEqual(
            deps.knowledge_directory_manager.create_calls[0],
            {"name": "Folder A", "parent_id": None, "created_by": "u1"},
        )

    def test_assign_dataset_allows_user_with_manage_permission(self):
        client, deps = _make_client(role="viewer", can_manage_kb_directory=True)
        with client:
            resp = client.put(
                "/api/knowledge/directories/datasets/ds_1/node",
                json={"node_id": "node_1"},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "result": {
                    "message": "knowledge_dataset_directory_assigned",
                    "dataset_id": "ds_1",
                    "node_id": "node_1",
                }
            },
        )
        self.assertEqual(
            deps.knowledge_directory_manager.assign_calls,
            [{"dataset_id": "ds_1", "node_id": "node_1"}],
        )

    def test_assign_dataset_rejects_unknown_dataset_ref(self):
        client, _deps = _make_client(role="viewer", can_manage_kb_directory=True)
        with client:
            resp = client.put(
                "/api/knowledge/directories/datasets/unknown-ds/node",
                json={"node_id": "node_1"},
            )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json().get("detail"), "dataset_not_found")

    def test_delete_directory_returns_result_envelope(self):
        client, deps = _make_client(role="viewer", can_manage_kb_directory=True)
        with client:
            deps.knowledge_directory_manager.create_node(
                name="Folder A",
                parent_id=None,
                created_by="seed",
            )
            resp = client.delete("/api/knowledge/directories/node_1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {"result": {"message": "knowledge_directory_deleted", "node_id": "node_1"}},
        )
        self.assertEqual(deps.knowledge_directory_manager.delete_calls, ["node_1"])

    def test_admin_company_override_lists_and_creates_target_company_directories(self):
        client, deps = _make_client(role="admin", can_manage_kb_directory=False)
        tenant_deps = _Deps(user=_User(role="admin"), can_manage_kb_directory=True)
        tenant_deps.knowledge_directory_manager.create_node(
            name="Tenant Folder",
            parent_id=None,
            created_by="seed",
        )

        with patch(
            "backend.app.modules.knowledge.routes.directory.get_tenant_dependencies",
            return_value=tenant_deps,
        ) as mocked_get_tenant_deps:
            with client:
                list_resp = client.get("/api/knowledge/directories?company_id=2")
                create_resp = client.post(
                    "/api/knowledge/directories?company_id=2",
                    json={"name": "Folder B", "parent_id": None},
                )

        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(create_resp.status_code, 200)
        self.assertEqual(len(tenant_deps.knowledge_directory_manager.create_calls), 2)
        self.assertEqual(
            tenant_deps.knowledge_directory_manager.create_calls[-1],
            {"name": "Folder B", "parent_id": None, "created_by": "u1"},
        )
        mocked_get_tenant_deps.assert_called_with(client.app, company_id=2)
        self.assertEqual([], deps.knowledge_directory_manager.create_calls)

    def test_non_admin_cannot_use_company_override(self):
        client, _ = _make_client(role="viewer", can_manage_kb_directory=True)
        with client:
            resp = client.get("/api/knowledge/directories?company_id=2")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("detail"), "admin_required")

    def test_list_directories_fails_fast_on_invalid_tree_payload(self):
        client, deps = _make_client(
            role="viewer",
            can_manage_kb_directory=False,
            accessible_kbs=["ds_1"],
            can_view_kb_config=False,
        )
        deps.knowledge_directory_manager.snapshot = lambda datasets, prune_unknown=False: {"nodes": {}, "datasets": [], "bindings": {}}  # noqa: ARG005
        with client:
            resp = client.get("/api/knowledge/directories")

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json().get("detail"), "knowledge_directory_tree_invalid_payload")

    def test_admin_list_directories_fails_fast_on_invalid_dataset_list_payload(self):
        client, deps = _make_client(role="admin", can_manage_kb_directory=False)
        deps.ragflow_service.list_datasets = lambda: "bad-datasets"
        with client:
            resp = client.get("/api/knowledge/directories")

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json().get("detail"), "knowledge_directory_dataset_list_invalid_payload")

    def test_create_directory_fails_fast_on_invalid_node_payload(self):
        client, deps = _make_client(role="viewer", can_manage_kb_directory=True)
        deps.knowledge_directory_manager.create_node = lambda **kwargs: "bad-node"
        with client:
            resp = client.post(
                "/api/knowledge/directories",
                json={"name": "Folder A", "parent_id": None},
            )

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json().get("detail"), "knowledge_directory_node_invalid_payload")

    def test_list_directories_requires_knowledge_tree_manager(self):
        client, deps = _make_client(
            role="viewer",
            can_manage_kb_directory=False,
            accessible_kbs=["ds_1"],
            can_view_kb_config=False,
        )
        del deps.knowledge_tree_manager
        with client:
            resp = client.get("/api/knowledge/directories")

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json().get("detail"), "knowledge_tree_manager_unavailable")


if __name__ == "__main__":
    unittest.main()
