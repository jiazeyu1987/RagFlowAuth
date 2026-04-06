import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.agents.router import router as agents_router
from backend.app.modules.chat.router import router as chat_router
from backend.app.modules.ragflow.routes.datasets import router as ragflow_datasets_router
from backend.app.modules.search_configs.router import router as search_configs_router


class _FakeUser:
    def __init__(self, *, role: str = "admin", group_id=None, group_ids=None, username: str = "u1"):
        self.role = role
        self.group_id = group_id
        self.group_ids = list(group_ids or [])
        self.username = username


class _FakeUserStore:
    def __init__(self, *, role: str, group_ids=None):
        self._role = role
        self._group_ids = list(group_ids or [])

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return _FakeUser(role=self._role, group_id=None, group_ids=self._group_ids)


class _FakePermissionGroupStore:
    def __init__(self, groups=None):
        self._groups = dict(groups or {})

    def get_group(self, group_id: int):
        return self._groups.get(group_id)


class _FakeChatService:
    def __init__(self):
        self.created = []
        self.updated = []

    def list_chats(self, *args, **kwargs):  # noqa: ARG002
        return []

    def create_chat(self, payload):
        self.created.append(payload)
        return {"id": "c1", **payload}

    def update_chat(self, chat_id, payload):
        self.updated.append((chat_id, payload))
        return {"id": chat_id, **payload}

    def delete_chat(self, chat_id):  # noqa: ARG002
        return True


class _FakeSearchConfigService:
    def __init__(self):
        self.created = []
        self.updated = []

    def list_agents(self, *args, **kwargs):  # noqa: ARG002
        return []

    def get_agent(self, agent_id):  # noqa: ARG002
        return None

    def create_agent(self, payload):
        self.created.append(payload)
        return {"id": "a1", "title": payload.get("title"), "create_time": 1, "update_time": 2, **payload}

    def update_agent(self, agent_id, payload):
        self.updated.append((agent_id, payload))
        return {"id": agent_id, "title": payload.get("title"), "create_time": 1, "update_time": 2, **payload}

    def delete_agent(self, agent_id):  # noqa: ARG002
        return True


class _FakeRagflowService:
    def __init__(self):
        self.created = []
        self.updated = []
        self.datasets = [
            {"id": "d1", "name": "kb1"},
            {"id": "d2", "name": "kb2"},
        ]

    def list_datasets(self):
        return list(self.datasets)

    def normalize_dataset_ids(self, values):
        return [str(v) for v in (values or [])]

    def create_dataset(self, payload):
        self.created.append(payload)
        return {"id": "d1", **payload}

    def update_dataset(self, dataset_ref, updates):
        self.updated.append((dataset_ref, updates))
        return {"id": dataset_ref, **updates}


class _FakeKnowledgeManagementManager:
    def __init__(self, ragflow_service, manageable_datasets=None):
        self._ragflow_service = ragflow_service
        self._manageable_datasets = list(manageable_datasets or [])
        self.list_manageable_calls = []

    def get_management_scope(self, user):  # noqa: ARG002
        return SimpleNamespace(can_manage=True, dataset_ids=frozenset({"d1"}))

    def list_manageable_datasets(self, user):  # noqa: ARG002
        self.list_manageable_calls.append(getattr(user, "role", None))
        return list(self._manageable_datasets)

    def create_dataset(self, *, user, payload):  # noqa: ARG002
        body = dict(payload or {})
        body.pop("id", None)
        body.pop("dataset_id", None)
        return self._ragflow_service.create_dataset(body)


