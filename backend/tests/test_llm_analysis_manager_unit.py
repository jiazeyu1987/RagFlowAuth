import unittest
from types import SimpleNamespace

from backend.services.llm_analysis import LLMAnalysisManager


class _FakeClient:
    def __init__(self):
        self.calls = []

    def post_json_with_fallback(self, path, body):
        self.calls.append((path, body))
        if path.endswith("/sessions"):
            return {"code": 0, "data": {"id": "sid-1"}}
        return {"code": 0, "data": {"answer": "analysis-ok"}}


class _FakeChatService:
    def __init__(self):
        self._client = _FakeClient()

    def list_chats(self, page_size=200):  # noqa: ARG002
        return [{"id": "chat-1", "name": "[通用LLM]"}]


class TestLLMAnalysisManagerUnit(unittest.TestCase):
    def test_ask_returns_answer(self):
        service = _FakeChatService()
        mgr = LLMAnalysisManager(
            chat_service=service,
            forced_id_env="X_TEST_LLM_ID",
            forced_name_env="X_TEST_LLM_NAME",
            session_prefix="unit-llm",
        )
        answer = mgr.ask(actor="u1", question="hello")
        self.assertEqual(answer, "analysis-ok")
        self.assertEqual(len(service._client.calls), 2)
        self.assertTrue(service._client.calls[0][0].endswith("/sessions"))
        self.assertTrue(service._client.calls[1][0].endswith("/completions"))

    def test_extract_completion_answer_walks_nested_payload(self):
        payload = {"code": 0, "data": {"choices": [{"message": {"content": "nested-answer"}}]}}
        self.assertEqual(LLMAnalysisManager.extract_completion_answer(payload), "nested-answer")


if __name__ == "__main__":
    unittest.main()
