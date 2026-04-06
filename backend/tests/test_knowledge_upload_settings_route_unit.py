import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.knowledge.routes.upload import router as upload_router


class _User:
    def __init__(self, *, role: str = "admin"):
        self.user_id = "admin-1"
        self.username = "admin"
        self.email = "admin@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.company_id = None
        self.department_id = None


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _UploadSettingsStore:
    def __init__(self):
        self.current = SimpleNamespace(allowed_extensions=[".pdf"], updated_at_ms=1)
        self.update_calls = []

    def get(self):
        return self.current

    def update_allowed_extensions(self, extensions, *, changed_by=None, change_reason=None):
        self.update_calls.append(
            {
                "extensions": list(extensions or []),
                "changed_by": changed_by,
                "change_reason": change_reason,
            }
        )
        self.current = SimpleNamespace(
            allowed_extensions=list(extensions or []),
            updated_at_ms=2,
        )
        return self.current


class _AuditLogManager:
    def __init__(self):
        self.events = []

    def log_event(self, **payload):
        self.events.append(dict(payload))


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="admin-1")


class TestKnowledgeUploadSettingsRouteUnit(unittest.TestCase):
    def _make_client(self):
        store = _UploadSettingsStore()
        audit = _AuditLogManager()
        app = FastAPI()
        app.state.deps = SimpleNamespace(
            user_store=_UserStore(_User()),
            upload_settings_store=store,
            audit_log_manager=audit,
            org_structure_manager=None,
        )
        app.include_router(upload_router, prefix="/api/knowledge")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app), store, audit

    def test_get_allowed_extensions_returns_explicit_contract(self):
        client, _, _ = self._make_client()
        with client:
            resp = client.get("/api/knowledge/settings/allowed-extensions")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(
            resp.json(),
            {"allowed_extensions": [".pdf"], "updated_at_ms": 1},
        )

    def test_update_allowed_extensions_returns_explicit_contract(self):
        client, store, audit = self._make_client()
        with client:
            resp = client.put(
                "/api/knowledge/settings/allowed-extensions",
                json={
                    "allowed_extensions": [".pdf", ".txt"],
                    "change_reason": "test reason",
                },
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(
            resp.json(),
            {"allowed_extensions": [".pdf", ".txt"], "updated_at_ms": 2},
        )
        self.assertEqual(
            store.update_calls,
            [
                {
                    "extensions": [".pdf", ".txt"],
                    "changed_by": "admin-1",
                    "change_reason": "test reason",
                }
            ],
        )
        self.assertEqual(audit.events[0]["action"], "upload_settings_update")

    def test_get_allowed_extensions_fails_fast_on_invalid_store_payload(self):
        client, store, _ = self._make_client()
        store.current = SimpleNamespace(allowed_extensions=".pdf", updated_at_ms=1)
        with client:
            resp = client.get("/api/knowledge/settings/allowed-extensions")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"], "upload_allowed_extensions_invalid_payload")
