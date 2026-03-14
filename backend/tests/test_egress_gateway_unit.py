import os
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import requests

from backend.app.core.config import settings
from backend.database.schema.ensure import ensure_schema
from backend.services.egress_gateway import (
    install_egress_gateway,
    is_egress_gateway_installed,
    uninstall_egress_gateway,
)
from backend.services.egress_mode_runtime import clear_egress_policy_cache
from backend.services.egress_policy_store import EgressPolicyStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.text = "ok"

    def json(self):
        return {"code": 0}


class _FakeUrlOpenContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return b"ok"


class TestEgressGatewayUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_egress_gateway")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = EgressPolicyStore(db_path=self.db_path)
        self._db_patch = patch.object(settings, "DATABASE_PATH", self.db_path)
        self._db_patch.start()
        self._enabled_patch = patch.object(settings, "EGRESS_MODE_ENFORCEMENT_ENABLED", True)
        self._enabled_patch.start()
        clear_egress_policy_cache()
        uninstall_egress_gateway()

    def tearDown(self):
        uninstall_egress_gateway()
        clear_egress_policy_cache()
        self._enabled_patch.stop()
        self._db_patch.stop()
        cleanup_dir(self._tmp)

    def test_gateway_blocks_public_requests_in_intranet_mode(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()
        install_egress_gateway()

        self.assertTrue(is_egress_gateway_installed())
        with self.assertRaises(requests.exceptions.RequestException):
            requests.get("https://api.openai.com/v1/models", timeout=0.5)

    def test_gateway_blocks_public_urllib_in_intranet_mode(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()
        install_egress_gateway()

        with self.assertRaises(urllib.error.URLError):
            urllib.request.urlopen("https://api.openai.com/v1/models", timeout=0.5)

    def test_gateway_allows_requests_after_switch_to_extranet(self):
        self.store.update({"mode": "extranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()
        install_egress_gateway()

        with patch(
            "backend.services.egress_gateway._ORIGINAL_REQUESTS_SESSION_REQUEST",
            return_value=_FakeResponse(200),
        ) as req_mock, patch(
            "backend.services.egress_gateway._ORIGINAL_URLLIB_URLOPEN",
            return_value=_FakeUrlOpenContext(),
        ) as urlopen_mock:
            resp = requests.get("https://api.openai.com/v1/models", timeout=0.5)
            with urllib.request.urlopen("https://api.openai.com/v1/models", timeout=0.5) as handle:
                body = handle.read()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body, b"ok")
        req_mock.assert_called_once()
        urlopen_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
