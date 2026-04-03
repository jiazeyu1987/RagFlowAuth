import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from starlette.requests import Request

from backend.app.core.authz import get_auth_context


class _TenantUserStore:
    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return None


class _Deps:
    def __init__(self):
        self.user_store = _TenantUserStore()


class TestAuthzAuthenticatedUserUnit(unittest.TestCase):
    def test_get_auth_context_reuses_authenticated_user_from_request_state(self):
        payload = TokenPayload(sub="u1")
        request = Request({"type": "http", "headers": []})
        request.state.authenticated_user = SimpleNamespace(
            user_id="u1",
            username="wangxin",
            role="sub_admin",
            status="active",
            group_id=None,
            group_ids=[],
        )
        deps = _Deps()
        snapshot = object()

        with patch("backend.app.core.authz.resolve_scoped_deps", return_value=deps):
            with patch("backend.app.core.authz.resolve_permissions", return_value=snapshot):
                ctx = get_auth_context(request=request, payload=payload)

        self.assertIs(ctx.user, request.state.authenticated_user)
        self.assertIs(ctx.deps, deps)
        self.assertIs(ctx.snapshot, snapshot)


if __name__ == "__main__":
    unittest.main()
