import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.users.router import router as users_router


class _User:
    def __init__(self, role: str):
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

    def list_users(self, *args, **kwargs):  # noqa: ARG002
        return []


class _Deps:
    def __init__(self, user: _User):
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore()
        self.user_kb_permission_store = _UserKbPermissionStore()
        self.user_chat_permission_store = _UserChatPermissionStore()


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _UserKbPermissionStore:
    def get_user_kbs(self, user_id: str):  # noqa: ARG002
        return []


class _UserChatPermissionStore:
    def get_user_chats(self, user_id: str):  # noqa: ARG002
        return []


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestAdminOnlyDependency(unittest.TestCase):
    def test_users_list_requires_admin(self):
        app = FastAPI()
        app.state.deps = _Deps(_User(role="viewer"))
        app.include_router(users_router, prefix="/api/users")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        with TestClient(app) as client:
            resp = client.get("/api/users")

        self.assertEqual(resp.status_code, 403)
