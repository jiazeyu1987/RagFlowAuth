import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.egress_decision_audit_store import EgressDecisionAuditStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestEgressDecisionAuditStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_egress_audit_store")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = EgressDecisionAuditStore(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_log_and_list_decisions(self):
        self.store.log_decision(
            request_id="r1",
            actor_user_id="u1",
            policy_mode="extranet",
            decision="allow",
            hit_rules=[{"level": "low", "rule": "public", "count": 1}],
            reason=None,
            target_host="api.openai.com",
            target_model="qwen-plus",
            payload_level="low",
            request_meta={"operation": "POST"},
            created_at_ms=1000,
        )
        self.store.log_decision(
            request_id="r2",
            actor_user_id="u2",
            policy_mode="extranet",
            decision="block",
            hit_rules=[{"level": "high", "rule": "secret", "count": 1}],
            reason="egress_blocked_high_sensitive_payload",
            target_host="api.openai.com",
            target_model="qwen-plus",
            payload_level="high",
            request_meta={"operation": "POST"},
            created_at_ms=2000,
        )

        rows = self.store.list_decisions(limit=10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].decision, "block")
        self.assertEqual(rows[1].decision, "allow")

        blocks = self.store.list_decisions(limit=10, decision="block")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].request_id, "r2")

        actor_rows = self.store.list_decisions(limit=10, actor_user_id="u1")
        self.assertEqual(len(actor_rows), 1)
        self.assertEqual(actor_rows[0].request_id, "r1")

        host_rows = self.store.list_decisions(limit=10, target_host="api.openai.com")
        self.assertEqual(len(host_rows), 2)

        after_rows = self.store.list_decisions(limit=10, since_ms=1500)
        self.assertEqual(len(after_rows), 1)
        self.assertEqual(after_rows[0].request_id, "r2")


if __name__ == "__main__":
    unittest.main()
