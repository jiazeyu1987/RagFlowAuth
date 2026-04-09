import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.drug_admin.router import router as drug_admin_router
from backend.app.modules.paper_download.router import router as paper_download_router
from backend.app.modules.patent_download.router import router as patent_download_router


class _User:
    def __init__(self):
        self.user_id = "u-1"
        self.username = "viewer"
        self.email = "viewer@example.com"
        self.role = "viewer"
        self.status = "active"
        self.group_id = None
        self.group_ids = []


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    @staticmethod
    def get_group(group_id: int):  # noqa: ARG002
        return None


class _RagflowService:
    @staticmethod
    def get_dataset_index():
        return {"by_id": {}, "by_name": {}}


class _UserToolPermissionStore:
    @staticmethod
    def list_tool_ids(user_id: str):  # noqa: ARG002
        return []


class _Deps:
    def __init__(self):
        self.user_store = _UserStore(_User())
        self.permission_group_store = _PermissionGroupStore()
        self.ragflow_service = _RagflowService()
        self.knowledge_directory_manager = None
        self.user_tool_permission_store = _UserToolPermissionStore()


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u-1")


class TestToolRouteGuardsUnit(unittest.TestCase):
    def _make_client(self) -> TestClient:
        app = FastAPI()
        app.state.deps = _Deps()
        app.include_router(drug_admin_router, prefix="/api")
        app.include_router(paper_download_router, prefix="/api")
        app.include_router(patent_download_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_drug_admin_requires_tool_permission(self):
        with self._make_client() as client:
            response = client.get("/api/drug-admin/provinces")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json().get("detail"), "no_tools_view_permission")

    def test_paper_download_requires_tool_permission(self):
        with self._make_client() as client:
            response = client.get("/api/paper-download/history/keywords")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json().get("detail"), "no_tools_view_permission")

    def test_patent_download_requires_tool_permission(self):
        with self._make_client() as client:
            response = client.get("/api/patent-download/history/keywords")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json().get("detail"), "no_tools_view_permission")


if __name__ == "__main__":
    unittest.main()
