import unittest
from unittest.mock import patch

from backend.services.notification.dingtalk_adapter import DingTalkNotificationAdapter


class _FakeResponse:
    def __init__(self, *, status_code: int, data, text: str = ""):
        self.status_code = int(status_code)
        self._data = data
        self.text = text

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if not self._responses:
            raise AssertionError("unexpected_http_call")
        return self._responses.pop(0)


class TestNotificationDingTalkAdapterUnit(unittest.TestCase):
    @staticmethod
    def _channel(config: dict):
        return {"channel_id": "ding-main", "channel_type": "dingtalk", "config": config}

    @staticmethod
    def _recipient(address: str = "ding-u1"):
        return {"user_id": "u1", "username": "alice", "address": address}

    @staticmethod
    def _approval_payload(**overrides):
        payload = {
            "request_id": "req-1",
            "operation_type": "knowledge_file_upload",
            "target_label": "ICE",
            "current_step_name": "第 1 层",
            "link_path": "/approvals?request_id=req-1",
            "approval_target": {
                "request_id": "req-1",
                "operation_type": "knowledge_file_upload",
                "route_path": "/approvals?request_id=req-1",
            },
        }
        payload.update(overrides)
        return payload

    def test_fail_fast_on_missing_required_config(self):
        adapter = DingTalkNotificationAdapter()

        with self.assertRaisesRegex(RuntimeError, "^dingtalk_app_key_required$"):
            adapter.send(
                channel=self._channel({"app_secret": "sec", "agent_id": 1, "recipient_map": {"u1": "ding-u1"}}),
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1"},
                recipient=self._recipient(),
            )

        with self.assertRaisesRegex(RuntimeError, "^dingtalk_app_secret_required$"):
            adapter.send(
                channel=self._channel({"app_key": "key", "agent_id": 1, "recipient_map": {"u1": "ding-u1"}}),
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1"},
                recipient=self._recipient(),
            )

        with self.assertRaisesRegex(RuntimeError, "^dingtalk_agent_id_required$"):
            adapter.send(
                channel=self._channel({"app_key": "key", "app_secret": "sec", "recipient_map": {"u1": "ding-u1"}}),
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1"},
                recipient=self._recipient(),
            )

        with self.assertRaisesRegex(RuntimeError, "^dingtalk_agent_id_invalid$"):
            adapter.send(
                channel=self._channel(
                    {"app_key": "key", "app_secret": "sec", "agent_id": "not-int", "recipient_map": {"u1": "ding-u1"}}
                ),
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1"},
                recipient=self._recipient(),
            )

        with self.assertRaisesRegex(RuntimeError, "^dingtalk_recipient_required$"):
            adapter.send(
                channel=self._channel({"app_key": "key", "app_secret": "sec", "agent_id": 1, "recipient_map": {"u1": "ding-u1"}}),
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1"},
                recipient={"user_id": "u1", "username": "alice"},
            )

    def test_access_token_http_failure(self):
        adapter = DingTalkNotificationAdapter()
        fake_session = _FakeSession(
            [
                _FakeResponse(status_code=401, data={"code": "Unauthorized"}, text="unauthorized"),
            ]
        )
        with patch("backend.services.notification.dingtalk_adapter.requests.Session", return_value=fake_session):
            with self.assertRaisesRegex(RuntimeError, "^dingtalk_access_token_failed:http_401:"):
                adapter.send(
                    channel=self._channel({"app_key": "key", "app_secret": "sec", "agent_id": 1, "recipient_map": {"u1": "ding-u1"}}),
                    event_type="review_todo_approval",
                    payload={"doc_id": "doc-1"},
                    recipient=self._recipient(),
                )
        self.assertEqual(len(fake_session.calls), 1)
        self.assertTrue(fake_session.calls[0]["url"].endswith("/v1.0/oauth2/accessToken"))

    def test_send_errcode_failure(self):
        adapter = DingTalkNotificationAdapter()
        fake_session = _FakeSession(
            [
                _FakeResponse(status_code=200, data={"accessToken": "token-1"}),
                _FakeResponse(status_code=200, data={"errcode": 33013, "errmsg": "invalid userid"}),
            ]
        )
        with patch("backend.services.notification.dingtalk_adapter.requests.Session", return_value=fake_session):
            with self.assertRaisesRegex(RuntimeError, "^dingtalk_send_failed:33013:invalid userid$"):
                adapter.send(
                    channel=self._channel({"app_key": "key", "app_secret": "sec", "agent_id": "4432005762", "recipient_map": {"u1": "ding-u1"}}),
                    event_type="review_todo_approval",
                    payload={"doc_id": "doc-1"},
                    recipient=self._recipient(),
                )
        self.assertEqual(len(fake_session.calls), 2)
        self.assertTrue(fake_session.calls[1]["url"].endswith("/topapi/message/corpconversation/asyncsend_v2"))

    def test_send_success_uses_asyncsend_v2_payload(self):
        adapter = DingTalkNotificationAdapter()
        fake_session = _FakeSession(
            [
                _FakeResponse(status_code=200, data={"accessToken": "token-1"}),
                _FakeResponse(status_code=200, data={"errcode": 0, "task_id": 123}),
            ]
        )
        with patch("backend.services.notification.dingtalk_adapter.requests.Session", return_value=fake_session):
            adapter.send(
                channel=self._channel(
                    {
                        "app_key": "key",
                        "app_secret": "sec",
                        "agent_id": "4432005762",
                        "api_base": "https://api.dingtalk.com",
                        "oapi_base": "https://oapi.dingtalk.com",
                        "timeout_seconds": 15,
                        "recipient_map": {"u1": "ding-u1"},
                    }
                ),
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1", "filename": "spec.pdf", "current_step_name": "QA"},
                recipient=self._recipient("ding-user-001"),
            )

        self.assertEqual(len(fake_session.calls), 2)
        access_call = fake_session.calls[0]
        send_call = fake_session.calls[1]

        self.assertTrue(access_call["url"].endswith("/v1.0/oauth2/accessToken"))
        self.assertEqual(access_call["json"], {"appKey": "key", "appSecret": "sec"})
        self.assertEqual(access_call["timeout"], 15)

        self.assertTrue(send_call["url"].endswith("/topapi/message/corpconversation/asyncsend_v2"))
        self.assertEqual(send_call["params"], {"access_token": "token-1"})
        self.assertEqual(send_call["json"]["agent_id"], 4432005762)
        self.assertEqual(send_call["json"]["userid_list"], "ding-user-001")
        self.assertEqual(send_call["json"]["msg"]["msgtype"], "text")
        self.assertIn("[RagflowAuth] review_todo_approval", send_call["json"]["msg"]["text"]["content"])
        self.assertEqual(send_call["timeout"], 15)

    def test_operation_approval_todo_message_uses_business_copy(self):
        message = DingTalkNotificationAdapter._message(
            event_type="operation_approval_todo",
            payload=self._approval_payload(),
            recipient={"user_id": "u2", "username": "jiazeyu"},
        )

        self.assertIn("您在知识库有一条上传信息需要审批。", message)
        self.assertIn("审批对象：ICE", message)
        self.assertIn("当前步骤：第 1 层", message)
        self.assertIn("申请单号：req-1", message)
        self.assertNotIn('"approval_target"', message)
        self.assertNotIn("recipient=", message)
        self.assertNotIn("[RagflowAuth]", message)
        self.assertNotIn("审批入口：", message)

    def test_operation_approval_messages_render_expected_operation_labels(self):
        cases = [
            (
                "operation_approval_todo",
                "knowledge_file_delete",
                "您在知识库有一条删除信息需要审批。",
            ),
            (
                "operation_approval_submitted",
                "knowledge_base_create",
                "您的新建知识库申请已提交审批。",
            ),
            (
                "operation_approval_rejected",
                "knowledge_base_delete",
                "您的删除知识库申请已被驳回。",
            ),
            (
                "operation_approval_withdrawn",
                "knowledge_file_upload",
                "您的上传申请已撤回。",
            ),
            (
                "operation_approval_executed",
                "knowledge_file_upload",
                "您的上传申请已审批通过并执行完成。",
            ),
            (
                "operation_approval_execution_failed",
                "knowledge_file_upload",
                "您的上传申请审批通过，但执行失败。",
            ),
        ]

        for event_type, operation_type, expected_line in cases:
            with self.subTest(event_type=event_type, operation_type=operation_type):
                message = DingTalkNotificationAdapter._message(
                    event_type=event_type,
                    payload=self._approval_payload(operation_type=operation_type),
                    recipient=None,
                )
                self.assertIn(expected_line, message)
