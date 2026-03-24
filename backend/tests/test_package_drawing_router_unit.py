import tempfile
import unittest
from pathlib import Path

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.package_drawing.router import router as package_drawing_router
from backend.database.schema import ensure_schema
from backend.services.package_drawing.store import PackageDrawingStore


class _User:
    def __init__(self, *, role: str, group_ids: list[int]):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = role
        self.status = "active"
        self.group_id = group_ids[0] if group_ids else None
        self.group_ids = group_ids


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    def __init__(self, groups: dict[int, dict]):
        self._groups = groups

    def get_group(self, group_id: int):
        return self._groups.get(group_id)


class _RagflowService:
    @staticmethod
    def get_dataset_index():
        return {"by_id": {}, "by_name": {}}


class _Deps:
    def __init__(self, *, user: _User, package_drawing_store: PackageDrawingStore, groups: dict[int, dict] | None = None):
        self.user_store = _UserStore(user)
        self.package_drawing_store = package_drawing_store
        self.permission_group_store = _PermissionGroupStore(groups or {})
        self.ragflow_service = _RagflowService()
        self.knowledge_directory_manager = None


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestPackageDrawingRouterUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = str(Path(self._tmp.name) / "auth.db")
        ensure_schema(db_path)
        self.store = PackageDrawingStore(db_path=db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_client(self, deps: _Deps) -> TestClient:
        app = FastAPI()
        app.state.deps = deps
        app.include_router(package_drawing_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_import_requires_admin(self):
        deps = _Deps(
            user=_User(role="viewer", group_ids=[1]),
            package_drawing_store=self.store,
            groups={1: {"can_view_tools": True, "accessible_tools": ["package_drawing"]}},
        )
        with self._make_client(deps) as client:
            resp = client.post(
                "/api/package-drawing/import",
                files={"file": ("x.xlsx", b"dummy", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertEqual(resp.json().get("detail"), "admin_required")

    def test_query_returns_not_found_when_model_absent(self):
        deps = _Deps(
            user=_User(role="admin", group_ids=[]),
            package_drawing_store=self.store,
        )
        with self._make_client(deps) as client:
            resp = client.get("/api/package-drawing/by-model", params={"model": "NOPE"})
        self.assertEqual(resp.status_code, 404, resp.text)
        self.assertEqual(resp.json().get("detail"), "model_not_found")


if __name__ == "__main__":
    unittest.main()
