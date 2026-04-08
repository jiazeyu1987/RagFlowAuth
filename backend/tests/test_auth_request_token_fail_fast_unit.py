import unittest
from unittest.mock import AsyncMock, patch

from authx.exceptions import JWTDecodeError
from fastapi import HTTPException
from starlette.requests import Request

from backend.app.core import auth as auth_module


def _request(path: str = "/api/users") -> Request:
    return Request({"type": "http", "headers": [], "path": path})


class TestAuthRequestTokenFailFastUnit(unittest.IsolatedAsyncioTestCase):
    async def test_get_deps_ignores_invalid_access_tokens(self):
        request = _request()
        resolved_deps = object()

        with patch("backend.app.core.auth.resolve_request_token", new=AsyncMock(return_value="bad-token")):
            with patch.object(auth_module.auth, "verify_token", side_effect=JWTDecodeError("bad-token")):
                with patch("backend.app.core.auth.resolve_scoped_deps", return_value=resolved_deps) as resolve_scoped:
                    result = await auth_module.get_deps(request)

        self.assertIs(result, resolved_deps)
        resolve_scoped.assert_called_once_with(request, payload=None, force_tenant_scope=False)

    async def test_get_deps_does_not_silence_unexpected_verifier_failures(self):
        request = _request()

        with patch("backend.app.core.auth.resolve_request_token", new=AsyncMock(return_value="broken-token")):
            with patch.object(auth_module.auth, "verify_token", side_effect=RuntimeError("token_verifier_failed")):
                with self.assertRaisesRegex(RuntimeError, "token_verifier_failed"):
                    await auth_module.get_deps(request)

    async def test_get_current_payload_maps_authx_failures_to_401(self):
        request = _request("/api/auth/me")

        with patch("backend.app.core.auth.resolve_request_token", new=AsyncMock(return_value="bad-token")):
            with patch.object(auth_module.auth, "verify_token", side_effect=JWTDecodeError("bad-token")):
                with self.assertRaises(HTTPException) as cm:
                    await auth_module.get_current_payload(request)

        self.assertEqual(cm.exception.status_code, 401)
        self.assertEqual(cm.exception.detail, "Invalid access token")

    async def test_get_current_payload_does_not_silence_unexpected_verifier_failures(self):
        request = _request("/api/auth/me")

        with patch("backend.app.core.auth.resolve_request_token", new=AsyncMock(return_value="broken-token")):
            with patch.object(auth_module.auth, "verify_token", side_effect=RuntimeError("token_verifier_failed")):
                with self.assertRaisesRegex(RuntimeError, "token_verifier_failed"):
                    await auth_module.get_current_payload(request)
