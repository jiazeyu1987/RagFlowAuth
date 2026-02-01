import sqlite3
import unittest

from authx import TokenPayload
from fastapi import HTTPException

from backend.app.core.authz import get_auth_context


class _UserStore:
    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        raise sqlite3.OperationalError("unable to open database file")


class _Deps:
    def __init__(self):
        self.user_store = _UserStore()


class TestAuthzDbUnavailable(unittest.TestCase):
    def test_get_auth_context_returns_503_when_db_unavailable(self):
        payload = TokenPayload(sub="u1")
        deps = _Deps()

        with self.assertRaises(HTTPException) as ctx:
            get_auth_context(payload=payload, deps=deps)  # type: ignore[arg-type]

        self.assertEqual(ctx.exception.status_code, 503)

