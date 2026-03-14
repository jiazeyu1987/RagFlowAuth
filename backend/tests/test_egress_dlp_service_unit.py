import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.egress_dlp_service import EgressDlpService
from backend.services.egress_policy_store import EgressPolicyStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestEgressDlpServiceUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_egress_dlp")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.policy_store = EgressPolicyStore(db_path=self.db_path)
        self.service = EgressDlpService(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_process_payload_masks_sensitive_text(self):
        self.policy_store.update(
            {
                "mode": "extranet",
                "sensitivity_rules": {
                    "low": ["public"],
                    "medium": ["internal"],
                    "high": ["secret", "机密"],
                },
                "sensitive_classification_enabled": True,
                "auto_desensitize_enabled": True,
            },
            actor_user_id="u1",
        )

        payload = {
            "question": "这是机密内容, includes SECRET token",
            "meta": {"notes": ["public note", "internal doc"]},
        }
        result = self.service.process_payload(payload)

        self.assertEqual(result.payload_level, "high")
        self.assertTrue(result.masked)
        self.assertGreaterEqual(len(result.hit_rules), 3)
        text = str(result.payload.get("question") or "")
        self.assertNotIn("SECRET", text.upper())
        self.assertNotIn("机密", text)
        self.assertIn("***", text)

    def test_process_payload_collects_level_without_masking(self):
        self.policy_store.update(
            {
                "mode": "extranet",
                "sensitivity_rules": {
                    "low": [],
                    "medium": [],
                    "high": ["secret"],
                },
                "sensitive_classification_enabled": True,
                "auto_desensitize_enabled": False,
            },
            actor_user_id="u1",
        )

        payload = {"question": "contains secret text"}
        result = self.service.process_payload(payload)

        self.assertEqual(result.payload_level, "high")
        self.assertFalse(result.masked)
        self.assertEqual(result.payload["question"], "contains secret text")
        self.assertTrue(any(item.get("rule") == "secret" for item in result.hit_rules))

    def test_process_payload_returns_none_level_when_disabled(self):
        self.policy_store.update(
            {
                "sensitive_classification_enabled": False,
                "auto_desensitize_enabled": True,
            },
            actor_user_id="u1",
        )

        payload = {"question": "secret"}
        result = self.service.process_payload(payload)

        self.assertEqual(result.payload_level, "none")
        self.assertFalse(result.masked)
        self.assertEqual(result.hit_rules, [])
        self.assertEqual(result.payload, payload)


if __name__ == "__main__":
    unittest.main()