class _FakeSearchChatService:
    def __init__(self, *, raise_error: bool = False):
        self.raise_error = bool(raise_error)
        self.calls = []

    def retrieve_chunks(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_error:
            raise RuntimeError("upstream_failed")
        return {"chunks": [], "count": 0}


def _make_client(*, router, deps, prefix="/api") -> TestClient:
    app = FastAPI()
    app.state.deps = deps
    app.include_router(router, prefix=prefix)

    def _override_get_current_payload(request: Request) -> TokenPayload:  # noqa: ARG001
        return TokenPayload(sub="u1")

    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
    return TestClient(app)


class TestChatRequestModelsUnit(unittest.TestCase):
    def test_chat_create_and_update_invalid_body_codes_stable(self):
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="admin"),
            permission_group_store=_FakePermissionGroupStore(),
            ragflow_chat_service=_FakeChatService(),
        )
        with _make_client(router=chat_router, deps=deps) as client:
            r1 = client.post("/api/chats", json="invalid")
            self.assertEqual(r1.status_code, 400)
            self.assertEqual(r1.json().get("detail"), "invalid_body")

            r2 = client.put("/api/chats/c1", json="invalid")
            self.assertEqual(r2.status_code, 400)
            self.assertEqual(r2.json().get("detail"), "invalid_updates")

            r3 = client.post("/api/chats", json={"name": 123})
            self.assertEqual(r3.status_code, 400)
            self.assertEqual(r3.json().get("detail"), "missing_name")


class TestSearchConfigRequestModelsUnit(unittest.TestCase):
    def test_search_config_create_and_update_validate_body(self):
        svc = _FakeSearchConfigService()
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="admin"),
            permission_group_store=_FakePermissionGroupStore(),
            ragflow_chat_service=svc,
        )
        with _make_client(router=search_configs_router, deps=deps) as client:
            r1 = client.post("/api/search/configs", json="invalid")
            self.assertEqual(r1.status_code, 400)
            self.assertEqual(r1.json().get("detail"), "invalid_body")

            r2 = client.put("/api/search/configs/a1", json="invalid")
            self.assertEqual(r2.status_code, 400)
            self.assertEqual(r2.json().get("detail"), "invalid_updates")

            r3 = client.post("/api/search/configs", json={"name": "n1", "config": []})
            self.assertEqual(r3.status_code, 400)
            self.assertEqual(r3.json().get("detail"), "invalid_config")

            r4 = client.post(
                "/api/search/configs",
                json={"name": " n1 ", "config": {"description": " d1 ", "dsl": {"x": 1}}},
            )
            self.assertEqual(r4.status_code, 200)
            self.assertEqual(svc.created[0].get("title"), "n1")


class TestDatasetRequestModelsUnit(unittest.TestCase):
    def test_dataset_create_and_update_validate_body(self):
        ragflow = _FakeRagflowService()
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="admin"),
            permission_group_store=_FakePermissionGroupStore(),
            ragflow_service=ragflow,
            knowledge_management_manager=_FakeKnowledgeManagementManager(ragflow),
        )
        with _make_client(router=agents_router, deps=deps) as client:
            r1 = client.post("/api/datasets", json="invalid")
            self.assertEqual(r1.status_code, 400)
            self.assertEqual(r1.json().get("detail"), "invalid_body")

            r2 = client.put("/api/datasets/d1", json="invalid")
            self.assertEqual(r2.status_code, 400)
            self.assertEqual(r2.json().get("detail"), "invalid_updates")

            r3 = client.post("/api/datasets", json={"name": ""})
            self.assertEqual(r3.status_code, 400)
            self.assertEqual(r3.json().get("detail"), "missing_name")

            r4 = client.post("/api/datasets", json={"name": "kb1", "id": "xx", "dataset_id": "xx", "foo": "bar"})
            self.assertEqual(r4.status_code, 200)
            self.assertEqual(r4.json().get("dataset", {}).get("name"), "kb1")
            self.assertEqual(ragflow.created[0].get("id"), None)
            self.assertEqual(ragflow.created[0].get("dataset_id"), None)
            self.assertEqual(ragflow.created[0].get("foo"), "bar")

            r5 = client.put("/api/datasets/d1", json={"name": "kb2", "id": "xx", "dataset_id": "xx"})
            self.assertEqual(r5.status_code, 200)
            self.assertEqual(ragflow.updated[0][0], "d1")
            self.assertEqual(ragflow.updated[0][1].get("id"), None)
            self.assertEqual(ragflow.updated[0][1].get("dataset_id"), None)


