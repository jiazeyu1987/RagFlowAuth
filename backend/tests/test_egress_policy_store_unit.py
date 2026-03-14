import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.egress_policy_store import EgressPolicyStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestEgressPolicyStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_egress_policy_store")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = EgressPolicyStore(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_get_returns_default_policy(self):
        settings_obj = self.store.get()

        self.assertEqual(settings_obj.mode, "intranet")
        self.assertTrue(settings_obj.minimal_egress_enabled)
        self.assertTrue(settings_obj.sensitive_classification_enabled)
        self.assertTrue(settings_obj.auto_desensitize_enabled)
        self.assertTrue(settings_obj.high_sensitive_block_enabled)
        self.assertTrue(settings_obj.domestic_model_whitelist_enabled)
        self.assertIn("qwen-plus", settings_obj.domestic_model_allowlist)
        self.assertIn("high", settings_obj.sensitivity_rules)

    def test_update_applies_mode_allowlist_and_actor(self):
        updated = self.store.update(
            {
                "mode": "extranet",
                "domestic_model_allowlist": ["QWEN-PLUS", "glm-4-plus", "QWEN-PLUS"],
                "allowed_target_hosts": ["api.openai.com", "api.openai.com", "model.example.com"],
                "sensitivity_rules": {
                    "low": ["公开"],
                    "medium": ["内部"],
                    "high": ["机密"],
                },
            },
            actor_user_id="admin_u1",
        )

        self.assertEqual(updated.mode, "extranet")
        self.assertEqual(updated.domestic_model_allowlist, ["qwen-plus", "glm-4-plus"])
        self.assertEqual(updated.allowed_target_hosts, ["api.openai.com", "model.example.com"])
        self.assertEqual(updated.sensitivity_rules["high"], ["机密"])
        self.assertEqual(updated.updated_by_user_id, "admin_u1")
        self.assertGreater(updated.updated_at_ms, 0)

    def test_update_rejects_invalid_mode(self):
        with self.assertRaises(ValueError):
            self.store.update({"mode": "public"})

    def test_update_rejects_empty_allowlist_when_whitelist_enabled(self):
        with self.assertRaises(ValueError):
            self.store.update(
                {
                    "domestic_model_whitelist_enabled": True,
                    "domestic_model_allowlist": [],
                }
            )

    def test_update_allows_empty_allowlist_when_whitelist_disabled(self):
        updated = self.store.update(
            {
                "domestic_model_whitelist_enabled": False,
                "domestic_model_allowlist": [],
            }
        )
        self.assertFalse(updated.domestic_model_whitelist_enabled)
        self.assertEqual(updated.domestic_model_allowlist, [])


if __name__ == "__main__":
    unittest.main()
