import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.egress_mode_runtime import EgressModeRuntime, clear_egress_policy_cache
from backend.services.egress_policy_store import EgressPolicyStore
from backend.services.system_feature_flag_store import FLAG_EGRESS_POLICY_ENABLED, SystemFeatureFlagStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestEgressModeRuntimeUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_egress_mode_runtime")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = EgressPolicyStore(db_path=self.db_path)
        self.feature_flag_store = SystemFeatureFlagStore(db_path=self.db_path)
        self.runtime = EgressModeRuntime(db_path=self.db_path)
        clear_egress_policy_cache()

    def tearDown(self):
        clear_egress_policy_cache()
        cleanup_dir(self._tmp)

    def test_intranet_mode_blocks_public_host(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()

        decision = self.runtime.evaluate_target("https://api.openai.com/v1/chat/completions", source="ut")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.mode, "intranet")
        self.assertEqual(decision.host, "api.openai.com")
        self.assertIn("egress_blocked_by_mode", str(decision.reason))

    def test_intranet_mode_allows_private_ip_target(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()

        decision = self.runtime.evaluate_target("http://172.30.30.57:9380/api/v1")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.mode, "intranet")

    def test_intranet_mode_allows_public_host_when_whitelisted(self):
        self.store.update(
            {
                "mode": "intranet",
                "allowed_target_hosts": ["api.openai.com"],
            },
            actor_user_id="u1",
        )
        clear_egress_policy_cache()

        decision = self.runtime.evaluate_target("https://api.openai.com/v1/chat/completions")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.host, "api.openai.com")

    def test_extranet_mode_allows_public_host(self):
        self.store.update({"mode": "extranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()

        decision = self.runtime.evaluate_target("https://api.openai.com/v1/chat/completions")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.mode, "extranet")

    def test_feature_flag_disabled_allows_public_host_even_in_intranet_mode(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        self.feature_flag_store.update_flags({FLAG_EGRESS_POLICY_ENABLED: False}, actor_user_id="u1")
        clear_egress_policy_cache()

        decision = self.runtime.evaluate_target("https://api.openai.com/v1/chat/completions")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.mode, "feature_disabled")


if __name__ == "__main__":
    unittest.main()