class TestDatasetListingRoutesUnit(unittest.TestCase):
    def test_sub_admin_dataset_listing_requires_management_manager(self):
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="sub_admin"),
            permission_group_store=_FakePermissionGroupStore(),
            ragflow_service=_FakeRagflowService(),
        )
        with _make_client(router=agents_router, deps=deps) as client:
            resp = client.get("/api/datasets")
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json().get("detail"), "knowledge_management_manager_unavailable")

    def test_dataset_listing_routes_align_on_manageable_dataset_contract(self):
        ragflow = _FakeRagflowService()
        manager = _FakeKnowledgeManagementManager(
            ragflow,
            manageable_datasets=[{"id": "managed-1", "name": "Managed KB"}],
        )
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="sub_admin"),
            permission_group_store=_FakePermissionGroupStore(),
            ragflow_service=ragflow,
            knowledge_management_manager=manager,
        )

        with _make_client(router=agents_router, deps=deps) as primary_client:
            primary_resp = primary_client.get("/api/datasets")
        self.assertEqual(primary_resp.status_code, 200, primary_resp.text)
        self.assertEqual(
            primary_resp.json(),
            {"datasets": [{"id": "managed-1", "name": "Managed KB"}], "count": 1},
        )

        with _make_client(router=ragflow_datasets_router, deps=deps, prefix="/api/ragflow") as legacy_client:
            legacy_resp = legacy_client.get("/api/ragflow/datasets")
        self.assertEqual(legacy_resp.status_code, 200, legacy_resp.text)
        self.assertEqual(
            legacy_resp.json(),
            {"datasets": [{"id": "managed-1", "name": "Managed KB"}], "count": 1},
        )
        self.assertNotIn("Deprecation", legacy_resp.headers)
        self.assertNotIn("X-Replaced-By", legacy_resp.headers)
        self.assertEqual(manager.list_manageable_calls, ["sub_admin", "sub_admin"])


class TestSearchChunksUnit(unittest.TestCase):
    def test_search_request_rejects_invalid_page(self):
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="admin"),
            permission_group_store=_FakePermissionGroupStore(),
            ragflow_service=_FakeRagflowService(),
            ragflow_chat_service=_FakeSearchChatService(),
        )
        with _make_client(router=agents_router, deps=deps) as client:
            resp = client.post(
                "/api/search",
                json={"question": "q1", "dataset_ids": ["d1"], "page": 0, "page_size": 30},
            )
        self.assertEqual(resp.status_code, 422)

    def test_search_returns_dataset_not_allowed_for_forbidden_dataset(self):
        groups = {
            1: {
                "can_upload": False,
                "can_review": False,
                "can_download": False,
                "can_delete": False,
                "accessible_kbs": ["dataset:d1"],
                "accessible_chats": [],
            }
        }
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="user", group_ids=[1]),
            permission_group_store=_FakePermissionGroupStore(groups=groups),
            ragflow_service=_FakeRagflowService(),
            ragflow_chat_service=_FakeSearchChatService(),
        )
        with _make_client(router=agents_router, deps=deps) as client:
            resp = client.post(
                "/api/search",
                json={"question": "q1", "dataset_ids": ["d2"], "page": 1, "page_size": 30},
            )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("detail"), "dataset_not_allowed")

    def test_search_returns_stable_error_when_retrieve_fails(self):
        groups = {
            1: {
                "can_upload": False,
                "can_review": False,
                "can_download": False,
                "can_delete": False,
                "accessible_kbs": ["dataset:d1"],
                "accessible_chats": [],
            }
        }
        deps = SimpleNamespace(
            user_store=_FakeUserStore(role="user", group_ids=[1]),
            permission_group_store=_FakePermissionGroupStore(groups=groups),
            ragflow_service=_FakeRagflowService(),
            ragflow_chat_service=_FakeSearchChatService(raise_error=True),
        )
        with _make_client(router=agents_router, deps=deps) as client:
            resp = client.post(
                "/api/search",
                json={"question": "q1", "dataset_ids": ["d1"], "page": 1, "page_size": 30},
            )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json().get("detail"), "search_failed")


if __name__ == "__main__":
    unittest.main()
