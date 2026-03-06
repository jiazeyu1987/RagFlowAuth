import unittest
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.drug_admin.router import router as drug_admin_router


class _User:
    def __init__(self, role: str = "admin"):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _Deps:
    def __init__(self):
        self.user_store = _UserStore(_User(role="admin"))


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestDrugAdminRouterUnit(unittest.TestCase):
    def _make_client(self) -> TestClient:
        app = FastAPI()
        app.state.deps = _Deps()
        app.include_router(drug_admin_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_list_provinces_contract(self):
        with self._make_client() as client:
            resp = client.get("/api/drug-admin/provinces")

        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("provinces", data)
        self.assertIn("count", data)
        provinces = data.get("provinces") or []
        self.assertGreater(len(provinces), 0)
        self.assertEqual(int(data.get("count") or 0), len(provinces))
        self.assertIn("name", provinces[0])
        self.assertIn("urls", provinces[0])

    @patch("backend.app.modules.drug_admin.router._find_reachable_url", return_value=(True, 200, "https://example.com", []))
    def test_resolve_province_ok(self, _mock_find):
        with self._make_client() as client:
            listing = client.get("/api/drug-admin/provinces").json()
            province = str((listing.get("provinces") or [])[0].get("name"))
            resp = client.post("/api/drug-admin/resolve", json={"province": province})

        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("url"), "https://example.com")
        self.assertEqual(data.get("province"), province)

    def test_resolve_province_not_found(self):
        with self._make_client() as client:
            resp = client.post("/api/drug-admin/resolve", json={"province": "__missing__"})

        self.assertEqual(resp.status_code, 404, resp.text)
        data = resp.json()
        self.assertEqual(data.get("detail"), "province_not_found")

    @patch(
        "backend.app.modules.drug_admin.router._verify_all",
        return_value=[
            {"province": "A", "ok": True, "code": 200, "url": "https://a", "errors": []},
            {"province": "B", "ok": False, "code": None, "url": "", "errors": ["timeout"]},
        ],
    )
    def test_verify_all_contract(self, _mock_verify):
        with self._make_client() as client:
            resp = client.post("/api/drug-admin/verify")

        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data.get("total"), 2)
        self.assertEqual(data.get("success"), 1)
        self.assertEqual(data.get("failed"), 1)
        self.assertEqual(len(data.get("rows") or []), 2)

