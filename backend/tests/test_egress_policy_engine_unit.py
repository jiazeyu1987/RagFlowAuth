import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.egress_policy_engine import EgressPolicyEngine
from backend.services.egress_policy_store import EgressPolicyStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestEgressPolicyEngineUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_egress_policy_engine")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = EgressPolicyStore(db_path=self.db_path)
        self.engine = EgressPolicyEngine(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_block_high_sensitive_payload_in_extranet_mode(self):
        self.store.update(
            {
                "mode": "extranet",
                "high_sensitive_block_enabled": True,
                "sensitive_classification_enabled": True,
                "auto_desensitize_enabled": True,
                "sensitivity_rules": {
                    "low": [],
                    "medium": [],
                    "high": ["secret"],
                },
            },
            actor_user_id="u1",
        )

        decision = self.engine.evaluate_payload({"model": "qwen-plus", "question": "top secret content"})
        self.assertFalse(decision.allowed)
        self.assertIn("high_sensitive", str(decision.blocked_reason))
        self.assertEqual(decision.payload_level, "high")

    def test_block_non_whitelisted_model_in_extranet_mode(self):
        self.store.update(
            {
                "mode": "extranet",
                "high_sensitive_block_enabled": False,
                "domestic_model_whitelist_enabled": True,
                "domestic_model_allowlist": ["qwen-plus"],
                "sensitive_classification_enabled": True,
                "auto_desensitize_enabled": True,
                "sensitivity_rules": {"low": [], "medium": [], "high": []},
            },
            actor_user_id="u1",
        )

        decision = self.engine.evaluate_payload({"model": "gpt-4", "question": "hello"})
        self.assertFalse(decision.allowed)
        self.assertIn("model_not_allowed", str(decision.blocked_reason))
        self.assertEqual(decision.target_model, "gpt-4")

    def test_allow_whitelisted_model_in_extranet_mode(self):
        self.store.update(
            {
                "mode": "extranet",
                "high_sensitive_block_enabled": False,
                "domestic_model_whitelist_enabled": True,
                "domestic_model_allowlist": ["qwen-plus"],
                "sensitive_classification_enabled": True,
                "auto_desensitize_enabled": True,
                "sensitivity_rules": {"low": [], "medium": [], "high": []},
            },
            actor_user_id="u1",
        )

        decision = self.engine.evaluate_payload({"model": "qwen-plus", "question": "hello"})
        self.assertTrue(decision.allowed)
        self.assertIsNone(decision.blocked_reason)
        self.assertEqual(decision.target_model, "qwen-plus")

    def test_minimal_egress_prunes_nonessential_fields_in_extranet_mode(self):
        self.store.update(
            {
                "mode": "extranet",
                "minimal_egress_enabled": True,
                "sensitive_classification_enabled": False,
                "auto_desensitize_enabled": False,
                "high_sensitive_block_enabled": False,
                "domestic_model_whitelist_enabled": False,
                "sensitivity_rules": {"low": [], "medium": [], "high": []},
            },
            actor_user_id="u1",
        )

        decision = self.engine.evaluate_payload(
            {
                "model": "qwen-plus",
                "question": "how are you",
                "attachments": [{"name": "paper.pdf", "content": "very long text"}],
                "raw_text": "raw body",
                "source_documents": [{"id": "doc-1"}],
                "messages": [{"role": "user", "content": "hello", "attachments": [{"id": "a1"}]}],
            }
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.sanitized_payload.get("model"), "qwen-plus")
        self.assertEqual(decision.sanitized_payload.get("question"), "how are you")
        self.assertNotIn("attachments", decision.sanitized_payload)
        self.assertNotIn("raw_text", decision.sanitized_payload)
        self.assertNotIn("source_documents", decision.sanitized_payload)
        self.assertIn("messages", decision.sanitized_payload)
        first_message = (decision.sanitized_payload.get("messages") or [{}])[0]
        self.assertEqual(first_message.get("content"), "hello")
        self.assertNotIn("attachments", first_message)

    def test_minimal_egress_not_applied_in_intranet_mode(self):
        self.store.update(
            {
                "mode": "intranet",
                "minimal_egress_enabled": True,
                "sensitive_classification_enabled": False,
                "auto_desensitize_enabled": False,
                "sensitivity_rules": {"low": [], "medium": [], "high": []},
            },
            actor_user_id="u1",
        )

        payload = {
            "model": "qwen-plus",
            "question": "hello",
            "attachments": [{"id": "att-1"}],
        }
        decision = self.engine.evaluate_payload(payload)
        self.assertTrue(decision.allowed)
        self.assertIn("attachments", decision.sanitized_payload)


if __name__ == "__main__":
    unittest.main()
