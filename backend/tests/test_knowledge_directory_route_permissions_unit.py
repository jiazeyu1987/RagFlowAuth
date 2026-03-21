import unittest

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
    def __init__(self, *, can_manage_kb_directory: bool):
        self._can_manage_kb_directory = bool(can_manage_kb_directory)

    def get_group(self, group_id: int):  # noqa: ARG002
        return {
            "can_upload": False,
            "can_review": False,
            "can_download": False,
            "can_delete": False,
            "can_manage_kb_directory": self._can_manage_kb_directory,
            "accessible_kbs": [],
            "accessible_chats": [],
        }


class _RagflowService:
    def get_dataset_index(self):
        return {"by_id": {}, "by_name": {}}

    def normalize_dataset_id(self, dataset_ref: str):
        return dataset_ref


class _DirectoryManager:
    def __init__(self):
        self.create_calls = []
        self.assign_calls = []

    def create_node(self, *, name: str, parent_id: str | None, created_by: str):
        self.create_calls.append({"name": name, "parent_id": parent_id, "created_by": created_by})
        return {"id": "node_1", "name": name, "parent_id": parent_id}

    def assign_dataset(self, *, dataset_id: str, node_id: str | None):
        self.assign_calls.append({"dataset_id": dataset_id, "node_id": node_id})
        return True


class _Deps:
    def __init__(self, *, user: _User, can_manage_kb_directory: bool):
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore(
            can_manage_kb_directory=can_manage_kb_directory
        )
        self.ragflow_service = _RagflowService()
        self.knowledge_directory_manager = _DirectoryManager()


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


def _make_client(*, role: str, can_manage_kb_directory: bool) -> tuple[TestClient, _Deps]:
    user = _User(role=role, group_ids=[1] if role != "admin" else [])
    deps = _Deps(user=user, can_manage_kb_directory=can_manage_kb_directory)

    app = FastAPI()
    app.state.deps = deps
    app.include_router(directory_router, prefix="/api/knowledge")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

    return TestClient(app), deps


class TestKnowledgeDirectoryRoutePermissionsUnit(unittest.TestCase):
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
        self.assertEqual(resp.json().get("ok"), True)
        self.assertEqual(
            deps.knowledge_directory_manager.assign_calls,
            [{"dataset_id": "ds_1", "node_id": "node_1"}],
        )


if __name__ == "__main__":
    unittest.main()
