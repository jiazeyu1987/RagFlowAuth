import json
import tempfile
import unittest
from pathlib import Path

from backend.services.ragflow_connection import create_ragflow_connection
from backend.services.ragflow_config import LOCAL_RAGFLOW_API_KEY


class TestRagflowLocalApiKeyOverrideUnit(unittest.TestCase):
    def _write_config(self, payload: dict) -> Path:
        fd, p = tempfile.mkstemp(prefix="ragflow_config_", suffix=".json")
        Path(p).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return Path(p)

    def test_overrides_api_key_when_base_url_is_local(self):
        cfg = self._write_config({"base_url": "http://127.0.0.1:9380", "api_key": "YOUR_RAGFLOW_API_KEY_HERE"})
        conn = create_ragflow_connection(config_path=cfg)
        self.assertEqual(conn.config.get("api_key"), LOCAL_RAGFLOW_API_KEY)
        self.assertEqual(conn.http.config.api_key, LOCAL_RAGFLOW_API_KEY)

    def test_prefers_configured_api_key_when_base_url_is_local(self):
        cfg = self._write_config({"base_url": "http://127.0.0.1:9380", "api_key": "LOCAL_KEY"})
        conn = create_ragflow_connection(config_path=cfg)
        self.assertEqual(conn.config.get("api_key"), "LOCAL_KEY")
        self.assertEqual(conn.http.config.api_key, "LOCAL_KEY")

    def test_keeps_configured_api_key_when_base_url_is_remote(self):
        cfg = self._write_config({"base_url": "http://172.30.30.57:9380", "api_key": "REMOTE_KEY"})
        conn = create_ragflow_connection(config_path=cfg)
        self.assertEqual(conn.config.get("api_key"), "REMOTE_KEY")
        self.assertEqual(conn.http.config.api_key, "REMOTE_KEY")


if __name__ == "__main__":
    unittest.main()
