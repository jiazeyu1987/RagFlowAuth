import os
import unittest
from unittest.mock import patch

from backend.app.core.config import settings
from backend.database.schema.ensure import ensure_schema
from backend.services.egress_decision_audit_store import EgressDecisionAuditStore
from backend.services.egress_mode_runtime import clear_egress_policy_cache
from backend.services.egress_policy_store import EgressPolicyStore
from backend.services.ragflow_http_client import RagflowHttpClient, RagflowHttpClientConfig
from backend.services.system_feature_flag_store import FLAG_EGRESS_POLICY_ENABLED, SystemFeatureFlagStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = ""

    def json(self):
        return self._payload


class TestRagflowHttpClientEgressModeUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_ragflow_http_egress")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = EgressPolicyStore(db_path=self.db_path)
        self.feature_flag_store = SystemFeatureFlagStore(db_path=self.db_path)
        self.audit_store = EgressDecisionAuditStore(db_path=self.db_path)
        clear_egress_policy_cache()
        self._db_patch = patch.object(settings, "DATABASE_PATH", self.db_path)
        self._db_patch.start()
        self._enforce_patch = patch.object(settings, "EGRESS_MODE_ENFORCEMENT_ENABLED", True)
        self._enforce_patch.start()

    def tearDown(self):
        self._enforce_patch.stop()
        self._db_patch.stop()
        clear_egress_policy_cache()
        cleanup_dir(self._tmp)

    @staticmethod
    def _client(base_url: str) -> RagflowHttpClient:
        return RagflowHttpClient(RagflowHttpClientConfig(base_url=base_url, api_key="k", timeout_s=5.0))

    def test_get_json_blocked_in_intranet_mode(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch("backend.services.ragflow_http_client.requests.get") as get_mock:
            result = client.get_json("/api/v1/datasets")

        self.assertIsNone(result)
        get_mock.assert_not_called()
        records = self.audit_store.list_decisions(limit=10, decision="block")
        self.assertGreaterEqual(len(records), 1)
        self.assertEqual(records[0].target_host, "api.openai.com")

    def test_get_json_allows_after_switch_to_extranet(self):
        self.store.update({"mode": "extranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch(
            "backend.services.ragflow_http_client.requests.get",
            return_value=_FakeResponse(200, {"code": 0, "data": []}),
        ) as get_mock:
            result = client.get_json("/api/v1/datasets")

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("code"), 0)
        get_mock.assert_called_once()
        records = self.audit_store.list_decisions(limit=10, decision="allow")
        self.assertGreaterEqual(len(records), 1)
        self.assertEqual(records[0].target_host, "api.openai.com")

    def test_post_sse_blocked_in_intranet_mode(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch("backend.services.ragflow_http_client.requests.post") as post_mock:
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "hi"}))

        self.assertEqual(len(events), 1)
        self.assertEqual(int(events[0].get("code") or 0), 403)
        self.assertIn("egress_blocked_by_mode", str(events[0].get("message") or ""))
        post_mock.assert_not_called()

    def test_post_json_masks_sensitive_payload_before_send(self):
        self.store.update(
            {
                "mode": "extranet",
                "high_sensitive_block_enabled": False,
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
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch(
            "backend.services.ragflow_http_client.requests.post",
            return_value=_FakeResponse(200, {"code": 0}),
        ) as post_mock:
            result = client.post_json("/api/v1/chats/c1/completions", body={"question": "my secret content"})

        self.assertIsInstance(result, dict)
        sent_payload = post_mock.call_args.kwargs.get("json") or {}
        question = str(sent_payload.get("question") or "")
        self.assertIn("***", question)
        self.assertNotIn("secret", question.lower())

    def test_post_json_applies_minimal_egress_before_send(self):
        self.store.update(
            {
                "mode": "extranet",
                "minimal_egress_enabled": True,
                "sensitive_classification_enabled": False,
                "auto_desensitize_enabled": False,
                "high_sensitive_block_enabled": False,
                "domestic_model_whitelist_enabled": False,
                "sensitivity_rules": {
                    "low": [],
                    "medium": [],
                    "high": [],
                },
            },
            actor_user_id="u1",
        )
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch(
            "backend.services.ragflow_http_client.requests.post",
            return_value=_FakeResponse(200, {"code": 0}),
        ) as post_mock:
            result = client.post_json(
                "/api/v1/chats/c1/completions",
                body={
                    "model": "qwen-plus",
                    "question": "normal content",
                    "attachments": [{"name": "paper.pdf", "content": "details"}],
                    "raw_content": "full body",
                    "messages": [{"role": "user", "content": "hello", "attachments": [{"id": "a1"}]}],
                },
            )

        self.assertIsInstance(result, dict)
        sent_payload = post_mock.call_args.kwargs.get("json") or {}
        self.assertEqual(sent_payload.get("model"), "qwen-plus")
        self.assertEqual(sent_payload.get("question"), "normal content")
        self.assertNotIn("attachments", sent_payload)
        self.assertNotIn("raw_content", sent_payload)
        first_message = (sent_payload.get("messages") or [{}])[0]
        self.assertEqual(first_message.get("content"), "hello")
        self.assertNotIn("attachments", first_message)

    def test_post_json_blocks_high_sensitive_payload_when_enabled(self):
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
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch("backend.services.ragflow_http_client.requests.post") as post_mock:
            result = client.post_json(
                "/api/v1/chats/c1/completions",
                body={"model": "qwen-plus", "question": "this is secret content"},
            )

        self.assertIsNone(result)
        post_mock.assert_not_called()

    def test_post_json_blocks_non_whitelisted_model(self):
        self.store.update(
            {
                "mode": "extranet",
                "high_sensitive_block_enabled": False,
                "domestic_model_whitelist_enabled": True,
                "domestic_model_allowlist": ["qwen-plus"],
                "sensitive_classification_enabled": True,
                "auto_desensitize_enabled": True,
                "sensitivity_rules": {
                    "low": [],
                    "medium": [],
                    "high": [],
                },
            },
            actor_user_id="u1",
        )
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch("backend.services.ragflow_http_client.requests.post") as post_mock:
            result = client.post_json(
                "/api/v1/chats/c1/completions",
                body={"model": "gpt-4", "question": "normal content"},
            )

        self.assertIsNone(result)
        post_mock.assert_not_called()

    def test_feature_flag_disabled_skips_egress_mode_blocking(self):
        self.store.update({"mode": "intranet", "allowed_target_hosts": []}, actor_user_id="u1")
        self.feature_flag_store.update_flags({FLAG_EGRESS_POLICY_ENABLED: False}, actor_user_id="u1")
        clear_egress_policy_cache()
        client = self._client("https://api.openai.com")

        with patch(
            "backend.services.ragflow_http_client.requests.get",
            return_value=_FakeResponse(200, {"code": 0, "data": []}),
        ) as get_mock:
            result = client.get_json("/api/v1/datasets")

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("code"), 0)
        get_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
