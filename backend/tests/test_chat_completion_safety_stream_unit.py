import json
import os
import unittest
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import backend.app.modules.chat.routes_completions as chat_completions_module
from backend.app.core import auth as auth_module
from backend.app.modules.chat.router import router as chat_router
from backend.database.schema.ensure import ensure_schema
from backend.services.egress_policy_engine import EgressPolicyEngine
from backend.services.egress_policy_store import EgressPolicyStore
from backend.services.system_feature_flag_store import SystemFeatureFlagStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _FakeUser:
    def __init__(self, *, role: str = "admin"):
        self.user_id = "u_admin"
        self.username = "admin"
        self.role = role
        self.group_id = None
        self.group_ids = []


class _FakeUserStore:
    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return _FakeUser(role="admin")


class _FakePermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _FakeRagflowChatService:
    async def chat(
        self,
        chat_id: str,  # noqa: ARG002
        question: str,  # noqa: ARG002
        stream: bool = True,  # noqa: ARG002
        session_id: str | None = None,
        user_id: str | None = None,  # noqa: ARG002
        trace_id: str | None = None,  # noqa: ARG002
    ):
        yield {
            "code": 0,
            "data": {
                "session_id": session_id or "s_1",
                "answer": "这是模型回复",
            },
        }


class _FakeDeps:
    def __init__(self):
        self.user_store = _FakeUserStore()
        self.permission_group_store = _FakePermissionGroupStore()
        self.ragflow_chat_service = _FakeRagflowChatService()


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u_admin")


def _parse_sse_payloads(raw_text: str) -> list[dict]:
    payloads: list[dict] = []
    for line in str(raw_text or "").splitlines():
        if not line.startswith("data:"):
            continue
        body = line[5:].strip()
        if not body or body == "[DONE]":
            continue
        try:
            payload = json.loads(body)
        except Exception:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


class TestChatCompletionSafetyStreamUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_chat_safety_stream")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)

        self.store = EgressPolicyStore(db_path=self.db_path)
        self.store.update(
            {
                "mode": "extranet",
                "sensitive_classification_enabled": True,
                "auto_desensitize_enabled": True,
                "high_sensitive_block_enabled": False,
                "sensitivity_rules": {
                    "low": [],
                    "medium": ["身份证号"],
                    "high": [],
                },
            },
            actor_user_id="admin_u1",
        )

        self._policy_store_patcher = patch.object(
            chat_completions_module,
            "EgressPolicyStore",
            side_effect=lambda: EgressPolicyStore(db_path=self.db_path),
        )
        self._policy_store_patcher.start()
        self._policy_engine_patcher = patch.object(
            chat_completions_module,
            "EgressPolicyEngine",
            side_effect=lambda: EgressPolicyEngine(db_path=self.db_path),
        )
        self._policy_engine_patcher.start()
        self._feature_store_patcher = patch.object(
            chat_completions_module,
            "SystemFeatureFlagStore",
            side_effect=lambda *args, **kwargs: SystemFeatureFlagStore(db_path=self.db_path),
        )
        self._feature_store_patcher.start()

        app = FastAPI()
        app.state.deps = _FakeDeps()
        app.include_router(chat_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        self.client = TestClient(app)

    def tearDown(self):
        self._feature_store_patcher.stop()
        self._policy_engine_patcher.stop()
        self._policy_store_patcher.stop()
        cleanup_dir(self._tmp)

    def test_chat_completion_stream_contains_safety_events(self):
        with self.client as client:
            resp = client.post(
                "/api/chats/chat_1/completions",
                json={"question": "我的身份证号是 123456", "stream": True, "session_id": "s_1"},
                headers={"X-Chat-Trace-Id": "t_safety"},
            )

        self.assertEqual(resp.status_code, 200)
        payloads = _parse_sse_payloads(resp.text)
        self.assertGreater(len(payloads), 0)

        safety_payloads = [
            item.get("data", {}).get("security")
            for item in payloads
            if isinstance(item.get("data"), dict) and isinstance(item.get("data", {}).get("security"), dict)
        ]
        self.assertGreaterEqual(len(safety_payloads), 3)
        stage_set = {
            (str(item.get("security_stage") or ""), str(item.get("security_status") or ""))
            for item in safety_payloads
        }
        self.assertIn(("classify", "success"), stage_set)
        self.assertIn(("desensitize", "success"), stage_set)
        self.assertIn(("intercept", "success"), stage_set)

        answer_payloads = [
            item for item in payloads if isinstance(item.get("data"), dict) and str(item.get("data", {}).get("answer") or "")
        ]
        self.assertEqual(len(answer_payloads), 1)
        self.assertEqual(answer_payloads[0]["data"]["answer"], "这是模型回复")


if __name__ == "__main__":
    unittest.main()

