from __future__ import annotations

import json
import unittest
from pathlib import Path

from tool.maintenance.core.tempdir import cleanup_dir, make_temp_dir
from tool.maintenance.core.ragflow_base_url_guard import (
    BaseUrlFixResult,
    desired_base_url_for_role,
    ensure_local_base_url,
)


class TestRagflowBaseUrlGuardUnit(unittest.TestCase):
    def test_desired_base_url_for_role(self) -> None:
        self.assertIn("127.0.0.1", desired_base_url_for_role("local"))
        self.assertIn("172.30.30.58", desired_base_url_for_role("test"))
        self.assertIn("172.30.30.57", desired_base_url_for_role("prod"))

    def test_ensure_local_base_url_rewrites_json(self) -> None:
        td = make_temp_dir(prefix="ragflowauth_base_url_guard")
        try:
            path = Path(td) / "ragflow_config.json"
            path.write_text(json.dumps({"base_url": "http://1.2.3.4:9380"}, ensure_ascii=False), encoding="utf-8")

            res = ensure_local_base_url(desired="http://127.0.0.1:9380", path=path)
            self.assertIsInstance(res, BaseUrlFixResult)
            self.assertTrue(res.ok)
            self.assertTrue(res.changed)
            self.assertIn("1.2.3.4", res.before)
            self.assertIn("127.0.0.1", res.after)
        finally:
            cleanup_dir(td)
